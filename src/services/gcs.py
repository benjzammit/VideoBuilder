import uuid
from google.cloud import storage
from google.auth import exceptions as auth_exceptions
from src.config import settings

# Initialize the client.
# The google-cloud-python library handles authentication automatically via the
# GOOGLE_APPLICATION_CREDENTIALS environment variable.
try:
    storage_client = storage.Client()
except auth_exceptions.DefaultCredentialsError:
    print("⚠️ WARNING: Google Cloud credentials not found. GCS client will not be initialized.")
    print("         The application will run in mocked GCS mode.")
    # In a sandboxed environment without credentials, we set the client to None
    # so the app can load without crashing. The upload function will handle this.
    storage_client = None

def upload_video_to_gcs(file, original_filename: str, prompt: str) -> str:
    """
    Uploads a video file to Google Cloud Storage and attaches the prompt as metadata.

    Args:
        file: The file-like object to upload.
        original_filename: The original name of the uploaded file.
        prompt: The user's prompt to be stored as custom metadata.

    Returns:
        The GCS URI of the uploaded file, or None if an error occurs.
    """
    bucket_name = settings.GCS_BUCKET_NAME
    if not bucket_name:
        print("🚫 Error: GCS_BUCKET_NAME is not configured in your .env file.")
        return None

    # Create a unique filename to avoid overwrites, while keeping it traceable.
    unique_id = uuid.uuid4()
    extension = ""
    if '.' in original_filename:
        extension = original_filename.rsplit('.', 1)[1]

    unique_filename = f"{unique_id}.{extension}" if extension else str(unique_id)

    # --- Mocking for Sandbox Environment ---
    if storage_client is None:
        print("MOCK: Pretending to upload to GCS, as no credentials were found.")
        gcs_uri = f"gs://{bucket_name}/{unique_filename}"
        print(f"✅ (Mocked) Successfully generated GCS URI: {gcs_uri}")
        print(f"✅ (Mocked) Would have set metadata 'prompt': '{prompt}'")
        return gcs_uri
    # --- End Mocking ---

    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(unique_filename)

        # Set custom metadata to be stored with the GCS object.
        # This is how the Cloud Function will retrieve the prompt.
        metadata = {"prompt": prompt, "originalFilename": original_filename}
        blob.metadata = metadata

        # Rewind the file stream before uploading
        file.seek(0)

        print(f"Uploading {original_filename} as {unique_filename} to GCS bucket '{bucket_name}'...")
        blob.upload_from_file(file, content_type='video/mp4')

        gcs_uri = f"gs://{bucket_name}/{unique_filename}"
        print(f"✅ Successfully uploaded to {gcs_uri}")
        return gcs_uri

    except exceptions.NotFound:
        print(f"🚫 Error: GCS bucket '{bucket_name}' not found. Please create it or check for typos.")
        return None
    except Exception as e:
        print(f"🚫 An unexpected error occurred during GCS upload: {e}")
        return None
