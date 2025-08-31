from supabase import create_client, Client
from src.config import settings
import uuid

# Initialize the client. This will only succeed if the URL and key are set.
if settings.SUPABASE_URL and settings.SUPABASE_KEY:
    try:
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    except Exception as e:
        print(f"⚠️ WARNING: Supabase client could not be initialized: {e}")
        supabase = None
else:
    print("⚠️ WARNING: SUPABASE_URL or SUPABASE_KEY not set. Supabase client will run in mocked mode.")
    supabase = None


def save_video_metadata(
    video_id: uuid.UUID,
    file_path: str,
    duration: float,
    metadata: dict,
    summary_embedding: list[float],
    segments: list[dict]
    ) -> dict:
    """
    Saves the video's metadata to the Supabase 'videos' table.

    Args:
        video_id: The unique UUID for the video.
        file_path: The path to the video file in cloud storage (GCS URI).
        duration: The total duration of the video in seconds.
        metadata: The raw JSON output from the analysis API.
        summary_embedding: The vector embedding for the overall video.
        segments: An array of JSON objects for each segment.

    Returns:
        A dictionary with the result of the operation.
    """
    if supabase is None:
        print("MOCK_DB: Pretending to save metadata to Supabase.")
        print(f"  - Video ID: {video_id}")
        print(f"  - Segments: {len(segments)}")
        return {"status": "success", "video_id": video_id, "mocked": True}

    try:
        print(f"Saving metadata for video {video_id} to Supabase...")
        data, count = supabase.table('videos').insert({
            "id": str(video_id),
            "file_path": file_path,
            "duration": int(duration),
            "metadata": metadata,
            "summary_embedding": summary_embedding,
            "segments": segments
        }).execute()

        if count and count.count > 0:
            print(f"✅ Successfully saved metadata for video {video_id} to Supabase.")
            return {"status": "success", "data": data}
        else:
            print(f"🚫 Error: No data was inserted into Supabase. Response: {data}")
            return {"status": "error", "message": "Insert failed"}

    except Exception as e:
        print(f"🚫 An unexpected error occurred while saving to Supabase: {e}")
        return {"status": "error", "message": str(e)}

def get_video_metadata(video_id: str) -> dict:
    """
    Retrieves a video's full metadata record from Supabase.

    Args:
        video_id: The UUID of the video to retrieve.

    Returns:
        A dictionary containing the video's metadata, or None if not found.
    """
    if supabase is None:
        print(f"MOCK_DB: Pretending to fetch metadata for video {video_id}.")
        # Return some dummy data for mocked environments
        return {
            "id": video_id,
            "segments": [
                {"shot_id": 0, "start_time": 0, "end_time": 5},
                {"shot_id": 1, "start_time": 5, "end_time": 10},
            ],
            "transcript": "This is a mocked transcript.",
            "labels": ["mocked", "data"],
        }

    try:
        print(f"Fetching metadata for video {video_id} from Supabase...")
        data, count = supabase.table('videos').select('*').eq('id', video_id).single().execute()

        if data:
            print(f"✅ Successfully fetched metadata for video {video_id}.")
            return data
        else:
            print(f"🚫 Video with ID {video_id} not found in Supabase.")
            return None

    except Exception as e:
        print(f"🚫 An unexpected error occurred while fetching from Supabase: {e}")
        return None

# --- Task Management Functions ---

def create_task() -> str:
    """Creates a new task in the 'tasks' table and returns its ID."""
    if supabase is None:
        task_id = str(uuid.uuid4())
        print(f"MOCK_DB: Pretending to create task with ID: {task_id}")
        return task_id

    try:
        data, count = supabase.table('tasks').insert({}).select('id').execute()
        task_id = data[1][0]['id']
        print(f"✅ Created new task with ID: {task_id}")
        return task_id
    except Exception as e:
        print(f"🚫 Error creating task in Supabase: {e}")
        return None

def update_task(task_id: str, updates: dict):
    """Updates a task record in Supabase."""
    if supabase is None:
        print(f"MOCK_DB: Pretending to update task {task_id} with: {updates}")
        return {"status": "success", "mocked": True}

    try:
        print(f"Updating task {task_id}: {updates}")
        supabase.table('tasks').update(updates).eq('id', task_id).execute()
    except Exception as e:
        print(f"🚫 Error updating task {task_id} in Supabase: {e}")

def get_task_status(task_id: str) -> dict:
    """Retrieves the status and details of a task."""
    if supabase is None:
        print(f"MOCK_DB: Pretending to get status for task {task_id}.")
        return {"status": "rendering", "final_url": None, "mocked": True}

    try:
        data, count = supabase.table('tasks').select('status, final_url, error_message').eq('id', task_id).single().execute()
        if data:
            return data[1]
        else:
            return None
    except Exception as e:
        print(f"🚫 Error getting task status for {task_id}: {e}")
        return None
