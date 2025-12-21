import logging
import json
from typing import List, Dict, Any, Union, Tuple
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
        top_k: int = config.RERANK_TOP_K,
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

        system_prompt = """You are a Senior Legal Expert AI specialized in Vietnamese Traffic Law (Luật Giao thông đường bộ Việt Nam). 
Your task is to rerank retrieved legal documents based on their relevance and legal validity regarding a user's natural language query.

### 1. TASK DEFINITION
- **Input:** A user query (often colloquial/informal) and a list of candidate legal documents (formal language).
- **Goal:** Assign a relevance score (0.0 to 10.0) to each document.
- **Critical Requirement:** You must bridge the gap between "Colloquial User Intent" and "Formal Legal Terminology" (Semantic Matching).
- **Temporal Priority:** Vietnamese Traffic Law changes frequently. If two documents cover the exact same violation, **the document with the more recent 'Year' MUST score higher** (e.g., Decree 123/2021 supersedes parts of Decree 100/2019).

### 2. SCORING RUBRIC (Total: 10 Points)

**A. Semantic Relevance & Intent Match (Max 5.0 points)**
- **5 pts:** Document identifies the *exact* violation mapped from the query. (e.g., Query: "vượt đèn đỏ" -> Doc: "không chấp hành hiệu lệnh của đèn tín hiệu giao thông"). The penalty/fine is explicitly visible.
- **3 pts:** Document covers the correct category of violation but lacks specific detail or is a general definition without sanctions.
- **1 pts:** Vaguely related to the topic (e.g., query about 'speeding', doc about 'lane usage').
- **0 pts:** Completely irrelevant.

**B. Contextual Accuracy (Max 3.0 points)**
- **3 pts:** Perfect match for **Vehicle Type** (Car vs. Motorbike vs. Truck) and **Subject** (Driver vs. Owner). If the query not specifies a vehicle type, all the types mentioned in the document are acceptable.
    * Note: "Xe máy" = "Xe mô tô, xe gắn máy". "Ô tô" = "Xe ô tô".
- **1 pts:** Matches the violation behavior but for the wrong vehicle type (e.g., Query is about Cars, Doc describes penalty for Motorbikes).
- **0 pts:** Wrong context entirely.

**C. Temporal Validity & Completeness (Max 2.0 points)**
- **2 pts:** The document is the **most recent** regulation available in the list for this specific issue (Check 'Year' field). It provides a concrete sanction/fine.
- **1 pts:** Relevant and correct, but there is another document in the list covering the same issue with a *later* Year. Or the document is older (e.g., Year < 2019) but still potentially valid.
- **0 pts:** Old/Superseded regulation that contradicts newer documents in the list.
* Note: This year is 2025, so prefer documents from 2024 than 2021 than 2019.
### 3. CHAIN OF THOUGHT (Internal Reasoning Process)
Before outputting JSON, perform these steps silently:
1.  **Analyze Query:** Identify the core intent (Violation), the Subject (who), and the Object (Vehicle type).
2.  **Semantic Translation:** Translate user slang to legal terms (e.g., "kẹp 3" -> "chở quá số người quy định", "say rượu" -> "nồng độ cồn").
3.  **Evaluate Each Document:**
    - Does the content match the translated legal term?
    - Does the vehicle type match?
    - **Compare Years:** Group documents by topic. For the same topic, check which ID has the highest Year. Boost that ID's score.
4.  **Calculate Final Score:** Sum A + B + C.

### 4. OUTPUT FORMAT
Return strictly a JSON object. No markdown, no explanation.
Format:
{
    "reason": "Explanation of your reasoning process and how scores were assigned.",
    "id_0": <float_score>,
    "id_1": <float_score>,
    ...
}
"""

        user_prompt = f"""User Query: "{query}"

Candidate Documents:
{docs_content}

Perform the analysis and return the JSON scores."""

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