import logging
from app.repositories.sales_repository import SalesRepository

logger = logging.getLogger(__name__)


class ProcessorService:
    def __init__(self, repository: SalesRepository):
        self.repository = repository

    def process_csv_stream(self, lines_iterable, chunk_size: int = 10000):
        try:
            header = next(lines_iterable)
            logger.debug("CSV header skipped: %s", header)
        except StopIteration:
            logger.warning("CSV stream is empty, nothing to process.")
            return

        chunk_buffer = ""
        count = 0
        total_rows = 0

        for line in lines_iterable:
            chunk_buffer += line + "\n"
            count += 1
            if count >= chunk_size:
                logger.info("Inserting chunk of %d rows (total so far: %d).", count, total_rows + count)
                self.repository.bulk_insert_sales_copy(chunk_buffer)
                total_rows += count
                chunk_buffer = ""
                count = 0

        if count > 0:
            logger.info("Inserting final chunk of %d rows (total: %d).", count, total_rows + count)
            self.repository.bulk_insert_sales_copy(chunk_buffer)
            total_rows += count

        logger.info("CSV processing complete. Total rows inserted: %d", total_rows)