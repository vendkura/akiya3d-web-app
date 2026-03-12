"""
Configuration for the Floorplan 3D Pipeline API
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional
import os
import platform


def get_default_project_root() -> Path:
    """Get default project root based on OS"""
    if platform.system() == "Windows":
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
    port: int = 8000
    
    # CORS Settings (for Vue frontend)
    cors_origins: list[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    
    # Path Configuration - Override via .env file or environment variables
    project_root: Optional[Path] = None
    pipeline_path: Optional[Path] = None
    model_weights_path: Optional[Path] = None
    
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
    
    def model_post_init(self, __context):
        """Set default paths after model initialization based on OS"""
        default_root = get_default_project_root()
        
        if self.project_root is None:
            self.project_root = default_root
        if self.pipeline_path is None:
            self.pipeline_path = self.project_root / "3D-Pipeline"
        if self.model_weights_path is None:
            self.model_weights_path = self.project_root / "U-NET" / "scripts" / "model_output" / "fpn_62images" / "best_model.pth"
    
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
