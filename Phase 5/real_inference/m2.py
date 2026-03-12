from __future__ import annotations

import json
import random
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Make Phase 4 real_core importable when this package is imported directly.
_THIS_FILE = Path(__file__).resolve()
_PHASE2_DIR = _THIS_FILE.parents[2]
_PHASE4_DIR = _PHASE2_DIR / "Phase 4"
if str(_PHASE4_DIR) not in sys.path:
    sys.path.insert(0, str(_PHASE4_DIR))

from real_core.engine import RealCoreEngine

from .adapter import InferenceActionBackend, InferenceRuntimeState
from .coherence import InferenceCoherenceModel
from .live import LiveLoopConfig, LiveSegmentObservationAdapter


DEFAULT_MODEL_NAME_MAP = {
    "qwen3_0_6b": "Qwen/Qwen3-0.6B",
    "qwen2_5_0_5b": "Qwen/Qwen2.5-0.5B",
    "tinyllama_1_1b": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "pythia_1b": "EleutherAI/pythia-1b",
    "pythia_2_8b": "EleutherAI/pythia-2.8b",
}


@dataclass
class M2RunConfig:
    model_key: str = "tinyllama_1_1b"
    fallback_model_keys: tuple[str, ...] = ("qwen3_0_6b",)
    prompt_id: str = "cp_001"
    run_mode: str = "smoke"  # smoke | full
    seed: int = 42
    initial_temperature: float = 0.8
    segment_tokens_smoke: int = 16
    segment_tokens_full: int = 24
    max_new_tokens_smoke: int = 96
    max_new_tokens_full: int = 240
    target_cycles_smoke: int = 8
    target_cycles_full: int = 20
    interventions_enabled: bool = True
    output_tag_suffix: str = ""


