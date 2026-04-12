"""
FastAPI Server Entry Point.

This script exposes HTTP endpoints for the AI Job Prep Assistant.
It handles file uploads, dispatches background processing tasks, 
and provides endpoints to poll the job status and retrieve final results.
"""

import os
import uuid
import json
import tempfile
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .schemas import UploadResponse, JobStatusResponse, JobResultResponse, HealthResponse
from .services import process_job, get_s3_service
from config.settings import config
import botocore.exceptions
import logging

# Configure basic logging so logger.info shows up in the terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)

app = FastAPI(title="AI Job Prep Assistant API")

app.add_middleware(
    CORSMiddleware,
    # In production, replace the wildcard with your specific frontend domains
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify the API server is up and responsive.
    
    Returns:
        A JSON dictionary with a "healthy" status.
    """
    return {"status": "healthy"}

@app.post("/upload", response_model=UploadResponse)
def upload_files(
    background_tasks: BackgroundTasks,
    resume: UploadFile = File(...),
    job_description: UploadFile = File(...)
):
    """
    Accepts resume and job description file uploads from the frontend client.

    The files are temporarily saved to the local disk, and processing is offloaded 
    to a background task. It immediately returns a tracking Job ID.

    Args:
        background_tasks: FastAPI primitive for queueing asynchronous functions.
        resume: The uploaded resume PDF/Image file.
        job_description: The uploaded JD PDF/Image file.

    Returns:
        JSON response with the generated `job_id` and a success message.
    """
    # 1. Generate a unique ID to track this specific user session/job
    job_id = str(uuid.uuid4())
    temp_dir = tempfile.gettempdir()
    
    # 2. Build secure temporary file paths for both documents
    # Sanitize filenames to prevent directory traversal attacks
    safe_resume_name = os.path.basename(resume.filename) if resume.filename else "resume"
    safe_jd_name = os.path.basename(job_description.filename) if job_description.filename else "jd"
    resume_path = os.path.join(temp_dir, f"{job_id}_resume_{safe_resume_name}")
    jd_path = os.path.join(temp_dir, f"{job_id}_jd_{safe_jd_name}")
    
    # 3. Stream the uploaded content in chunks to local disk to prevent memory overflow
    MAX_FILE_SIZE = config.processing.max_file_size_bytes
    MAX_MB = config.processing.max_file_size_mb
    
    def write_upload(upload_file: UploadFile, dest: str):
        size = 0
        with open(dest, "wb") as f:
            while chunk := upload_file.file.read(1024 * 1024):  # 1MB chunks
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    f.close()
                    os.remove(dest)
                    raise HTTPException(status_code=413, detail=f"File {upload_file.filename} exceeds {MAX_MB}MB limit.")
                f.write(chunk)

    try:
        write_upload(resume, resume_path)
        write_upload(job_description, jd_path)
    except Exception:
        # If either file write fails for any reason, clean up any partially
        # written files to avoid leaking disk space before re-raising.
        if os.path.exists(resume_path):
            os.remove(resume_path)
        if os.path.exists(jd_path):
            os.remove(jd_path)
        raise
        
    # 4. Start the heavy AI processing pipeline in a background thread 
    #    so the web browser isn't forced to wait for it to complete.
    background_tasks.add_task(process_job, job_id, resume_path, jd_path)
    
    return {"job_id": job_id, "message": "Files uploaded successfully and processing started."}

@app.get("/status/{job_id}", response_model=JobStatusResponse)
def get_status(job_id: str):
    """
    Check the current processing status of an uploaded job.
    
    This endpoint does NOT track state in a database. Instead, it queries 
    the external AWS S3 bucket looking for a state file linked to the job_id.

    Args:
        job_id (str): The unique UUID returned by the /upload endpoint.

    Returns:
        JSON with the status: "processing", "completed", or "failed".
    """
    # Target S3 path where the background task saves its final state
    key = f"{config.s3.processed_prefix}{job_id}/result.json"
    
    try:
        # Try to download the state file from AWS S3
        data_bytes = get_s3_service().download_file_bytes(key)
        data = json.loads(data_bytes)
        
        # If the file exists, parse its 'status' attribute
        status = data.get("status", "completed")
        error = data.get("error")
        return {"job_id": job_id, "status": status, "error": error}
        
    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404' or error_code == 'NoSuchKey':
            # File not found means the background worker is still running 
            # and hasn't produced an output yet. We safely assume "processing".
            return {"job_id": job_id, "status": "processing"}
        # If another AWS error occurs (e.g. Permission Denied), crash naturally
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/result/{job_id}", response_model=JobResultResponse)
def get_result(job_id: str):
    """
    Retrieve the fully completed job output (the Final API Response).
    
    This retrieves the actual structured JSON containing the candidate 
    profile match scores, strengths, and weaknesses from the AI comparison.
    Ideally, call this endpoint only when /status/{job_id} returns "completed".

    Args:
        job_id (str): The unique UUID returned by the /upload endpoint.

    Returns:
        JSON blob identical to what the CLI version outputs to `result.json`.
    """
    # The expected output path of the final JSON result in S3
    key = f"{config.s3.processed_prefix}{job_id}/result.json"
    
    try:
        # Download, load from bytes to string, then parse as JSON
        data_bytes = get_s3_service().download_file_bytes(key)
        data = json.loads(data_bytes)
        
        status = data.get("status", "completed")
        error = data.get("error")
        # Extract the deep comparison output block to return to the frontend UI
        result = data.get("comparison") if status == "completed" else None
        
        return {"job_id": job_id, "status": status, "result": result, "error": error}
        
    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404' or error_code == 'NoSuchKey':
            # The client asked for a result before the job was done (or using bad ID)
            raise HTTPException(status_code=404, detail="Result not found. It might still be processing or job ID is invalid.")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    import os
    
    # 1. Fetch from the environment, falling back to localhost and 8000
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    reload_enabled = os.getenv("RELOAD", "false").strip().lower() in ("1", "true", "yes", "on")
    
    print(f"Starting server on http://{host}:{port} (reload={reload_enabled})")
    
    # 2. Programmatically start Uvicorn using the variables
    uvicorn.run("backend.main:app", host=host, port=port, reload=reload_enabled)