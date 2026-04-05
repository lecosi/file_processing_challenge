import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.schemas import JobResponse
from app.core.azure.client import AzureClient
from app.repositories.jobs_repository import JobsRepository
from app.services.upload_service import UploadService, JobNotFoundException

router = APIRouter()
logger = logging.getLogger(__name__)

azure_client = AzureClient()


def get_upload_service(db: Session = Depends(get_db)) -> UploadService:
    return UploadService(jobs_repo=JobsRepository(db), azure_client=azure_client)


@router.post("/upload", response_model=JobResponse, status_code=202)
async def upload_sales_file(
    file: UploadFile = File(...),
    service: UploadService = Depends(get_upload_service),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be CSV")

    try:
        job = service.upload_file(file.file, file.filename)
        return JobResponse.model_validate(job)
    except Exception as e:
        logger.error("Unexpected error during file upload: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    service: UploadService = Depends(get_upload_service),
):
    try:
        job = service.get_job_status(job_id)
        return JobResponse.model_validate(job)
    except JobNotFoundException:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")


@router.get("/health", status_code=200, tags=["health"])
async def health_check():
    return {"status": "ok"}