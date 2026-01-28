"""
Color Analyzer - PCCS Color Analysis and Style Matching
Extracts dominant colors from clothing images and converts to PCCS coordinates.
"""

import asyncio
import colorsys
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import httpx
from io import BytesIO

from services.musinsa_proxy import proxify_url, proxy_headers, httpx_proxies
try:
    import numpy as np
    from PIL import Image
    from sklearn.cluster import KMeans
    HAS_ML_DEPS = True
except ImportError:
    HAS_ML_DEPS = False
    print("Warning: numpy, PIL, or sklearn not installed. Color analysis disabled.")


# PCCS Tone definitions based on Value and Chroma
# Format: (min_value, max_value, min_chroma, max_chroma)
PCCS_TONE_MAP = {
    'v':   (5.5, 7.5, 9, 14),    # Vivid - high chroma, medium-high value
    'b':   (6.5, 8.5, 6, 9),     # Bright - high value, medium-high chroma
    's':   (5.0, 7.0, 6, 9),     # Strong - medium value, medium-high chroma
    'dp':  (3.5, 5.5, 6, 9),     # Deep - low-medium value, medium-high chroma
    'lt':  (7.5, 9.0, 3, 6),     # Light - high value, low-medium chroma
    'sf':  (5.5, 7.5, 3, 6),     # Soft - medium value, low-medium chroma
    'd':   (4.0, 5.5, 3, 6),     # Dull - low-medium value, low-medium chroma
    'dk':  (2.5, 4.0, 3, 6),     # Dark - low value, low-medium chroma
    'p':   (8.5, 9.5, 0, 3),     # Pale - very high value, very low chroma
    'ltg': (7.0, 8.5, 0, 3),     # Light grayish - high value, very low chroma
    'g':   (4.5, 7.0, 0, 3),     # Grayish - medium value, very low chroma
    'dkg': (2.0, 4.5, 0, 3),     # Dark grayish - low value, very low chroma
    'W':   (9.5, 10.0, 0, 0.5),  # White
    'Bk':  (0, 2.0, 0, 0.5),     # Black
    'Gy':  (2.0, 9.5, 0, 0.5),   # Gray
}


@dataclass
class PCCSColor:
    """PCCS Color representation"""
    hue: float          # 0-360 degrees
    value: float        # 0-10 (lightness)
    chroma: float       # 0-14 (saturation intensity)
    tone: str           # PCCS tone code (v, b, s, dp, lt, sf, d, dk, p, ltg, g, dkg)
    hex_color: str      # Original hex color


@dataclass
class ColorAnalysisResult:
    """Result of color analysis"""
    primary_color: PCCSColor
    secondary_colors: List[PCCSColor]
    dominant_hex: str
    color_palette: List[str]  # List of hex colors
    category_suggestion: str  # warm/cool/neutral


