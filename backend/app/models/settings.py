from datetime import datetime
from sqlalchemy import Column, DateTime, String, Text
from app.db.base import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key         = Column(String(100), primary_key=True)
    value       = Column(Text, nullable=True)
    description = Column(String(255), nullable=True)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
