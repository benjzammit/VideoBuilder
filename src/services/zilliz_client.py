from pymilvus import Collection, connections
from src.config import settings
from src.setup_vector_db import COLLECTION_NAME

# Initialize the connection. This will only succeed if the credentials are set.
is_connected = False
if settings.ZILLIZ_CLOUD_URI and settings.ZILLIZ_CLOUD_TOKEN:
    try:
        connections.connect("default", uri=settings.ZILLIZ_CLOUD_URI, token=settings.ZILLIZ_CLOUD_TOKEN)
        is_connected = True
    except Exception as e:
        print(f"⚠️ WARNING: Zilliz Cloud connection could not be established: {e}")
else:
    print("⚠️ WARNING: ZILLIZ_CLOUD_URI or ZILLIZ_CLOUD_TOKEN not set. Zilliz client will run in mocked mode.")

def save_segment_embeddings(video_id: str, segments: list[dict]) -> dict:
    """
    Saves video segment embeddings to the Zilliz Cloud collection.

    Args:
        video_id: The UUID of the parent video.
        segments: A list of segment dictionaries, each containing a 'shot_embedding'.

    Returns:
        A dictionary with the result of the operation.
    """
    if not is_connected:
        print("MOCK_DB: Pretending to save segment embeddings to Zilliz.")
        print(f"  - Parent Video ID: {video_id}")
        print(f"  - Number of segments: {len(segments)}")
        return {"status": "success", "inserted_count": len(segments), "mocked": True}

    try:
        print(f"Saving {len(segments)} segment embeddings for video {video_id} to Zilliz...")
        collection = Collection(COLLECTION_NAME)

        # Prepare data for insertion
        data_to_insert = [
            {
                "video_id": video_id,
                "shot_embedding": segment['shot_embedding']
            }
            for segment in segments
        ]

        mutation_result = collection.insert(data_to_insert)
        collection.flush() # Ensure data is indexed

        inserted_count = len(mutation_result.primary_keys)
        print(f"✅ Successfully inserted {inserted_count} embeddings into Zilliz.")
        return {"status": "success", "inserted_count": inserted_count}

    except Exception as e:
        print(f"🚫 An unexpected error occurred while saving to Zilliz: {e}")
        return {"status": "error", "message": str(e)}

def search_similar_segments(video_id: str, query_vector: list[float], top_k: int = 5) -> list:
    """
    Searches for the most similar video segments in Zilliz Cloud.

    Args:
        video_id: The UUID of the video to search within.
        query_vector: The vector embedding of the user's prompt.
        top_k: The number of similar segments to return.

    Returns:
        A list of results, each containing the segment ID and similarity score.
    """
    if not is_connected:
        print(f"MOCK_DB: Pretending to search for {top_k} segments in Zilliz for video {video_id}.")
        # Return some dummy data that looks like the real output
        mock_results = [
            {"id": i, "distance": round(random.random(), 4)} for i in range(top_k)
        ]
        return mock_results

    try:
        collection = Collection(COLLECTION_NAME)
        collection.load() # Ensure collection is loaded for searching

        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 10},
        }

        print(f"Searching for top {top_k} similar segments for video {video_id}...")

        results = collection.search(
            data=[query_vector],
            anns_field="shot_embedding",
            param=search_params,
            limit=top_k,
            expr=f'video_id == "{video_id}"', # Filter by the video ID
            output_fields=["video_id"] # Optionally retrieve other fields
        )

        # Process results
        hits = results[0]
        print(f"✅ Found {len(hits)} similar segments.")
        return [
            {"id": hit.id, "distance": hit.distance} for hit in hits
        ]

    except Exception as e:
        print(f"🚫 An unexpected error occurred during Zilliz search: {e}")
        return []