def rgb_to_pccs(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """
    Convert RGB (0-255) to PCCS-like coordinates.
    Returns (hue: 0-360, value: 0-10, chroma: 0-14)

    Note: This is an approximation since true PCCS requires physical color samples.
    We use HSV as a basis and map to PCCS-like coordinates.
    """
    # Normalize to 0-1
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0

    # Convert to HLS (Hue, Lightness, Saturation)
    h, l, s = colorsys.rgb_to_hls(r_norm, g_norm, b_norm)

    # Map to PCCS coordinates
    hue = h * 360  # 0-360 degrees

    # Value in PCCS is similar to Munsell Value (0-10 scale)
    # We approximate using lightness
    value = l * 10

    # Chroma in PCCS (0-14) approximated from saturation and lightness
    # Chroma is highest when lightness is mid-range and saturation is high
    chroma_factor = 1 - abs(l - 0.5) * 2  # Max at l=0.5
    chroma = s * chroma_factor * 14

    return (hue, value, chroma)


def determine_pccs_tone(value: float, chroma: float) -> str:
    """
    Determine PCCS tone based on value and chroma coordinates.
    """
    # Handle achromatic colors first
    if chroma < 0.5:
        if value >= 9.5:
            return 'W'
        elif value <= 2.0:
            return 'Bk'
        else:
            return 'Gy'

    # Find best matching tone
    best_tone = 'g'  # Default fallback
    min_distance = float('inf')

    for tone, (v_min, v_max, c_min, c_max) in PCCS_TONE_MAP.items():
        if tone in ['W', 'Bk', 'Gy']:
            continue

        # Calculate distance to tone's center
        v_center = (v_min + v_max) / 2
        c_center = (c_min + c_max) / 2

        # Check if in range
        if v_min <= value <= v_max and c_min <= chroma <= c_max:
            return tone

        # Calculate distance for fallback
        v_dist = min(abs(value - v_min), abs(value - v_max)) if not (v_min <= value <= v_max) else 0
        c_dist = min(abs(chroma - c_min), abs(chroma - c_max)) if not (c_min <= chroma <= c_max) else 0
        distance = v_dist + c_dist

        if distance < min_distance:
            min_distance = distance
            best_tone = tone

    return best_tone


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB to hex color code."""
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def analyze_rgb_color(r: int, g: int, b: int) -> PCCSColor:
    """Analyze a single RGB color and return PCCS representation."""
    hue, value, chroma = rgb_to_pccs(r, g, b)
    tone = determine_pccs_tone(value, chroma)
    hex_color = rgb_to_hex(r, g, b)

    return PCCSColor(
        hue=round(hue, 1),
        value=round(value, 2),
        chroma=round(chroma, 2),
        tone=tone,
        hex_color=hex_color
    )


def determine_color_temperature(hue: float) -> str:
    """Determine if a color is warm, cool, or neutral based on hue."""
    # Warm colors: Red, Orange, Yellow (roughly 0-60, 300-360)
    # Cool colors: Green, Blue, Purple (roughly 120-270)
    # Neutral: transitions

    if (0 <= hue <= 60) or (300 <= hue <= 360):
        return 'warm'
    elif 120 <= hue <= 270:
        return 'cool'
    else:
        return 'neutral'


async def download_image(url: str) -> Optional[bytes]:
    """Download image from URL."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.musinsa.com/',
    }
    headers.update(proxy_headers())

    try:
        async with httpx.AsyncClient(timeout=30.0, proxies=httpx_proxies()) as client:
            response = await client.get(proxify_url(url), headers=headers, follow_redirects=True)
            if response.status_code == 200:
                return response.content
    except Exception as e:
        print(f"Failed to download image: {e}")

    return None


