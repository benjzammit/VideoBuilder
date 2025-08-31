import os
import shutil
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Create uploads directory if it doesn't exist
os.makedirs("src/uploads", exist_ok=True)

# Mount static files directory
app.mount("/static", StaticFiles(directory="src/static"), name="static")

UPLOADS_DIR = "src/uploads"


@app.get("/")
async def read_index():
    return FileResponse('src/static/index.html')


@app.post("/upload/")
async def upload_video(
    file: UploadFile = File(...),
    prompt: str = Form("")
):
    if not file.content_type == "video/mp4":
        return JSONResponse(status_code=400, content={"message": "Only .mp4 files are allowed."})

    try:
        file_path = os.path.join(UPLOADS_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # For now, we just return the filename and the received prompt.
        # In the future, this endpoint will trigger the analysis pipeline.
        return {"filename": file.filename, "prompt": prompt}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"There was an error uploading the file: {e}"})
    finally:
        file.file.close()
