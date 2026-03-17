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
        print("⚠️ No MODEL_WEIGHTS_URL environment variable configured.")
        print("💡 Set MODEL_WEIGHTS_URL to enable automatic model download.")
        return False
        
    model_path = settings.model_weights_path
    if model_path.exists():
        size_mb = round(model_path.stat().st_size / 1024 / 1024, 2)
        print(f"✅ Model already exists at: {model_path} ({size_mb} MB)")
        return True
        
    print(f"📥 Downloading model weights...")
    print(f"📍 From: {settings.model_weights_url}")
    print(f"📍 To: {model_path}")
    
    # Create models directory if it doesn't exist
    model_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        import urllib.request
        import time
        start_time = time.time()
        
        def progress_hook(block_num, block_size, total_size):
            if total_size > 0:
                percent = min(100, (block_num * block_size * 100) // total_size)
                mb_downloaded = (block_num * block_size) // (1024 * 1024)
                mb_total = total_size // (1024 * 1024)
                print(f"\r📥 Downloading: {percent}% ({mb_downloaded}/{mb_total} MB)", end="", flush=True)
        
        urllib.request.urlretrieve(settings.model_weights_url, model_path, progress_hook)
        
        elapsed = time.time() - start_time
        final_size = round(model_path.stat().st_size / 1024 / 1024, 2)
        print(f"\n✅ Model downloaded successfully!")
        print(f"📊 Size: {final_size} MB")
        print(f"⏱️ Time: {elapsed:.1f}s")
        return True
        
    except Exception as e:
        print(f"\n❌ Failed to download model: {e}")
        print("🔍 Possible issues:")
        print("  - Invalid URL")
        print("  - Network connectivity") 
        print("  - File permissions")
        print("  - Insufficient disk space")
        
        # Clean up partial download
        if model_path.exists():
            model_path.unlink()
            print("🧹 Cleaned up partial download")
        
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