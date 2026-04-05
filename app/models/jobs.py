from datetime import datetime
from sqlalchemy import Column, String, DateTime
from app.models.base import Base


class JobStatusModel(Base):
    __tablename__ = "job_status"
    job_id = Column(String, primary_key=True, index=True)
    status = Column(String, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
