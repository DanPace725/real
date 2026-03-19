from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phase8 import (
    OCCUPANCY_EXECUTION_SINK_ID,
    build_occupancy_episodes_from_preset,
    build_occupancy_execution_system,
    occupancy_execution_topology,
    run_occupancy_episode,
    summarize_occupancy_results,
)


class TestOccupancyExecution(unittest.TestCase):
    def test_execution_topology_uses_single_sink(self) -> None:
        adjacency, positions, source_id, sink_id = occupancy_execution_topology()
        self.assertEqual(sink_id, OCCUPANCY_EXECUTION_SINK_ID)
        self.assertEqual(source_id, 'src_temperature')
        self.assertIn('evidence_occ', adjacency)
        self.assertEqual(positions[sink_id], 3)

    def test_single_episode_executes_and_scores(self) -> None:
        system = build_occupancy_execution_system(selector_seed=0)
        episode = build_occupancy_episodes_from_preset('synth_v1_default')[0]
        result = run_occupancy_episode(system, episode, cycles_per_timestep=2, drain_cycles=6)

        self.assertIn(result.predicted_label, (0, 1))
        self.assertEqual(result.example_index, episode.example_index)
        self.assertEqual(result.routed_packets, 25)
        self.assertGreater(result.cycles_used, 0)
        self.assertIn('evidence_occ', result.decision_counts)
        self.assertIn('evidence_empty', result.decision_counts)

    def test_episode_feedback_updates_local_state(self) -> None:
        system = build_occupancy_execution_system(selector_seed=1)
        episode = build_occupancy_episodes_from_preset('synth_v1_default')[0]
        before_feedback = sum(state.received_feedback for state in system.environment.node_states.values())

        result = run_occupancy_episode(system, episode, cycles_per_timestep=2, drain_cycles=6, feedback_amount=0.05)
        after_feedback = sum(state.received_feedback for state in system.environment.node_states.values())

        self.assertGreaterEqual(result.feedback_events, 0)
        self.assertGreaterEqual(result.feedback_amount, 0.0)
        self.assertGreaterEqual(after_feedback, before_feedback)

    def test_result_summary_aggregates_episode_metrics(self) -> None:
        system = build_occupancy_execution_system(selector_seed=1)
        episodes = build_occupancy_episodes_from_preset('synth_v1_default')[:3]
        results = [
            run_occupancy_episode(system, episode, cycles_per_timestep=2, drain_cycles=6)
            for episode in episodes
        ]
        summary = summarize_occupancy_results(results)

        self.assertEqual(summary['episodes'], 3.0)
        self.assertGreaterEqual(summary['accuracy'], 0.0)
        self.assertGreater(summary['mean_cycles_used'], 0.0)
        self.assertIn('mean_feedback_events', summary)
        self.assertIn('mean_feedback_amount', summary)


if __name__ == '__main__':
    unittest.main()
