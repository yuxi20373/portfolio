from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship

from ..config import settings
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

    agent_mode: False (default) until the user sends "/agent" in this
      session. False = every turn is a plain, single-message call to the
      chat model (app/agent/simple_chat.py) - no history, no tools. True =
      turns go through the deep agent (app/agent/runner.py), which gets the
      full conversation history/memory summary and can use tools. See
      app/services/chat/chat_service.py:process_chat_message.

    experimental_agent: None (default) unless the user sends a command like
      "/da-subagent" - names which experimental deep-agent implementation
      (see app/agent/EXPERIMENTAL_AGENTS in chat_service.py) this session's
      turns get routed through instead of the agent_mode/simple_chat split
      above. Kept as a separate string field (not a new agent_mode value)
      so trying an experimental implementation never touches the original
      agent_mode code path - "/normal" clears this back to None too.

    da_subagent_files: JSON-encoded virtual filesystem carried across turns
      for the "da_subagent" experimental implementation specifically (its
      worker subagent writes long output to /results/ - see
      app/agent/da_subagent/). Unused by every other mode.

    model_name: which OpenAI model (see app/agent/model_catalog.py) this
      session's turns are sent to. None = fall back to the deployment
      default (settings.openai_model) - see the `model` property below,
      which is what the API actually exposes (SessionOut.model).

    user_id: which logged-in account this session belongs to (see
      app/models/auth.py) - nullable because the LINE channel has no web
      login concept of its own (see external_user_id instead) and its
      sessions are never attributed to a User row. Web-channel sessions
      always have one; see app/auth.py:get_current_user and
      app/routers/chat.py.
    """

    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), default="New Conversation")
    channel = Column(String(20), default="web", index=True)
    external_user_id = Column(String(100), nullable=True, index=True)
    is_open = Column(Boolean, default=True)
    is_favorited = Column(Boolean, default=False, index=True)
    agent_mode = Column(Boolean, default=False)
    experimental_agent = Column(String(30), nullable=True)
    da_subagent_files = Column(Text, nullable=True)
    model_name = Column(String(50), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_message_at = Column(DateTime, default=datetime.utcnow)

    memory_summary = Column(Text, nullable=True)
    summarized_up_to_message_id = Column(Integer, nullable=True)

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

    @property
    def model(self) -> str:
        """The model this session's turns actually get sent to - its own
        override if set, otherwise the deployment default."""
        return self.model_name or settings.openai_model


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
