"""
AI Pipeline Configuration Management
Loads environment variables and provides type-safe configuration access.
"""

from typing import List, Optional
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Main configuration class for AI Pipeline."""

    # ============================================
    # Server Configuration
    # ============================================
    environment: str = Field(default="development", env="ENVIRONMENT")
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8001, env="API_PORT")
    api_workers: int = Field(default=4, env="API_WORKERS")
    api_reload: bool = Field(default=True, env="API_RELOAD")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )

    # ============================================
    # Redis Configuration
    # ============================================
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")

    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        env="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0",
        env="CELERY_RESULT_BACKEND"
    )

    # ============================================
    # Database Configuration
    # ============================================
    database_url: Optional[str] = Field(
        default=None,
        env="DATABASE_URL"
    )

    # ============================================
    # Model Paths
    # ============================================
    model_weights_dir: Path = Field(
        default=Path("/root/MadCamp_3week/ai-pipeline/models/weights"),
        env="MODEL_WEIGHTS_DIR"
    )

    # ECON
    econ_checkpoint_path: Optional[Path] = Field(default=None, env="ECON_CHECKPOINT_PATH")
    smplx_model_path: Optional[Path] = Field(default=None, env="SMPLX_MODEL_PATH")

    # BCNet
    bcnet_checkpoint_path: Optional[Path] = Field(default=None, env="BCNET_CHECKPOINT_PATH")

    # IDM-VTON
    vton_model_id: str = Field(default="yisol/IDM-VTON", env="VTON_MODEL_ID")
    vton_cache_dir: Optional[Path] = Field(default=None, env="VTON_CACHE_DIR")

    # 3DGS
    gaussians_checkpoint_path: Optional[Path] = Field(default=None, env="GAUSSIANS_CHECKPOINT_PATH")

    # ============================================
    # File Storage
    # ============================================
    upload_dir: Path = Field(
        default=Path("/root/MadCamp_3week/ai-pipeline/data/uploads"),
        env="UPLOAD_DIR"
    )
    output_dir: Path = Field(
        default=Path("/root/MadCamp_3week/ai-pipeline/data/outputs"),
        env="OUTPUT_DIR"
    )
    cdn_base_url: str = Field(default="http://localhost:8001", env="CDN_BASE_URL")

    # ============================================
    # GPU & VRAM Management
    # ============================================
    cuda_visible_devices: str = Field(default="0,1,2,3", env="CUDA_VISIBLE_DEVICES")

    vram_econ: int = Field(default=40, env="VRAM_ECON", description="VRAM for ECON (GB)")
    vram_bcnet: int = Field(default=20, env="VRAM_BCNET", description="VRAM for BCNet (GB)")
    vram_3dgs: int = Field(default=20, env="VRAM_3DGS", description="VRAM for 3DGS (GB)")
    vram_vton: int = Field(default=16, env="VRAM_VTON", description="VRAM for VTON (GB)")

    celery_max_concurrent: int = Field(default=2, env="CELERY_MAX_CONCURRENT")
    celery_task_timeout: int = Field(default=3600, env="CELERY_TASK_TIMEOUT")

    # ============================================
    # AI Model Configuration
    # ============================================
    # ECON
    econ_image_resolution: int = Field(default=512, env="ECON_IMAGE_RESOLUTION")
    econ_batch_size: int = Field(default=1, env="ECON_BATCH_SIZE")
    econ_num_iterations: int = Field(default=100, env="ECON_NUM_ITERATIONS")

    # BCNet
    bcnet_image_size: int = Field(default=512, env="BCNET_IMAGE_SIZE")
    bcnet_num_layers: int = Field(default=3, env="BCNET_NUM_LAYERS")

    # IDM-VTON
    vton_image_size: int = Field(default=768, env="VTON_IMAGE_SIZE")
    vton_num_inference_steps: int = Field(default=50, env="VTON_NUM_INFERENCE_STEPS")
    vton_guidance_scale: float = Field(default=7.5, env="VTON_GUIDANCE_SCALE")

    # 3DGS
    gaussian_num_points: int = Field(default=100000, env="GAUSSIAN_NUM_POINTS")
    gaussian_sh_degree: int = Field(default=3, env="GAUSSIAN_SH_DEGREE")

    # ============================================
    # External Services
    # ============================================
    aws_access_key_id: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="ap-northeast-2", env="AWS_REGION")
    s3_bucket_name: Optional[str] = Field(default=None, env="S3_BUCKET_NAME")

    gcs_project_id: Optional[str] = Field(default=None, env="GCS_PROJECT_ID")
    gcs_bucket_name: Optional[str] = Field(default=None, env="GCS_BUCKET_NAME")

    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")

    # ============================================
    # Logging
    # ============================================
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file: Path = Field(
        default=Path("/root/MadCamp_3week/ai-pipeline/logs/ai-pipeline.log"),
        env="LOG_FILE"
    )

    # ============================================
    # Security
    # ============================================
    api_secret_key: str = Field(
        default="your-secret-key-here-change-in-production",
        env="API_SECRET_KEY"
    )
    jwt_secret_key: Optional[str] = Field(default=None, env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=30, env="JWT_EXPIRE_MINUTES")

    # ============================================
    # Feature Flags
    # ============================================
    enable_econ: bool = Field(default=True, env="ENABLE_ECON")
    enable_bcnet: bool = Field(default=True, env="ENABLE_BCNET")
    enable_vton: bool = Field(default=True, env="ENABLE_VTON")
    enable_3dgs: bool = Field(default=True, env="ENABLE_3DGS")

    debug_mode: bool = Field(default=False, env="DEBUG_MODE")
    enable_vram_monitoring: bool = Field(default=True, env="ENABLE_VRAM_MONITORING")

    # ============================================
    # Performance Tuning
    # ============================================
    torch_num_threads: int = Field(default=8, env="TORCH_NUM_THREADS")
    omp_num_threads: int = Field(default=8, env="OMP_NUM_THREADS")
    use_mixed_precision: bool = Field(default=True, env="USE_MIXED_PRECISION")
    allow_tf32: bool = Field(default=True, env="ALLOW_TF32")

    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @validator("model_weights_dir", "upload_dir", "output_dir", "log_file", pre=True)
    def validate_path(cls, v):
        """Convert string paths to Path objects."""
        if isinstance(v, str):
            return Path(v)
        return v

    @validator("econ_checkpoint_path", "smplx_model_path", "bcnet_checkpoint_path",
               "vton_cache_dir", "gaussians_checkpoint_path", pre=True)
    def validate_optional_path(cls, v):
        """Convert optional string paths to Path objects."""
        if v is None:
            return None
        if isinstance(v, str):
            return Path(v)
        return v

    def create_directories(self):
        """Create necessary directories if they don't exist."""
        directories = [
            self.model_weights_dir,
            self.upload_dir,
            self.output_dir,
            self.log_file.parent,
        ]

        if self.vton_cache_dir:
            directories.append(self.vton_cache_dir)

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def get_redis_url(self) -> str:
        """Get Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"

    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# ============================================
# Global Settings Instance
# ============================================
settings = Settings()

# Create necessary directories on import
settings.create_directories()


# ============================================
# Helper Functions
# ============================================
def get_settings() -> Settings:
    """
    Dependency injection for FastAPI.

    Usage:
        @app.get("/config")
        async def get_config(settings: Settings = Depends(get_settings)):
            return {"environment": settings.environment}
    """
    return settings


def print_config_summary():
    """Print configuration summary for debugging."""
    print("=" * 50)
    print("AI Pipeline Configuration Summary")
    print("=" * 50)
    print(f"Environment: {settings.environment}")
    print(f"API: {settings.api_host}:{settings.api_port}")
    print(f"Redis: {settings.redis_host}:{settings.redis_port}")
    print(f"CUDA Devices: {settings.cuda_visible_devices}")
    print(f"Upload Dir: {settings.upload_dir}")
    print(f"Output Dir: {settings.output_dir}")
    print(f"Feature Flags:")
    print(f"  - ECON: {settings.enable_econ}")
    print(f"  - BCNet: {settings.enable_bcnet}")
    print(f"  - VTON: {settings.enable_vton}")
    print(f"  - 3DGS: {settings.enable_3dgs}")
    print("=" * 50)


if __name__ == "__main__":
    # Test configuration loading
    print_config_summary()
