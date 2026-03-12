"""
Model weights downloader for deployment
"""
import os
import urllib.request
from pathlib import Path
from app.config import settings

def download_model_weights():
    """Download model weights from URL if configured"""
    if not settings.model_weights_url:
        print("⚠️ No model_weights_url configured. Skipping model download.")
        return False
        
    model_path = settings.model_weights_path
    if model_path.exists():
        print(f"✅ Model already exists at: {model_path}")
        return True
        
    print(f"📥 Downloading model weights from: {settings.model_weights_url}")
    
    # Create models directory if it doesn't exist
    model_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        urllib.request.urlretrieve(settings.model_weights_url, model_path)
        print(f"✅ Model downloaded successfully to: {model_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to download model: {e}")
        return False

def check_model_weights():
    """Check if model weights exist, try to download if not"""
    model_path = settings.model_weights_path
    
    if model_path.exists():
        print(f"✅ Model weights found at: {model_path}")
        return True
    
    print(f"⚠️ Model weights not found at: {model_path}")
    
    # Try to download if URL is configured
    if settings.model_weights_url:
        return download_model_weights()
    else:
        print("💡 To use model weights in production, set MODEL_WEIGHTS_URL environment variable")
        return False

if __name__ == "__main__":
    check_model_weights()