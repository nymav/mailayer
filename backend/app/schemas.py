from typing import List, Optional
from pydantic import BaseModel, Field


class FullSyncRequest(BaseModel):
    days: int = Field(default=90, ge=0, le=3650)
    include_sent: bool = True


class FeedbackRequest(BaseModel):
    useful: Optional[bool] = None
    category_override: str = ""
    note: str = ""


class ReviewRequest(BaseModel):
    priority: str = "NORMAL"
    reason: str = ""


class ChatRequest(BaseModel):
    query: str = Field(min_length=2, max_length=3000)
    days: int = Field(default=90, ge=1, le=3650)


class ChatSource(BaseModel):
    message_id: int
    gmail_id: str
    subject: str
    sender_email: str
    received_at: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[ChatSource]
    tool: str
