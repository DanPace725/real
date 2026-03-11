from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from domains.hardware.adapter import (
    HardwareActionBackend,
    HardwareCoherenceModel,
    HardwareObservationAdapter,
)
from domains.llm_api.adapter import make_llm_api_bundle
from domains.repo_health.adapter import (
    RepoHealthActionBackend,
    RepoHealthCoherenceModel,
    RepoHealthObservationAdapter,
)


@dataclass
class DomainBundle:
    observer: Any
    actions: Any
    coherence: Any


def _resolve_path(path_value: str, base_dir: Path) -> Path:
    p = Path(path_value)
    if not p.is_absolute():
        p = (base_dir / p).resolve()
    return p


def build_domain(name: str, domain_config: Dict[str, Any] | None = None, base_dir: str | Path = ".") -> DomainBundle:
    cfg = domain_config or {}
    base = Path(base_dir).resolve()

    if name == "hardware":
        seed = cfg.get("seed")
        return DomainBundle(
            observer=HardwareObservationAdapter(seed=seed),
            actions=HardwareActionBackend(),
            coherence=HardwareCoherenceModel(),
        )

    if name == "repo_health":
        root_value = cfg.get("root_path", "../Phase 2")
        root = _resolve_path(str(root_value), base)
        max_scan_files = int(cfg.get("max_scan_files", 2000))
        return DomainBundle(
            observer=RepoHealthObservationAdapter(root_path=root, max_scan_files=max_scan_files),
            actions=RepoHealthActionBackend(root_path=root),
            coherence=RepoHealthCoherenceModel(),
        )

    if name == "llm_api":
        seed = cfg.get("seed")
        mode = str(cfg.get("mode", "synthetic"))
        trace_input = cfg.get("trace_input_path")
        trace_output = cfg.get("trace_output_path")
        strict_action_match = bool(cfg.get("strict_action_match", False))
        loop_replay = bool(cfg.get("loop_replay", True))
        observation_noise = float(cfg.get("observation_noise", 0.01))

        resolved_trace_input = None
        if trace_input:
            resolved_trace_input = _resolve_path(str(trace_input), base)
        resolved_trace_output = None
        if trace_output:
            resolved_trace_output = _resolve_path(str(trace_output), base)

        observer, actions, coherence = make_llm_api_bundle(
            seed=seed,
            mode=mode,
            trace_input_path=resolved_trace_input,
            trace_output_path=resolved_trace_output,
            strict_action_match=strict_action_match,
            loop_replay=loop_replay,
            observation_noise=observation_noise,
        )
        return DomainBundle(observer=observer, actions=actions, coherence=coherence)

    raise ValueError("Unknown domain '%s'. Supported: hardware, repo_health, llm_api" % name)
