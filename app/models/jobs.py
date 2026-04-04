from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class JobStatusModel(Base):
    __tablename__ = "job_status"
    job_id = Column(String, primary_key=True, index=True)
    status = Column(String, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
