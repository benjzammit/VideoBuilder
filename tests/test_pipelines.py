import json
import pytest
import uuid
from src.pipelines import parse_video_intelligence_results, run_analysis_pipeline, run_creation_pipeline

@pytest.fixture
def sample_api_response():
    """Loads the sample API response from the fixture file."""
    with open("tests/fixtures/sample_video_intelligence_response.json", "r") as f:
        return json.load(f)

def test_parse_video_intelligence_results(sample_api_response):
    """Tests that the parsing function correctly transforms the raw API response."""
    parsed_data = parse_video_intelligence_results(sample_api_response)
    assert len(parsed_data["shots"]) == 3
    assert "cat" in parsed_data["labels"]
    assert parsed_data["transcript"].startswith("This is a test transcript")

@pytest.mark.asyncio
async def test_run_analysis_pipeline_success(mocker, sample_api_response):
    """Tests the success path of the analysis pipeline."""
    # Mock all external service calls
    mocker.patch("src.services.gcs.upload_video_to_gcs", return_value="gs://fake-bucket/video.mp4")
    mocker.patch("src.services.video_intelligence_client.analyze_video_from_gcs", return_value=sample_api_response)
    mocker.patch("src.services.gemini_client.get_text_embedding", return_value=[0.1] * 768)
    mocker.patch("src.services.supabase_client.save_video_metadata")
    mocker.patch("src.services.supabase_client.save_video_segments")
    mocker.patch("src.services.zilliz_client.save_segment_embeddings", return_value=[101, 102, 103])

    # Mock the supabase client object itself to allow for chained call mocking
    mock_supabase_client = mocker.MagicMock()
    mocker.patch("src.services.supabase_client.supabase", new=mock_supabase_client)

    mock_update_task = mocker.patch("src.services.supabase_client.update_task")

    await run_analysis_pipeline(str(uuid.uuid4()), b"file", "video.mp4")

    assert mock_update_task.call_count >= 3
    assert mock_update_task.call_args.args[1]['status'] == 'complete'

@pytest.mark.asyncio
async def test_run_creation_pipeline_success(mocker):
    """Tests the success path of the creation pipeline."""
    mock_segments = [{"id": str(uuid.uuid4()), "videos": {"file_path": "gs://b/v.mp4"}, "start_time": 0, "end_time": 5}]
    mocker.patch("src.services.gemini_client.get_text_embedding", return_value=[0.1] * 768)
    mocker.patch("src.services.zilliz_client.search_similar_segments", return_value=["seg1"])
    mocker.patch("src.services.supabase_client.get_segments_by_zilliz_ids", return_value=mock_segments)
    mocker.patch("src.services.gemini_client.generate_production_plan", return_value={"title": "test", "clips": []})
    mocker.patch("src.services.creatomate_client.start_video_render", return_value="render-123")
    mocker.patch("src.services.creatomate_client.get_render_status", return_value={"status": "succeeded", "url": "http://final.video"})
    mock_update_task = mocker.patch("src.services.supabase_client.update_task")

    await run_creation_pipeline(str(uuid.uuid4()), "a prompt")
    assert mock_update_task.call_count >= 4
    assert mock_update_task.call_args.args[1]['status'] == 'complete'
    assert "final_url" in mock_update_task.call_args.args[1]
