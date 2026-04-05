import logging
from sqlalchemy.orm import Session
from app.models.jobs import JobStatusModel

logger = logging.getLogger(__name__)


class JobsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, job_id: str) -> JobStatusModel | None:
        logger.debug("Querying job record for job_id='%s'.", job_id)
        return (
            self.db.query(JobStatusModel)
            .filter(JobStatusModel.job_id == job_id)
            .first()
        )

    def create(self, job_id: str, status: str) -> JobStatusModel:
        logger.debug("Creating job record job_id='%s' with status='%s'.", job_id, status)
        job = JobStatusModel(job_id=job_id, status=status)
        self.db.add(job)
        self.db.commit()
        logger.info("Job record created: job_id='%s'.", job_id)
        return job
