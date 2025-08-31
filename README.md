# Content Intelligence Platform MVP

This project is a Minimum Viable Product (MVP) for a Content Intelligence Platform. The platform uses AI to automatically edit videos based on natural language prompts. This MVP sets up the foundational structure, including the backend server, a modern user interface for uploading videos and prompts, and the necessary database schemas and configurations.

## Features

*   **Modern UI:** A clean, intuitive, and responsive interface for uploading `.mp4` videos and submitting editing prompts.
*   **Drag-and-Drop:** Supports dragging and dropping video files for a better user experience.
*   **Orchestration Backend:** A FastAPI server to handle requests, ready to be extended.
*   **Test Suite:** A suite of `pytest` tests to ensure backend reliability.
*   **Scalable Foundation:** The project is structured to integrate with a suite of cloud services for analysis, storage, and video rendering.

## Project Architecture

The application is composed of two main parts: a **FastAPI web server** for handling user interactions and a **Google Cloud Function** for background processing.

### FastAPI Web Server (`src/`)
*   `main.py`: The main entry point for the FastAPI application. It serves the frontend and provides three key endpoints:
    -   `/upload`: Accepts a video file for ingestion and analysis.
    -   `/create`: Accepts a text prompt to generate a new video from the library.
    -   `/status/{task_id}`: Allows the frontend to poll for the status of either analysis or creation tasks.
*   `pipelines.py`: This module orchestrates the two main workflows of the application:
    -   `run_analysis_pipeline`: Handles the ingestion of a new video (upload, analysis, metadata/embedding storage).
    -   `run_creation_pipeline`: Handles the generation of a new video (semantic search, AI planning, rendering).
*   `services/`: This directory contains a client module for each external service (GCS, Supabase, Zilliz, Gemini, Video Intelligence, Creatomate).
*   `config.py`: A centralized, Pydantic-based configuration module for managing all settings and secrets.

### Google Cloud Function (`gcp_function/`)
*   `main.py`: The entry point for the serverless function. In a production environment, this function would be triggered by a new video upload to GCS. It is responsible for calling the `run_full_pipeline` to start the analysis. This provides a more robust, event-driven alternative to the FastAPI background task for production use.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

*   Python 3.10+
*   An account with the following services (the current code does not yet integrate them, but they will be needed to build out the full functionality):
    *   **Google Cloud Platform:** For Cloud Storage and the Video Intelligence API.
    *   **Supabase:** For the main PostgreSQL database.
    *   **Zilliz Cloud:** For the vector database.
    *   **Google AI Studio:** For the Gemini API.
    *   **Creatomate:** For programmatic video editing.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create and activate a Python virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up your environment variables:**
    *   Create a `.env` file by copying the example file:
        ```bash
        cp .env.example .env
        ```
    *   Open the `.env` file and add your credentials. See the "Environment Variables" section below for details on how to get these keys for the next development phase.

### Database Setup

This project requires two databases: a primary database (Supabase) and a vector database (Zilliz Cloud).

1.  **Set up Supabase:**
    *   Navigate to your Supabase project's "SQL Editor".
    *   Open the `database.sql` file from this repository, copy its content, and run it in the editor. This will create the `videos` table and enable the `vector` extension.

2.  **Set up Zilliz Cloud:**
    *   Ensure your `.env` file is correctly filled with your Zilliz Cloud credentials (`ZILLIZ_CLOUD_URI` and `ZILLIZ_CLOUD_TOKEN`).
    *   Run the setup script from your terminal:
        ```bash
        python src/setup_vector_db.py
        ```
    *   This script will connect to your Zilliz instance and create the necessary `video_segments` collection for storing vector embeddings.

### Running the Application

Once the setup is complete, you can run the FastAPI server using `uvicorn`:

```bash
uvicorn src.main:app --reload
```

The application will be available at `http://127.0.0.1:8000`. You can open this URL in your browser to see the UI.

## Deployment

While the FastAPI server can be run locally for development, a more scalable production setup involves deploying the analysis pipeline as a serverless cloud function.

### Deploying the Google Cloud Function

The `gcp_function/` directory contains the code for this. The function is designed to be triggered by a new file upload to your GCS bucket.

1.  **Prepare the deployment package:**
    The cloud function needs access to the code in the `src/` directory. You will need to create a deployment package that includes both `gcp_function/` and `src/`. A simple way is to zip the relevant files from the project root:
    ```bash
    zip -r deployment.zip gcp_function/ src/ .env
    ```
    *Note: Including the `.env` file is a simple way to deploy secrets for this MVP. For higher security, use a secret manager like Google Secret Manager.*

