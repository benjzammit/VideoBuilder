from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid

# Import services and the new pipeline orchestrator
from src.services import supabase_client
from src.pipelines import run_analysis_pipeline, run_creation_pipeline

app = FastAPI()

# Mount static files directory for the frontend
app.mount("/static", FileResponse('src/static/index.html'), name="static")


@app.get("/")
async def read_index():
    """Serves the main HTML page."""
    return FileResponse('src/static/index.html')


@app.post("/upload", status_code=202)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Accepts a video upload for ingestion, creates a task for analysis,
    and starts the analysis pipeline in the background.
    """
    if not file.content_type == "video/mp4":
        raise HTTPException(status_code=400, detail="Only .mp4 files are allowed.")

    task_id = supabase_client.create_task()
    if not task_id:
        raise HTTPException(status_code=500, detail="Failed to create a new processing task.")

    background_tasks.add_task(
        run_analysis_pipeline,
        task_id=task_id,
        file=file.file,
        original_filename=file.filename
    )

    print(f"Started analysis task {task_id} for video {file.filename}.")
    return {"task_id": task_id, "message": "Video upload successful. Analysis has started."}


class CreateRequest(BaseModel):
    prompt: str

@app.post("/create", status_code=202)
async def create_video(
    request: CreateRequest,
    background_tasks: BackgroundTasks
):
    """
    Accepts a prompt, creates a task for video creation, and starts
    the creation pipeline in the background.
    """
    task_id = supabase_client.create_task()
    if not task_id:
        raise HTTPException(status_code=500, detail="Failed to create a new creation task.")

    background_tasks.add_task(
        run_creation_pipeline,
        task_id=task_id,
        prompt=request.prompt
    )

    print(f"Started creation task {task_id} for prompt: '{request.prompt}'.")
    return {"task_id": task_id}


@app.get("/status/{task_id}")
async def get_task_status(task_id: uuid.UUID):
    """
    Endpoint for the client to poll for the status of any task.
    """
    status = supabase_client.get_task_status(str(task_id))
    if not status:
        raise HTTPException(status_code=404, detail="Task not found.")
    return status
