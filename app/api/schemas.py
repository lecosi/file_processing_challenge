from pydantic import BaseModel, Field
from datetime import date
from typing import Optional
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: Optional[str] = None

    class Config:
        from_attributes = True