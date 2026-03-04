"""
Sandbox — the boundary between the agent and the real OS.

The sandbox is an *architectural constraint*, not a rule system.
Two layers:

    1. Action whitelist (nervous system): only implemented functions exist.
       Fork-bombing is not prohibited — it is not implemented.

    2. Path validation (skin): every file operation resolves its path and
       rejects anything that escapes SANDBOX_DIR.  The agent's world has
       walls.

Hard limits: 50 MB sandbox, bounded paths, no network access.
These are P4 (Symmetric/Constraint) artifacts — boundaries baked into
what the system physically is, not rules it could choose to break.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from real.coherence.engine import SystemState


# ── Configuration ─────────────────────────────────────────────────────

SANDBOX_DIR = Path(os.environ.get(
    "REAL_SANDBOX", str(Path.home() / ".real_sandbox")
))
MEMORY_DIR = SANDBOX_DIR / "memory"
TERRAIN_DIR = SANDBOX_DIR / "terrain"
TEMP_DIR = SANDBOX_DIR / "temp"

MAX_SANDBOX_MB = 50
MAX_FILE_KB = 512


# ── Path safety ──────────────────────────────────────────────────────

def _safe_path(requested: str | Path) -> Path:
    """
    Resolve a path and verify it stays within SANDBOX_DIR.
    Raises ValueError if the path escapes.
    """
    resolved = (SANDBOX_DIR / requested).resolve()
    sandbox_resolved = SANDBOX_DIR.resolve()
    if not str(resolved).startswith(str(sandbox_resolved)):
        raise ValueError(
            f"Path escape attempt: {requested} resolves to {resolved}"
        )
    return resolved


def _sandbox_size_mb() -> float:
    """Total size of sandbox directory in MB."""
    total = 0
    if SANDBOX_DIR.exists():
        for f in SANDBOX_DIR.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    return total / (1024 * 1024)


# ── Sandbox initialization ───────────────────────────────────────────

def initialize_sandbox() -> Dict[str, Any]:
    """
    Create sandbox directory structure.  Returns metadata about the space.
    Safe to call multiple times.
    """
    for d in [SANDBOX_DIR, MEMORY_DIR, TERRAIN_DIR, TEMP_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    return {
        "sandbox_dir": str(SANDBOX_DIR),
        "size_mb": _sandbox_size_mb(),
        "max_mb": MAX_SANDBOX_MB,
    }


# ── Sandbox actions (the body's interface with reality) ──────────────

class Sandbox:
    """
    The agent's physical boundary.  All real-world interactions go through here.
    Provides safe file I/O, terrain operations, and system state reading.
    """

    def __init__(self) -> None:
        self.info = initialize_sandbox()
        self.session_start = time.time()
        self.action_count = 0

    def read_system_state(self, cycle: int) -> SystemState:
        """Read real hardware state.  This is the ground truth."""
        return SystemState.read(
            cycle_number=cycle,
            session_start=self.session_start,
        )

    # ── Terrain operations ────────────────────────────────────────────

    def list_terrain(self) -> list[str]:
        """List terrain files (real filesystem scan)."""
        if not TERRAIN_DIR.exists():
            return []
        return [f.name for f in TERRAIN_DIR.iterdir() if f.is_file()]

    def read_terrain(self, name: str) -> Optional[str]:
        """Read a terrain file (real file read)."""
        try:
            path = _safe_path(f"terrain/{name}")
            if path.exists() and path.is_file():
                return path.read_text(encoding="utf-8")
        except (ValueError, OSError):
            pass
        return None

    def mark_terrain(self, name: str, content: str) -> bool:
        """
        Write a terrain mark (real file write).
        Returns False if sandbox size limit would be exceeded.
        """
        if _sandbox_size_mb() >= MAX_SANDBOX_MB:
            return False
        try:
            path = _safe_path(f"terrain/{name}")
            if len(content.encode("utf-8")) > MAX_FILE_KB * 1024:
                return False
            path.write_text(content, encoding="utf-8")
            return True
        except (ValueError, OSError):
            return False

    # ── Memory file operations ────────────────────────────────────────

    def save_memory(self, name: str, data: str) -> bool:
        """Write to the memory directory (real file write)."""
        try:
            path = _safe_path(f"memory/{name}")
            path.write_text(data, encoding="utf-8")
            return True
        except (ValueError, OSError):
            return False

    def read_memory(self, name: str) -> Optional[str]:
        """Read from the memory directory (real file read)."""
        try:
            path = _safe_path(f"memory/{name}")
            if path.exists():
                return path.read_text(encoding="utf-8")
        except (ValueError, OSError):
            pass
        return None

    # ── Cleanup ───────────────────────────────────────────────────────

    def cleanup_temp(self) -> int:
        """Remove temp files.  Returns count removed."""
        removed = 0
        if TEMP_DIR.exists():
            for f in TEMP_DIR.iterdir():
                if f.is_file():
                    f.unlink()
                    removed += 1
        return removed

    # ── Stats ─────────────────────────────────────────────────────────

    def sandbox_stats(self) -> Dict[str, Any]:
        return {
            "size_mb": _sandbox_size_mb(),
            "max_mb": MAX_SANDBOX_MB,
            "terrain_files": len(self.list_terrain()),
            "actions_performed": self.action_count,
        }
