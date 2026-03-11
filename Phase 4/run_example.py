from __future__ import annotations

import sys
from pathlib import Path

# Ensure Phase 4 package roots are importable when run directly.
THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from run_experiment import run_from_config


def main() -> None:
    config = THIS_DIR / "experiments" / "example_hardware.toml"
    result = run_from_config(config)

    print("REAL Phase 4 demo session")
    print(f"  domain: {result['domain']}")
    print(f"  cycles: {result['cycles']}")
    print(f"  mean coherence: {result['mean_coherence']:.3f}")
    print(f"  final coherence: {result['final_coherence']:.3f}")
    print(f"  gco: {result['gco_counts']}")
    if result.get("session_id") is not None:
        print(f"  session id: {result['session_id']}")


if __name__ == "__main__":
    main()
