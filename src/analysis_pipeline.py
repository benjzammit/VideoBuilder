import asyncio
import json
import random
import uuid

# Import the mocked service clients
from src.services import supabase_client, zilliz_client
from src.setup_vector_db import EMBEDDING_DIMENSION

def _time_to_seconds(time_offset: dict) -> float:
    """Converts Google's time offset format to seconds."""
    return time_offset.get("seconds", 0) + time_offset.get("nanos", 0) / 1e9

def parse_video_intelligence_results(raw_results: dict) -> dict:
    """Parses the raw JSON from the Video Intelligence API."""
    print("PIPELINE: Parsing raw analysis results...")

    annotation_results = raw_results.get("annotation_results", [])[0]

    # Extract shots
    shots = [
        {
            "start_time": _time_to_seconds(shot["start_time_offset"]),
            "end_time": _time_to_seconds(shot["end_time_offset"]),
        }
        for shot in annotation_results.get("shot_annotations", [])
    ]

    # Extract labels
    labels = list(set(
        label["entity"]["description"]
        for label in annotation_results.get("segment_label_annotations", [])
    ))

    # Extract transcript
    transcript = " ".join(
        alt["transcript"]
        for trans in annotation_results.get("speech_transcriptions", [])
        for alt in trans.get("alternatives", [])
    )

    parsed_data = {
        "shots": shots,
        "labels": labels,
        "transcript": transcript,
        "raw_json": raw_results # Store the original JSON as well
    }
    print("PIPELINE: Parsing complete.")
    return parsed_data


async def analyze_video(gcs_uri: str) -> dict:
    """
    (Mocked) Simulates calling the Video Intelligence API by reading a local file.
    """
    print(f"PIPELINE: Starting video analysis for {gcs_uri}...")
    await asyncio.sleep(2)  # Simulate API call latency

    try:
        with open("tests/fixtures/sample_video_intelligence_response.json", "r") as f:
            raw_results = json.load(f)
    except FileNotFoundError:
        print("🚫 Error: Sample response file not found.")
        return None

    print("PIPELINE: Mock analysis complete.")
    return parse_video_intelligence_results(raw_results)


async def store_results(video_id: str, parsed_data: dict):
    """
    (Mocked) Simulates generating embeddings and storing all results.
    """
    print("PIPELINE: Storing analysis results...")

    # 1. (Mocked) Generate dummy embeddings for each shot
    segments_with_embeddings = []
    for segment in parsed_data["shots"]:
        segment_data = segment.copy()
        # In a real app, you'd call the Gemini API here to get the embedding
        segment_data["shot_embedding"] = [random.random() for _ in range(EMBEDDING_DIMENSION)]
        segments_with_embeddings.append(segment_data)

    # 2. (Mocked) Save segment embeddings to Zilliz
    await asyncio.sleep(1) # Simulate network call
    zilliz_client.save_segment_embeddings(video_id=video_id, segments=segments_with_embeddings)

    # 3. (Mocked) Prepare data and save master record to Supabase
    supabase_metadata = {
        "duration": parsed_data["shots"][-1]["end_time"] if parsed_data["shots"] else 0,
        "segments_with_embeddings": segments_with_embeddings, # Will be stored as JSONB
        "raw_json": parsed_data["raw_json"],
        # Add other fields as needed
    }
    await asyncio.sleep(1) # Simulate network call
    supabase_client.save_video_metadata(video_id=video_id, metadata=supabase_metadata)

    print("PIPELINE: Results storage complete.")


async def start_analysis_pipeline(gcs_uri: str, prompt: str, video_filename: str):
    """
    Orchestrates the end-to-end video processing workflow (simulated).
    """
    print(f"\n---[BACKGROUND TASK]--- Starting Analysis Pipeline for '{video_filename}' ---")

    # 1. Get analysis from Video Intelligence API (mocked)
    parsed_data = await analyze_video(gcs_uri)
    if not parsed_data:
        print("---[BACKGROUND TASK]--- Pipeline failed: Could not analyze video. ---")
        return

    # 2. Generate a unique ID for the video
    video_id = str(uuid.uuid4())
    print(f"PIPELINE: Generated new video ID: {video_id}")

    # 3. Store the results in our databases (mocked)
    await store_results(video_id, parsed_data)

    # 4. (Future) Generate production plan from prompt and assemble video
    print(f"---[BACKGROUND TASK]--- Finished Analysis Pipeline for '{video_filename}' (ID: {video_id}) ---\n")
