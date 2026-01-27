"""
Static File Path Management Utility
Manages output paths for AI-generated files and provides URLs for Nginx serving.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import uuid


class StaticPathManager:
    """
    Manages file paths for AI pipeline outputs.
    Ensures files are saved to Nginx-served directories.
    """
    
    def __init__(
        self,
        base_output_dir: str = "/data/outputs",
        base_images_dir: str = "/data/images",
        base_uploads_dir: str = "/data/uploads",
        static_base_url: str = "http://nginx-static:8080"
    ):
        self.base_output_dir = Path(base_output_dir)
        self.base_images_dir = Path(base_images_dir)
        self.base_uploads_dir = Path(base_uploads_dir)
        self.static_base_url = static_base_url.rstrip("/")
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create base directories if they don't exist."""
        for directory in [self.base_output_dir, self.base_images_dir, self.base_uploads_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _generate_timestamp(self) -> str:
        """Generate timestamp string for file naming."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _generate_unique_id(self) -> str:
        """Generate short unique ID."""
        return uuid.uuid4().hex[:8]
    
    # ===========================================
    # Path Generators
    # ===========================================
    
    def get_task_output_dir(self, task_id: str) -> Path:
        """
        Get output directory for a specific task.
        Creates the directory if it doesn't exist.
        """
        task_dir = self.base_output_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        return task_dir
    
    def get_json_path(
        self, 
        task_id: str, 
        filename: Optional[str] = None
    ) -> Path:
        """Get path for JSON result file."""
        task_dir = self.get_task_output_dir(task_id)
        if filename is None:
            filename = f"result_{self._generate_timestamp()}.json"
        return task_dir / filename
    
    def get_image_path(
        self,
        task_id: str,
        image_type: str = "output",
        extension: str = "png"
    ) -> Path:
        """
        Get path for output image.
        
        Args:
            task_id: Task identifier
            image_type: Type of image (e.g., 'vton', 'segmentation', 'preview')
            extension: File extension (png, jpg, webp)
        """
        task_dir = self.get_task_output_dir(task_id)
        filename = f"{image_type}_{self._generate_timestamp()}.{extension}"
        return task_dir / filename
    
    def get_glb_path(self, task_id: str, model_name: str = "model") -> Path:
        """Get path for GLB 3D model file."""
        task_dir = self.get_task_output_dir(task_id)
        filename = f"{model_name}_{self._generate_timestamp()}.glb"
        return task_dir / filename
    
    def get_obj_path(self, task_id: str, model_name: str = "mesh") -> Path:
        """Get path for OBJ mesh file."""
        task_dir = self.get_task_output_dir(task_id)
        filename = f"{model_name}_{self._generate_timestamp()}.obj"
        return task_dir / filename
    
    # ===========================================
    # URL Generators
    # ===========================================
    
    def path_to_url(self, file_path: Path) -> str:
        """
        Convert local file path to Nginx-served URL.
        
        Example:
            /data/outputs/task123/result.json -> http://nginx-static:8080/data/outputs/task123/result.json
        """
        # Get relative path from /data
        try:
            relative = file_path.relative_to("/data")
            return f"{self.static_base_url}/data/{relative}"
        except ValueError:
            # If not under /data, return as-is with base URL
            return f"{self.static_base_url}/{file_path.name}"
    
    def get_json_url(self, task_id: str, filename: str) -> str:
        """Get URL for JSON file."""
        return f"{self.static_base_url}/data/outputs/{task_id}/{filename}"
    
    def get_image_url(self, task_id: str, filename: str) -> str:
        """Get URL for image file."""
        return f"{self.static_base_url}/data/outputs/{task_id}/{filename}"
    
    def get_glb_url(self, task_id: str, filename: str) -> str:
        """Get URL for GLB file."""
        return f"{self.static_base_url}/data/outputs/{task_id}/{filename}"
    
    # ===========================================
    # Batch Operations
    # ===========================================
    
    def create_task_paths(self, task_id: str, task_type: str) -> Dict[str, Path]:
        """
        Create all standard paths for a task.
        
        Returns dict with paths for common output types.
        """
        task_dir = self.get_task_output_dir(task_id)
        timestamp = self._generate_timestamp()
        
        paths = {
            "output_dir": task_dir,
            "result_json": task_dir / f"result_{timestamp}.json",
            "metadata_json": task_dir / f"metadata_{timestamp}.json",
        }
        
        # Add task-type specific paths
        if task_type == "vton":
            paths["vton_image"] = task_dir / f"vton_result_{timestamp}.png"
            paths["masked_image"] = task_dir / f"masked_{timestamp}.png"
        
        elif task_type == "3d_reconstruction":
            paths["glb_model"] = task_dir / f"garment_3d_{timestamp}.glb"
            paths["obj_mesh"] = task_dir / f"scaled_mesh_{timestamp}.obj"
            paths["uv_atlas"] = task_dir / f"uv_atlas_{timestamp}.png"
            paths["preview_front"] = task_dir / f"preview_front_{timestamp}.png"
            paths["preview_back"] = task_dir / f"preview_back_{timestamp}.png"
        
        elif task_type == "segmentation":
            paths["front_mask"] = task_dir / f"mask_front_{timestamp}.png"
            paths["back_mask"] = task_dir / f"mask_back_{timestamp}.png"
            paths["front_rgba"] = task_dir / f"rgba_front_{timestamp}.png"
            paths["back_rgba"] = task_dir / f"rgba_back_{timestamp}.png"
        
        return paths
    
    def paths_to_urls(self, paths: Dict[str, Path]) -> Dict[str, str]:
        """Convert dict of paths to dict of URLs."""
        urls = {}
        for key, path in paths.items():
            if isinstance(path, Path) and path.suffix:  # Skip directories
                urls[key] = self.path_to_url(path)
        return urls
    
    # ===========================================
    # Cleanup
    # ===========================================
    
    def cleanup_task(self, task_id: str) -> List[Path]:
        """
        Remove all files for a task.
        Returns list of deleted paths.
        """
        task_dir = self.get_task_output_dir(task_id)
        deleted = []
        
        if task_dir.exists():
            for file_path in task_dir.glob("*"):
                if file_path.is_file():
                    file_path.unlink()
                    deleted.append(file_path)
            task_dir.rmdir()
        
        return deleted


# ===========================================
# Global Instance
# ===========================================

# Create instance with environment variables
static_path_manager = StaticPathManager(
    base_output_dir=os.getenv("OUTPUT_DIR", "/data/outputs"),
    base_images_dir=os.getenv("IMAGES_DIR", "/data/images"),
    base_uploads_dir=os.getenv("UPLOAD_DIR", "/data/uploads"),
    static_base_url=os.getenv("STATIC_BASE_URL", "http://nginx-static:8080"),
)


def get_path_manager() -> StaticPathManager:
    """Dependency injection for FastAPI."""
    return static_path_manager
