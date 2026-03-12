"""
colab_setup.py - Path bootstrap for Phase 5 notebooks.

Usage (Cell 1 in notebooks):
    exec(open("/content/Phase 5/colab_setup.py").read())

Then PHASE5_ROOT and PHASE4_ROOT are available and both are on sys.path.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


_PHASE5_CANDIDATES = [
    Path(os.environ.get("COLAB_PHASE5_PATH", "")),
    Path("/content/Phase 5"),
    Path("/content/phase5"),
    Path("/content/workspace/real_phase5/Phase 5"),
    Path("/content/drive/MyDrive/real_phase5/Phase 5"),
    Path("/content/drive/MyDrive/REAL_Phase5/Phase 5"),
    Path("/content/Relationally Embedded Allostatic Learning/Phase 2/Phase 5"),
]


def _find_phase5_root() -> Path:
    for candidate in _PHASE5_CANDIDATES:
        if not str(candidate):
            continue
        if (candidate / "plan.md").exists():
            return candidate.resolve()

    for candidate in [Path.cwd(), *Path.cwd().parents]:
        if (candidate / "plan.md").exists() and (candidate / "README.md").exists():
            return candidate.resolve()
        nested = candidate / "Phase 2" / "Phase 5"
        if (nested / "plan.md").exists():
            return nested.resolve()

    raise FileNotFoundError(
        "Could not locate Phase 5 root. "
        "Set COLAB_PHASE5_PATH or place Phase 5 under /content/Phase 5."
    )


def _find_phase4_root(phase5_root: Path) -> Path:
    override = os.environ.get("COLAB_PHASE4_PATH")
    if override:
        p = Path(override)
        if p.exists():
            return p.resolve()

    candidates = [
        phase5_root.parent / "Phase 4",
        Path("/content/Phase 4"),
        Path("/content/workspace/real_phase5/Phase 4"),
        Path("/content/drive/MyDrive/real_phase5/Phase 4"),
        Path("/content/drive/MyDrive/REAL_Phase5/Phase 4"),
    ]
    for c in candidates:
        if c.exists():
            return c.resolve()

    raise FileNotFoundError(
        "Could not locate Phase 4 root. "
        "Set COLAB_PHASE4_PATH or place Phase 4 next to Phase 5."
    )


def bootstrap_paths(add_to_sys_path: bool = True) -> tuple[Path, Path]:
    phase5_root = _find_phase5_root()
    phase4_root = _find_phase4_root(phase5_root)

    if add_to_sys_path:
        for p in [str(phase5_root), str(phase4_root)]:
            if p not in sys.path:
                sys.path.insert(0, p)

    return phase5_root, phase4_root


PHASE5_ROOT, PHASE4_ROOT = bootstrap_paths(add_to_sys_path=True)
print(f"Phase 5 root : {PHASE5_ROOT}")
print(f"Phase 4 root : {PHASE4_ROOT}")
