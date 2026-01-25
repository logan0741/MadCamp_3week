# Musinsa AI Pipeline

AI-powered virtual try-on and 3D avatar generation system for Musinsa price tracking service.

## 📋 Overview

This pipeline provides three core functionalities:

1. **2D Virtual Try-On (IDM-VTON)**: Instant preview (<1 second) of garments on user's body
2. **3D Avatar Generation (ECON + SMPL-X + 3DGS)**: High-fidelity digital twin creation from video
3. **3D Garment Modeling (BCNet)**: Convert 2D product images to 3D meshes

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- CUDA 11.8+ (for GPU acceleration)
- 96GB VRAM (4x RTX 3090 or equivalent)
- Redis server (for Celery)
- Docker (optional, for containerized deployment)

### Installation

```bash
# 1. Clone repository (already done)
cd /root/MadCamp_3week/ai-pipeline

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install PyTorch with CUDA support
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 4. Install dependencies
pip install -r requirements.txt

# 5. Copy environment file and configure
cp .env.example .env
nano .env  # Edit configuration

# 6. Create necessary directories
python3 config.py  # This auto-creates directories

# 7. Download model weights (see Model Setup below)
```

### Model Setup

#### IDM-VTON (HuggingFace)

```bash
# Models are automatically downloaded on first use
# Cache location: $VTON_CACHE_DIR (default: ./models/weights/vton_cache)
```

#### ECON, BCNet, 3DGS (Manual)

```bash
# TODO: Add download links for model weights
# Expected structure:
# models/weights/
# ├── econ/
# │   └── econ_checkpoint.pth
# ├── bcnet/
# │   └── bcnet_checkpoint.pth
# ├── smplx/
# │   └── SMPLX_NEUTRAL.npz
# └── 3dgs/
#     └── point_cloud.ply
```

### Running the API Server

```bash
# Start Redis (required for Celery)
redis-server

# Start API server (in new terminal)
cd /root/MadCamp_3week/ai-pipeline
source venv/bin/activate
python3 api/main.py

# API will be available at http://localhost:8001
```

### Running Celery Workers

```bash
# Start Celery worker for heavy tasks (in new terminal)
cd /root/MadCamp_3week/ai-pipeline
source venv/bin/activate

celery -A workers.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --max-tasks-per-child=10 \
    --queues=vton,avatar,garment

# Monitor with Flower (optional)
celery -A workers.celery_app flower --port=5555
# Access dashboard at http://localhost:5555
```

## 📁 Project Structure

```
ai-pipeline/
├── api/                      # FastAPI REST API
│   ├── main.py              # API entry point
│   ├── routers/             # API route handlers
│   │   └── vton.py          # VTON endpoints
│   └── schemas/             # Pydantic models
│       ├── common.py        # Shared schemas
│       └── vton.py          # VTON schemas
│
├── models/                   # AI model implementations
│   └── vton/                # IDM-VTON pipeline
│       ├── idm_vton.py      # Main model wrapper
│       ├── preprocessor.py  # Image preprocessing
│       └── postprocessor.py # Output enhancement
│
├── workers/                  # Celery background tasks
│   ├── celery_app.py        # Celery configuration
│   ├── vram_manager.py      # VRAM resource management
│   └── tasks/               # Task definitions
│       └── vton_tasks.py    # VTON async tasks
│
├── data/                     # Data storage
│   ├── uploads/             # User uploads
│   └── outputs/             # Generated results
│       └── vton/            # VTON outputs
│
├── docs/                     # Documentation
│   └── UNITY_REQUIREMENTS.md  # Unity developer guide
│
├── config.py                 # Configuration management
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
└── README.md                # This file
```

## 🔌 API Endpoints

### Health Check

```bash
GET /health

Response:
{
  "status": "healthy",
  "cuda_available": true,
  "cuda_devices": 4
}
```

### VRAM Status

```bash
GET /vram-status

Response:
{
  "total_devices": 4,
  "devices": [
    {
      "device_id": 0,
      "name": "NVIDIA GeForce RTX 3090",
      "allocated_gb": 12.5,
      "total_gb": 24.0,
      "utilization_percent": 52.08
    },
    ...
  ]
}
```

### Virtual Try-On

#### Synchronous (URL Input)

```bash
POST /api/vton/try-on
Content-Type: application/json

{
  "person_image_url": "https://example.com/person.jpg",
  "garment_image_url": "https://example.com/garment.jpg",
  "num_inference_steps": 50,
  "guidance_scale": 7.5,
  "enhance_output": true,
  "restore_face": true
}

Response:
{
  "success": true,
  "result_url": "http://localhost:8001/outputs/vton/result_abc123.png",
  "processing_time_seconds": 2.35,
  "vram_allocated_mb": 8192.5
}
```

