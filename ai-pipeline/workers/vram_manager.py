"""
VRAM Resource Manager
Manages VRAM allocation across concurrent AI model tasks.
"""

import torch
from typing import Optional, Dict, Literal
from dataclasses import dataclass
from loguru import logger
from threading import Lock

from config import settings


@dataclass
class VRAMAllocation:
    """VRAM allocation record."""
    task_id: str
    model_type: Literal["ECON", "BCNet", "VTON", "3DGS"]
    allocated_gb: float
    device_id: int


class VRAMManager:
    """
    Singleton VRAM resource manager.

    Ensures that concurrent tasks don't exceed available VRAM by
    tracking allocations and enforcing limits.
    """

    _instance: Optional["VRAMManager"] = None
    _lock = Lock()

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize VRAM manager."""
        if not hasattr(self, "_initialized"):
            self.allocations: Dict[str, VRAMAllocation] = {}
            self._allocation_lock = Lock()
            self._initialized = True

            logger.info("VRAMManager initialized")

    def get_available_vram(self, device_id: int = 0) -> float:
        """
        Get available VRAM on specified device.

        Args:
            device_id: CUDA device ID

        Returns:
            Available VRAM in GB
        """
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA not available")

        total_memory = torch.cuda.get_device_properties(device_id).total_memory / 1024**3
        allocated_memory = torch.cuda.memory_allocated(device_id) / 1024**3

        # Account for reserved memory
        reserved_memory = torch.cuda.memory_reserved(device_id) / 1024**3

        # Calculate truly available memory
        available = total_memory - max(allocated_memory, reserved_memory)

        logger.debug(
            f"Device {device_id}: Total={total_memory:.2f}GB, "
            f"Allocated={allocated_memory:.2f}GB, "
            f"Available={available:.2f}GB"
        )

        return available

    def can_allocate(
        self,
        model_type: Literal["ECON", "BCNet", "VTON", "3DGS"],
        device_id: int = 0,
    ) -> bool:
        """
        Check if sufficient VRAM is available for model.

        Args:
            model_type: Type of model to load
            device_id: CUDA device ID

        Returns:
            True if allocation is possible
        """
        required_vram = self._get_required_vram(model_type)
        available_vram = self.get_available_vram(device_id)

        can_allocate = available_vram >= required_vram

        logger.debug(
            f"Allocation check for {model_type}: "
            f"Required={required_vram}GB, Available={available_vram}GB, "
            f"Can allocate={can_allocate}"
        )

        return can_allocate

    def allocate(
        self,
        task_id: str,
        model_type: Literal["ECON", "BCNet", "VTON", "3DGS"],
        device_id: int = 0,
    ) -> bool:
        """
        Allocate VRAM for task.

        Args:
            task_id: Unique task identifier
            model_type: Type of model
            device_id: CUDA device ID

        Returns:
            True if allocation successful

        Raises:
            RuntimeError: If insufficient VRAM
        """
        with self._allocation_lock:
            # Check if already allocated
            if task_id in self.allocations:
                logger.warning(f"Task {task_id} already has VRAM allocated")
                return False

            # Check availability
            if not self.can_allocate(model_type, device_id):
                available = self.get_available_vram(device_id)
                required = self._get_required_vram(model_type)

                raise RuntimeError(
                    f"Insufficient VRAM for {model_type}. "
                    f"Required: {required}GB, Available: {available}GB"
                )

            # Record allocation
            allocated_gb = self._get_required_vram(model_type)

            self.allocations[task_id] = VRAMAllocation(
                task_id=task_id,
                model_type=model_type,
                allocated_gb=allocated_gb,
                device_id=device_id,
            )

            logger.success(
                f"Allocated {allocated_gb}GB VRAM for {model_type} (task={task_id}, device={device_id})"
            )

            return True

    def deallocate(self, task_id: str):
        """
        Deallocate VRAM for completed task.

        Args:
            task_id: Task identifier
        """
        with self._allocation_lock:
            if task_id not in self.allocations:
                logger.warning(f"No allocation found for task {task_id}")
                return

            allocation = self.allocations.pop(task_id)

            # Force garbage collection
            import gc
            gc.collect()

            # Clear CUDA cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            logger.success(
                f"Deallocated {allocation.allocated_gb}GB VRAM "
                f"for {allocation.model_type} (task={task_id})"
            )

    def get_allocation_summary(self) -> Dict:
        """
        Get summary of current VRAM allocations.

        Returns:
            Dictionary with allocation statistics
        """
        with self._allocation_lock:
            total_allocated = sum(a.allocated_gb for a in self.allocations.values())

            allocations_by_model = {}
            for alloc in self.allocations.values():
                if alloc.model_type not in allocations_by_model:
                    allocations_by_model[alloc.model_type] = {
                        "count": 0,
                        "total_gb": 0.0,
                    }

                allocations_by_model[alloc.model_type]["count"] += 1
                allocations_by_model[alloc.model_type]["total_gb"] += alloc.allocated_gb

            return {
                "total_allocations": len(self.allocations),
                "total_allocated_gb": round(total_allocated, 2),
                "by_model": allocations_by_model,
                "active_tasks": list(self.allocations.keys()),
            }

    def _get_required_vram(
        self,
        model_type: Literal["ECON", "BCNet", "VTON", "3DGS"],
    ) -> float:
        """
        Get required VRAM for model type.

        Args:
            model_type: Model type

        Returns:
            Required VRAM in GB
        """
        vram_requirements = {
            "ECON": settings.vram_econ,
            "BCNet": settings.vram_bcnet,
            "VTON": settings.vram_vton,
            "3DGS": settings.vram_3dgs,
        }

        return vram_requirements.get(model_type, 16.0)  # Default 16GB

    def clear_all(self):
        """
        Emergency: Clear all allocations.

        WARNING: This will not actually unload models, just clear tracking.
        Use only for debugging.
        """
        with self._allocation_lock:
            self.allocations.clear()
            torch.cuda.empty_cache()

            logger.warning("All VRAM allocations forcefully cleared")


# ============================================
# Singleton Instance
# ============================================
vram_manager = VRAMManager()


# ============================================
# Context Manager for VRAM Allocation
# ============================================
class VRAMContext:
    """
    Context manager for automatic VRAM allocation/deallocation.

    Usage:
        with VRAMContext("task-123", "ECON") as vram:
            # Load and use model
            model = ECON()
            result = model.inference(...)
        # VRAM automatically deallocated
    """

    def __init__(
        self,
        task_id: str,
        model_type: Literal["ECON", "BCNet", "VTON", "3DGS"],
        device_id: int = 0,
    ):
        self.task_id = task_id
        self.model_type = model_type
        self.device_id = device_id

    def __enter__(self):
        """Allocate VRAM on context entry."""
        vram_manager.allocate(self.task_id, self.model_type, self.device_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Deallocate VRAM on context exit."""
        vram_manager.deallocate(self.task_id)

        # Return False to propagate exceptions
        return False


# ============================================
# Decorator for Automatic VRAM Management
# ============================================
def manage_vram(model_type: Literal["ECON", "BCNet", "VTON", "3DGS"]):
    """
    Decorator for automatic VRAM allocation/deallocation.

    Usage:
        @manage_vram("ECON")
        def process_avatar(task_id: str, video_path: str):
            # VRAM allocated before this runs
            model = ECON()
            result = model.process(video_path)
            return result
            # VRAM deallocated after return
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract task_id from arguments
            task_id = kwargs.get("task_id") or args[0] if args else "unknown"

            with VRAMContext(task_id, model_type):
                return func(*args, **kwargs)

        return wrapper

    return decorator
