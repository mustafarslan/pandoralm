from datetime import datetime
from sqlalchemy import String, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
import uuid

from app.core.database import Base

class MemorySummary(Base):
    """
    Memory Summary Model.
    Stores consolidated summaries of user memories for specific time ranges.
    """
    __tablename__ = "memory_summaries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Time range this summary covers
    date_range_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    date_range_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    metadata_json: Mapped[dict] = mapped_column(JSON, default={})

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "summary_text": self.summary_text,
            "date_range_start": self.date_range_start.isoformat(),
            "date_range_end": self.date_range_end.isoformat(),
            "created_at": self.created_at.isoformat(),
            "metadata_json": self.metadata_json
        }
