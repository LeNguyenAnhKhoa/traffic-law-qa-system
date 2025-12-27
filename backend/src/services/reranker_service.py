import logging
import json
from typing import List, Dict, Any, Union, Tuple
from openai import AsyncOpenAI
from src.config import settings
from src.utils.prompt_manager import prompt_manager

logger = logging.getLogger(__name__)

RERANKER_MODEL = settings.RERANKER_MODEL


class RerankerService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        logger.info(f"Initializing reranker with model: {RERANKER_MODEL}...")
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._initialized = True
    
    async def rerank(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        top_k: int = settings.RERANK_TOP_K,
        return_reasoning: bool = False
    ) -> Union[List[Dict[str, Any]], Tuple[List[Dict[str, Any]], str]]:
        """
        Rerank documents using the LLM model with advanced legal reasoning.
        """
        if not documents:
            if return_reasoning:
                return [], ""
            return []
        
        # Prepare documents for the prompt
        docs_content = ""
        for i, doc in enumerate(documents):
            payload = doc.get("payload", {})
            content = payload.get("content", "")
            title = payload.get("title", "")
            year = payload.get("year", "N/A")  # Ensure year is passed explicitly
            
            # Formatting document block
            docs_content += (
                f"--- Document ID {i} ---\n"
                f"Year: {year}\n"
                f"Title: {title}\n"
                f"Content: {content}\n\n"
            )

        system_prompt = prompt_manager.render("reranker_system_prompt.jinja2")

        user_prompt = prompt_manager.render(
            "reranker_user_prompt.jinja2",
            query=query,
            docs_content=docs_content
        )

        try:
            response = await self.client.chat.completions.create(
                model=RERANKER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            scores_map = json.loads(content)
            reasoning = scores_map.get("reason", "")
            
            # Combine scores with documents
            scored_docs = []
            for i, doc in enumerate(documents):
                # Handle keys: "0", 0, or "id_0"
                score = scores_map.get(str(i))
                if score is None:
                    score = scores_map.get(i)
                if score is None:
                    score = scores_map.get(f"id_{i}", 0.0)
                
                doc_with_score = doc.copy()
                doc_with_score["rerank_score"] = float(score)
                scored_docs.append(doc_with_score)
            
            # Sort by score descending
            scored_docs.sort(key=lambda x: x["rerank_score"], reverse=True)
            
            if return_reasoning:
                return scored_docs[:top_k], reasoning
            return scored_docs[:top_k]
            
        except Exception as e:
            logger.error(f"Error during LLM reranking: {e}")
            # Fallback: return original top_k documents with dummy score
            logger.info("Falling back to original order due to error.")
            fallback_docs = []
            for doc in documents[:top_k]:
                d = doc.copy()
                d["rerank_score"] = 0.0
                fallback_docs.append(d)
            
            if return_reasoning:
                return fallback_docs, f"Error during reranking: {str(e)}"
            return fallback_docs

# Singleton instance
reranker_service = RerankerService()