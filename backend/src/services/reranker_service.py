import logging
import json
from typing import List, Dict, Any
from openai import AsyncOpenAI
from src import config

logger = logging.getLogger(__name__)

RERANKER_MODEL = config.RERANKER_MODEL


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
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self._initialized = True
    
    async def rerank(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        top_k: int = config.RERANK_TOP_K
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents using the LLM model.
        
        Args:
            query: The search query
            documents: List of documents with 'payload' containing 'content'
            top_k: Number of top results to return
            
        Returns:
            Top-k reranked documents
        """
        if not documents:
            return []
        
        # Prepare documents for the prompt
        docs_content = ""
        for i, doc in enumerate(documents):
            content = doc.get("payload", {}).get("content", "")
            title = doc.get("payload", {}).get("title", "")
            # Truncate content if it's too long to avoid token limits, though gpt-4.1-mini should handle it.
            # Let's keep it reasonable, maybe first 500 chars for reranking context if needed, 
            # but user wants accuracy so full content is better. 
            # Assuming documents are chunks, they shouldn't be huge.
            docs_content += f"Document ID {i}:\nTitle: {title}\nContent: {content}\n\n"

        system_prompt = """You are an expert in Vietnamese traffic law. Your task is to evaluate and rank the relevance of the provided legal documents to the user's query.

IMPORTANT: Assume that all provided documents are 100% accurate and trustworthy. Your sole focus is to determine whether the document is helpful in answering the user's query.

Please follow this Chain of Thoughts process:
1. Analyze the user's query to understand the specific legal issue, vehicle type, and context.
2. For each document, analyze its content to see if it addresses the query.
3. Evaluate the document based on the following 4 criteria:
    - **Direct Relevance:** Does the document explicitly mention the violation, rule, or penalty asked in the query?
    - **Completeness:** Does the document provide a complete answer (e.g., fine levels, additional penalties) or just a partial one?
    - **Contextual Fit:** Does the document match the specific context of the query (e.g., correct vehicle type, road type, subject)?
    - **Utility:** Is this document useful for constructing a comprehensive and accurate answer for the user?
4. Assign a relevance score from 0 to 10 based on these criteria.
5. Output the results as a JSON object where keys are Document IDs (strings) and values are the scores (floats).
{
    "id_0": "score of id_0",
    "id_1": "score of id_1",
    ...
}
"""

        user_prompt = f"""Query: "{query}"

Documents List:
{docs_content}
"""

        try:
            response = await self.client.chat.completions.create(
                model=RERANKER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                # reasoning_effort="low",  # Not supported by gpt-4-mini
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            scores_map = json.loads(content)
            
            # Combine scores with documents
            scored_docs = []
            for i, doc in enumerate(documents):
                score = scores_map.get(str(i))
                if score is None:
                    score = scores_map.get(i, 0.0) # Try integer key just in case
                
                doc_with_score = doc.copy()
                doc_with_score["rerank_score"] = float(score)
                scored_docs.append(doc_with_score)
            
            # Sort by score descending
            scored_docs.sort(key=lambda x: x["rerank_score"], reverse=True)
            
            # Return top 10 documents with highest scores (no threshold)
            return scored_docs[:top_k]
            
        except Exception as e:
            logger.error(f"Error during LLM reranking: {e}")
            # Fallback: return original top_k documents with dummy score if LLM fails
            logger.info("Falling back to original order due to error.")
            fallback_docs = []
            for doc in documents[:top_k]:
                d = doc.copy()
                d["rerank_score"] = 0.0
                fallback_docs.append(d)
            return fallback_docs


# Singleton instance
reranker_service = RerankerService()

