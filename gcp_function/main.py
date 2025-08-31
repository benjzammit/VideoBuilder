import sys
import os
import asyncio

# Add the project root to the Python path to allow imports from 'src'.
# This is a common pattern for structuring GCP Functions with shared code.
# The path is relative to this file's location.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analysis_pipeline import start_analysis_pipeline

def process_video_trigger(event, context):
    """
    Background Cloud Function to be triggered by a new file in a GCS bucket.
    This function orchestrates the video analysis pipeline.

    Args:
        event (dict): The dictionary with data specific to this type of event.
                      It contains information about the GCS object.
        context (google.cloud.functions.Context): Event metadata.
    """
    # Extract file and bucket details from the GCS event payload
    bucket = event['bucket']
    name = event['name']
    gcs_uri = f"gs://{bucket}/{name}"

    # Extract custom metadata that was set during the upload.
    # This is how we pass the user's prompt to the analysis pipeline.
    metadata = event.get('metadata', {})
    prompt = metadata.get('prompt', '') # Default to empty string if not found
    original_filename = metadata.get('originalFilename', name)

    print(f"--- GCP Function Triggered for: {original_filename} ---")
    print(f"  - GCS URI: {gcs_uri}")
    print(f"  - Prompt: '{prompt}'")

    # The analysis pipeline is an async function.
    # The Python runtime for Google Cloud Functions is synchronous by default,
    # so we use asyncio.run() to execute our async pipeline and wait for it to complete.
    try:
        asyncio.run(start_analysis_pipeline(
            gcs_uri=gcs_uri,
            prompt=prompt,
            video_filename=original_filename
        ))
    except Exception as e:
        # Log any exceptions that occur during the pipeline execution
        print(f"🚫 An error occurred in the analysis pipeline for {original_filename}: {e}")
        # Depending on the error, you might want to raise it to have the
        # function execution marked as a failure for retries.
        # raise e

    print(f"--- GCP Function Finished for: {original_filename} ---")
