# Render Deployment Guide

## Backend Deployment on Render

### 1. Repository Setup
- Push your code to GitHub  
- Connect your GitHub repo to Render

### 2. Render Service Configuration
**Service Type**: Web Service
**Runtime**: Python 3
**Root Directory**: `./backend` (IMPORTANT: Set this in Render dashboard)
**Build Command**: `pip install -r requirements.txt && python download_model.py`
**Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 3. Model Weights Handling

**Option A: Host model externally (Recommended)**
```
MODEL_WEIGHTS_URL=https://github.com/yourusername/yourrepo/releases/download/v1.0/best_model.pth
```

**Option B: Bundle with repository (if < 100MB)**
- Place `best_model.pth` in `backend/models/` folder
- Remove `*.pth` from `.gitignore` temporarily
- Commit and push

**Option C: Use cloud storage**
```
MODEL_WEIGHTS_URL=https://drive.google.com/uc?export=download&id=YOUR_FILE_ID
```

### 4. Environment Variables (Set in Render Dashboard)
```
DEBUG=false
MODEL_WEIGHTS_URL=https://your-model-download-url.com/best_model.pth
CORS_ORIGINS=["https://your-frontend-domain.netlify.app"]
```

### 5. Important Notes
- Render automatically detects Python and installs dependencies
- The `$PORT` environment variable is provided by Render
- Model will be downloaded automatically on first build
- Your backend URL: `https://your-backend-name.onrender.com`