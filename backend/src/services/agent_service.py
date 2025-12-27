import logging
import json
import asyncio
from typing import List, Dict, Any, AsyncGenerator, Annotated, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, BaseMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from src.config import settings
from src.services.qdrant_service import qdrant_service
from src.services.reranker_service import reranker_service
from src.utils.prompt_manager import prompt_manager

logger = logging.getLogger(__name__)


@tool
def search_traffic_law_db(query: str) -> str:
    """
    Search for information in the Vietnamese traffic law database.
    Use this tool when the user asks about:
    - Traffic violation fines (alcohol level, running red lights, speeding, ...)
    - Regulations on driver's licenses, vehicle registration
    - Road traffic rules
    - Decrees 100/2019, 123/2021, 168/2024 on traffic violation penalties
    
    Args:
        query: Question or search keywords about traffic law
        
    Returns:
        Relevant documents from the traffic law database
    """
    logger.info(f"Searching traffic law DB for: {query}")
    search_results = qdrant_service.hybrid_search(query, limit=settings.HYBRID_SEARCH_TOP_K)
    
    if not search_results:
        return "No relevant documents found in the database."
    
    return json.dumps(search_results, ensure_ascii=False)


class AgentState(TypedDict):
    """State definition for the LangGraph agent."""
    messages: Annotated[list, add_messages]
    search_results: List[Dict[str, Any]]
    reranked_docs: List[Dict[str, Any]]
    tool_calls_info: List[Dict[str, Any]]
    last_tool_call_id: Optional[str]


class AgentService:
    def __init__(self):
        # Initialize LLM with tool calling capability
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
            streaming=True,
        )
        
        # Define tools
        self.tools = [search_traffic_law_db]
        
        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Build the agent graph
        self.graph = self._build_graph()
        
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph agent."""
        
        # Create the graph
        graph_builder = StateGraph(AgentState)
        
        # Add nodes
        graph_builder.add_node("agent", self._agent_node)
        graph_builder.add_node("tools", self._tool_node)
        graph_builder.add_node("rerank", self._rerank_node)
        
        # Add edges
        graph_builder.add_edge(START, "agent")
        graph_builder.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "tools": "tools",
                "end": END
            }
        )
        graph_builder.add_edge("tools", "rerank")
        graph_builder.add_edge("rerank", "agent")
        
        return graph_builder.compile()
    
    async def _agent_node(self, state: AgentState) -> dict:
        """Agent node that decides whether to call tools or respond."""
        messages = state["messages"]
        response = await self.llm_with_tools.ainvoke(messages)
        return {"messages": [response]}
    
    async def _tool_node(self, state: AgentState) -> dict:
        """Execute tools and store results."""
        messages = state["messages"]
        last_message = messages[-1]
        
        tool_calls_info = list(state.get("tool_calls_info", []))
        search_results = []
        tool_messages = []
        last_tool_call_id = None
        
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_call_id = tool_call["id"]
                
                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                
                # Record tool call info
                tool_info = {
                    "name": tool_name,
                    "args": tool_args,
                    "content": "Processing..."
                }
                tool_calls_info.append(tool_info)
                
                # Execute the tool
                if tool_name == "search_traffic_law_db":
                    result = search_traffic_law_db.invoke(tool_args)
                    try:
                        search_results = json.loads(result)
                    except json.JSONDecodeError:
                        search_results = []
                    
                    # Update tool info with result count
                    tool_info["content"] = f"Found {len(search_results)} results"
                    last_tool_call_id = tool_call_id
                    
                    # Don't add ToolMessage here, let rerank_node do it with formatted context
        
        return {
            "search_results": search_results,
            "tool_calls_info": tool_calls_info,
            "last_tool_call_id": last_tool_call_id
        }
    
    async def _rerank_node(self, state: AgentState) -> dict:
        """Rerank search results and return formatted context as ToolMessage."""
        search_results = state.get("search_results", [])
        tool_calls_info = list(state.get("tool_calls_info", []))
        last_tool_call_id = state.get("last_tool_call_id")
        
        if not search_results or not last_tool_call_id:
            logger.warning("No search results or tool_call_id found for reranking")
            # Still need to return a ToolMessage to satisfy the agent
            if last_tool_call_id:
                return {
                    "messages": [ToolMessage(
                        content="No relevant documents found.",
                        tool_call_id=last_tool_call_id
                    )],
                    "reranked_docs": [],
                    "tool_calls_info": tool_calls_info
                }
            return {"reranked_docs": [], "tool_calls_info": tool_calls_info}
        
        # Get the original query from messages (last HumanMessage)
        query = ""
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                query = msg.content
                break
        
        logger.info(f"Reranking {len(search_results)} results for query: {query[:50]}...")
        
        # Add rerank tool info
        rerank_info = {
            "name": "rerank",
            "args": {"model": settings.RERANKER_MODEL, "top_k": settings.RERANK_TOP_K},
            "content": "Processing..."
        }
        tool_calls_info.append(rerank_info)
        
        try:
            # Perform reranking
            reranked_docs = await reranker_service.rerank(
                query,
                search_results,
                settings.RERANK_TOP_K
            )
            
            # Update rerank info
            rerank_info["content"] = f"Selected top {len(reranked_docs)} most relevant documents"
            logger.info(f"Reranking completed: {len(reranked_docs)} documents selected")
            
            # Format context for the agent
            context = self._format_context(reranked_docs)
            
            # Create ToolMessage with formatted context
            tool_message = ToolMessage(
                content=f"Reference documents:\n{context}",
                tool_call_id=last_tool_call_id
            )
            
            return {
                "messages": [tool_message],
                "reranked_docs": reranked_docs,
                "tool_calls_info": tool_calls_info
            }
            
        except Exception as e:
            logger.error(f"Error during reranking: {e}", exc_info=True)
            rerank_info["content"] = f"Error during reranking: {str(e)}"
            
            # Return a ToolMessage with error info
            return {
                "messages": [ToolMessage(
                    content=f"Error processing documents: {str(e)}",
                    tool_call_id=last_tool_call_id
                )],
                "reranked_docs": [],
                "tool_calls_info": tool_calls_info
            }
    
    def _format_context(self, documents: List[Dict[str, Any]]) -> str:
        """Format retrieved documents into context string."""
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            payload = doc.get("payload", {})
            year = payload.get("year", "")
            article = payload.get("article", "")
            title = payload.get("title", "")
            content = payload.get("content", "")
            
            context_part = f"""
