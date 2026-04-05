import pytest
from unittest.mock import MagicMock, patch, call

from app.workers.sales_worker import stream_blob_lines, process_message


def make_msg(content: str) -> MagicMock:
    """Build a fake Azure queue message."""
    msg = MagicMock()
    msg.content = content
    return msg

def make_job_record(job_id: str, status: str = "PENDING") -> MagicMock:
    """Build a fake JobStatusModel instance."""
    record = MagicMock()
    record.job_id = job_id
    record.status = status
    return record

class TestStreamBlobLines:
    def _make_blob_client(self, chunks: list[bytes]) -> MagicMock:
        stream = MagicMock()
        stream.chunks.return_value = iter(chunks)
        blob_client = MagicMock()
        blob_client.download_blob.return_value = stream
        return blob_client

    def test_single_chunk_yields_all_lines(self):
        blob_client = self._make_blob_client([b"header\nrow1\nrow2\n"])
        result = list(stream_blob_lines(blob_client))
        assert result == ["header", "row1", "row2"]

    def test_multiple_chunks_reassembles_lines(self):
        # Line split across two chunks
        blob_client = self._make_blob_client([b"hea", b"der\nrow1\n"])
        result = list(stream_blob_lines(blob_client))
        assert result == ["header", "row1"]

    def test_empty_lines_are_skipped(self):
        blob_client = self._make_blob_client([b"row1\n\n\nrow2\n"])
        result = list(stream_blob_lines(blob_client))
        assert result == ["row1", "row2"]

    def test_trailing_content_without_newline_is_yielded(self):
        blob_client = self._make_blob_client([b"row1\nrow2"])  # no trailing \n
        result = list(stream_blob_lines(blob_client))
        assert result == ["row1", "row2"]

    def test_empty_blob_yields_nothing(self):
        blob_client = self._make_blob_client([b""])
        result = list(stream_blob_lines(blob_client))
        assert result == []

class TestProcessMessageMalformed:
    def test_malformed_message_is_deleted_and_returns(self):
        msg = make_msg("only_one_part")
        db = MagicMock()
        queue_client = MagicMock()
        blob_service_client = MagicMock()
        azure_client = MagicMock()

        process_message(msg, db, queue_client, blob_service_client, azure_client)

        queue_client.delete_message.assert_called_once_with(msg)
        db.query.assert_not_called()

    def test_too_many_parts_treated_as_malformed(self):
        msg = make_msg("a|b|c")
        db = MagicMock()
        queue_client = MagicMock()

        process_message(msg, db, queue_client, MagicMock(), MagicMock())

        queue_client.delete_message.assert_called_once_with(msg)

class TestProcessMessageNoJobRecord:
    def test_missing_job_record_deletes_message_and_returns(self):
        msg = make_msg("job-123|file.csv")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        queue_client = MagicMock()

        process_message(msg, db, queue_client, MagicMock(), MagicMock())

        queue_client.delete_message.assert_called_once_with(msg)
        db.commit.assert_not_called()

class TestProcessMessageSuccess:
    @patch("app.workers.sales_worker.ProcessorService")
    @patch("app.workers.sales_worker.SalesRepository")
    @patch("app.workers.sales_worker.stream_blob_lines")
    def test_successful_processing_updates_status_and_deletes_message(
        self, mock_stream, mock_repo_cls, mock_service_cls
    ):
        job_id = "job-abc"
        blob_name = "job-abc_sales.csv"
        msg = make_msg(f"{job_id}|{blob_name}")

        job_record = make_job_record(job_id)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = job_record

        queue_client = MagicMock()
        blob_service_client = MagicMock()
        azure_client = MagicMock()

        mock_stream.return_value = iter(["header", "row1", "row2"])

        process_message(msg, db, queue_client, blob_service_client, azure_client)

        assert job_record.status == "COMPLETED"
        assert db.commit.call_count == 2  # once for PROCESSING, once for COMPLETED

        azure_client.move_blob.assert_called_once_with(blob_name, "processed")
        queue_client.delete_message.assert_called_once_with(msg)
        mock_service_cls.return_value.process_csv_stream.assert_called_once()

    @patch("app.workers.sales_worker.ProcessorService")
    @patch("app.workers.sales_worker.SalesRepository")
    @patch("app.workers.sales_worker.stream_blob_lines")
    def test_blob_client_created_with_correct_container_and_blob(
        self, mock_stream, mock_repo_cls, mock_service_cls
    ):
        job_id = "job-xyz"
        blob_name = "job-xyz_data.csv"
        msg = make_msg(f"{job_id}|{blob_name}")

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = make_job_record(job_id)

        blob_service_client = MagicMock()
        mock_stream.return_value = iter([])

        process_message(msg, db, MagicMock(), blob_service_client, MagicMock())

        blob_service_client.get_blob_client.assert_called_once_with(
            container="sales-files", blob=blob_name
        )

class TestProcessMessageError:
    @patch("app.workers.sales_worker.ProcessorService")
    @patch("app.workers.sales_worker.SalesRepository")
    @patch("app.workers.sales_worker.stream_blob_lines")
    def test_exception_in_csv_processing_propagates(
        self, mock_stream, mock_repo_cls, mock_service_cls
    ):
        msg = make_msg("job-fail|fail.csv")
        job_record = make_job_record("job-fail")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = job_record

        mock_service_cls.return_value.process_csv_stream.side_effect = RuntimeError("DB error")
        mock_stream.return_value = iter([])

        with pytest.raises(RuntimeError, match="DB error"):
            process_message(msg, db, MagicMock(), MagicMock(), MagicMock())
