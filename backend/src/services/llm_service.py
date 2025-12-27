import logging
from typing import List, Dict, Any, AsyncGenerator

from openai import AsyncOpenAI

from src.config import settings
from src.utils.prompt_manager import prompt_manager

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
    
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
--- Tài liệu {i} ---
Năm: {year}
Điều: {article}
Tiêu đề: {title}
Nội dung: {content}
"""
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
    
    async def generate_response_stream(
        self, 
        query: str, 
        documents: List[Dict[str, Any]],
        chat_history: List[Dict[str, str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response from LLM.
        
        Args:
            query: User's question
            documents: Retrieved and reranked documents
            chat_history: Previous chat history
            
        Yields:
            Chunks of the generated response
        """
        context = self._format_context(documents)
        
        # Render system prompt
        system_content = prompt_manager.render("system_prompt.jinja2")
        messages = [{"role": "system", "content": system_content}]
        
        # Add chat history if available
        if chat_history:
            for item in chat_history:
                messages.append({"role": "user", "content": item.get("query", "")})
                messages.append({"role": "assistant", "content": item.get("response", "")})
        
        # Render user prompt with context
        user_content = prompt_manager.render("user_prompt.jinja2", query=query, context=context)
        messages.append({"role": "user", "content": user_content})
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                temperature=0,
                seed=13,
                # reasoning_effort="low", 
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            yield f"Xin lỗi, đã có lỗi xảy ra khi xử lý yêu cầu của bạn: {str(e)}"


# Singleton instance
llm_service = LLMService()
