from pymilvus import connections, utility, FieldSchema, CollectionSchema, DataType, Collection
from src.config import settings

# --- Configuration ---
COLLECTION_NAME = "video_segments"
# This dimension must match the output dimension of your embedding model (e.g., Gemini).
# Using 768 as a common dimension for models like text-embedding-004.
EMBEDDING_DIMENSION = 768


def create_zilliz_collection():
    """
    Connects to Zilliz Cloud and sets up the required 'video_segments' collection.
    This function is idempotent and can be run multiple times safely.
    """
    uri = settings.ZILLIZ_CLOUD_URI
    token = settings.ZILLIZ_CLOUD_TOKEN

    if not all([uri, token]):
        print("🚫 Error: Zilliz Cloud credentials not found in your configuration.")
        print("Please set ZILLIZ_CLOUD_URI and ZILLIZ_CLOUD_TOKEN in your .env file.")
        return

    print(f"Connecting to Zilliz Cloud at {uri}...")
    try:
        connections.connect("default", uri=uri, token=token)
        print("✅ Successfully connected to Zilliz Cloud.")
    except Exception as e:
        print(f"🚫 Error connecting to Zilliz Cloud: {e}")
        return

    # Check if collection already exists
    if utility.has_collection(COLLECTION_NAME):
        print(f"✅ Collection '{COLLECTION_NAME}' already exists. No action needed.")
        return

    print(f"Collection '{COLLECTION_NAME}' not found. Creating now...")

    # 1. Define schema fields
    # Zilliz's auto-generated primary key
    zilliz_id = FieldSchema(name="zilliz_id", dtype=DataType.INT64, is_primary=True, auto_id=True)
    # The UUID of the segment from our primary Supabase `video_segments` table
    supabase_segment_id = FieldSchema(name="supabase_segment_id", dtype=DataType.VARCHAR, max_length=36, description="FK to video_segments table")
    # The UUID of the parent video, useful for filtering
    video_id = FieldSchema(name="video_id", dtype=DataType.VARCHAR, max_length=36, description="Parent Video UUID")
    # The vector embedding for the video segment
    shot_embedding = FieldSchema(name="shot_embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIMENSION)

    schema = CollectionSchema(
        fields=[zilliz_id, supabase_segment_id, video_id, shot_embedding],
        description="Collection to store vector embeddings of video segments for similarity search"
    )

    # 2. Create collection
    try:
        collection = Collection(name=COLLECTION_NAME, schema=schema, using='default')
        print(f"✅ Collection '{COLLECTION_NAME}' created successfully.")
    except Exception as e:
        print(f"🚫 Error creating collection: {e}")
        return

    # 3. Create an index for the vector field for efficient search
    print("Creating index for the vector field...")
    index_params = {
        "metric_type": "L2",      # L2 is a common choice for semantic similarity
        "index_type": "AUTOINDEX", # Zilliz Cloud will automatically choose the best index type
        "params": {}
    }
    try:
        collection.create_index(field_name="shot_embedding", index_params=index_params)
        print("✅ Index created successfully.")

        # Load the collection into memory for searching
        collection.load()
        print(f"✅ Collection '{COLLECTION_NAME}' loaded into memory.")
    except Exception as e:
        print(f"🚫 Error creating index or loading collection: {e}")


if __name__ == "__main__":
    print("Running Zilliz Cloud setup script...")
    create_zilliz_collection()
    print("\nSetup script finished.")
