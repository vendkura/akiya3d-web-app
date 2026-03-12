# 🏠 Floorplan 3D Web App

**2D to 3D Converter for Japanese Floorplans**

A web application that converts 2D Japanese floorplan images into interactive 3D models using deep learning segmentation and procedural geometry generation.

---

## 📁 Project Structure

```
thesis-web-app/
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── main.py          # Application entry point
│   │   ├── config.py        # Configuration settings
│   │   ├── routes/          # API endpoints
│   │   │   └── convert.py   # Conversion endpoints
│   │   ├── services/        # Business logic
│   │   │   └── pipeline.py  # Pipeline orchestration
│   │   └── utils/           # Utilities
│   │       └── sse.py       # SSE helpers
│   ├── requirements.txt
│   └── run.py               # Dev server launcher
│
├── frontend/                 # Vue 3 frontend
│   ├── src/
│   │   ├── App.vue          # Main application
│   │   ├── components/      # UI components
│   │   │   ├── UploadPanel.vue
│   │   │   ├── ProgressSteps.vue
│   │   │   └── ModelViewer.vue
│   │   └── composables/     # Vue composables
│   │       └── useConversion.js
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- GPU with CUDA (optional, CPU works but slower)

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure paths (edit app/config.py)
# Update these paths to match your setup:
#   - project_root
#   - pipeline_path
#   - model_weights_path

# Run the server
python run.py
```

The API will be available at `http://localhost:8000`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

The app will be available at `http://localhost:5173`

---

## 🔧 Configuration

Edit `backend/app/config.py` to configure:

```python
# Path to your main project
project_root = Path(r"E:\github.com\akiya-3d-thesis")

# Path to pipeline modules
pipeline_path = Path(r"E:\github.com\akiya-3d-thesis\3D-Pipeline")

# Path to model weights
model_weights_path = Path(
    r"E:\github.com\akiya-3d-thesis\U-NET\scripts\model_output\fpn_62images\best_model.pth"
)
```

Or use environment variables via `.env` file.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/convert` | Upload image & convert (SSE stream) |
| `GET` | `/api/v1/download/{job_id}/{file}` | Download generated files |
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/warmup` | Pre-load model |

### SSE Progress Events

The `/convert` endpoint streams progress updates:

```json
{"name": "segmentation", "status": "running", "progress": 0, "message": "Running FPN inference..."}
{"name": "segmentation", "status": "completed", "progress": 100, "data": {"preview": "data:image/png;base64,..."}}
{"name": "boundary", "status": "running", ...}
...
{"success": true, "job_id": "abc123", "obj_url": "/api/v1/download/abc123/abc123.obj", ...}
```

---

## 🎨 Features

- **Drag & Drop Upload** - Easy image upload
- **Real-time Progress** - SSE streaming with step previews
- **3D Viewer** - Interactive model preview with orbit controls
- **Download Files** - OBJ, MTL, mask, boundaries JSON

---

## 🛠️ Development

### Backend

```bash
# Run with auto-reload
python run.py

# API docs available at:
# http://localhost:8000/docs
```

### Frontend

```bash
# Development
npm run dev

# Production build
npm run build
```

---

## 📋 Tech Stack

**Backend:**
- FastAPI
- PyTorch + segmentation-models-pytorch
- SSE-Starlette
- Python 3.10+

**Frontend:**
- Vue 3 (Composition API)
- TroisJS (Three.js wrapper)
- Vite

---

## 📝 License

Thesis Project - Akiya 3D Pipeline