def _sanitize_tag(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _load_prompt(prompt_path: Path, prompt_id: str) -> dict[str, Any]:
    data = json.loads(prompt_path.read_text(encoding="utf-8"))
    for p in data["prompts"]:
        if p["id"] == prompt_id:
            return p
    raise ValueError(f"Prompt id not found: {prompt_id}")


def _load_model(model_name_map: dict[str, str], model_key: str, fallback_keys: tuple[str, ...]):
    try:
        import torch
        from transformer_lens import HookedTransformer
    except Exception as exc:
        raise RuntimeError(
            "M2 live run requires torch + transformer_lens installed in the active environment"
        ) from exc

    requested = [model_key] + [k for k in fallback_keys if k != model_key]
    unknown = [k for k in requested if k not in model_name_map]
    if unknown:
        raise ValueError(f"Unknown model keys: {unknown}. Available keys: {sorted(model_name_map)}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    errors: list[dict[str, str]] = []
    for key in requested:
        name = model_name_map[key]
        try:
            model = HookedTransformer.from_pretrained(name, device=device, dtype=dtype)
            return model, key, name, device, str(dtype), requested
        except Exception as exc:
            errors.append({"model_key": key, "model_name": name, "error": str(exc)})

    raise RuntimeError(f"Unable to load requested models: {errors}")


def run_m2_minimal_session(
    *,
    phase5_root: Path,
    config: M2RunConfig,
    model_name_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    model_map = model_name_map or DEFAULT_MODEL_NAME_MAP

    if config.run_mode not in {"smoke", "full"}:
        raise ValueError("run_mode must be 'smoke' or 'full'")

    random.seed(config.seed)

    prompt_path = phase5_root / "experiments" / "m0" / "prompts_m0.json"
    prompt_obj = _load_prompt(prompt_path, config.prompt_id)

    model, resolved_model_key, resolved_model_name, device_name, dtype_name, requested_keys = _load_model(
        model_map,
        config.model_key,
        config.fallback_model_keys,
    )

    segment_tokens = config.segment_tokens_smoke if config.run_mode == "smoke" else config.segment_tokens_full
    max_total_new_tokens = config.max_new_tokens_smoke if config.run_mode == "smoke" else config.max_new_tokens_full
    target_cycles = config.target_cycles_smoke if config.run_mode == "smoke" else config.target_cycles_full

    state = InferenceRuntimeState(
        current_temperature=config.initial_temperature,
        enable_interventions=config.interventions_enabled,
    )
    live_cfg = LiveLoopConfig(
        segment_tokens=segment_tokens,
        max_total_new_tokens=max_total_new_tokens,
        temperature=config.initial_temperature,
        sample_multinomial=True,
    )

    observer = LiveSegmentObservationAdapter(
        model=model,
        runtime_state=state,
        prompt=prompt_obj["prompt"],
        config=live_cfg,
    )
    actions = InferenceActionBackend(state, enable_interventions=config.interventions_enabled)
    coherence = InferenceCoherenceModel()

    engine = RealCoreEngine(
        observer=observer,
        actions=actions,
        coherence=coherence,
        domain_name="phase5_inference_m2_minimal",
    )

    cycles = min(target_cycles, observer.max_cycles_estimate)
    summary = engine.run_session(cycles=cycles, consolidate_on_action="rest")

    gco_values = [e.gco.value for e in engine.memory.entries]
    unique_gco = sorted(set(gco_values))
    m2_success = len(unique_gco) >= 2

    base_tag = f"{_sanitize_tag(config.model_key)}_{_sanitize_tag(config.run_mode)}"
    if config.output_tag_suffix:
        base_tag = f"{base_tag}_{_sanitize_tag(config.output_tag_suffix)}"
    mode_tag = "active" if config.interventions_enabled else "passive"
    experiment_tag = f"{base_tag}_{mode_tag}"

    results_dir = phase5_root / "experiments" / "m2" / "minimal" / experiment_tag
    results_dir.mkdir(parents=True, exist_ok=True)

    run_meta = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase5_root": str(phase5_root),
        "results_dir": str(results_dir),
        "experiment_tag": experiment_tag,
        "run_mode": config.run_mode,
        "prompt_id": config.prompt_id,
        "prompt_topic": prompt_obj["topic"],
        "prompt_text": prompt_obj["prompt"],
        "requested_model_key": config.model_key,
        "fallback_model_keys": list(config.fallback_model_keys),
        "requested_model_keys_in_order": requested_keys,
        "resolved_model_key": resolved_model_key,
        "resolved_model_name": resolved_model_name,
        "device": device_name,
        "dtype": dtype_name,
        "seed": config.seed,
        "initial_temperature": config.initial_temperature,
        "segment_tokens": segment_tokens,
        "max_total_new_tokens": max_total_new_tokens,
        "cycles": cycles,
        "interventions_enabled": config.interventions_enabled,
    }

    summary_artifact = {
        "cycles": summary.cycles,
        "mean_coherence": summary.mean_coherence,
        "final_coherence": summary.final_coherence,
        "gco_counts": summary.gco_counts,
        "unique_gco_states": unique_gco,
        "m2_success_gco_variation": m2_success,
        "generation_complete": observer.generation_complete,
    }

    cycle_log = [
        {
            "cycle": e.cycle,
            "action": e.action,
            "mode": e.mode,
            "coherence": e.coherence,
            "delta": e.delta,
            "gco": e.gco.value,
            "state_after": e.state_after,
        }
        for e in engine.memory.entries
    ]

    (results_dir / "run_meta.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")
    (results_dir / "m2_summary.json").write_text(json.dumps(summary_artifact, indent=2), encoding="utf-8")
    (results_dir / "generated_text.txt").write_text(observer.generated_text(), encoding="utf-8")

    with (results_dir / "m2_cycle_log.jsonl").open("w", encoding="utf-8") as f:
        for row in cycle_log:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    with (results_dir / "m2_segment_trace.jsonl").open("w", encoding="utf-8") as f:
        for row in observer.segment_trace:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return {
        "results_dir": str(results_dir),
        "run_meta": run_meta,
        "summary": summary_artifact,
    }
