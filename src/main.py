from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid

# Import services and the new pipeline orchestrator
from src.services import supabase_client
from src.analysis_pipeline import run_full_pipeline

app = FastAPI()

# Mount static files directory for the frontend
app.mount("/static", FileResponse('src/static/index.html'), name="static")


@app.get("/")
async def read_index():
    """Serves the main HTML page."""
    return FileResponse('src/static/index.html')


@app.post("/upload", status_code=202)
async def upload_and_process_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    prompt: str = Form("")
):
    """
    Accepts a video upload, creates a task, and starts the full
    end-to-end pipeline in the background.
    """
    if not file.content_type == "video/mp4":
        raise HTTPException(status_code=400, detail="Only .mp4 files are allowed.")

    # 1. Create a new task in the database
    task_id = supabase_client.create_task()
    if not task_id:
        raise HTTPException(status_code=500, detail="Failed to create a new processing task.")

    # 2. Add the full pipeline to run in the background
    background_tasks.add_task(
        run_full_pipeline,
        task_id=task_id,
        file=file.file,
        original_filename=file.filename,
        user_prompt=prompt
    )

    print(f"Started task {task_id} for video {file.filename}.")

    # 3. Return the task ID to the client for polling
    return {"task_id": task_id}


@app.get("/status/{task_id}")
async def get_task_status(task_id: uuid.UUID):
    """
    Endpoint for the client to poll for the status of a task.
    """
    status = supabase_client.get_task_status(str(task_id))
    if not status:
        raise HTTPException(status_code=404, detail="Task not found.")
    return status
