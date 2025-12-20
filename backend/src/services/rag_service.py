import logging
from typing import List, Dict, Any, AsyncGenerator
import json
import asyncio

from src.services.qdrant_service import qdrant_service
from src.services.reranker_service import reranker_service
from src.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self):
        self.qdrant = qdrant_service
        self.reranker = reranker_service
        self.llm = llm_service
    
    async def process_query(
        self, 
        query: str, 
        chat_history: List[Dict[str, str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process a user query through the RAG pipeline.
        
        Steps:
        1. Hybrid search to get 100 documents
        2. Rerank to get exactly top 10 documents with highest scores
        3. Generate response using LLM
        
        Args:
            query: User's question
            chat_history: Previous conversation history
            
        Yields:
            Streaming chunks with type indicators
        """
        try:
            # Step 1: Hybrid search
            logger.info(f"Processing query: {query}")
            yield json.dumps({"type": "tool_name", "content": "hybrid_search"}) + "\n"
            yield json.dumps({"type": "tool_args", "content": {"query": query, "limit": 100}}) + "\n"
            
            search_results = self.qdrant.hybrid_search(query, limit=100)
            
            yield json.dumps({
                "type": "tool_content", 
                "content": f"Tìm thấy {len(search_results)} kết quả"
            }) + "\n"
            
            # Step 2: Rerank
            yield json.dumps({"type": "tool_name", "content": "rerank"}) + "\n"
            yield json.dumps({"type": "tool_args", "content": {"model": "gpt-5.1", "top_k": 10}}) + "\n"
            
            # Run reranking (get top 10 with highest scores)
            reranked_docs = await self.reranker.rerank(
                query, 
                search_results, 
                10
            )
            
            # Format sources for display
            sources_info = []
            for doc in reranked_docs:
                payload = doc.get("payload", {})
                sources_info.append({
                    "article": payload.get("article", ""),
                    "title": payload.get("title", ""),
                    "score": doc.get("rerank_score", 0)
                })
            
            yield json.dumps({
                "type": "tool_content", 
                "content": f"Đã chọn top 10 tài liệu liên quan nhất"
            }) + "\n"
            
            # Step 3: Generate response
            full_answer = ""
            async for chunk in self.llm.generate_response_stream(
                query, 
                reranked_docs, 
                chat_history
            ):
                full_answer += chunk
                yield json.dumps({"type": "answer", "content": full_answer}) + "\n"
                
        except Exception as e:
            logger.error(f"Error in RAG pipeline: {e}")
            yield json.dumps({
                "type": "answer", 
                "content": f"Xin lỗi, đã có lỗi xảy ra: {str(e)}"
            }) + "\n"


# Singleton instance
rag_service = RAGService()
