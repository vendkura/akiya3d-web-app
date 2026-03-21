"""
Floorplan 3D Pipeline API - Main Application
"""
import asyncio
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
    Pre-loads the model so the first convert request doesn't timeout.
    """
    # Startup
    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    print(f"📁 Pipeline path: {settings.pipeline_path}")
    print(f"🧠 Model weights: {settings.model_weights_path}")
    
    # Setup directories
    settings.setup_directories()
    print(f"📂 Upload dir: {settings.upload_dir.absolute()}")
    print(f"📂 Output dir: {settings.output_dir.absolute()}")
    
    # Check model weights
    try:
        from app.download_model import check_model_weights
        model_ready = check_model_weights()
        if model_ready:
            print("✅ Model weights are ready!")
        else:
            print("⚠️ Model weights not found - processing will fail!")
    except Exception as e:
        print(f"❌ Error checking model weights: {e}")
    
    # Pre-load the model at startup (background task)
    # This way the first /convert request won't spend time loading
    async def warmup():
        try:
            from app.services.pipeline import pipeline_service
            print("🔥 Warming up model at startup...")
            await pipeline_service.initialize()
            print("✅ Model pre-loaded and ready!")
        except Exception as e:
            print(f"⚠️ Startup warmup failed (will retry on first request): {e}")
    
    # Fire and forget - don't block startup
    asyncio.create_task(warmup())
    
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
            "health": "GET /health",
            "warmup": "POST /api/v1/warmup"
        }
    }

@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    from app.services.pipeline import pipeline_service
    
    model_exists = settings.model_weights_path.exists() if settings.model_weights_path else False
    
    return {
        "status": "healthy",
        "model_weights": {
            "path": str(settings.model_weights_path),
            "exists": model_exists,
            "size_mb": round(settings.model_weights_path.stat().st_size / 1024 / 1024, 2) if model_exists else None
        },
        "directories": {
            "uploads": settings.upload_dir.exists(),
            "outputs": settings.output_dir.exists()
        },
        "environment": {
            "debug": settings.debug,
            "has_model_url": bool(settings.model_weights_url),
            "device": settings.get_device().type
        },
        "pipeline": {
            "initialized": pipeline_service._initialized,
            "initializing": pipeline_service._initializing
        }
    }