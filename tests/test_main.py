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
    # Check for the title text, which is less brittle than a full tag with classes
    assert "Content Intelligence Platform" in response.text

async def test_upload_and_process_video(client: AsyncClient, mocker):
    """
    Tests that the /upload endpoint creates a task and returns a task_id.
    """
    # Mock the service calls made by the endpoint
    mock_create_task = mocker.patch("src.services.supabase_client.create_task", return_value=str(uuid.uuid4()))
    # We don't need to mock background_tasks.add_task as it works in tests,
    # but we do need to mock the pipeline it calls to prevent it from running.
    mocker.patch("src.analysis_pipeline.run_full_pipeline")

    files = {'file': ("test.mp4", b"content", 'video/mp4')}
    data = {'prompt': 'This is a test prompt.'}

    response = await client.post("/upload", files=files, data=data)

    # Assert the endpoint responds correctly
    assert response.status_code == 202 # Accepted
    json_response = response.json()
    assert "task_id" in json_response
    assert isinstance(json_response["task_id"], str)

    # Assert that our mock for creating a task was called
    mock_create_task.assert_called_once()


async def test_upload_invalid_file_type(client: AsyncClient):
    """Tests that uploading a non-mp4 file returns a 400 error."""
    files = {'file': ("test.txt", b"content", 'text/plain')}
    data = {'prompt': 'A prompt.'}

    response = await client.post("/upload", files=files, data=data)

    assert response.status_code == 400
    assert "Only .mp4 files are allowed" in response.json()['detail']

async def test_get_task_status(client: AsyncClient, mocker):
    """
    Tests the /status/{task_id} endpoint.
    """
    task_id = str(uuid.uuid4())
    mock_status = {"status": "rendering", "final_url": None}

    # Mock the supabase client function that this endpoint calls
    mocker.patch("src.services.supabase_client.get_task_status", return_value=mock_status)

    response = await client.get(f"/status/{task_id}")

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["status"] == "rendering"
    assert json_response["final_url"] is None
