from pydantic import BaseModel
from typing import Optional, Dict, Any

class UploadResponse(BaseModel):
    job_id: str
    message: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    error: Optional[str] = None

class JobResultResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
