"""
Conversion API Routes - Handles floorplan upload and processing
"""
import uuid
import json
import aiofiles
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.services.pipeline import pipeline_service

router = APIRouter(prefix="/api/v1", tags=["conversion"])


@router.post("/convert")
async def convert_floorplan(file: UploadFile = File(...)):
    """
    Convert a 2D floorplan image to 3D model.
    
    Returns an SSE stream with progress updates for each step.
    Sends an immediate acknowledgment event to prevent proxy timeouts.
    """
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Allowed: {allowed_types}"
        )
    
    # Generate job ID
    job_id = str(uuid.uuid4())[:8]
    
    # Ensure directories exist
    settings.setup_directories()
    
    # Save uploaded file
    upload_path = settings.upload_dir / f"{job_id}_{file.filename}"
    async with aiofiles.open(upload_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Create output directory for this job
    job_output_dir = settings.output_dir / job_id
    job_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Return SSE stream
    async def event_generator():
        try:
            # Send immediate acknowledgment so Render proxy sees a response fast
            yield {"data": json.dumps({
                "type": "ack",
                "job_id": job_id,
                "message": "Job accepted, starting pipeline..."
            })}
            
            print(f"🎬 Starting SSE generator for job: {job_id}")
            async for event_data in pipeline_service.process_image(
                image_path=upload_path,
                job_id=job_id,
                output_dir=job_output_dir
            ):
                print(f"📡 Sending SSE event: {event_data.get('type', 'unknown')}")
                yield {"data": json.dumps(event_data)}
        except Exception as e:
            print(f"❌ Error in SSE generator: {e}")
            import traceback
            traceback.print_exc()
            error_event = {
                "type": "error",
                "job_id": job_id,
                "message": str(e),
                "error": True
            }
            yield {"data": json.dumps(error_event)}
    
    return EventSourceResponse(
        event_generator(),
        ping=15,  # Send SSE ping every 15s to keep connection alive
    )


@router.get("/download/{job_id}/{filename}")
async def download_file(job_id: str, filename: str):
    """
    Download a generated file by job ID and filename.
    """
    file_path = settings.output_dir / job_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type
    media_types = {
        ".obj": "model/obj",
        ".mtl": "text/plain",
        ".png": "image/png",
        ".json": "application/json",
    }
    suffix = file_path.suffix.lower()
    media_type = media_types.get(suffix, "application/octet-stream")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type
    )


@router.get("/health")
async def health_check():
    """
    Health check endpoint - also reports if model is loaded.
    """
    return {
        "status": "healthy",
        "model_loaded": pipeline_service._initialized,
        "device": str(settings.get_device()) if pipeline_service._initialized else "not initialized"
    }


@router.post("/warmup")
async def warmup_model():
    """
    Pre-load the model to speed up first conversion.
    Call this on frontend load for better UX.
    """
    try:
        await pipeline_service.initialize()
        return {
            "status": "ready",
            "device": str(pipeline_service.device)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))