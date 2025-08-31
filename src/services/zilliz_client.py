from pymilvus import Collection, connections
from src.config import settings
from src.setup_vector_db import COLLECTION_NAME
from typing import List, Dict, Any
import random
import uuid

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

def save_segment_embeddings(segments: List[Dict[str, Any]]) -> List[int]:
    """
    Saves video segment embeddings to the Zilliz Cloud collection.

    Args:
        segments: A list of segment dictionaries from our primary DB.
                  Each dict must contain 'id' (the supabase_segment_id) and 'shot_embedding'.

    Returns:
        A list of the Zilliz-generated primary keys for the inserted vectors.
    """
    if not is_connected:
        print(f"MOCK_DB: Pretending to save {len(segments)} segment embeddings to Zilliz.")
        return [random.randint(1000, 9999) for _ in segments]

    try:
        collection = Collection(COLLECTION_NAME)
        data_to_insert = [
            {
                "supabase_segment_id": str(segment['id']),
                "video_id": str(segment['video_id']),
                "shot_embedding": segment['shot_embedding']
            }
            for segment in segments
        ]
        print(f"Saving {len(data_to_insert)} segment embeddings to Zilliz...")
        mutation_result = collection.insert(data_to_insert)
        collection.flush()
        print(f"✅ Successfully inserted {len(mutation_result.primary_keys)} embeddings into Zilliz.")
        return mutation_result.primary_keys
    except Exception as e:
        print(f"🚫 An unexpected error occurred while saving to Zilliz: {e}")
        return []

def search_similar_segments(query_vector: list[float], top_k: int = 10) -> List[str]:
    """
    Searches for the most similar video segments across the entire library.

    Args:
        query_vector: The vector embedding of the user's prompt.
        top_k: The number of similar segments to return.

    Returns:
        A list of the supabase_segment_id's for the top matching segments.
    """
    if not is_connected:
        print(f"MOCK_DB: Pretending to search for {top_k} segments in Zilliz.")
        return [str(uuid.uuid4()) for _ in range(top_k)]

    try:
        collection = Collection(COLLECTION_NAME)
        collection.load()
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        print(f"Searching for top {top_k} similar segments...")

        results = collection.search(
            data=[query_vector],
            anns_field="shot_embedding",
            param=search_params,
            limit=top_k,
            output_fields=["supabase_segment_id"] # Return our primary key
        )

        hits = results[0]
        print(f"✅ Found {len(hits)} similar segments.")
        return [hit.entity.get('supabase_segment_id') for hit in hits]
    except Exception as e:
        print(f"🚫 An unexpected error occurred during Zilliz search: {e}")
        return []
