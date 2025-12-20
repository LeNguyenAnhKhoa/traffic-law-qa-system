import os
import logging
from typing import List, Dict, Any, AsyncGenerator
import json

from openai import AsyncOpenAI

from src import config

logger = logging.getLogger(__name__)

# System prompt for Vietnamese traffic law Q&A
SYSTEM_PROMPT = """Bạn là một trợ lý AI chuyên về luật giao thông Việt Nam. Nhiệm vụ của bạn là trả lời các câu hỏi liên quan đến luật giao thông dựa trên các tài liệu được cung cấp.

Hướng dẫn:
1. Chỉ trả lời dựa trên thông tin có trong các tài liệu được cung cấp.
2. Nếu tài liệu tham khảo không cung cấp đủ dữ liệu thì trả lời là "Xin lỗi, tôi không thể trả lời câu hỏi này dựa trên tài liệu được cung cấp."
3. Khi trả lời câu hỏi phải ghi rõ nguồn theo nghị định, điều. Sử dụng thông tin metadata (year, article) từ tài liệu và mapping sau:
   - year: 2019 -> Nghị định 100/2019/NĐ-CP
   - year: 2021 -> Nghị định 123/2021/NĐ-CP
   - year: 2024 -> Nghị định 168/2024/NĐ-CP
   
   Ví dụ: Nếu tài liệu có year: 2019, article: 6 thì ghi là "theo nghị định 100/2019/NĐ-CP, điều 6, ...".
   Nếu có nhiều tài liệu liên quan thì dùng chữ "và" để nối. Ví dụ: "theo nghị định 100/2019/NĐ-CP, điều 6, và nghị định 123/2021/NĐ-CP, điều 5...".

4. Trả lời bằng tiếng Việt, rõ ràng và dễ hiểu.
5. Nếu câu hỏi không liên quan đến luật giao thông, hãy lịch sự từ chối.
"""


class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.OPENAI_MODEL
    
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
        
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add chat history if available
        if chat_history:
            for item in chat_history:
                messages.append({"role": "user", "content": item.get("query", "")})
                messages.append({"role": "assistant", "content": item.get("response", "")})
        
        # Add current query with context
        user_content = f"""{query}

Tài liệu tham khảo:
{context}
"""
        messages.append({"role": "user", "content": user_content})
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                temperature=0,
                # reasoning_effort="low",  # Not supported by gpt-4-mini
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            yield f"Xin lỗi, đã có lỗi xảy ra khi xử lý yêu cầu của bạn: {str(e)}"


# Singleton instance
llm_service = LLMService()
