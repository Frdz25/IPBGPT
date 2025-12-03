from pydantic import BaseModel
from typing import List, Optional

class ThesisTitle(BaseModel):
    title: str
    number: int

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatQuery(BaseModel):
    query: str
    context: Optional[str] = None 
    chat_history: List[ChatMessage]
    session_id: Optional[str] = None