--- Document {i} ---
Year: {year}
Article: {article}
Title: {title}
Content: {content}
"""
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
    
    def _should_continue(self, state: AgentState) -> str:
        """Determine if we should continue to tools or end."""
        messages = state["messages"]
        last_message = messages[-1]
        
        # If there are tool calls, continue to tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        
        return "end"
    
    async def process_query(
        self,
        query: str,
        chat_history: List[Dict[str, str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process a user query through the Agent pipeline.
        
        The agent will:
        1. Decide if the query needs database search
        2. If yes: search -> rerank -> generate response with context
        3. If no: respond directly (greetings or refuse non-traffic questions)
        
        Args:
            query: User's question
            chat_history: Previous conversation history
            
        Yields:
            Streaming chunks with type indicators
        """
        try:
            # Build system prompt
            system_content = prompt_manager.render("agent_system_prompt.jinja2")
            
            # Build messages
            messages = [SystemMessage(content=system_content)]
            
            # Add chat history
            if chat_history:
                for item in chat_history:
                    messages.append(HumanMessage(content=item.get("query", "")))
                    messages.append(AIMessage(content=item.get("response", "")))
            
            # Add current query
            messages.append(HumanMessage(content=query))
            
            # Initialize state
            initial_state = {
                "messages": messages,
                "search_results": [],
                "reranked_docs": [],
                "tool_calls_info": [],
                "last_tool_call_id": None
            }
            
            # Track tool calls that we've already sent to frontend
            sent_tool_indices = set()
            full_answer = ""
            
            # Use astream to get state updates, then stream final response separately
            async for event in self.graph.astream(initial_state, stream_mode="updates"):
                # Each event is a dict with node name as key
                for node_name, output in event.items():
                    # Send tool call info to frontend
                    if isinstance(output, dict):
                        tool_calls_info = output.get("tool_calls_info", [])
                        for i, tool_info in enumerate(tool_calls_info):
                            if i not in sent_tool_indices:
                                sent_tool_indices.add(i)
                                yield json.dumps({"type": "tool_name", "content": tool_info["name"]}) + "\n"
                                yield json.dumps({"type": "tool_args", "content": tool_info["args"]}) + "\n"
                                yield json.dumps({"type": "tool_content", "content": tool_info["content"]}) + "\n"
                    
                    # Get final answer from agent node output
                    if node_name == "agent" and isinstance(output, dict):
                        new_messages = output.get("messages", [])
                        for msg in new_messages:
                            # Check if this is a final AI response (not a tool call)
                            if hasattr(msg, "content") and msg.content:
                                has_tool_calls = hasattr(msg, "tool_calls") and msg.tool_calls
                                if not has_tool_calls:
                                    full_answer = msg.content
            
            # Stream the final answer
            if full_answer:
                yield json.dumps({"type": "answer", "content": full_answer}) + "\n"
            else:
                logger.warning(f"No answer generated. sent_tool_indices: {sent_tool_indices}")
                yield json.dumps({
                    "type": "answer",
                    "content": "Sorry, an error occurred while processing your request."
                }) + "\n"
                
        except Exception as e:
            logger.error(f"Error in Agent pipeline: {e}", exc_info=True)
            yield json.dumps({
                "type": "answer",
                "content": f"Sorry, an error occurred: {str(e)}"
            }) + "\n"


# Singleton instance
agent_service = AgentService()
