"""
Configuration for the Floorplan 3D Pipeline API
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os
import platform


def get_default_project_root() -> Path:
    """Get default project root based on OS and environment"""
    # Check if running in cloud environment (Render, Heroku, etc.)
    if os.getenv("RENDER") or os.getenv("DYNO"):  # Render or Heroku
        return Path("/opt/render/project/src")
    elif platform.system() == "Windows":
        return Path(r"E:\github.com\akiya-3d-thesis")
    else:
        # WSL/Linux - Windows drives are mounted under /mnt/
        return Path("/mnt/e/github.com/akiya-3d-thesis")


class Settings(BaseSettings):
    """Application settings - can be overridden via environment variables"""
    
    # API Settings
    app_name: str = "Floorplan 3D API"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # Server Settings
    host: str = "0.0.0.0"
    port: int = int(os.getenv("PORT", "8000"))  # Use PORT from environment (Render/Heroku) or default to 8000
    
    # CORS Settings (for Vue frontend)
    # Don't set via environment variables - use code defaults
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:5173",  # Vite dev server
            "http://localhost:3000",  # Alternative dev port
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
            # Production URLs - update these when you deploy
            "https://*.vercel.app",  # All Vercel subdomains 
            "https://*.netlify.app",  # All Netlify subdomains (backup)
            "https://floorplan-3d-converter.vercel.app",  # Your specific frontend URL
        ],
        env=None
    )
    
    # Model Configuration
    # Path to the trained model weights directory  
    project_root: Optional[Path] = None
    pipeline_path: Optional[Path] = None
    model_weights_path: Optional[Path] = None
    
    # Model weights URL for cloud deployment (if hosting model externally)
    model_weights_url: Optional[str] = None
    
    # Output directories
    upload_dir: Path = Path("./uploads")
    output_dir: Path = Path("./outputs")
    
    # Pipeline Settings
    room_height: float = 2.5  # meters
    wall_thickness: float = 0.1  # meters (10cm)
    
    # Processing Settings
    device: str = "auto"  # "auto", "cuda", or "cpu"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Exclude cors_origins from environment variable parsing to avoid JSON issues
        env_ignore = {"cors_origins"}
    
    def model_post_init(self, __context):
        """Set default paths after model initialization based on OS"""
        # On Render/cloud, use local paths instead of trying to access project root
        is_cloud = os.getenv("RENDER") or os.getenv("DYNO")
        
        if is_cloud:
            # On cloud deployment, use only local relative paths
            if self.model_weights_path is None:
                self.model_weights_path = Path("./models/best_model.pth")
        else:
            # Local development - use full project paths
            default_root = get_default_project_root()
            
            if self.project_root is None:
                self.project_root = default_root
            if self.pipeline_path is None:
                self.pipeline_path = self.project_root / "3D-Pipeline"
            if self.model_weights_path is None:
                # Try multiple possible locations for model weights
                possible_paths = [
                    self.project_root / "U-NET" / "scripts" / "model_output" / "fpn_62images" / "best_model.pth",
                    Path("./models/best_model.pth"),  # Local models folder
                    Path("./best_model.pth"),  # Root of backend folder
                ]
                
                # Use first existing path or default to local models folder
                for path in possible_paths:
                    if path.exists():
                        self.model_weights_path = path
                        break
                else:
                    # Default to models folder (create if deployment needs it)
                    self.model_weights_path = Path("./models/best_model.pth")
    
    def setup_directories(self):
        """Create necessary directories if they don't exist"""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_device(self):
        """Get torch device based on settings"""
        import torch
        if self.device == "auto":
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return torch.device(self.device)


# Global settings instance
settings = Settings()
