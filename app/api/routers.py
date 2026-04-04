from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
import uuid
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.schemas import JobResponse, JobStatus
from app.models.jobs import JobStatusModel
from app.core.azure.client import AzureClient

router = APIRouter()
azure_client = AzureClient()


@router.post("/upload", response_model=JobResponse)
async def upload_sales_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be CSV")

    try:
        job_id = str(uuid.uuid4())
        new_job = JobStatusModel(job_id=job_id, status=JobStatus.PENDING)
        db.add(new_job)
        db.commit()
    
        blob_name = f"{job_id}_{file.filename}"
        azure_client.upload_blob(file.file, blob_name)
        message = f"{job_id}|{blob_name}"
        azure_client.send_message_to_queue(message)
        
        return JobResponse(job_id=job_id, status=JobStatus.PENDING)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
