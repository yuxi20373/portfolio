from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship

from ..database import Base


class ChatSession(Base):
    """
    One session = one continuous conversation (the scope of short-term memory).

    channel: "web" or "line" (more channels can be added later).
    external_user_id: the user id on that channel (e.g. LINE userId); empty for web.
    is_open: whether this is still considered "the same conversation". Channels
      without an explicit boundary (like LINE) use an inactivity timeout to
      decide when to start a new session automatically.

    memory_summary / summarized_up_to_message_id: rolling short-term-memory
      compaction (see app/agent/memory_manager.py). Older messages get folded
      into memory_summary instead of being resent verbatim on every turn, to
      keep per-turn input tokens down. Raw messages are never deleted - this
      only affects what gets sent to the LLM. (This is unrelated to the wiki
      knowledge base - there is no more automatic session -> wiki pipeline.)
    """

    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), default="New Conversation")
    channel = Column(String(20), default="web", index=True)
    external_user_id = Column(String(100), nullable=True, index=True)
    is_open = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_message_at = Column(DateTime, default=datetime.utcnow)

    memory_summary = Column(Text, nullable=True)
    summarized_up_to_message_id = Column(Integer, nullable=True)

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    role = Column(String(20))  # user / assistant / system
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Usage/cost tracking - only populated on assistant messages. Aggregated
    # across every underlying model call in the turn (a turn can involve more
    # than one LLM call when the agent uses tools), so this reflects the true
    # total cost of that turn even if it looks larger than a single reply.
    model = Column(String(100), nullable=True)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)

    session = relationship("ChatSession", back_populates="messages")
