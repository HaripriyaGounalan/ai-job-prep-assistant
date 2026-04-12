import os
import uuid
import json
import tempfile
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .schemas import UploadResponse, JobStatusResponse, JobResultResponse, HealthResponse
from .services import process_job
from ocr_pipeline.services.s3_service import S3Service
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return {"status": "healthy"}

@app.post("/upload", response_model=UploadResponse)
async def upload_files(
    background_tasks: BackgroundTasks,
    resume: UploadFile = File(...),
    job_description: UploadFile = File(...)
):
    job_id = str(uuid.uuid4())
    temp_dir = tempfile.gettempdir()
    
    resume_path = os.path.join(temp_dir, f"{job_id}_resume_{resume.filename}")
    jd_path = os.path.join(temp_dir, f"{job_id}_jd_{job_description.filename}")
    
    with open(resume_path, "wb") as f:
        f.write(await resume.read())
        
    with open(jd_path, "wb") as f:
        f.write(await job_description.read())
        
    # Start the processing in the background
    background_tasks.add_task(process_job, job_id, resume_path, jd_path)
    
    return {"job_id": job_id, "message": "Files uploaded successfully and processing started."}

@app.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_status(job_id: str):
    s3 = S3Service()
    key = f"{config.s3.processed_prefix}{job_id}/result.json"
    
    try:
        data_bytes = s3.download_file_bytes(key)
        data = json.loads(data_bytes)
        
        status = data.get("status", "completed")
        error = data.get("error")
        return {"job_id": job_id, "status": status, "error": error}
        
    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404' or error_code == 'NoSuchKey':
            # File not found means it's still processing (or invalid ID)
            return {"job_id": job_id, "status": "processing"}
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/result/{job_id}", response_model=JobResultResponse)
async def get_result(job_id: str):
    s3 = S3Service()
    key = f"{config.s3.processed_prefix}{job_id}/result.json"
    
    try:
        data_bytes = s3.download_file_bytes(key)
        data = json.loads(data_bytes)
        
        status = data.get("status", "completed")
        error = data.get("error")
        result = data.get("comparison") if status == "completed" else None
        
        return {"job_id": job_id, "status": status, "result": result, "error": error}
        
    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404' or error_code == 'NoSuchKey':
            raise HTTPException(status_code=404, detail="Result not found. It might still be processing or job ID is invalid.")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
