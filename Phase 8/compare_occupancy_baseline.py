from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from phase8.occupancy_compare import (
        OccupancyComparisonConfig,
        compare_occupancy_baseline_and_real,
        compare_occupancy_baseline_and_real_series,
        save_occupancy_comparison,
    )
else:
    from .phase8.occupancy_compare import (
        OccupancyComparisonConfig,
        compare_occupancy_baseline_and_real,
        compare_occupancy_baseline_and_real_series,
        save_occupancy_comparison,
    )


DEFAULT_SERIES_SEEDS = (0, 7, 13, 29, 43)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Compare the occupancy baseline against the Phase 8 REAL path.')
    parser.add_argument('--preset', default='synth_v1_default')
    parser.add_argument('--selector-seed', type=int, default=0)
    parser.add_argument('--selector-seeds', type=int, nargs='+', help='Run a repeated comparison series across these selector seeds.')
    parser.add_argument('--default-series-seeds', action='store_true', help='Run the built-in multi-seed comparison series.')
    parser.add_argument('--cycles-per-timestep', type=int, default=4)
    parser.add_argument('--drain-cycles', type=int, default=12)
    parser.add_argument('--feedback-amount', type=float, default=0.05)
    parser.add_argument('--max-train-episodes', type=int)
    parser.add_argument('--max-eval-episodes', type=int)
    parser.add_argument('--output-json')
    return parser.parse_args()



def main() -> None:
    args = parse_args()
    config = OccupancyComparisonConfig(
        preset_name=args.preset,
        selector_seed=args.selector_seed,
        cycles_per_timestep=args.cycles_per_timestep,
        drain_cycles=args.drain_cycles,
        feedback_amount=args.feedback_amount,
        max_train_episodes=args.max_train_episodes,
        max_eval_episodes=args.max_eval_episodes,
    )

    selector_seeds = tuple(args.selector_seeds or ())
    if args.default_series_seeds:
        selector_seeds = DEFAULT_SERIES_SEEDS

    result = (
        compare_occupancy_baseline_and_real_series(selector_seeds=selector_seeds, config=config)
        if selector_seeds
        else compare_occupancy_baseline_and_real(config)
    )
    payload = result.to_dict()
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.output_json:
        save_occupancy_comparison(result, args.output_json)


if __name__ == '__main__':
    main()
