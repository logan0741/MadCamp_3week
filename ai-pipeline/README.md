# AI Pipeline - 3D Garment Reconstruction System

## Master Implementation Prompt (Immutable Memory)

This section preserves the full project vision for any future AI agent continuation.

### Project Vision
High-precision 3D garment visualization system that reconstructs size-accurate 3D garments from dual-view Musinsa product images and size charts, applying SNUG-based physics for realistic behavior.

### Hardware Constraints
- **VRAM**: 20GB available
- **Storage**: 96GB available
- **Target**: GLB export for Unity WebGL viewer

### Core Pipeline Architecture
```
[Musinsa Product Images] → [Dual-View Segmentation] → [Size-Accurate Scaling]
         ↓                         ↓                          ↓
    Front + Back            fashn-human-parser          cm-to-Vertex
         ↓                         ↓                          ↓
   [Texture Extraction] → [Template Mesh Loading] → [Non-Uniform Scaling]
                                   ↓
                    [SNUG Physics Simulation]
                                   ↓
                    [GLB Export with SMPL-X Rigging]
```

### Five Missions
1. **Context Preservation** - README.md + development_progress.md logging
2. **Dual-View Segmentation** - fashn-human-parser with VRAM management
3. **Size-Accurate Reconstruction** - cm-to-vertex non-uniform scaling
4. **Physics Simulation** - SNUG framework for realistic draping
5. **GLB Export** - Unity-ready rigged output with UV atlas

### Key Technical Requirements
- Non-uniform vertex scaling: Independent $S_x, S_y, S_z$ scale factors
- UV Atlas: $2048 \times 1024$ resolution blending front/back textures
- Skeletal Mapping: SMPL-X hierarchy for future interaction
- Physics State: Pre-computed for responsive rotation/touch

---

## Current Infrastructure Status

### Existing Components (Ready to Use)
| Component | Location | Status |
|-----------|----------|--------|
| FashnHumanParser | `models/segmentation/fashn_parser.py` | Working |
| Size Scaler | `models/scaling/size_scaler.py` | Working |
| SNUG Wrapper | `models/garment/snug_wrapper.py` | Fallback mode |
| GLB Exporter | `models/export/unity_exporter.py` | Working |
| VRAM Manager | `workers/vram_manager.py` | Production-ready |
| Template Meshes | `models/3d/snug/assets/meshes/` | 5 types available |
| Mannequin Generator | `models/smplx/mannequin.py` | Working |

### Components to Enhance
| Component | Gap | Priority |
|-----------|-----|----------|
| SNUG Neural Model | Uses fallback physics, needs TF weights | High |
| Dual-View Pipeline | Single-image only, needs front+back fusion | High |
| Size Integration | Template scaling, needs cm verification | Medium |

---

## Quick Start

```bash
# Activate environment
cd /home/MadCamp/MadCamp_3week/ai-pipeline
source venv/bin/activate

# Start Redis (required for async tasks)
redis-server --daemonize yes

# Start API server
python3 api/main.py  # Port 8001

# Start Celery worker
celery -A workers.celery_app worker -Q vton,garment --loglevel=info
```

## API Endpoints

### Garment Processing
```bash
POST /api/garment/process
{
  "product_id": "123456",
  "front_image_url": "https://...",
  "back_image_url": "https://...",
  "target_size": "M"
}
```

### Health Check
```bash
GET /health
GET /vram-status
```

---

## Development Progress

See `development_progress.md` for detailed checkpoint states and implementation progress.

---

*Last Updated: 2026-01-26*
*Version: 2.0.0 (Phase 1: High-Precision Infrastructure)*
