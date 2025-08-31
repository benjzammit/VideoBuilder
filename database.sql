-- Enable the pgvector extension to use the vector type
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the videos table
CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    file_path VARCHAR(255),
    duration INT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    -- Assuming an embedding model that produces vectors of 768 dimensions (e.g., some Gemini models).
    -- This should be adjusted based on the actual embedding model used.
    summary_embedding VECTOR(768),
    segments JSONB[]
);

-- Add indexes for performance
CREATE INDEX idx_videos_user_id ON videos(user_id);

-- Optional: Add comments to the columns for clarity
COMMENT ON COLUMN videos.summary_embedding IS 'Vector embedding for the entire video summary. Assumes 768 dimensions.';
COMMENT ON COLUMN videos.segments IS 'Array of JSON objects, each representing a searchable segment with its own metadata and embedding.';
