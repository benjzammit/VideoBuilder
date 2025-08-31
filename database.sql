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

-- Create a table to track the status of asynchronous jobs
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    video_id UUID REFERENCES videos(id) NULL,
    render_id VARCHAR(255) NULL,
    final_url TEXT NULL,
    error_message TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add an index on status for faster querying
CREATE INDEX idx_tasks_status ON tasks(status);

-- Create a function to automatically update the 'updated_at' timestamp
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create a trigger to call the function before any update on the 'tasks' table
CREATE TRIGGER set_timestamp
BEFORE UPDATE ON tasks
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();
