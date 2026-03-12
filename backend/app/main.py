"""
Floorplan 3D Pipeline API - Main Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.config import settings
from app.routes import convert_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.
    """
    # Startup
    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    print(f"📁 Pipeline path: {settings.pipeline_path}")
    print(f"🧠 Model weights: {settings.model_weights_path}")
    
    # Setup directories
    settings.setup_directories()
    print(f"📂 Upload dir: {settings.upload_dir.absolute()}")
    print(f"📂 Output dir: {settings.output_dir.absolute()}")
    
    yield
    
    # Shutdown
    print("👋 Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Convert 2D Japanese floorplans to 3D models",
    lifespan=lifespan
)

# CORS middleware for Vue frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(convert_router)

# Serve static files (outputs) - optional, for direct file access
# app.mount("/files", StaticFiles(directory=settings.output_dir), name="files")


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "endpoints": {
            "convert": "POST /api/v1/convert",
            "download": "GET /api/v1/download/{job_id}/{filename}",
            "health": "GET /api/v1/health",
            "warmup": "POST /api/v1/warmup"
        }
    }
