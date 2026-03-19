from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from occupancy_baseline import get_preset
from phase8 import (
    EMPTY_SINK_ID,
    OCCUPANCY_TASK_ID,
    OCCUPIED_SINK_ID,
    build_occupancy_episodes_from_preset,
    occupancy_bridge_topology,
    occupancy_episode_summary,
)


class TestOccupancyRealMapping(unittest.TestCase):
    def test_preset_builds_expected_episode_shape(self) -> None:
        episodes = build_occupancy_episodes_from_preset('synth_v1_default')
        preset = get_preset('synth_v1_default')
        expected_examples = 14 * 24 * 4 - preset.config.window_size + 1

        self.assertEqual(len(episodes), expected_examples)
        first = episodes[0]
        self.assertEqual(len(first.timestep_packets), preset.config.window_size)
        self.assertEqual(first.packet_count, preset.config.window_size * 5)
        self.assertIn(first.target_sink_id, (OCCUPIED_SINK_ID, EMPTY_SINK_ID))

    def test_packet_specs_only_use_fair_local_information(self) -> None:
        episode = build_occupancy_episodes_from_preset('synth_v1_default')[0]
        first_packet = episode.timestep_packets[0][0]

        self.assertTrue(first_packet.source_id.startswith('src_'))
        self.assertEqual(first_packet.signal.task_id, OCCUPANCY_TASK_ID)
        self.assertEqual(len(first_packet.signal.input_bits), 4)
        self.assertEqual(sum(first_packet.signal.input_bits), 1)
        self.assertEqual(first_packet.signal.context_bit, 0)
        self.assertEqual(first_packet.feature_name, 'temperature')

        recent_packet = episode.timestep_packets[-1][-1]
        self.assertEqual(recent_packet.signal.context_bit, 1)

    def test_topology_and_summary_match_adapter_design(self) -> None:
        adjacency, positions, sink_ids = occupancy_bridge_topology()
        episodes = build_occupancy_episodes_from_preset('synth_v1_default')[:3]
        summary = occupancy_episode_summary(episodes)

        self.assertEqual(sink_ids, (OCCUPIED_SINK_ID, EMPTY_SINK_ID))
        self.assertIn('src_temperature', adjacency)
        self.assertIn('evidence_occ', adjacency)
        self.assertEqual(positions[OCCUPIED_SINK_ID], 3)
        self.assertEqual(summary['episodes'], 3)
        self.assertEqual(summary['timesteps_per_episode'], 5)
        self.assertEqual(summary['sensor_channels'], 5)
        self.assertEqual(summary['packets'], 75)


if __name__ == '__main__':
    unittest.main()
