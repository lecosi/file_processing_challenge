import logging
import os
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueClient
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class AzureClient:
    def __init__(self):
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.blob_container = "sales-files"
        self.queue_name = "process-sales-queue"
        self._blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
        self._queue_client = QueueClient.from_connection_string(self.connection_string, self.queue_name)
        self._check_resources_exist()

    def _check_resources_exist(self):
        try:
            container_client = self._blob_service_client.get_container_client(self.blob_container)
            if not container_client.exists():
                logger.info(f"Container {self.blob_container} does not exist. Creating...")
                container_client.create_container()
                logger.info(f"✅ Created container {self.blob_container}")
            else:
                logger.debug(f"Container {self.blob_container} already exists.")

            try:
                self._queue_client.create_queue()
                logger.info(f"✅ Created queue {self.queue_name}")
            except Exception:
                logger.debug(f"Queue {self.queue_name} already exists or there was a conflict during creation.")
        except Exception as e:
            logger.warning(f"⚠️ Note: Resources could not be automatically created: {e}")

    def upload_blob(self, file_content, blob_name: str):
        logger.info(f"Starting blob upload: {blob_name} in container {self.blob_container}")
        try:
            blob_client = self._blob_service_client.get_blob_client(
                container=self.blob_container, blob=blob_name
            )
            blob_client.upload_blob(file_content, overwrite=True)
            logger.info(f"✅ Blob {blob_name} uploaded successfully. URL: {blob_client.url}")
            return blob_client.url
        except Exception as e:
            logger.error(f"❌ Error uploading blob {blob_name}: {e}")
            raise

    def move_blob(self, blob_name: str, target_folder: str):
        logger.info(f"Moving blob {blob_name} to {target_folder}/")
        try:
            target_blob = f"{target_folder}/{blob_name}"
            source_client = self._blob_service_client.get_blob_client(self.blob_container, blob_name)
            destination_client = self._blob_service_client.get_blob_client(self.blob_container, target_blob)

            destination_client.start_copy_from_url(source_client.url)
            source_client.delete_blob()

            logger.info(f"✅ Blob moved successfully to destination: {target_blob}")
            return target_blob
        except Exception as e:
            logger.error(f"❌ Error moving blob {blob_name}: {e}")
            raise

    def send_message_to_queue(self, message: str):
        logger.info(f"Sending message to queue '{self.queue_name}'")
        try:
            self._queue_client.send_message(message)
            logger.info("✅ Message sent successfully to the queue.")
        except Exception as e:
            logger.error(f"❌ Error sending message to queue {self.queue_name}: {e}")
            raise