2.  **Deploy using `gcloud` CLI:**
    Run the following command, replacing the placeholders with your own values:
    ```bash
    gcloud functions deploy process-video-trigger \
      --gen2 \
      --runtime=python312 \
      --region=YOUR_GCP_REGION \
      --source=./deployment.zip \
      --entry-point=process_video_trigger \
      --trigger-event-filters="type=google.cloud.storage.object.v1.finalized" \
      --trigger-event-filters="bucket=YOUR_GCS_BUCKET_NAME"
    ```

Once deployed, you can disable the background task in `src/main.py` to have all processing handled by the more robust, event-driven Cloud Function.

## Environment Variables

You need to set the following environment variables in a `.env` file in the project root for the full MVP functionality. The current code will run without them, but they are placeholders for the full implementation.

*   `GOOGLE_APPLICATION_CREDENTIALS`: The path to your Google Cloud service account key JSON file.
    *   **How to get:** Create a service account in your Google Cloud project with the necessary permissions (e.g., Storage Admin, Video Intelligence API User) and download the key. See the [Google Cloud Docs](https://cloud.google.com/iam/docs/creating-managing-service-account-keys).
*   `GCS_BUCKET_NAME`: The name of your Google Cloud Storage bucket for storing videos.
    *   **How to get:** Create a new bucket in the Google Cloud Storage console.
*   `SUPABASE_URL`: Your Supabase project URL.
    *   **How to get:** Find this in your Supabase project's "API" settings.
*   `SUPABASE_KEY`: Your Supabase project's `anon` key.
    *   **How to get:** Find this in your Supabase project's "API" settings.
*   `ZILLIZ_CLOUD_URI`: The public endpoint for your Zilliz Cloud cluster.
    *   **How to get:** Find this in your Zilliz Cloud cluster's connection details.
*   `ZILLIZ_CLOUD_TOKEN`: The API token for your Zilliz Cloud cluster.
    *   **How to get:** Create a token in your Zilliz Cloud cluster's access control settings.
*   `GEMINI_API_KEY`: Your API key for the Gemini API.
    *   **How to get:** Generate an API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
*   `CREATOMATE_API_KEY`: Your API key for Creatomate.
    *   **How to get:** Find this in your Creatomate project settings.

## Next Steps to Complete the MVP

This repository contains the foundational code for the MVP. The UI is functional, the backend server runs, and the project structure is in place. However, the core logic that connects to and orchestrates the various AI and cloud services is not yet implemented.

Here are the remaining high-level tasks for you or your development team to complete the MVP:

1.  **Integrate Google Cloud Storage:**
    *   Update the `/upload` endpoint in `src/main.py` to upload files directly to your GCS bucket instead of saving them to the local filesystem.

2.  **Set up the Analysis Trigger:**
    *   Create a Google Cloud Function that triggers whenever a new video is uploaded to the specified GCS bucket. This function will be the starting point of the automated analysis pipeline.

3.  **Implement the Core Analysis Logic (in the Cloud Function):**
    *   **Call Google Video Intelligence API:** Use the video's GCS URL to start an analysis job.
    *   **Process API Response:** Parse the JSON output from the Video Intelligence API to extract shot detection times, object labels, and the audio transcript.
    *   **Store Metadata in Supabase:** Connect to your Supabase instance and insert a new record into the `videos` table with the extracted metadata.
    *   **Generate and Store Embeddings:** Use an embedding model (e.g., via the Gemini API) to create vector embeddings for the video summary and individual segments. Store these in your Zilliz Cloud vector database.

4.  **Implement the Prompt-to-Edit Logic:**
    *   The frontend already sends a prompt to the backend. You will need to create a new endpoint or extend the existing one to handle this.
    *   **Call Gemini API:** Send the user's prompt to the Gemini API to transform it into a structured "production plan" (e.g., a JSON object specifying shots, order, and duration).
    *   **Semantic Search:** Use the user's prompt to query the Zilliz Cloud database to find the most semantically similar video segments.

5.  **Implement Video Assembly:**
    *   **Call Creatomate API:** Take the production plan from Gemini and the segment timestamps retrieved from Supabase (via the semantic search results) and send them to the Creatomate API to generate the final video.

6.  **Handle Final Delivery:**
    *   Creatomate will render the video and return a URL. You need a mechanism to handle this asynchronous process.
    *   A common pattern is to have the client poll a status endpoint on your backend. Once the video is ready, the backend provides the final shareable URL to the client.
    *   The frontend JavaScript needs to be updated to implement this polling logic and display the final video link to the user.
