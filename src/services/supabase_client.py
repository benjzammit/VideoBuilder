from supabase import create_client, Client
from src.config import settings
import uuid
from typing import List, Dict, Any

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


def save_video_metadata(video_id: uuid.UUID, file_path: str, duration: float, metadata: dict, summary_embedding: list[float]) -> dict:
    """Saves the main video metadata to the Supabase 'videos' table."""
    if supabase is None:
        print(f"MOCK_DB: Pretending to save video metadata for ID: {video_id}")
        return {"status": "success", "mocked": True}
    try:
        print(f"Saving video metadata for {video_id} to Supabase...")
        supabase.table('videos').insert({
            "id": str(video_id),
            "file_path": file_path,
            "duration": int(duration),
            "metadata": metadata,
            "summary_embedding": summary_embedding,
        }).execute()
        print(f"✅ Successfully saved video metadata for {video_id}.")
        return {"status": "success"}
    except Exception as e:
        print(f"🚫 An unexpected error occurred while saving video metadata: {e}")
        return {"status": "error", "message": str(e)}

def save_video_segments(segments_data: List[Dict[str, Any]]) -> dict:
    """Batch inserts video segments into the 'video_segments' table."""
    if supabase is None:
        print(f"MOCK_DB: Pretending to save {len(segments_data)} segments to Supabase.")
        return {"status": "success", "mocked": True}
    try:
        print(f"Batch saving {len(segments_data)} segments to Supabase...")
        supabase.table('video_segments').insert(segments_data).execute()
        print(f"✅ Successfully saved {len(segments_data)} segments.")
        return {"status": "success"}
    except Exception as e:
        print(f"🚫 An unexpected error occurred while saving segments: {e}")
        return {"status": "error", "message": str(e)}

def get_video_metadata(video_id: str) -> dict:
    """Retrieves a video's full metadata record from Supabase."""
    if supabase is None:
        print(f"MOCK_DB: Pretending to fetch metadata for video {video_id}.")
        return {"id": video_id, "transcript": "This is a mocked transcript.", "labels": ["mocked"]}
    try:
        print(f"Fetching metadata for video {video_id} from Supabase...")
        response = supabase.table('videos').select('*').eq('id', video_id).single().execute()
        return response.data
    except Exception as e:
        print(f"🚫 An unexpected error occurred while fetching from Supabase: {e}")
        return None

def get_segments_by_zilliz_ids(zilliz_ids: List[int]) -> List[Dict[str, Any]]:
    """Retrieves segment details from Supabase using their Zilliz IDs."""
    if supabase is None:
        print(f"MOCK_DB: Pretending to fetch {len(zilliz_ids)} segments by Zilliz ID.")
        return [{"id": str(uuid.uuid4()), "video_id": str(uuid.uuid4()), "start_time": i, "end_time": i+5} for i in range(len(zilliz_ids))]
    try:
        print(f"Fetching {len(zilliz_ids)} segments from Supabase by Zilliz ID...")
        response = supabase.table('video_segments').select('*, videos(file_path)').in_('zilliz_id', zilliz_ids).execute()
        # The join syntax `videos(file_path)` fetches the file_path from the related videos table.
        return response.data
    except Exception as e:
        print(f"🚫 An unexpected error occurred while fetching segments: {e}")
        return []

# --- Task Management Functions ---

def create_task() -> str:
    """Creates a new task in the 'tasks' table and returns its ID."""
    if supabase is None:
        task_id = str(uuid.uuid4())
        print(f"MOCK_DB: Pretending to create task with ID: {task_id}")
        return task_id
    try:
        response = supabase.table('tasks').insert({}).select('id').execute()
        return response.data[0]['id']
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
        response = supabase.table('tasks').select('status, final_url, error_message').eq('id', task_id).single().execute()
        return response.data
    except Exception as e:
        print(f"🚫 Error getting task status for {task_id}: {e}")
        return None