def extract_dominant_colors(
    image_bytes: bytes,
    n_colors: int = 5,
    exclude_background: bool = True
) -> List[Tuple[int, int, int]]:
    """
    Extract dominant colors from an image using K-means clustering.

    Args:
        image_bytes: Raw image bytes
        n_colors: Number of dominant colors to extract
        exclude_background: Try to exclude white/black backgrounds

    Returns:
        List of RGB tuples sorted by dominance
    """
    if not HAS_ML_DEPS:
        return []

    try:
        # Load image
        img = Image.open(BytesIO(image_bytes))
        img = img.convert('RGB')

        # Resize for faster processing
        img.thumbnail((200, 200))

        # Convert to numpy array
        pixels = np.array(img)
        pixels = pixels.reshape(-1, 3)

        # Filter out near-white and near-black pixels (background)
        if exclude_background:
            # Calculate brightness
            brightness = np.mean(pixels, axis=1)
            mask = (brightness > 20) & (brightness < 235)

            # Also filter very low saturation (gray)
            max_channel = np.max(pixels, axis=1)
            min_channel = np.min(pixels, axis=1)
            saturation = (max_channel - min_channel) / (max_channel + 1e-10)
            mask = mask & (saturation > 0.1)

            filtered_pixels = pixels[mask]

            # Fall back to all pixels if too few remain
            if len(filtered_pixels) < n_colors * 10:
                filtered_pixels = pixels
        else:
            filtered_pixels = pixels

        # K-means clustering
        kmeans = KMeans(n_clusters=min(n_colors, len(filtered_pixels) // 10 + 1), random_state=42, n_init=10)
        kmeans.fit(filtered_pixels)

        # Get cluster centers and sort by cluster size
        labels, counts = np.unique(kmeans.labels_, return_counts=True)
        sorted_indices = np.argsort(-counts)

        colors = []
        for idx in sorted_indices:
            color = kmeans.cluster_centers_[idx]
            colors.append((int(color[0]), int(color[1]), int(color[2])))

        return colors

    except Exception as e:
        print(f"Error extracting colors: {e}")
        return []


async def analyze_image_colors(image_url: str) -> Optional[ColorAnalysisResult]:
    """
    Analyze colors from a clothing image URL.

    Args:
        image_url: URL of the clothing image

    Returns:
        ColorAnalysisResult with PCCS color analysis
    """
    if not HAS_ML_DEPS:
        print("ML dependencies not available for color analysis")
        return None

    # Download image
    image_bytes = await download_image(image_url)
    if not image_bytes:
        return None

    # Extract dominant colors
    colors = extract_dominant_colors(image_bytes)
    if not colors:
        return None

    # Analyze each color
    pccs_colors = [analyze_rgb_color(r, g, b) for r, g, b in colors]

    # Primary color is the most dominant
    primary = pccs_colors[0]
    secondary = pccs_colors[1:] if len(pccs_colors) > 1 else []

    # Color palette as hex
    palette = [c.hex_color for c in pccs_colors]

    # Determine overall color temperature
    temp = determine_color_temperature(primary.hue)

    return ColorAnalysisResult(
        primary_color=primary,
        secondary_colors=secondary,
        dominant_hex=primary.hex_color,
        color_palette=palette,
        category_suggestion=temp
    )


def calculate_color_distance(color1: PCCSColor, color2: PCCSColor) -> float:
    """
    Calculate perceptual distance between two PCCS colors.
    Lower values mean more similar colors.
    """
    # Hue distance (circular). For near-achromatic colors, hue is less meaningful.
    if color1.chroma < 0.5 and color2.chroma < 0.5:
        hue_dist = 0.0
    else:
        hue_diff = abs(color1.hue - color2.hue)
        if hue_diff > 180:
            hue_diff = 360 - hue_diff
        hue_dist = hue_diff / 180  # Normalize to 0-1

    # Value distance
    value_dist = abs(color1.value - color2.value) / 10

    # Chroma distance
    chroma_dist = abs(color1.chroma - color2.chroma) / 14

    # Weighted combination (hue is most important for fashion matching)
    return hue_dist * 0.5 + value_dist * 0.25 + chroma_dist * 0.25


def find_complementary_colors(color: PCCSColor) -> List[Dict]:
    """
    Find complementary/matching colors based on PCCS color theory.

    Returns suggested color schemes for outfit matching.
    """
    suggestions = []

    # Complementary (opposite on color wheel)
    comp_hue = (color.hue + 180) % 360
    suggestions.append({
        'type': 'complementary',
        'hue_range': (comp_hue - 15, comp_hue + 15),
        'description': '보색 (강렬한 대비)'
    })

    # Analogous (adjacent colors)
    suggestions.append({
        'type': 'analogous',
        'hue_range': ((color.hue - 30) % 360, (color.hue + 30) % 360),
        'description': '유사색 (자연스러운 조화)'
    })

    # Triadic
    triad1 = (color.hue + 120) % 360
    triad2 = (color.hue + 240) % 360
    suggestions.append({
        'type': 'triadic',
        'hue_range': [(triad1 - 15, triad1 + 15), (triad2 - 15, triad2 + 15)],
        'description': '삼색 조화 (균형잡힌 배색)'
    })

    # Same tone different hue (for outfit coordination)
    suggestions.append({
        'type': 'same_tone',
        'tone': color.tone,
        'description': f'같은 톤({color.tone}) 다른 색상'
    })

    return suggestions


# Convenience function for integration with scraper
async def analyze_product_colors(thumbnail_url: str, image_urls: List[str]) -> Optional[Dict]:
    """
    Analyze colors for a product from its images.

    Args:
        thumbnail_url: Main thumbnail image URL
        image_urls: Additional product image URLs

    Returns:
        Dict with color analysis results suitable for DB storage
    """
    # Try thumbnail first
    result = await analyze_image_colors(thumbnail_url)

    # If thumbnail fails, try other images
    if not result and image_urls:
        for url in image_urls[:3]:
            result = await analyze_image_colors(url)
            if result:
                break

    if not result:
        return None

    return {
        'pccs_hue': result.primary_color.hue,
        'pccs_value': result.primary_color.value,
        'pccs_chroma': result.primary_color.chroma,
        'pccs_tone': result.primary_color.tone,
        'primary_color_hex': result.dominant_hex,
        'color_palette': result.color_palette,
        'color_temperature': result.category_suggestion,
        'complementary_suggestions': find_complementary_colors(result.primary_color)
    }
