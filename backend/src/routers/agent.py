from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.schemas.chat import ChatRequest
from src.services.rag_service import rag_service
from src import config

router = APIRouter(
    prefix=f"/api/{config.API_VERSION}/agent",
    tags=["Agent"]
)


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat endpoint for traffic law Q&A.
    
    Uses RAG pipeline:
    1. Hybrid search (40 documents)
    2. Rerank to top 5
    3. LLM generates response
    
    Returns streaming response.
    """
    try:
        # Convert chat history to the expected format
        chat_history = []
        if request.chat_history:
            for item in request.chat_history:
                chat_history.append({
                    "query": item.query,
                    "response": item.response
                })
        
        return StreamingResponse(
            rag_service.process_query(request.query, chat_history),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
