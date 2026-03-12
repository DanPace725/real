from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def find_phase5_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "plan.md").exists() and (candidate / "README.md").exists():
            return candidate
        nested = candidate / "Phase 2" / "Phase 5"
        if (nested / "plan.md").exists():
            return nested
    raise FileNotFoundError("Could not locate Phase 5 root from current working directory.")


def parse_tuple_csv(value: str) -> tuple[str, ...]:
    value = value.strip()
    if not value:
        return tuple()
    return tuple(part.strip() for part in value.split(",") if part.strip())


def main() -> None:
    phase5_root = find_phase5_root(Path(__file__).resolve().parents[1])
    if str(phase5_root) not in sys.path:
        sys.path.insert(0, str(phase5_root))

    from real_inference.m2 import M2RunConfig, run_m2_minimal_session

    parser = argparse.ArgumentParser(description="Run Phase 5 M2 minimal REAL loop")
    parser.add_argument("--model-key", default="tinyllama_1_1b")
    parser.add_argument("--fallback-model-keys", default="qwen3_0_6b")
    parser.add_argument("--prompt-id", default="cp_001")
    parser.add_argument("--run-mode", default="smoke", choices=["smoke", "full"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--initial-temperature", type=float, default=0.8)
    parser.add_argument("--output-tag-suffix", default="")
    parser.add_argument(
        "--passive",
        action="store_true",
        help="Disable interventions (observe/rest only). Useful as a control run.",
    )
    args = parser.parse_args()

    cfg = M2RunConfig(
        model_key=args.model_key,
        fallback_model_keys=parse_tuple_csv(args.fallback_model_keys),
        prompt_id=args.prompt_id,
        run_mode=args.run_mode,
        seed=args.seed,
        initial_temperature=args.initial_temperature,
        interventions_enabled=not args.passive,
        output_tag_suffix=args.output_tag_suffix,
    )

    result = run_m2_minimal_session(
        phase5_root=phase5_root,
        config=cfg,
    )

    print(json.dumps(result["summary"], indent=2))
    print(f"Results dir: {result['results_dir']}")


if __name__ == "__main__":
    main()
