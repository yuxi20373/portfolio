from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from ..database import Base


class BashCommand(Base):
    """One entry in the bash command reference dictionary (see
    routers/bash_reference.py) - a shared lookup table, same for every user,
    not personal data. Populated in bulk from whatever reference dataset the
    user provides (see backend/scripts/import_bash_commands.py), not created
    one at a time through the UI."""

    __tablename__ = "bash_commands"

    id = Column(Integer, primary_key=True)
    command = Column(String(200), nullable=False, unique=True, index=True)  # e.g. "grep", "chmod"
    description = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
