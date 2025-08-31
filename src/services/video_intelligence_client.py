from google.cloud import videointelligence_v1 as videointelligence
from google.auth import exceptions as auth_exceptions
from google.protobuf.json_format import MessageToDict
import json

# Initialize the client. This will only succeed if credentials are set up.
try:
    video_client = videointelligence.VideoIntelligenceServiceClient()
except auth_exceptions.DefaultCredentialsError:
    print("⚠️ WARNING: Google Cloud credentials not found. Video Intelligence client will run in mocked mode.")
    video_client = None


def analyze_video_from_gcs(gcs_uri: str) -> dict:
    """
    Starts and waits for a video analysis job using the Google Cloud Video Intelligence API.

    Args:
        gcs_uri: The GCS URI of the video to analyze (e.g., "gs://bucket-name/file-name.mp4").

    Returns:
        The raw JSON annotation results as a dictionary, or None on error.
    """
    if video_client is None:
        print(f"MOCK_VI: Pretending to analyze video: {gcs_uri}")
        # In mock mode, we'll return the sample fixture data directly.
        try:
            with open("tests/fixtures/sample_video_intelligence_response.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print("🚫 Error: Mock response file not found for Video Intelligence.")
            return None

    features = [
        videointelligence.Feature.SPEECH_TRANSCRIPTION,
        videointelligence.Feature.LABEL_DETECTION,
        videointelligence.Feature.SHOT_CHANGE_DETECTION,
    ]

    # Configure speech transcription for better accuracy
    speech_config = videointelligence.SpeechTranscriptionConfig(
        language_code="en-US",
        enable_automatic_punctuation=True
    )
    video_context = videointelligence.VideoContext(speech_transcription_config=speech_config)

    print(f"Starting video analysis job for {gcs_uri}...")
    try:
        operation = video_client.annotate_video(
            request={
                "features": features,
                "input_uri": gcs_uri,
                "video_context": video_context,
            }
        )

        print("Waiting for operation to complete... (This can take several minutes)")

        # This is a simple polling mechanism. In a production system for very long videos,
        # you might use Pub/Sub notifications for a more robust, event-driven approach.
        response = operation.result(timeout=600) # 10 minute timeout

        print("✅ Video analysis finished.")

        # The API returns a complex protobuf object. We convert it to a dictionary
        # to make it serializable and easier to work with (e.g., storing as JSONB).
        return MessageToDict(response._pb)

    except exceptions.GoogleAPICallError as e:
        print(f"🚫 API Error during video analysis for {gcs_uri}: {e}")
        return None
    except Exception as e:
        print(f"🚫 An unexpected error occurred during video analysis for {gcs_uri}: {e}")
        return None
