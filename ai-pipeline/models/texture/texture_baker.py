"""
Smart Texture Baking Module for MemeForty Phase 2 Step 4.

UV Projection and PBR map generation.
- Symmetry Filling for blind spots
- Normal/Roughness map generation
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Dict, Any, Union

import numpy as np
from PIL import Image
from loguru import logger

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class UVProjector:
    """
    Projects 2D textures onto 3D mesh UV coordinates.
    """
    
    def __init__(self, atlas_size: Tuple[int, int] = (2048, 2048)):
        """
        Initialize UV projector.
        
        Args:
            atlas_size: Output atlas resolution (width, height)
        """
        self.atlas_size = atlas_size
    
    def project_front_back(
        self,
        front_image: Image.Image,
        back_image: Image.Image,
        uv_coords: np.ndarray,
        face_uvs: np.ndarray,
        vertex_normals: np.ndarray,
    ) -> np.ndarray:
        """
        Project front and back images to UV atlas.
        
        Args:
            front_image: Front view texture
            back_image: Back view texture
            uv_coords: (N, 2) UV coordinates per vertex
            face_uvs: (F, 3) UV indices per face
            vertex_normals: (N, 3) vertex normals
            
        Returns:
            UV atlas as numpy array (H, W, 3)
        """
        atlas = np.zeros((self.atlas_size[1], self.atlas_size[0], 3), dtype=np.uint8)
        
        front_np = np.array(front_image.convert("RGB"))
        back_np = np.array(back_image.convert("RGB"))
        
        # For each face, determine if front or back facing
        for face_idx, face_uv in enumerate(face_uvs):
            # Get UVs for this face
            uvs = uv_coords[face_uv]
            
            # Get average normal for this face
            avg_normal = vertex_normals[face_uv].mean(axis=0)
            
            # Determine if front or back facing
            is_front = avg_normal[2] > 0  # Z+ is front
            
            source = front_np if is_front else back_np
            
            # Project face to atlas
            self._project_face(atlas, source, uvs)
        
        return atlas
    
    def _project_face(
        self,
        atlas: np.ndarray,
        source: np.ndarray,
        uvs: np.ndarray,
    ) -> None:
        """Project single face to atlas."""
        h, w = atlas.shape[:2]
        src_h, src_w = source.shape[:2]
        
        # Convert UV to atlas coordinates
        atlas_coords = uvs.copy()
        atlas_coords[:, 0] *= w
        atlas_coords[:, 1] = (1 - atlas_coords[:, 1]) * h
        atlas_coords = atlas_coords.astype(int)
        
        # Simple bounding box fill
        min_x = max(0, atlas_coords[:, 0].min())
        max_x = min(w - 1, atlas_coords[:, 0].max())
        min_y = max(0, atlas_coords[:, 1].min())
        max_y = min(h - 1, atlas_coords[:, 1].max())
        
        if max_x <= min_x or max_y <= min_y:
            return
        
        # Sample from source center
        src_x = src_w // 2
        src_y = src_h // 2
        
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                # Map atlas position to source
                u = (x - min_x) / max(1, max_x - min_x)
                v = (y - min_y) / max(1, max_y - min_y)
                
                sx = int(u * src_w * 0.5 + src_w * 0.25)
                sy = int(v * src_h * 0.5 + src_h * 0.25)
                
                sx = np.clip(sx, 0, src_w - 1)
                sy = np.clip(sy, 0, src_h - 1)
                
                atlas[y, x] = source[sy, sx]


class SymmetryFiller:
    """
    Fills blind spots using symmetry and edge blending.
    """
    
    def __init__(self, blend_width: int = 32):
        """
        Initialize symmetry filler.
        
        Args:
            blend_width: Width of blending region in pixels
        """
        self.blend_width = blend_width
    
    def fill_blind_spots(
        self,
        atlas: np.ndarray,
        left_image: Optional[np.ndarray] = None,
        right_image: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Fill blind spots in texture atlas.
        
        Uses symmetry and edge gradient filling.
        
        Args:
            atlas: Input atlas with potential gaps
            left_image: Optional left side reference
            right_image: Optional right side reference
            
        Returns:
            Filled atlas
        """
        result = atlas.copy()
        
        # Detect empty regions (black pixels)
        empty_mask = np.all(atlas < 10, axis=2)
        
        if not np.any(empty_mask):
            return result
        
        logger.info(f"Filling {np.sum(empty_mask)} empty pixels")
        
        # Strategy 1: Mirror symmetry for left-right gaps
        result = self._mirror_fill(result, empty_mask)
        
        # Strategy 2: Edge gradient for remaining gaps
        empty_mask = np.all(result < 10, axis=2)
        if np.any(empty_mask):
            result = self._gradient_fill(result, empty_mask)
        
        return result
    
    def _mirror_fill(
        self,
        atlas: np.ndarray,
        empty_mask: np.ndarray,
    ) -> np.ndarray:
        """Fill using horizontal mirror symmetry."""
        h, w = atlas.shape[:2]
        result = atlas.copy()
        
        for y in range(h):
            for x in range(w):
                if empty_mask[y, x]:
                    # Try to fill from mirrored position
                    mirror_x = w - 1 - x
                    if not empty_mask[y, mirror_x]:
                        result[y, x] = atlas[y, mirror_x]
        
        return result
    
    def _gradient_fill(
        self,
        atlas: np.ndarray,
        empty_mask: np.ndarray,
    ) -> np.ndarray:
        """Fill using edge gradient interpolation."""
        import cv2
        
        # Use OpenCV inpainting
        mask_uint8 = (empty_mask.astype(np.uint8) * 255)
        result = cv2.inpaint(atlas, mask_uint8, 3, cv2.INPAINT_TELEA)
        
        return result


