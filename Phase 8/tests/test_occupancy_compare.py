from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phase8 import (
    OccupancyComparisonConfig,
    compare_occupancy_baseline_and_real,
    compare_occupancy_baseline_and_real_series,
    save_occupancy_comparison,
)


class TestOccupancyComparison(unittest.TestCase):
    def test_comparison_runner_returns_baseline_real_and_delta_summaries(self) -> None:
        result = compare_occupancy_baseline_and_real(
            OccupancyComparisonConfig(
                max_train_episodes=6,
                max_eval_episodes=3,
                cycles_per_timestep=2,
                drain_cycles=6,
                feedback_amount=0.05,
            )
        )

        self.assertEqual(result.train_episodes, 6)
        self.assertEqual(result.eval_episodes, 3)
        self.assertIn('metrics', result.baseline_result)
        self.assertIn('accuracy', result.baseline_metrics)
        self.assertIn('accuracy', result.real_train_summary)
        self.assertIn('accuracy', result.real_eval_summary)
        self.assertIn('accuracy', result.eval_minus_baseline)
        self.assertIn('mean_feedback_amount', result.real_train_summary)

    def test_comparison_series_aggregates_multiple_selector_seeds(self) -> None:
        result = compare_occupancy_baseline_and_real_series(
            selector_seeds=(0, 1),
            config=OccupancyComparisonConfig(
                max_train_episodes=4,
                max_eval_episodes=2,
                cycles_per_timestep=2,
                drain_cycles=6,
            ),
        )

        self.assertEqual(result.selector_seeds, (0, 1))
        self.assertEqual(len(result.runs), 2)
        self.assertIn('accuracy', result.aggregate_train_summary)
        self.assertIn('accuracy', result.aggregate_eval_summary)
        self.assertIn('accuracy', result.aggregate_eval_minus_baseline)

    def test_comparison_result_can_be_saved(self) -> None:
        result = compare_occupancy_baseline_and_real_series(
            selector_seeds=(0, 1),
            config=OccupancyComparisonConfig(
                max_train_episodes=4,
                max_eval_episodes=2,
                cycles_per_timestep=2,
                drain_cycles=6,
            ),
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'comparison.json'
            save_occupancy_comparison(result, output_path)
            payload = json.loads(output_path.read_text(encoding='utf-8'))

        self.assertEqual(payload['selector_seeds'], [0, 1])
        self.assertEqual(len(payload['runs']), 2)
        self.assertIn('aggregate_eval_summary', payload)
        self.assertIn('aggregate_eval_minus_baseline', payload)


if __name__ == '__main__':
    unittest.main()
