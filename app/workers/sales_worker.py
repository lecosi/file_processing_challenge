import time
import os
import logging

from azure.storage.queue import QueueClient
from azure.storage.blob import BlobServiceClient

from app.core.database import SessionLocal
from app.models.jobs import JobStatusModel
from app.repositories.sales_repository import SalesRepository
from app.services.processor_service import ProcessorService
from app.core.azure.client import AzureClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def stream_blob_lines(blob_client):
    """Stream a blob line by line without loading the entire file into memory."""
    stream = blob_client.download_blob()
    buffer = ""
    for chunk in stream.chunks():
        buffer += chunk.decode("utf-8")
        lines = buffer.split("\n")
        for line in lines[:-1]:
            if line.strip():
                yield line
        buffer = lines[-1]
    if buffer.strip():
        yield buffer


def process_message(msg, db, queue_client, blob_service_client, azure_client):
    """Handle a single queue message: parse, update job status, process CSV, finalize."""
    content_parts = msg.content.split("|")
    if len(content_parts) != 2:
        logger.warning("Malformed message received, deleting it: '%s'", msg.content)
        queue_client.delete_message(msg)
        return

    job_id, blob_name = content_parts
    logger.info("Processing job_id='%s' | blob='%s'", job_id, blob_name)

    job_record = db.query(JobStatusModel).filter(JobStatusModel.job_id == job_id).first()
    if not job_record:
        logger.warning("No job record found for job_id='%s'. Skipping.", job_id)
        queue_client.delete_message(msg)
        return

    job_record.status = "PROCESSING"
    db.commit()
    logger.debug("Job '%s' status set to PROCESSING.", job_id)

    blob_client = blob_service_client.get_blob_client(container="sales-files", blob=blob_name)
    lines_iterable = stream_blob_lines(blob_client)

    repository = SalesRepository(db)
    service = ProcessorService(repository)
    service.process_csv_stream(lines_iterable)

    azure_client.move_blob(blob_name, "processed")
    logger.info("Blob '%s' moved to 'processed' container.", blob_name)

    job_record.status = "COMPLETED"
    db.commit()

    queue_client.delete_message(msg)
    logger.info("Job '%s' completed successfully.", job_id)


def run_worker():
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    queue_name = "process-sales-queue"

    azure_client = AzureClient()
    queue_client = QueueClient.from_connection_string(connection_string, queue_name)
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    logger.info("Worker started. Listening for messages on queue '%s'...", queue_name)

    while True:
        messages = queue_client.receive_messages(messages_per_page=1, visibility_timeout=300)

        for msg in messages:
            db = SessionLocal()
            try:
                process_message(msg, db, queue_client, blob_service_client, azure_client)
            except Exception as e:
                logger.error("Unhandled error processing message '%s': %s", msg.content, e, exc_info=True)
                db.rollback()
                
                try:
                    job_id = msg.content.split("|")[0]
                    job_record = db.query(JobStatusModel).filter(JobStatusModel.job_id == job_id).first()
                    if job_record:
                        job_record.status = "FAILED"
                        db.commit()
                        logger.info("Job '%s' marked as FAILED.", job_id)
                except Exception as inner_e:
                    logger.error("Failed to update job status to FAILED: %s", inner_e, exc_info=True)
            finally:
                db.close()
                logger.debug("Database session closed.")

        time.sleep(5)


if __name__ == "__main__":
    run_worker()