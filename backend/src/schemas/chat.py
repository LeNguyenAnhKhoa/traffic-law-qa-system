from pydantic import BaseModel
from typing import List, Optional


class ChatHistory(BaseModel):
    query: str
    response: str


class ChatRequest(BaseModel):
    query: str
    chat_history: Optional[List[ChatHistory]] = []
    user_id: str


class ChatResponse(BaseModel):
    answer: str
    sources: Optional[List[dict]] = []
