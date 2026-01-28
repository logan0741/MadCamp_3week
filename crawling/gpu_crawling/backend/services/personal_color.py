"""
Personal Color Analyzer - heuristic PCA (personal color analysis) pipeline.
Implements a lightweight 4-step flow with optional face detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from io import BytesIO

import numpy as np
from PIL import Image

try:
    import cv2  # type: ignore
    HAS_CV2 = True
except Exception:
    HAS_CV2 = False


@dataclass
class PersonalColorResult:
    base_tone: str  # warm/cool/neutral
    season: Optional[str]
    tone_type: Optional[str]
    kstyle: Optional[str]
    skin_tone_hex: Optional[str]
    lab_mean: Tuple[float, float, float]
    chroma: float
    contrast: float


# Heuristic seasonal palettes (hex colors)
SEASON_PALETTES = {
    "spring_warm": ["#f7c4a4", "#f6d36f", "#a9d6a1", "#9fd7e5", "#ff8f7a", "#f4b7c6"],
    "summer_cool": ["#f3b6c8", "#cbd7f6", "#b9c6d4", "#9fb5c9", "#d2b7d9", "#a0adb8"],
    "autumn_warm": ["#c96b4b", "#a56c3a", "#6f7b3a", "#b07c5b", "#7a4b2a", "#d2a24c"],
    "winter_cool": ["#c62828", "#3949ab", "#1565c0", "#00897b", "#212121", "#f5f5f5"],
}

BASE_TONE_PALETTES = {
    "warm": ["#f2b7a0", "#f2d06b", "#c97b63", "#a67c52", "#6e8b3d", "#ff8f7a"],
    "cool": ["#f2b6c6", "#c6d4ff", "#7b9fd9", "#5b6eae", "#2f3a6f", "#9fb5c9"],
    "neutral": ["#d9cbb6", "#bfc7ce", "#8f9aa6", "#6d6d6d", "#f2f2f2", "#2b2b2b"],
}


def _hex_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def get_recommended_palette(
    base_tone: Optional[str],
    season: Optional[str],
    tone_type: Optional[str],
    limit: int = 6,
) -> list[str]:
    palette = SEASON_PALETTES.get(season or "") or BASE_TONE_PALETTES.get(base_tone or "", [])
    if not palette:
        return []

    # Sort by luminance for tone_type filtering
    ordered = sorted(palette, key=_hex_luminance, reverse=True)

    if tone_type == "light":
        return ordered[:limit]
    if tone_type == "bright":
        return ordered[:limit]
    if tone_type == "deep":
        return ordered[-limit:]
    if tone_type == "muted":
        mid_start = max(0, (len(ordered) - limit) // 2)
        return ordered[mid_start:mid_start + limit]

    return ordered[:limit]


def _center_crop(image: Image.Image, ratio: float = 0.6) -> Image.Image:
    w, h = image.size
    crop_w = int(w * ratio)
    crop_h = int(h * ratio)
    left = (w - crop_w) // 2
    top = (h - crop_h) // 2
    return image.crop((left, top, left + crop_w, top + crop_h))


def _detect_face_bbox(image: Image.Image) -> Optional[Tuple[int, int, int, int]]:
    if not HAS_CV2:
        return None
    img = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    if len(faces) == 0:
        return None
    # Choose the largest face
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    return (x, y, w, h)


def _extract_face_region(image: Image.Image) -> Image.Image:
    bbox = _detect_face_bbox(image)
    if bbox:
        x, y, w, h = bbox
        return image.crop((x, y, x + w, y + h))
    return _center_crop(image, ratio=0.6)


def _skin_mask_ycbcr(rgb: np.ndarray) -> np.ndarray:
    ycbcr = Image.fromarray(rgb).convert("YCbCr")
    ycbcr_arr = np.asarray(ycbcr)
    cb = ycbcr_arr[:, :, 1]
    cr = ycbcr_arr[:, :, 2]
    mask = (cb >= 77) & (cb <= 127) & (cr >= 133) & (cr <= 173)
    return mask


def _rgb_to_lab(rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    rgb = rgb.astype(np.float32) / 255.0
    mask = rgb > 0.04045
    rgb = np.where(mask, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)

    # sRGB to XYZ (D65)
    matrix = np.array([
        [0.4124, 0.3576, 0.1805],
        [0.2126, 0.7152, 0.0722],
        [0.0193, 0.1192, 0.9505],
    ], dtype=np.float32)
    xyz = rgb @ matrix.T

    # Normalize by reference white
    xyz = xyz / np.array([0.95047, 1.0, 1.08883], dtype=np.float32)

    epsilon = 0.008856
    kappa = 903.3

    def f(t: np.ndarray) -> np.ndarray:
        return np.where(t > epsilon, np.cbrt(t), (kappa * t + 16) / 116)

    f_xyz = f(xyz)
    l = (116 * f_xyz[:, :, 1]) - 16
    a = 500 * (f_xyz[:, :, 0] - f_xyz[:, :, 1])
    b = 200 * (f_xyz[:, :, 1] - f_xyz[:, :, 2])
    return l, a, b


def _rgb_to_hex(rgb: Tuple[float, float, float]) -> str:
    r, g, b = [int(max(0, min(255, round(v)))) for v in rgb]
    return f"#{r:02x}{g:02x}{b:02x}"


def _classify_tone(base_tone: str, l_mean: float, chroma: float) -> Tuple[str, str]:
    # tone_type heuristic
    if l_mean >= 70 and chroma >= 35:
        tone_type = "bright"
    elif l_mean >= 70:
        tone_type = "light"
    elif l_mean < 50 and chroma >= 35:
        tone_type = "deep"
    else:
        tone_type = "muted"

    # season heuristic
    if base_tone == "warm":
        season = "spring_warm" if tone_type in ("bright", "light") else "autumn_warm"
    elif base_tone == "cool":
        season = "winter_cool" if tone_type in ("bright", "deep") else "summer_cool"
    else:
        season = "neutral"

    return season, tone_type


def analyze_personal_color(image_bytes: bytes) -> Dict[str, object]:
    """
    Analyze personal color from a user image.
    Returns dict compatible with API response and user profile fields.
    """
    image = Image.open(BytesIO(image_bytes))
    image = image.convert("RGB")

    face_region = _extract_face_region(image)
    face_arr = np.asarray(face_region)

    mask = _skin_mask_ycbcr(face_arr)
    if mask.sum() < 50:
        # Fallback to full face region
        mask = np.ones((face_arr.shape[0], face_arr.shape[1]), dtype=bool)

    l, a, b = _rgb_to_lab(face_arr)
    l_vals = l[mask]
    a_vals = a[mask]
    b_vals = b[mask]

    l_mean = float(np.mean(l_vals)) if l_vals.size else 0.0
    a_mean = float(np.mean(a_vals)) if a_vals.size else 0.0
    b_mean = float(np.mean(b_vals)) if b_vals.size else 0.0

    chroma = float(np.sqrt(a_mean ** 2 + b_mean ** 2))
    contrast = float(np.percentile(l_vals, 90) - np.percentile(l_vals, 10)) if l_vals.size else 0.0

    # Warm/Cool base tone
    delta = b_mean - a_mean
    if delta > 2:
        base_tone = "warm"
    elif delta < -2:
        base_tone = "cool"
    else:
        base_tone = "neutral"

    season, tone_type = _classify_tone(base_tone, l_mean, chroma)
    kstyle = f"{season}_{tone_type}" if season and tone_type else None

    # Skin tone hex
    skin_rgb = tuple(np.mean(face_arr[mask], axis=0)) if mask.any() else (0, 0, 0)
    skin_hex = _rgb_to_hex(skin_rgb)

    result = PersonalColorResult(
        base_tone=base_tone,
        season=season,
        tone_type=tone_type,
        kstyle=kstyle,
        skin_tone_hex=skin_hex,
        lab_mean=(round(l_mean, 2), round(a_mean, 2), round(b_mean, 2)),
        chroma=round(chroma, 2),
        contrast=round(contrast, 2),
    )

    recommended_palette = get_recommended_palette(
        base_tone=result.base_tone,
        season=result.season,
        tone_type=result.tone_type,
    )

    return {
        "base_tone": result.base_tone,
        "season": result.season,
        "tone_type": result.tone_type,
        "kstyle": result.kstyle,
        "skin_tone_hex": result.skin_tone_hex,
        "lab_mean": result.lab_mean,
        "chroma": result.chroma,
        "contrast": result.contrast,
        "recommended_palette": recommended_palette,
    }
