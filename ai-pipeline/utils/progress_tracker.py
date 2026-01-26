"""
Progress State Manager

Auto-updates development_progress.md for checkpoint tracking
and session continuity across AI agent sessions.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class ProgressTracker:
    """
    Manages development_progress.md for checkpoint state tracking.

    Provides atomic updates to preserve session state across
    interruptions and high-cost task continuity.
    """

    def __init__(
        self,
        progress_file: Optional[Path] = None,
        project_root: Optional[Path] = None,
    ):
        self.project_root = project_root or Path(__file__).parent.parent
        self.progress_file = progress_file or self.project_root / "development_progress.md"
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Create progress file if it doesn't exist."""
        if not self.progress_file.exists():
            self._create_initial_file()

    def _create_initial_file(self) -> None:
        """Create initial progress tracking file."""
        template = '''# Development Progress - State Save Protocol

This file serves as "Immutable Memory" for checkpoint tracking.

---

## Current Session State

**Session ID**: {session_id}
**Status**: IN_PROGRESS
**Last Checkpoint**: Initialization

---

## Mission Progress Tracker

### Mission 1: Context Preservation
- [ ] Pending

### Mission 2: Dual-View Segmentation
- [ ] Pending

### Mission 3: Size-Accurate Reconstruction
- [ ] Pending

### Mission 4: Physics Simulation
- [ ] Pending

### Mission 5: GLB Export
- [ ] Pending

---

## Resource Status

### VRAM Allocation
| Model | Allocated | Status |
|-------|-----------|--------|
| Available | {vram_available} GB | Ready |

---

## Checkpoint States

*No checkpoints recorded yet*

---

## Fact Check Log

| Measurement | Input (cm) | Mesh Output (cm) | Accuracy | Timestamp |
|-------------|------------|------------------|----------|-----------|
| *No measurements verified yet* | - | - | - | - |

---

*Auto-updated by Progress Tracker*
'''
        session_id = datetime.now().strftime("%Y-%m-%d-init")
        vram = self._get_vram_available_gb()

        content = template.format(
            session_id=session_id,
            vram_available=f"{vram:.1f}",
        )

        self.progress_file.write_text(content)

    def _get_vram_available_gb(self) -> float:
        """Get available VRAM in GB."""
        if HAS_TORCH and torch.cuda.is_available():
            total = torch.cuda.get_device_properties(0).total_memory
            allocated = torch.cuda.memory_allocated()
            return (total - allocated) / (1024 ** 3)
        return 20.0  # Default assumption

    def _get_vram_used_mb(self) -> float:
        """Get used VRAM in MB."""
        if HAS_TORCH and torch.cuda.is_available():
            return torch.cuda.memory_allocated() / (1024 ** 2)
        return 0.0

    def update_session_state(
        self,
        session_id: str,
        status: str,
        last_checkpoint: str,
    ) -> None:
        """Update the current session state section."""
        content = self.progress_file.read_text()

        # Update session ID
        content = re.sub(
            r'\*\*Session ID\*\*: .*',
            f'**Session ID**: {session_id}',
            content
        )

        # Update status
        content = re.sub(
            r'\*\*Status\*\*: .*',
            f'**Status**: {status}',
            content
        )

        # Update last checkpoint
        content = re.sub(
            r'\*\*Last Checkpoint\*\*: .*',
            f'**Last Checkpoint**: {last_checkpoint}',
            content
        )

        self.progress_file.write_text(content)

    def update_mission_status(
        self,
        mission_number: int,
        status: str,
        tasks_completed: List[str],
        tasks_pending: List[str],
    ) -> None:
        """Update a specific mission's status."""
        content = self.progress_file.read_text()

        # Build task list
        task_lines = []
        for task in tasks_completed:
            task_lines.append(f"- [x] {task}")
        for task in tasks_pending:
            task_lines.append(f"- [ ] {task}")

        # Find and replace mission section
        mission_pattern = rf'(### Mission {mission_number}:.*?\n)((?:- \[.\].*\n)*)'

        def replace_mission(match):
            header = match.group(1)
            # Add status emoji
            if status == "COMPLETE":
                header = header.rstrip() + " ✅ COMPLETE\n"
            elif status == "IN_PROGRESS":
                header = header.rstrip() + " 🔄 IN_PROGRESS\n"
            else:
                header = header.rstrip() + " ⏳ PENDING\n"

            return header + "\n".join(task_lines) + "\n"

        content = re.sub(mission_pattern, replace_mission, content, flags=re.MULTILINE)
        self.progress_file.write_text(content)

    def add_checkpoint(
        self,
        checkpoint_name: str,
        state: Dict[str, Any],
    ) -> None:
        """Add a new checkpoint entry."""
        content = self.progress_file.read_text()

        timestamp = datetime.now().isoformat()
        vram = self._get_vram_used_mb()

        checkpoint_entry = f'''
### Checkpoint: {checkpoint_name} ({timestamp})
```json
{json.dumps(state, indent=2)}
```
VRAM Usage: {vram:.1f} MB
'''

        # Find checkpoint section and append
        checkpoint_marker = "## Checkpoint States"
        if checkpoint_marker in content:
            # Remove "no checkpoints" placeholder
            content = content.replace(
                "*No checkpoints recorded yet*",
                ""
            )

            # Insert after header
            parts = content.split(checkpoint_marker)
            content = parts[0] + checkpoint_marker + "\n" + checkpoint_entry + parts[1]

        self.progress_file.write_text(content)

    def add_fact_check(
        self,
        measurement: str,
        input_cm: float,
        output_cm: float,
        accuracy: float,
    ) -> None:
        """Add a fact check entry to the log."""
        content = self.progress_file.read_text()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Remove placeholder if present
        content = content.replace(
            "| *No measurements verified yet* | - | - | - | - |",
            ""
        )

        # Add new row
        new_row = f"| {measurement} | {input_cm:.1f} | {output_cm:.1f} | {accuracy:.1f}% | {timestamp} |"

        # Find fact check table
        pattern = r'(\| Measurement \| Input.*\n\|[-|]+\n)'

        def add_row(match):
            return match.group(1) + new_row + "\n"

        content = re.sub(pattern, add_row, content)
        self.progress_file.write_text(content)

    def update_vram_status(self) -> None:
        """Update VRAM allocation table."""
        content = self.progress_file.read_text()

        available = self._get_vram_available_gb()
        used = self._get_vram_used_mb() / 1024

        # Update available row
        content = re.sub(
            r'\| Available \| [\d.]+ GB \| Ready \|',
            f'| Available | {available:.1f} GB | Ready |',
            content
        )

        self.progress_file.write_text(content)

    def mark_work_in_progress(
        self,
        current_task: str,
        files_being_modified: List[str],
        resume_instructions: str,
    ) -> None:
        """Update work-in-progress section for session interruption."""
        content = self.progress_file.read_text()

        wip_section = f'''
## Work-in-Progress State

**Current Task**: {current_task}
**Files Being Modified**:
{chr(10).join(f"- `{f}`" for f in files_being_modified)}

**Resume Instructions**:
{resume_instructions}

**Timestamp**: {datetime.now().isoformat()}
'''

        # Find or create WIP section
        if "## Work-in-Progress State" in content:
            content = re.sub(
                r'## Work-in-Progress State.*?(?=\n## |\n---|\Z)',
                wip_section,
                content,
                flags=re.DOTALL
            )
        else:
            # Insert before error log or at end
            if "## Error Log" in content:
                content = content.replace("## Error Log", wip_section + "\n## Error Log")
            else:
                content += "\n" + wip_section

        self.progress_file.write_text(content)

    def log_error(
        self,
        error: str,
        resolution: str = "",
        status: str = "OPEN",
    ) -> None:
        """Log an error to the error log section."""
        content = self.progress_file.read_text()

        timestamp = datetime.now().isoformat()

        # Remove placeholder if present
        content = content.replace(
            "| *No errors logged yet* | - | - | - |",
            ""
        )

        # Add new error row
        error_short = error[:50] + "..." if len(error) > 50 else error
        resolution_short = resolution[:30] + "..." if len(resolution) > 30 else resolution

        new_row = f"| {timestamp} | {error_short} | {resolution_short} | {status} |"

        pattern = r'(\| Timestamp \| Error.*\n\|[-|]+\n)'

        def add_row(match):
            return match.group(1) + new_row + "\n"

        content = re.sub(pattern, add_row, content)
        self.progress_file.write_text(content)


# Global singleton instance
_tracker: Optional[ProgressTracker] = None


def get_tracker(
    progress_file: Optional[Path] = None,
    project_root: Optional[Path] = None,
) -> ProgressTracker:
    """Get or create singleton ProgressTracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = ProgressTracker(progress_file, project_root)
    return _tracker


def update_progress(
    mission: int,
    status: str,
    completed: List[str],
    pending: List[str],
) -> None:
    """Convenience function to update mission progress."""
    tracker = get_tracker()
    tracker.update_mission_status(mission, status, completed, pending)
    tracker.update_vram_status()


def checkpoint(name: str, state: Dict[str, Any]) -> None:
    """Convenience function to add checkpoint."""
    tracker = get_tracker()
    tracker.add_checkpoint(name, state)
