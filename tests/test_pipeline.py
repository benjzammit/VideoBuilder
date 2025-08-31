import json
import pytest
import uuid
from src.analysis_pipeline import parse_video_intelligence_results, run_full_pipeline

@pytest.fixture
def sample_api_response():
    """Loads the sample API response from the fixture file."""
    with open("tests/fixtures/sample_video_intelligence_response.json", "r") as f:
        return json.load(f)

def test_parse_video_intelligence_results(sample_api_response):
    """
    Tests that the parsing function correctly transforms the raw API response.
    """
    parsed_data = parse_video_intelligence_results(sample_api_response)

    assert "shots" in parsed_data and len(parsed_data["shots"]) == 3
    assert parsed_data["shots"][0]["start_time"] == 0.0
    assert parsed_data["shots"][0]["end_time"] == 4.5
    assert "cat" in parsed_data["labels"]
    assert parsed_data["transcript"].startswith("This is a test transcript")

@pytest.mark.asyncio
async def test_run_full_pipeline_success(mocker, sample_api_response):
    """
    Tests the success path of the main pipeline orchestrator.
    """
    # Mock all external service calls
    mocker.patch("src.services.gcs.upload_video_to_gcs", return_value="gs://fake-bucket/video.mp4")
    mocker.patch("src.services.video_intelligence_client.analyze_video_from_gcs", return_value=sample_api_response)
    mocker.patch("src.services.gemini_client.get_text_embedding", return_value=[0.1] * 768)
    mocker.patch("src.services.gemini_client.generate_production_plan", return_value={"clips": []})
    mocker.patch("src.services.supabase_client.save_video_metadata", return_value={"status": "success"})
    mocker.patch("src.services.zilliz_client.save_segment_embeddings", return_value={"status": "success"})
    mocker.patch("src.services.creatomate_client.start_video_render", return_value="mock-render-id")
    # Mock the polling status, make it succeed on the first try
    mocker.patch("src.services.creatomate_client.get_render_status", return_value={"status": "succeeded", "url": "http://final.video"})

    mock_update_task = mocker.patch("src.services.supabase_client.update_task")

    # Run the pipeline
    task_id = str(uuid.uuid4())
    await run_full_pipeline(task_id, b"file", "video.mp4", "a prompt")

    # Assert that the task status was updated at each stage
    assert mock_update_task.call_count >= 5
    assert any(call.args[1]['status'] == 'uploading' for call in mock_update_task.call_args_list)
    assert any(call.args[1]['status'] == 'analyzing' for call in mock_update_task.call_args_list)
    assert any(call.args[1]['status'] == 'storing_metadata' for call in mock_update_task.call_args_list)
    assert any(call.args[1]['status'] == 'rendering' for call in mock_update_task.call_args_list)
    # Final call should be to set status to 'complete'
    final_call_args = mock_update_task.call_args.args
    assert final_call_args[0] == task_id
    assert final_call_args[1]['status'] == 'complete'
    assert final_call_args[1]['final_url'] == "http://final.video"


@pytest.mark.asyncio
async def test_run_full_pipeline_failure(mocker):
    """
    Tests that the pipeline correctly handles a failure in one of the steps.
    """
    # Mock a service to fail
    mocker.patch("src.services.gcs.upload_video_to_gcs", return_value=None) # Simulate GCS upload failure
    mock_update_task = mocker.patch("src.services.supabase_client.update_task")

    # Run the pipeline
    task_id = str(uuid.uuid4())
    await run_full_pipeline(task_id, b"file", "video.mp4", "a prompt")

    # Assert that the final task status is 'failed'
    final_call_args = mock_update_task.call_args.args
    assert final_call_args[0] == task_id
    assert final_call_args[1]['status'] == 'failed'
    assert "error_message" in final_call_args[1]
    assert "Failed to upload to GCS" in final_call_args[1]['error_message']
