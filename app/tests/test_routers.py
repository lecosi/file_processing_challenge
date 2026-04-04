import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.core.database import get_db

client = TestClient(app)

def override_get_db():
    db = MagicMock()
    yield db

app.dependency_overrides[get_db] = override_get_db

def test_upload_sales_file_invalid_extension():
    """Test uploading a file that is not a CSV."""
    response = client.post(
        "/api/v1/upload",
        files={"file": ("data.json", b'{"key": "value"}', "application/json")}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "File must be CSV"}

@patch("app.api.routers.azure_client.upload_blob")
@patch("app.api.routers.azure_client.send_message_to_queue")
def test_upload_sales_file_success(mock_send_message, mock_upload_blob):
    """Test successful CSV file upload."""
    mock_upload_blob.return_value = None
    mock_send_message.return_value = None
    
    response = client.post(
        "/api/v1/upload",
        files={"file": ("data.csv", b"col1,col2\n1,2", "text/csv")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "PENDING"
    
    mock_upload_blob.assert_called_once()
    mock_send_message.assert_called_once()

@patch("app.api.routers.azure_client.upload_blob")
def test_upload_sales_file_exception(mock_upload_blob):
    """Test server error handling when Azure/DB operations fail."""
    mock_upload_blob.side_effect = Exception("Mocked exception")
    
    response = client.post(
        "/api/v1/upload",
        files={"file": ("data.csv", b"col1,col2\n1,2", "text/csv")}
    )
    
    assert response.status_code == 500
    assert response.json() == {"detail": "Mocked exception"}
