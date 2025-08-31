import json
import pytest
from src.analysis_pipeline import parse_video_intelligence_results, start_analysis_pipeline

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

    # Check top-level keys
    assert "shots" in parsed_data
    assert "labels" in parsed_data
    assert "transcript" in parsed_data
    assert "raw_json" in parsed_data

    # Check content correctness
    assert len(parsed_data["shots"]) == 3
    assert parsed_data["shots"][0]["start_time"] == 0.0
    assert parsed_data["shots"][0]["end_time"] == 4.5
    assert "cat" in parsed_data["labels"]
    assert "sofa" in parsed_data["labels"]
    assert parsed_data["transcript"].startswith("This is a test transcript")

@pytest.mark.asyncio
async def test_start_analysis_pipeline_orchestration(mocker):
    """
    Tests that the main pipeline function calls its dependencies correctly.
    """
    # Mock the dependencies of the pipeline
    mock_parsed_data = {"shots": [{"start_time": 1, "end_time": 2}], "labels": [], "transcript": "", "raw_json": {}}
    mock_analyze = mocker.patch("src.analysis_pipeline.analyze_video", return_value=mock_parsed_data)
    mock_store = mocker.patch("src.analysis_pipeline.store_results")

    # Define inputs for the pipeline
    test_gcs_uri = "gs://fake-bucket/test.mp4"
    test_prompt = "a test prompt"
    test_filename = "test.mp4"

    # Run the pipeline
    await start_analysis_pipeline(test_gcs_uri, test_prompt, test_filename)

    # Assert that the mocked functions were called correctly
    mock_analyze.assert_called_once_with(test_gcs_uri)

    # Assert that store_results was called once
    mock_store.assert_called_once()

    # Check the positional arguments passed to the mocked store_results
    # call_args is a tuple of (args, kwargs)
    pos_args = mock_store.call_args[0]

    video_id_arg = pos_args[0]
    parsed_data_arg = pos_args[1]

    assert isinstance(video_id_arg, str)
    assert len(video_id_arg) == 36  # Length of a UUID string
    assert parsed_data_arg == mock_parsed_data
