import requests
import json
from src.config import settings
import uuid
from typing import List, Dict, Any

API_URL = "https://api.creatomate.com/v1/renders"

def start_video_render(plan: Dict[str, Any], relevant_segments: List[Dict[str, Any]]) -> str:
    """
    Starts a video rendering job on Creatomate using a template
    and a dynamic list of source clips.

    Args:
        plan: The production plan from Gemini (e.g., title, clip order).
        relevant_segments: The full segment data from Supabase for the shots
                           selected for the edit.

    Returns:
        The ID of the render job, or None on error.
    """
    if not settings.CREATOMATE_API_KEY or not settings.CREATOMATE_TEMPLATE_ID:
        print("MOCK_CREATOMATE: Pretending to start render job (API key or template ID not set).")
        return f"mock-render-{uuid.uuid4()}"

    headers = {
        "Authorization": f"Bearer {settings.CREATOMATE_API_KEY}",
        "Content-Type": "application/json",
    }

    # Create a mapping of our segment IDs to their full data
    segment_map = {str(segment['id']): segment for segment in relevant_segments}

    # Prepare the sources and edits for the Creatomate template
    # The template will receive this JSON and use it to build the video
    clips_for_template = []
    for clip_instruction in plan.get('clips', []):
        segment_id = clip_instruction.get('segment_id')
        segment_data = segment_map.get(segment_id)
        if not segment_data:
            continue

        # The public URL of the source video
        public_url = segment_data['videos']['file_path'].replace("gs://", "https://storage.googleapis.com/")

        clips_for_template.append({
            "source": public_url,
            "trim_start": segment_data['start_time'],
            "duration": segment_data['end_time'] - segment_data['start_time'],
            "text_overlay": clip_instruction.get('text_overlay', '')
        })

    payload = {
        "template_id": settings.CREATOMATE_TEMPLATE_ID,
        "modifications": {
            "video_title": plan.get('title', 'My AI-Generated Video'),
            # We serialize our clips array into a JSON string to pass to the template's
            # 'dynamic-clips' element. The template will then iterate over this.
            "dynamic-clips": json.dumps(clips_for_template)
        }
    }

    try:
        print("Starting Creatomate render job with dynamic sources...")
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()

        render_data = response.json()
        render_id = render_data[0]['id']
        print(f"✅ Creatomate job started with ID: {render_id}")
        return render_id
    except requests.exceptions.RequestException as e:
        print(f"🚫 Error starting Creatomate render: {e}")
        return None
    except (KeyError, IndexError) as e:
        print(f"🚫 Error parsing Creatomate response: {e}")
        return None

def get_render_status(render_id: str) -> dict:
    """Gets the status of a rendering job from Creatomate."""
    if render_id.startswith("mock-render-"):
        print(f"MOCK_CREATOMATE: Pretending to get status for render {render_id}.")
        import random
        if random.random() > 0.3:
            return {"status": "in_progress", "url": None}
        else:
            return {"status": "succeeded", "url": "https://creatomate.com/files/mock/final_video.mp4"}

    if not settings.CREATOMATE_API_KEY:
        return {"status": "failed", "message": "Creatomate API key not configured."}

    headers = {"Authorization": f"Bearer {settings.CREATOMATE_API_KEY}"}
    status_url = f"{API_URL}/{render_id}"

    try:
        response = requests.get(status_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return {"status": data.get("status"), "url": data.get("url")}
    except requests.exceptions.RequestException as e:
        print(f"🚫 Error getting Creatomate status: {e}")
        return {"status": "failed", "message": str(e)}
