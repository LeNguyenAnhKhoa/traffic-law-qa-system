from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.schemas.chat import ChatRequest
from src.services.agent_service import agent_service
from src.config import settings

router = APIRouter(
    prefix=f"/api/{settings.API_VERSION}/agent",
    tags=["Agent"]
)



@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat endpoint for traffic law Q&A.
    
    Uses LangChain Agent with Tool Calling:
    - Agent decides whether to search database or respond directly
    - For traffic law questions: Hybrid search -> Rerank -> Generate response
    - For greetings: Respond directly
    - For unrelated questions: Politely refuse
    
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
            agent_service.process_query(request.query, chat_history),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
