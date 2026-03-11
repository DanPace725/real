from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from real_core.types import ActionOutcome, DimensionScores, GCOStatus, CycleEntry


class RepoHealthObservationAdapter:
    """Observes repository-structure signals as a substrate."""

    def __init__(self, root_path: str | Path, max_scan_files: int = 2000) -> None:
        self.root = Path(root_path).resolve()
        self.max_scan_files = max_scan_files

    def observe(self, cycle: int) -> Dict[str, float]:
        files: list[Path] = []
        pycache_dirs = 0
        todo_count = 0

        if self.root.exists():
            for p in self.root.rglob("*"):
                if p.is_dir() and p.name == "__pycache__":
                    pycache_dirs += 1
                if p.is_file():
                    files.append(p)
                    if len(files) >= self.max_scan_files:
                        break

        total_files = max(1, len(files))
        py_files = sum(1 for f in files if f.suffix == ".py")
        md_files = sum(1 for f in files if f.suffix.lower() == ".md")
        test_files = sum(
            1
            for f in files
            if f.name.startswith("test_") or "tests" in {part.lower() for part in f.parts}
        )

        # Sample text inspection for TODO density.
        for f in files[: min(250, len(files))]:
            if f.suffix.lower() in {".py", ".md", ".txt", ".toml", ".json"}:
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                    todo_count += text.lower().count("todo")
                except OSError:
                    continue

        py_ratio = py_files / total_files
        doc_ratio = md_files / total_files
        test_ratio = min(1.0, test_files / max(1, py_files))
        artifact_ratio = min(1.0, pycache_dirs / max(1, total_files))
        todo_density = min(1.0, todo_count / max(1, len(files[: min(250, len(files))]) * 3))
        size_norm = min(1.0, total_files / 3000.0)

        return {
            "cycle": float(cycle),
            "size_norm": size_norm,
            "py_ratio": py_ratio,
            "doc_ratio": doc_ratio,
            "test_ratio": test_ratio,
            "artifact_ratio": artifact_ratio,
            "todo_density": todo_density,
        }


class RepoHealthActionBackend:
    """Actions represent analysis strategies on repository health."""

    _ALL = [
        "scan_repo",
        "inspect_tests",
        "review_docs",
        "triage_todos",
        "stability_pass",
        "rest",
    ]

    def __init__(self, root_path: str | Path) -> None:
        self.root = Path(root_path).resolve()

    def available_actions(self, history_size: int) -> List[str]:
        if history_size < 4:
            return ["scan_repo", "rest", "inspect_tests"]
        if history_size < 10:
            return ["scan_repo", "rest", "inspect_tests", "review_docs", "triage_todos"]
        return list(self._ALL)

    def execute(self, action: str) -> ActionOutcome:
        t0 = time.perf_counter()
        result: Dict[str, float | int | str] = {"action": action}

        if action == "scan_repo":
            n = sum(1 for _ in self.root.rglob("*") if _.is_file()) if self.root.exists() else 0
            result["file_count"] = n
        elif action == "inspect_tests":
            n = 0
            if self.root.exists():
                for p in self.root.rglob("test_*.py"):
                    if p.is_file():
                        n += 1
            result["test_files"] = n
        elif action == "review_docs":
            n = 0
            if self.root.exists():
                for p in self.root.rglob("*.md"):
                    if p.is_file():
                        n += 1
            result["doc_files"] = n
        elif action == "triage_todos":
            n = 0
            if self.root.exists():
                for p in self.root.rglob("*.py"):
                    if p.is_file():
                        try:
                            n += p.read_text(encoding="utf-8", errors="ignore").lower().count("todo")
                        except OSError:
                            continue
            result["todo_hits"] = n
        elif action == "stability_pass":
            _ = sum(i * i for i in range(12000))
        elif action == "rest":
            pass

        elapsed = time.perf_counter() - t0
        return ActionOutcome(success=True, result=result, cost_secs=elapsed)


@dataclass
class RepoHealthCoherenceModel:
    dimension_names: Tuple[str, ...] = (
        "continuity",
        "vitality",
        "contextual_fit",
        "differentiation",
        "accountability",
        "reflexivity",
    )

    def score(self, state_after: Dict[str, float], history: List[CycleEntry]) -> DimensionScores:
        size_norm = state_after.get("size_norm", 0.3)
        py_ratio = state_after.get("py_ratio", 0.3)
        doc_ratio = state_after.get("doc_ratio", 0.1)
        test_ratio = state_after.get("test_ratio", 0.2)
        artifact_ratio = state_after.get("artifact_ratio", 0.0)
        todo_density = state_after.get("todo_density", 0.1)

        if len(history) < 3:
            continuity = 0.5
        else:
            recent_size = [e.state_after.get("size_norm", size_norm) for e in history[-6:]]
            mean_size = sum(recent_size) / len(recent_size)
            continuity = max(0.0, min(1.0, 1.0 - abs(size_norm - mean_size) * 3.0))

        vitality = max(0.0, min(1.0, 1.0 - ((py_ratio - 0.35) ** 2) / 0.20 - artifact_ratio * 0.3))
        contextual_fit = max(0.0, min(1.0, 0.55 * test_ratio + 0.45 * doc_ratio))
        differentiation = max(0.0, min(1.0, 1.0 - artifact_ratio))
        accountability = max(0.0, min(1.0, 1.0 - todo_density * 0.8))

        recent = history[-12:]
        if len(recent) < 4:
            reflexivity = 0.3
        else:
            dips = 0
            switches = 0
            recoveries = 0
            for i in range(1, len(recent)):
                if recent[i - 1].delta < -0.01:
                    dips += 1
                    if recent[i].action != recent[i - 1].action:
                        switches += 1
                        if recent[i].delta > 0:
                            recoveries += 1
            switch_rate = switches / max(1, dips)
            recovery_rate = recoveries / max(1, switches)
            reflexivity = 0.4 * switch_rate + 0.6 * recovery_rate

        return {
            "continuity": continuity,
            "vitality": vitality,
            "contextual_fit": contextual_fit,
            "differentiation": differentiation,
            "accountability": accountability,
            "reflexivity": reflexivity,
        }

    def composite(self, dimensions: DimensionScores) -> float:
        return sum(dimensions.values()) / max(1, len(dimensions))

    def gco_status(self, dimensions: DimensionScores, coherence: float) -> GCOStatus:
        if coherence < 0.40:
            return GCOStatus.CRITICAL
        if coherence < 0.65:
            return GCOStatus.DEGRADED
        if all(v >= 0.65 for v in dimensions.values()):
            return GCOStatus.STABLE
        return GCOStatus.PARTIAL
