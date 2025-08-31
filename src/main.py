from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Import services and pipelines
from src.services.gcs import upload_video_to_gcs
from src.analysis_pipeline import start_analysis_pipeline

app = FastAPI()

# Mount static files directory for the frontend
app.mount("/static", StaticFiles(directory="src/static"), name="static")


@app.get("/")
async def read_index():
    """Serves the main HTML page."""
    return FileResponse('src/static/index.html')


@app.post("/upload/")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    prompt: str = Form("")
):
    """
    Endpoint to upload a video. It uses a (mocked) GCS service and
    triggers a simulated analysis pipeline as a background task.
    """
    if not file.content_type == "video/mp4":
        return JSONResponse(status_code=400, content={"message": "Only .mp4 files are allowed."})

    try:
        # 1. Upload the file to Google Cloud Storage (currently mocked)
        gcs_uri = upload_video_to_gcs(file.file, file.filename)

        if not gcs_uri:
            return JSONResponse(status_code=500, content={"message": "Failed to upload video to cloud storage."})

        # 2. Trigger the asynchronous analysis pipeline in the background
        background_tasks.add_task(
            start_analysis_pipeline,
            gcs_uri=gcs_uri,
            prompt=prompt,
            video_filename=file.filename
        )

        print(f"Received prompt for {file.filename}: '{prompt}'")
        print(f"Analysis pipeline for {file.filename} added to background tasks.")

        # Return an immediate response to the client
        return {
            "filename": file.filename,
            "gcs_uri": gcs_uri,
            "prompt": prompt,
            "message": "Video upload successful. Analysis has started in the background."
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"An unexpected error occurred: {e}"})
    finally:
        # Ensure the file handle is closed
        file.file.close()
