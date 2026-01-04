import uuid
import os
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from app.workers.tasks.scraper import perform_scrape_task
# from app.core.auth import get_current_user # Assume auth exists

router = APIRouter()

class WebCaptureRequest(BaseModel):
    url: str
    html: str
    title: str
    layer_id: str = "user_private"

@router.post("/save", status_code=status.HTTP_202_ACCEPTED)
async def save_web_capture(
    request: WebCaptureRequest,
    # user = Depends(get_current_user) # Uncomment when auth is ready
):
    """
    Receive HTML from browser extension, save to storage, and trigger ingestion.
    """
    doc_id = str(uuid.uuid4())
    filename = f"{doc_id}.html"
    
    # Save to shared storage (simulating MinIO/S3 for now to avoid extra deps)
    # In production, replace with boto3 upload to MinIO
    storage_path = os.getenv("STORAGE_PATH", "/app/storage/raw/web")
    os.makedirs(storage_path, exist_ok=True)
    file_path = os.path.join(storage_path, filename)
    
    async with aiofiles.open(file_path, 'w') as f:
        await f.write(request.html)
        
    # Trigger ingestion task
    # We reuse the scraper task or a new ingestion task. 
    # Since scraper task expects URL and scrapes, we might need a dedicated 
    # "ingest_raw_html" task. For now, let's assume we have one or mock it.
    # Ideally: ingest_web_content.delay(doc_id, file_path, request.layer_id)
    
    # For MVP, we'll log it. In real impl, add `ingest_web_content` to tasks.
    # perform_scrape_task.delay(request.url, request.layer_id) # This re-scrapes!
    
    return {
        "status": "accepted", 
        "doc_id": doc_id, 
        "message": "Content saved and queued for ingestion"
    }
