from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from domains.registry import build_domain
from real_core.engine import RealCoreEngine
from real_core.memory import EpisodicMemory
from real_core.mesh import TiltRegulatoryMesh
from real_core.selector import CFARSelector
from real_core.session import SessionHistory


def load_config(config_path: Path) -> dict:
    with config_path.open("rb") as f:
        return tomllib.load(f)


def _resolve_path(path_value: str, base_dir: Path) -> Path:
    p = Path(path_value)
    if not p.is_absolute():
        p = (base_dir / p).resolve()
    return p


def build_engine_from_config(config: dict, config_path: Path) -> RealCoreEngine:
    domain_name = config.get("domain", "hardware")
    domain_cfg = config.get("domain_config", {})
    bundle = build_domain(domain_name, domain_cfg, base_dir=config_path.parent)

    selector_cfg = config.get("selector", {})
    selector = CFARSelector(
        exploration_rate=float(selector_cfg.get("exploration_rate", 0.40)),
        stagnation_window=int(selector_cfg.get("stagnation_window", 5)),
        stagnation_threshold=float(selector_cfg.get("stagnation_threshold", 0.005)),
        guided_threshold=int(selector_cfg.get("guided_threshold", 12)),
        budget_mode=bool(selector_cfg.get("budget_mode", True)),
    )

    mesh_cfg = config.get("mesh", {})
    mesh = TiltRegulatoryMesh(
        enabled=bool(mesh_cfg.get("enabled", True)),
        viability_floor=float(mesh_cfg.get("viability_floor", 0.757)),
        parametric_wall=float(mesh_cfg.get("parametric_wall", 0.289)),
    )

    memory_cfg = config.get("memory", {})
    memory = EpisodicMemory(maxlen=int(memory_cfg.get("maxlen", 500)))

    history_cfg = config.get("history", {})
    history_enabled = bool(history_cfg.get("enabled", True))
    session_history = None
    if history_enabled:
        history_path = _resolve_path(str(history_cfg.get("path", "memory/session_history.json")), config_path.parent)
        session_history = SessionHistory(path=history_path)

    return RealCoreEngine(
        observer=bundle.observer,
        actions=bundle.actions,
        coherence=bundle.coherence,
        selector=selector,
        mesh=mesh,
        memory=memory,
        domain_name=domain_name,
        session_history=session_history,
    )


def run_from_config(config_path: Path) -> dict:
    cfg = load_config(config_path)
    engine = build_engine_from_config(cfg, config_path)

    session_cfg = cfg.get("session", {})
    cycles = int(session_cfg.get("cycles", 50))
    consolidate_on_action = str(session_cfg.get("consolidate_on_action", "rest"))

    summary = engine.run_session(cycles=cycles, consolidate_on_action=consolidate_on_action)

    out = {
        "domain": cfg.get("domain", "hardware"),
        "cycles": summary.cycles,
        "mean_coherence": summary.mean_coherence,
        "final_coherence": summary.final_coherence,
        "gco_counts": summary.gco_counts,
        "session_id": summary.session_id,
    }
    if engine.session_history is not None:
        out["session_history_count"] = engine.session_history.count
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Run REAL Phase 4 experiment from TOML config")
    parser.add_argument(
        "--config",
        type=Path,
        default=THIS_DIR / "experiments" / "example_hardware.toml",
        help="Path to experiment TOML config",
    )
    args = parser.parse_args()

    result = run_from_config(args.config.resolve())
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
