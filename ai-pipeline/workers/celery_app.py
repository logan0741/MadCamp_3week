"""
Celery Application Configuration
Manages background tasks for heavy AI model inference.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from celery import Celery
from kombu import Queue, Exchange
from loguru import logger

from config import settings


# ============================================
# Celery App Instance
# ============================================
celery_app = Celery(
    "musinsa_ai_pipeline",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)


# ============================================
# Celery Configuration
# ============================================
celery_app.conf.update(
    # Task routing
    task_routes={
        "workers.tasks.vton_tasks.*": {"queue": "vton"},
        "workers.tasks.avatar_tasks.*": {"queue": "avatar"},
        "workers.tasks.garment_tasks.*": {"queue": "garment"},
    },

    # Queue definitions
    task_queues=(
        Queue("vton", Exchange("vton"), routing_key="vton",
              queue_arguments={"x-max-priority": 10}),
        Queue("avatar", Exchange("avatar"), routing_key="avatar",
              queue_arguments={"x-max-priority": 10}),
        Queue("garment", Exchange("garment"), routing_key="garment",
              queue_arguments={"x-max-priority": 10}),
    ),

    # Task execution
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,

    # Task time limits
    task_soft_time_limit=settings.celery_task_timeout,
    task_time_limit=settings.celery_task_timeout + 60,  # Hard limit with buffer

    # Task result settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,

    # Worker configuration
    worker_prefetch_multiplier=1,  # Only fetch 1 task at a time (for VRAM control)
    worker_max_tasks_per_child=10,  # Restart worker after 10 tasks (prevent memory leaks)

    # Task tracking
    task_track_started=True,
    task_send_sent_event=True,

    # Logging
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",

    # Beat schedule (for periodic tasks)
    beat_schedule={
        # Example: Clean up old result files every hour
        "cleanup-old-results": {
            "task": "workers.tasks.maintenance.cleanup_old_results",
            "schedule": 3600.0,  # Every hour
        },
    },
)


# ============================================
# Task Auto-discovery
# ============================================
celery_app.autodiscover_tasks(
    ["workers.tasks"],
    force=True,
)


# ============================================
# Celery Events
# ============================================
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery connection."""
    logger.info(f"Request: {self.request!r}")
    return {"status": "success", "message": "Celery is working!"}


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks."""
    logger.info("Periodic tasks configured")


# ============================================
# Worker Lifecycle Events
# ============================================
@celery_app.signals.worker_init.connect
def worker_init_handler(sender, **kwargs):
    """Worker initialization."""
    logger.info(f"Worker {sender} initializing...")

    # Set CUDA device based on worker name
    # This allows multiple workers to use different GPUs
    import os
    worker_id = kwargs.get("hostname", "worker1")

    # Extract worker index from hostname (e.g., "worker1@host" -> 1)
    try:
        worker_num = int(worker_id.split("@")[0].replace("worker", ""))
        cuda_device = (worker_num - 1) % 4  # Cycle through 4 GPUs

        os.environ["CUDA_VISIBLE_DEVICES"] = str(cuda_device)
        logger.info(f"Worker {worker_id} assigned to CUDA device {cuda_device}")

    except Exception as e:
        logger.warning(f"Could not assign CUDA device: {e}")

    logger.success(f"Worker {sender} initialized successfully")


@celery_app.signals.worker_ready.connect
def worker_ready_handler(sender, **kwargs):
    """Worker ready to accept tasks."""
    logger.success(f"Worker {sender} is ready")


@celery_app.signals.worker_shutdown.connect
def worker_shutdown_handler(sender, **kwargs):
    """Worker shutdown cleanup."""
    logger.info(f"Worker {sender} shutting down...")

    # Unload models to free VRAM
    try:
        import torch
        torch.cuda.empty_cache()
        logger.info("CUDA cache cleared")
    except Exception as e:
        logger.warning(f"Error during cleanup: {e}")

    logger.success(f"Worker {sender} shutdown complete")


# ============================================
# Task Events
# ============================================
@celery_app.signals.task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, **kwargs):
    """Before task execution."""
    logger.info(f"Task {task.name}[{task_id}] starting...")


@celery_app.signals.task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, state=None, **kwargs):
    """After task execution."""
    logger.info(f"Task {task.name}[{task_id}] completed with state: {state}")

    # Free VRAM after task
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.debug("CUDA cache cleared after task")
    except Exception:
        pass


@celery_app.signals.task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, **kwargs):
    """Task failure handler."""
    logger.error(f"Task {sender.name}[{task_id}] failed: {exception}", exc_info=True)

    # Clear VRAM on failure
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass


# ============================================
# VRAM Monitoring Task
# ============================================
@celery_app.task(name="workers.monitor_vram")
def monitor_vram():
    """Monitor VRAM usage across all GPUs."""
    import torch

    if not torch.cuda.is_available():
        return {"error": "CUDA not available"}

    stats = {}
    for i in range(torch.cuda.device_count()):
        allocated = torch.cuda.memory_allocated(i) / 1024**3
        reserved = torch.cuda.memory_reserved(i) / 1024**3
        total = torch.cuda.get_device_properties(i).total_memory / 1024**3

        stats[f"gpu_{i}"] = {
            "name": torch.cuda.get_device_name(i),
            "allocated_gb": round(allocated, 2),
            "reserved_gb": round(reserved, 2),
            "total_gb": round(total, 2),
            "free_gb": round(total - allocated, 2),
            "utilization_percent": round((allocated / total) * 100, 2),
        }

    return stats


if __name__ == "__main__":
    # Test Celery connection
    result = debug_task.delay()
    logger.info(f"Debug task result: {result.get(timeout=10)}")
