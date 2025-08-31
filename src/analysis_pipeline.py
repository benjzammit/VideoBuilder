import uuid
import asyncio
from src.services import (
    gcs,
    video_intelligence_client,
    gemini_client,
    supabase_client,
    zilliz_client,
    creatomate_client,
)

def _time_to_seconds(time_offset: dict) -> float:
    """Converts Google's time offset format to seconds."""
    if not time_offset: return 0.0
    return time_offset.get("seconds", 0) + time_offset.get("nanos", 0) / 1e9

def parse_video_intelligence_results(raw_results: dict) -> dict:
    """Parses the raw JSON from the Video Intelligence API."""
    print("PIPELINE: Parsing raw analysis results...")
    if not raw_results or not raw_results.get("annotation_results"):
        return None
    annotation_results = raw_results["annotation_results"][0]
    shots = [{"start_time": _time_to_seconds(shot.get("startTimeOffset")), "end_time": _time_to_seconds(shot.get("endTimeOffset"))} for shot in annotation_results.get("shotAnnotations", [])]
    labels = list(set(label["entity"]["description"] for label in annotation_results.get("segmentLabelAnnotations", [])))
    transcript = " ".join(alt["transcript"] for trans in annotation_results.get("speechTranscriptions", []) for alt in trans.get("alternatives", [])).strip()
    return {"shots": shots, "labels": labels, "transcript": transcript, "raw_json": raw_results}


async def run_full_pipeline(task_id: str, file, original_filename: str, user_prompt: str):
    """
    Orchestrates the entire end-to-end workflow from upload to final render.
    This function is designed to be run as a background task.
    """
    try:
        # 1. Upload to GCS
        supabase_client.update_task(task_id, {"status": "uploading"})
        gcs_uri = gcs.upload_video_to_gcs(file, original_filename, user_prompt)
        if not gcs_uri: raise ValueError("Failed to upload to GCS.")

        # 2. Analyze Video
        supabase_client.update_task(task_id, {"status": "analyzing"})
        raw_results = video_intelligence_client.analyze_video_from_gcs(gcs_uri)
        if not raw_results: raise ValueError("Failed to analyze video.")
        parsed_data = parse_video_intelligence_results(raw_results)
        if not parsed_data: raise ValueError("Failed to parse analysis results.")

        # 3. Generate Embeddings & Store Metadata
        supabase_client.update_task(task_id, {"status": "storing_metadata"})
        summary_embedding = gemini_client.get_text_embedding(parsed_data["transcript"])
        segments_for_db = [{"start_time": s["start_time"], "end_time": s["end_time"], "shot_embedding": gemini_client.get_text_embedding(f"Shot from {s['start_time']} to {s['end_time']}"), "labels": parsed_data["labels"]} for s in parsed_data["shots"]]
        video_id = uuid.uuid4()
        supabase_client.save_video_metadata(video_id, gcs_uri, parsed_data["shots"][-1]["end_time"], parsed_data["raw_json"], summary_embedding, segments_for_db)
        zilliz_client.save_segment_embeddings(str(video_id), segments_for_db)
        supabase_client.update_task(task_id, {"status": "editing", "video_id": str(video_id)})

        # 4. Generate Production Plan
        prompt_embedding = gemini_client.get_text_embedding(user_prompt)
        # In a real app, the zilliz search results would be used here.
        # For now, we use a simplified approach as noted in the previous step.
        relevant_shots = segments_for_db[:5]
        production_plan = gemini_client.generate_production_plan(user_prompt, relevant_shots, parsed_data["transcript"])
        if not production_plan: raise ValueError("Failed to generate production plan.")

        # 5. Start Video Assembly
        supabase_client.update_task(task_id, {"status": "rendering"})
        # The source video needs a public URL for Creatomate, not a gs:// URI.
        public_url = gcs_uri.replace("gs://", "https://storage.googleapis.com/")
        render_id = creatomate_client.start_video_render(production_plan, public_url)
        if not render_id: raise ValueError("Failed to start video render.")
        supabase_client.update_task(task_id, {"render_id": render_id})

        # 6. Poll for Render Completion
        while True:
            status_info = creatomate_client.get_render_status(render_id)
            if status_info["status"] == "succeeded":
                supabase_client.update_task(task_id, {"status": "complete", "final_url": status_info["url"]})
                print(f"✅ Task {task_id} completed successfully!")
                break
            elif status_info["status"] == "failed":
                raise ValueError(f"Video rendering failed: {status_info.get('message')}")

            print(f"Task {task_id}: Render in progress...")
            await asyncio.sleep(10) # Poll every 10 seconds

    except Exception as e:
        print(f"🚫 Pipeline for task {task_id} failed: {e}")
        supabase_client.update_task(task_id, {"status": "failed", "error_message": str(e)})
