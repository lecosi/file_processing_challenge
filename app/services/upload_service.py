import logging
import uuid

from app.models.jobs import JobStatusModel
from app.repositories.jobs_repository import JobsRepository
from app.core.azure.client import AzureClient

logger = logging.getLogger(__name__)


class JobNotFoundException(Exception):
    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Job '{job_id}' not found.")


class UploadService:
    def __init__(self, jobs_repo: JobsRepository, azure_client: AzureClient):
        self.jobs_repo = jobs_repo
        self.azure_client = azure_client

    def upload_file(self, file, filename: str) -> JobStatusModel:
        """Create a job record, upload the blob, and enqueue the processing message."""
        job_id = str(uuid.uuid4())
        logger.info("Initiating upload for file '%s', assigned job_id='%s'.", filename, job_id)

        job = self.jobs_repo.create(job_id, "PENDING")

        blob_name = f"{job_id}_{filename}"
        self.azure_client.upload_blob(file, blob_name)

        message = f"{job_id}|{blob_name}"
        self.azure_client.send_message_to_queue(message)

        logger.info("File '%s' uploaded and enqueued successfully.", filename)
        return job

    def get_job_status(self, job_id: str) -> JobStatusModel:
        """Retrieve the current status of a job. Raises JobNotFoundException if not found."""
        logger.debug("Fetching status for job_id='%s'.", job_id)
        job = self.jobs_repo.get_by_id(job_id)
        if not job:
            logger.warning("Job not found: job_id='%s'.", job_id)
            raise JobNotFoundException(job_id)
        return job
