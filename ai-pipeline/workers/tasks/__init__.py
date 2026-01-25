"""
Celery Tasks Package
Background tasks for AI model inference.
"""

from .vton_tasks import (
    process_vton_async,
    process_vton_batch_async,
)

__all__ = [
    "process_vton_async",
    "process_vton_batch_async",
]