#### File Upload

```bash
POST /api/vton/try-on/upload
Content-Type: multipart/form-data

Form Data:
  person_image: <file>
  garment_image: <file>
  num_inference_steps: 50
  guidance_scale: 7.5

Response: Same as above
```

#### Batch Processing

```bash
POST /api/vton/try-on/batch
Content-Type: application/json

{
  "requests": [
    {
      "person_image_url": "https://example.com/person1.jpg",
      "garment_image_url": "https://example.com/garment1.jpg"
    },
    {
      "person_image_url": "https://example.com/person2.jpg",
      "garment_image_url": "https://example.com/garment2.jpg"
    }
  ]
}

Response:
{
  "success": true,
  "results": [...],
  "total_processing_time_seconds": 4.8
}
```

## 🧪 Testing

```bash
# Test VTON endpoint
curl -X POST "http://localhost:8001/api/vton/try-on" \
  -H "Content-Type: application/json" \
  -d '{
    "person_image_url": "https://example.com/person.jpg",
    "garment_image_url": "https://example.com/garment.jpg"
  }'

# Check VRAM usage
curl "http://localhost:8001/vram-status"

# Test Celery connection
cd /root/MadCamp_3week/ai-pipeline
python3 -c "from workers.celery_app import debug_task; print(debug_task.delay().get())"
```

## ⚙️ Configuration

Key environment variables (see `.env.example` for full list):

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PORT` | 8001 | API server port |
| `VTON_IMAGE_SIZE` | 768 | VTON input/output resolution |
| `VTON_NUM_INFERENCE_STEPS` | 50 | Quality vs speed tradeoff |
| `VRAM_VTON` | 16 | VRAM allocated for VTON (GB) |
| `CELERY_MAX_CONCURRENT` | 2 | Max parallel Celery tasks |
| `CUDA_VISIBLE_DEVICES` | 0,1,2,3 | Available GPU devices |

## 📊 Performance Benchmarks

| Operation | Time (RTX 3090) | VRAM Usage |
|-----------|-----------------|------------|
| VTON Inference (50 steps) | ~2.5 seconds | 12-16 GB |
| ECON Avatar Generation | ~5 minutes | 30-40 GB |
| BCNet Garment Modeling | ~2 minutes | 15-20 GB |

## 🔧 Troubleshooting

### CUDA Out of Memory

```bash
# Check VRAM usage
curl http://localhost:8001/vram-status

# Reload model to clear cache
curl -X POST http://localhost:8001/api/vton/model/reload

# Or manually clear in Python
python3 -c "import torch; torch.cuda.empty_cache()"
```

### Celery Tasks Not Running

```bash
# Check Redis connection
redis-cli ping

# Check Celery worker status
celery -A workers.celery_app inspect active

# Restart worker
pkill -f "celery worker"
celery -A workers.celery_app worker --loglevel=info
```

### Model Download Issues

```bash
# Set HuggingFace cache directory
export HF_HOME=/root/MadCamp_3week/ai-pipeline/models/weights/hf_cache

# Use mirror (if blocked)
export HF_ENDPOINT=https://hf-mirror.com
```

## 🚢 Deployment

### Docker (Recommended)

```bash
# TODO: Add Dockerfile and docker-compose.yml

# Build image
docker build -t musinsa-ai-pipeline .

# Run with GPU support
docker run --gpus all -p 8001:8001 musinsa-ai-pipeline
```

### Systemd Service

```bash
# TODO: Add systemd service files

# /etc/systemd/system/musinsa-ai.service
# /etc/systemd/system/musinsa-celery.service
```

## 📝 Unity Integration

Unity developers should refer to [docs/UNITY_REQUIREMENTS.md](docs/UNITY_REQUIREMENTS.md) for:
- 3D avatar viewer implementation
- Garment fitting system
- React ↔ Unity communication protocol
- Performance optimization guidelines

## 🤝 Contributing

1. Follow Python PEP 8 style guide
2. Add type hints to all functions
3. Write docstrings for public APIs
4. Test VRAM cleanup after changes
5. Update this README for new features

## 📜 License

TBD - Proprietary for MadCamp 3-week project

## 🔗 Links

- **Hugging Face Models**: https://huggingface.co/yisol/IDM-VTON
- **ECON Paper**: https://arxiv.org/abs/2212.07422
- **SMPL-X**: https://smpl-x.is.tue.mpg.de/
- **3D Gaussian Splatting**: https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/

---

**Last Updated**: 2026-01-24
**Version**: 1.0.0
**Team**: MadCamp Week 3 - AI Pipeline
