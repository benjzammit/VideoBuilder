import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from src.main import app
import os

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
    assert "<h1>Content Intelligence Platform</h1>" in response.text

async def test_upload_video_success(client: AsyncClient):
    """Tests successful video and prompt upload."""
    dummy_file_name = "test_video.mp4"
    uploaded_file_path = os.path.join("src/uploads", dummy_file_name)

    # Clean up file if it exists from a previous failed run
    if os.path.exists(uploaded_file_path):
        os.remove(uploaded_file_path)

    files = {'file': (dummy_file_name, b"file content", 'video/mp4')}
    data = {'prompt': 'This is a test prompt.'}

    response = await client.post("/upload/", files=files, data=data)

    assert response.status_code == 200
    json_response = response.json()
    assert json_response['filename'] == dummy_file_name
    assert json_response['prompt'] == 'This is a test prompt.'

    # Verify file was created
    assert os.path.exists(uploaded_file_path)

    # Clean up the created file
    os.remove(uploaded_file_path)

async def test_upload_invalid_file_type(client: AsyncClient):
    """Tests that uploading a non-mp4 file returns an error."""
    dummy_file_name = "test_document.txt"
    files = {'file': (dummy_file_name, b"some text", 'text/plain')}
    data = {'prompt': 'Another test prompt.'}

    response = await client.post("/upload/", files=files, data=data)

    assert response.status_code == 400
    json_response = response.json()
    assert "Only .mp4 files are allowed." in json_response['message']

    # Ensure the invalid file was not saved
    uploaded_file_path = os.path.join("src/uploads", dummy_file_name)
    assert not os.path.exists(uploaded_file_path)
