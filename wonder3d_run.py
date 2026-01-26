import os
import sys
from datetime import datetime

# Ensure Wonder3D repo is on PYTHONPATH for mvdiffusion
REPO_PATH = "/home/MadCamp/MadCamp_3week/wonder3d_repo"
if REPO_PATH not in sys.path:
    sys.path.append(REPO_PATH)

import torch
import numpy as np
from PIL import Image
from diffusers import DiffusionPipeline
from torchvision.utils import make_grid, save_image

INPUT_PATH = "/home/MadCamp/KakaoTalk_20260126_202233039.jpg"
OUT_ROOT = "/home/MadCamp/MadCamp_3week/wonder3d_outputs"
TARGET_SIZE = 256  # pipeline expects 256x256
CROP_MARGIN = 0.08  # extra margin around subject

os.makedirs(OUT_ROOT, exist_ok=True)
out_dir = os.path.join(OUT_ROOT, datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(out_dir, exist_ok=True)

# Load image
orig = Image.open(INPUT_PATH).convert("RGB")
orig.save(os.path.join(out_dir, "input_original.jpg"))

# Background removal
def remove_background(image: Image.Image) -> Image.Image:
    try:
        from rembg import remove
    except Exception as e:
        print(f"rembg not available: {e}")
        return image.convert("RGBA")
    try:
        return remove(image)
    except Exception as e:
        print(f"rembg failed: {e}")
        return image.convert("RGBA")

# Crop around alpha mask
def crop_by_alpha(rgba: Image.Image, margin: float = 0.08) -> Image.Image:
    arr = np.array(rgba)
    if arr.shape[2] < 4:
        return rgba
    alpha = arr[:, :, 3]
    ys, xs = np.where(alpha > 10)
    if len(xs) == 0 or len(ys) == 0:
        return rgba
    x0, x1 = xs.min(), xs.max()
    y0, y1 = ys.min(), ys.max()
    # Add margin
    h, w = alpha.shape
    dx = int((x1 - x0 + 1) * margin)
    dy = int((y1 - y0 + 1) * margin)
    x0 = max(0, x0 - dx)
    x1 = min(w - 1, x1 + dx)
    y0 = max(0, y0 - dy)
    y1 = min(h - 1, y1 + dy)
    return rgba.crop((x0, y0, x1 + 1, y1 + 1))

# Pad to square
def pad_to_square(rgba: Image.Image) -> Image.Image:
    w, h = rgba.size
    side = max(w, h)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    offset = ((side - w) // 2, (side - h) // 2)
    canvas.paste(rgba, offset)
    return canvas

rgba = remove_background(orig)
rgba.save(os.path.join(out_dir, "input_no_bg.png"))

cropped = crop_by_alpha(rgba, margin=CROP_MARGIN)
boxed = pad_to_square(cropped)
boxed.save(os.path.join(out_dir, "input_crop.png"))

# Convert to RGB and resize for pipeline
cond = boxed.convert("RGB").resize((TARGET_SIZE, TARGET_SIZE), Image.BICUBIC)
cond.save(os.path.join(out_dir, "input_256.jpg"))

# Load pipeline
pipe = DiffusionPipeline.from_pretrained(
    "flamehaze1115/wonder3d-v1.0",
    custom_pipeline="flamehaze1115/wonder3d-pipeline",
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
)

# Optional xformers
try:
    pipe.unet.enable_xformers_memory_efficient_attention()
except Exception as e:
    print(f"xformers not enabled: {e}")

if torch.cuda.is_available():
    pipe.to("cuda:0")

# Run inference
with torch.inference_mode():
    images = pipe(
        cond,
        num_inference_steps=20,
        output_type="pt",
        guidance_scale=1.0,
    ).images

# Save grid
grid = make_grid(images, nrow=6, padding=0, value_range=(0, 1))
save_image(grid, os.path.join(out_dir, "mv_grid.png"))

# Save individual views
for i, img in enumerate(images):
    save_image(img, os.path.join(out_dir, f"view_{i:02d}.png"), value_range=(0, 1))

print(f"Saved outputs to: {out_dir}")
