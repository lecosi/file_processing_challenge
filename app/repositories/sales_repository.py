import io
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SalesRepository:
    def __init__(self, db: Session):
        self.db = db

    def bulk_insert_sales_copy(self, raw_csv_chunk: str):
        try:
            buffer = io.StringIO(raw_csv_chunk)
            raw_conn = self.db.connection().connection
            with raw_conn.cursor() as cursor:
                cursor.copy_expert(
                    "COPY sales (date, product_id, quantity, price) FROM STDIN WITH CSV",
                    buffer
                )
            self.db.commit()
            logger.debug("Bulk insert committed successfully.")
        except Exception as e:
            self.db.rollback()
            logger.error("Bulk insert failed, transaction rolled back: %s", e, exc_info=True)
            raise