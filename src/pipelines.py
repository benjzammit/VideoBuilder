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

async def run_analysis_pipeline(task_id: str, file, original_filename: str):
    """Orchestrates the ingestion and analysis of a single video."""
    try:
        # 1. Upload to GCS
        supabase_client.update_task(task_id, {"status": "uploading"})
        gcs_uri = gcs.upload_video_to_gcs(file, original_filename, "") # No prompt during ingestion
        if not gcs_uri: raise ValueError("Failed to upload to GCS.")

        # 2. Analyze Video
        supabase_client.update_task(task_id, {"status": "analyzing"})
        raw_results = video_intelligence_client.analyze_video_from_gcs(gcs_uri)
        if not raw_results: raise ValueError("Failed to analyze video.")
        parsed_data = parse_video_intelligence_results(raw_results)
        if not parsed_data: raise ValueError("Failed to parse analysis results.")

        # 3. Store Video Metadata in Supabase (main table)
        supabase_client.update_task(task_id, {"status": "storing_metadata"})
        summary_embedding = gemini_client.get_text_embedding(parsed_data["transcript"])
        video_id = uuid.uuid4()
        supabase_client.save_video_metadata(video_id, gcs_uri, parsed_data["shots"][-1]["end_time"], parsed_data["raw_json"], summary_embedding)

        # 4. Prepare and Store Segments
        segments_to_save = []
        for shot in parsed_data["shots"]:
            shot_text = f"labels: {', '.join(parsed_data['labels'])}. shot from {shot['start_time']} to {shot['end_time']}"
            segments_to_save.append({
                "id": uuid.uuid4(),
                "video_id": video_id,
                "start_time": shot["start_time"],
                "end_time": shot["end_time"],
                "labels": parsed_data["labels"],
                "shot_embedding": gemini_client.get_text_embedding(shot_text),
            })

        # Batch insert segments to Supabase
        supabase_client.save_video_segments(segments_to_save)

        # Insert into Zilliz and get back the auto-generated IDs
        zilliz_ids = zilliz_client.save_segment_embeddings(segments_to_save)

        # Update Supabase segments with their Zilliz IDs
        for segment, z_id in zip(segments_to_save, zilliz_ids):
            supabase_client.supabase.table('video_segments').update({'zilliz_id': z_id}).eq('id', str(segment['id'])).execute()

        supabase_client.update_task(task_id, {"status": "complete", "video_id": str(video_id)})
        print(f"✅ Analysis pipeline for task {task_id} completed successfully!")

    except Exception as e:
        print(f"🚫 Analysis pipeline for task {task_id} failed: {e}")
        supabase_client.update_task(task_id, {"status": "failed", "error_message": str(e)})

async def run_creation_pipeline(task_id: str, prompt: str):
    """Orchestrates the creation of a new video from a prompt."""
    try:
        # 1. Generate prompt embedding
        supabase_client.update_task(task_id, {"status": "searching"})
        prompt_embedding = gemini_client.get_text_embedding(prompt)
        if not prompt_embedding: raise ValueError("Failed to generate prompt embedding.")

        # 2. Search for relevant segments in Zilliz
        # This now searches across all videos
        similar_segment_ids = zilliz_client.search_similar_segments(prompt_embedding, top_k=15)
        if not similar_segment_ids: raise ValueError("No relevant video segments found.")

        # 3. Retrieve full segment data from Supabase
        relevant_segments = supabase_client.get_segments_by_zilliz_ids(similar_segment_ids)
        if not relevant_segments: raise ValueError("Could not retrieve segment details from database.")

        # 4. Generate Production Plan with Gemini
        supabase_client.update_task(task_id, {"status": "editing"})
        production_plan = gemini_client.generate_production_plan(prompt, relevant_segments, "")
        if not production_plan: raise ValueError("Failed to generate production plan.")

        # 5. Start Video Assembly with Creatomate
        supabase_client.update_task(task_id, {"status": "rendering"})
        render_id = creatomate_client.start_video_render(production_plan, relevant_segments)
        if not render_id: raise ValueError("Failed to start video render.")
        supabase_client.update_task(task_id, {"render_id": render_id})

        # 6. Poll for Render Completion
        while True:
            await asyncio.sleep(10)
            status_info = creatomate_client.get_render_status(render_id)
            if status_info.get("status") == "succeeded":
                supabase_client.update_task(task_id, {"status": "complete", "final_url": status_info["url"]})
                print(f"✅ Creation pipeline for task {task_id} completed successfully!")
                break
            elif status_info.get("status") == "failed":
                raise ValueError(f"Video rendering failed: {status_info.get('message', 'Unknown error')}")
            print(f"Task {task_id}: Render in progress...")

    except Exception as e:
        print(f"🚫 Creation pipeline for task {task_id} failed: {e}")
        supabase_client.update_task(task_id, {"status": "failed", "error_message": str(e)})
