from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SessionCreate(BaseModel):
    title: Optional[str] = None


class SessionUpdate(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = None


class SessionOut(BaseModel):
    id: int
    title: str
    channel: str
    created_at: datetime
    last_message_at: datetime
    agent_mode: bool
    is_favorited: bool
    model: str  # effective model for this session - override if set, else the deployment default

    class Config:
        from_attributes = True


class ModelInfo(BaseModel):
    id: str
    name: str
    family: str
    input_price: float  # USD per 1M input tokens
    output_price: float  # USD per 1M output tokens
    context_window: Optional[int] = None
    knowledge_cutoff: Optional[str] = None
    blurb: str
    recommended: bool = False


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    model: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str


class SearchRequest(BaseModel):
    query: str