class PBRMapGenerator:
    """
    Generates PBR material maps from albedo texture.
    """
    
    def __init__(self):
        """Initialize PBR map generator."""
        pass
    
    def generate_normal_map(
        self,
        albedo: np.ndarray,
        strength: float = 1.0,
    ) -> np.ndarray:
        """
        Generate normal map from albedo using Sobel gradients.
        
        Args:
            albedo: (H, W, 3) albedo texture
            strength: Normal map strength
            
        Returns:
            (H, W, 3) normal map
        """
        import cv2
        
        # Convert to grayscale
        gray = cv2.cvtColor(albedo, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
        
        # Compute gradients
        dx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        dy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        
        # Construct normal
        normal = np.zeros((*gray.shape, 3), dtype=np.float32)
        normal[:, :, 0] = -dx * strength  # X
        normal[:, :, 1] = -dy * strength  # Y
        normal[:, :, 2] = 1.0              # Z
        
        # Normalize
        length = np.sqrt(np.sum(normal ** 2, axis=2, keepdims=True))
        normal = normal / (length + 1e-8)
        
        # Convert to 0-255 range (x,y: -1,1 -> 0,255, z: 0,1 -> 128,255)
        normal = (normal * 0.5 + 0.5) * 255
        
        return normal.astype(np.uint8)
    
    def generate_roughness_map(
        self,
        albedo: np.ndarray,
        base_roughness: float = 0.5,
        variation: float = 0.3,
    ) -> np.ndarray:
        """
        Generate roughness map based on texture detail.
        
        Args:
            albedo: (H, W, 3) albedo texture
            base_roughness: Base roughness value
            variation: Roughness variation range
            
        Returns:
            (H, W) roughness map (grayscale)
        """
        import cv2
        
        # Convert to grayscale
        gray = cv2.cvtColor(albedo, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
        
        # Detect high-frequency detail (suggests fabric texture)
        laplacian = cv2.Laplacian(gray, cv2.CV_32F)
        detail = np.abs(laplacian)
        detail = cv2.GaussianBlur(detail, (15, 15), 0)
        detail = detail / (detail.max() + 1e-8)
        
        # Higher detail = higher roughness (matte fabric)
        roughness = base_roughness + (detail - 0.5) * variation * 2
        roughness = np.clip(roughness, 0, 1)
        
        return (roughness * 255).astype(np.uint8)
    
    def generate_all_maps(
        self,
        albedo: np.ndarray,
        material_type: str = "fabric",
    ) -> Dict[str, np.ndarray]:
        """
        Generate all PBR maps.
        
        Args:
            albedo: (H, W, 3) albedo texture
            material_type: "fabric", "leather", "silk", etc.
            
        Returns:
            Dict with 'albedo', 'normal', 'roughness', 'ao'
        """
        # Material-specific parameters
        material_params = {
            "fabric": {"roughness": 0.7, "normal_strength": 0.8},
            "leather": {"roughness": 0.4, "normal_strength": 1.2},
            "silk": {"roughness": 0.2, "normal_strength": 0.3},
            "cotton": {"roughness": 0.8, "normal_strength": 0.6},
            "denim": {"roughness": 0.9, "normal_strength": 1.0},
        }
        
        params = material_params.get(material_type, material_params["fabric"])
        
        return {
            "albedo": albedo,
            "normal": self.generate_normal_map(albedo, params["normal_strength"]),
            "roughness": self.generate_roughness_map(albedo, params["roughness"]),
            "ao": self._generate_ao_map(albedo),
        }
    
    def _generate_ao_map(self, albedo: np.ndarray) -> np.ndarray:
        """Generate ambient occlusion map (simplified)."""
        import cv2
        
        gray = cv2.cvtColor(albedo, cv2.COLOR_RGB2GRAY)
        
        # Dark areas get more occlusion
        ao = 255 - cv2.GaussianBlur(255 - gray, (21, 21), 0) // 4
        ao = np.clip(ao, 128, 255)
        
        return ao


class SmartTextureBaker:
    """
    Step 4 Pipeline: Smart Texture Baking
    
    Combines UV projection, symmetry filling, and PBR generation.
    """
    
    def __init__(
        self,
        atlas_size: Tuple[int, int] = (2048, 2048),
        material_type: str = "fabric",
    ):
        """
        Initialize smart texture baker.
        
        Args:
            atlas_size: Output atlas resolution
            material_type: Material type for PBR maps
        """
        self.atlas_size = atlas_size
        self.material_type = material_type
        
        self.projector = UVProjector(atlas_size)
        self.filler = SymmetryFiller()
        self.pbr_generator = PBRMapGenerator()
        
        logger.info(f"SmartTextureBaker initialized ({atlas_size[0]}x{atlas_size[1]})")
    
    def bake(
        self,
        front_image: Union[str, Path, Image.Image],
        back_image: Union[str, Path, Image.Image],
        mesh_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Bake textures onto mesh.
        
        Args:
            front_image: Front view texture
            back_image: Back view texture
            mesh_data: Optional mesh data with UVs
            
        Returns:
            Dict with 'atlas', 'pbr_maps', 'quality_score'
        """
        result = {}
        
        # Load images
        if isinstance(front_image, (str, Path)):
            front = Image.open(front_image).convert("RGB")
        else:
            front = front_image.convert("RGB")
        
        if isinstance(back_image, (str, Path)):
            back = Image.open(back_image).convert("RGB")
        else:
            back = back_image.convert("RGB")
        
        logger.info("[Step 4.1] Creating texture atlas...")
        atlas = self._create_simple_atlas(front, back)
        
        logger.info("[Step 4.2] Filling blind spots...")
        atlas = self.filler.fill_blind_spots(atlas)
        result["atlas"] = atlas
        
        logger.info("[Step 4.3] Generating PBR maps...")
        pbr_maps = self.pbr_generator.generate_all_maps(atlas, self.material_type)
        result["pbr_maps"] = pbr_maps
        
        # Quality score
        result["quality_score"] = self._calculate_quality(atlas)
        
        logger.info(f"Texture baking complete: quality={result['quality_score']:.1f}/10")
        return result
    
    def _create_simple_atlas(
        self,
        front: Image.Image,
        back: Image.Image,
    ) -> np.ndarray:
        """Create simple side-by-side atlas."""
        w, h = self.atlas_size
        
        # Resize images
        front_resized = front.resize((w // 2, h), Image.LANCZOS)
        back_resized = back.resize((w // 2, h), Image.LANCZOS)
        
        # Combine side by side
        atlas = np.zeros((h, w, 3), dtype=np.uint8)
        atlas[:, :w//2, :] = np.array(front_resized)
        atlas[:, w//2:, :] = np.array(back_resized)
        
        return atlas
    
    def _calculate_quality(self, atlas: np.ndarray) -> float:
        """Calculate texture quality score."""
        score = 5.0
        
        # Check coverage
        non_empty = np.any(atlas > 10, axis=2)
        coverage = np.mean(non_empty)
        score += coverage * 3
        
        # Check detail
        import cv2
        gray = cv2.cvtColor(atlas, cv2.COLOR_RGB2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        detail = np.var(laplacian)
        if detail > 100:
            score += 2.0
        elif detail > 50:
            score += 1.0
        
        return min(10.0, score)
    
    def save_outputs(
        self,
        result: Dict[str, Any],
        output_dir: Path,
        prefix: str = "texture",
    ) -> Dict[str, str]:
        """
        Save all texture outputs.
        
        Args:
            result: Baking result
            output_dir: Output directory
            prefix: Filename prefix
            
        Returns:
            Dict of output file paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        paths = {}
        
        # Save atlas
        atlas_path = output_dir / f"{prefix}_albedo.png"
        Image.fromarray(result["atlas"]).save(atlas_path)
        paths["albedo"] = str(atlas_path)
        
        # Save PBR maps
        for map_name, map_data in result["pbr_maps"].items():
            if map_name == "albedo":
                continue
            path = output_dir / f"{prefix}_{map_name}.png"
            if len(map_data.shape) == 2:
                Image.fromarray(map_data).save(path)
            else:
                Image.fromarray(map_data).save(path)
            paths[map_name] = str(path)
        
        logger.info(f"Saved texture outputs to {output_dir}")
        return paths
