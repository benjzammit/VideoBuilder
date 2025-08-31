import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from src.main import app
import uuid

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def client():
    """Async client fixture for testing."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

async def test_read_main(client: AsyncClient):
    """Tests if the root endpoint returns the HTML page."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "Content Intelligence Platform" in response.text

async def test_upload_video_endpoint(client: AsyncClient, mocker):
    """Tests the /upload endpoint for video ingestion."""
    mock_create_task = mocker.patch("src.services.supabase_client.create_task", return_value=str(uuid.uuid4()))
    mock_add_task = mocker.patch("fastapi.BackgroundTasks.add_task")

    files = {'file': ("test.mp4", b"content", 'video/mp4')}
    response = await client.post("/upload", files=files)

    assert response.status_code == 202
    assert "task_id" in response.json()
    mock_create_task.assert_called_once()
    mock_add_task.assert_called_once()

async def test_create_video_endpoint(client: AsyncClient, mocker):
    """Tests the /create endpoint for video generation."""
    mock_create_task = mocker.patch("src.services.supabase_client.create_task", return_value=str(uuid.uuid4()))
    mock_add_task = mocker.patch("fastapi.BackgroundTasks.add_task")

    request_data = {"prompt": "A test prompt"}
    response = await client.post("/create", json=request_data)

    assert response.status_code == 202
    assert "task_id" in response.json()
    mock_create_task.assert_called_once()
    mock_add_task.assert_called_once()

async def test_get_task_status_endpoint(client: AsyncClient, mocker):
    """Tests the /status/{task_id} endpoint."""
    task_id = str(uuid.uuid4())
    mock_status = {"status": "complete", "final_url": "http://video.url"}
    mocker.patch("src.services.supabase_client.get_task_status", return_value=mock_status)

    response = await client.get(f"/status/{task_id}")

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["status"] == "complete"
    assert json_response["final_url"] == "http://video.url"
