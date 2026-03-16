from __future__ import annotations

import sys
import unittest
import uuid
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PHASE4_ROOT = ROOT.parent / "Phase 4"
if str(PHASE4_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE4_ROOT))

from phase8 import (
    ConnectionSubstrate,
    NativeSubstrateSystem,
    RoutingEnvironment,
    SignalPacket,
    SignalSpec,
    phase8_scenarios,
)
from compare_task_transfer import aggregate_transfer, transfer_metrics
from real_core.types import CycleEntry, GCOStatus


class TestSignalPacket(unittest.TestCase):
    def test_payload_defaults_to_input_bits(self) -> None:
        packet = SignalPacket(
            packet_id="pkt-test",
            origin="n0",
            target="sink",
            created_cycle=0,
            input_bits=[1, 0, 1, 2],
            context_bit=3,
        )

        self.assertEqual(packet.input_bits, [1, 0, 1, 1])
        self.assertEqual(packet.payload_bits, [1, 0, 1, 1])
        self.assertEqual(packet.context_bit, 1)


class TestConnectionSubstrate(unittest.TestCase):
    def test_investment_reduces_route_cost(self) -> None:
        substrate = ConnectionSubstrate(("n1",))
        baseline = substrate.use_cost("n1")
        first = substrate.invest_connection("n1", atp_budget=1.0)
        second = substrate.invest_connection("n1", atp_budget=1.0)

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertLess(substrate.use_cost("n1"), baseline)

    def test_maintenance_refreshes_context_action_support(self) -> None:
        substrate = ConnectionSubstrate(("n1",))
        substrate.seed_action_support(
            "n1",
            "rotate_left_1",
            value=0.4,
            context_bit=0,
        )

        for _ in range(3):
            substrate.tick()

        self.assertGreater(substrate.action_support_age("n1", "rotate_left_1", 0), 0)

        result = substrate.maintain_supports(
            1.0,
            transform_credit={"rotate_left_1": 1.0},
            context_bit=0,
        )

        self.assertGreater(result["spent"], 0.0)
        self.assertIn("n1:rotate_left_1:context_0", result["maintained_actions"])
        self.assertEqual(substrate.action_support_age("n1", "rotate_left_1", 0), 0)

    def test_repeated_context_feedback_promotes_context_action_support(self) -> None:
        substrate = ConnectionSubstrate(("n1",))

        promoted = False
        for _ in range(4):
            promoted = substrate.record_context_feedback(
                "n1",
                "rotate_left_1",
                0,
                credit_signal=1.0,
                bit_match_ratio=1.0,
            ) or promoted

        self.assertTrue(promoted)
        self.assertGreaterEqual(
            substrate.contextual_action_support("n1", "rotate_left_1", 0),
            0.24,
        )
        self.assertEqual(
            substrate.contextual_action_support("n1", "rotate_left_1", 1),
            0.0,
        )

    def test_maintenance_avoids_high_debt_context_support_when_budget_is_tight(self) -> None:
        substrate = ConnectionSubstrate(("n1",))
        substrate.seed_action_support(
            "n1",
            "xor_mask_1010",
            value=0.45,
            context_bit=1,
        )
        substrate.seed_action_support(
            "n1",
            "xor_mask_0101",
            value=0.45,
            context_bit=1,
        )

        result = substrate.maintain_supports(
            0.04,
            transform_credit={"xor_mask_1010": 0.5, "xor_mask_0101": 0.5},
            context_transform_credit={
                "xor_mask_1010:context_1": 0.5,
                "xor_mask_0101:context_1": 0.5,
            },
            transform_debt={"xor_mask_1010": 0.8},
            context_transform_debt={"xor_mask_1010:context_1": 1.0},
            context_bit=1,
        )

        self.assertIn("n1:xor_mask_0101:context_1", result["maintained_actions"])
        self.assertNotIn("n1:xor_mask_1010:context_1", result["maintained_actions"])

    def test_maintenance_avoids_high_branch_context_debt_when_budget_is_tight(self) -> None:
        substrate = ConnectionSubstrate(("n1", "n2"))
        substrate.seed_support(("n1", "n2"), value=0.45)
        substrate.seed_action_support(
            "n1",
            "xor_mask_0101",
            value=0.45,
            context_bit=1,
        )
        substrate.seed_action_support(
            "n2",
            "xor_mask_0101",
            value=0.45,
            context_bit=1,
        )

        result = substrate.maintain_supports(
            0.03,
            transform_credit={"xor_mask_0101": 0.5},
            context_transform_credit={"xor_mask_0101:context_1": 0.5},
            branch_context_debt={"n1:context_1": 1.0},
            context_bit=1,
        )

        self.assertNotIn("n1:xor_mask_0101:context_1", result["maintained_actions"])
        self.assertIn("n2:xor_mask_0101:context_1", result["maintained_actions"])

    def test_maintenance_prefers_high_branch_context_credit_when_budget_is_tight(self) -> None:
        substrate = ConnectionSubstrate(("n1", "n2"))
        substrate.seed_support(("n1", "n2"), value=0.45)
        substrate.seed_action_support(
            "n1",
            "xor_mask_0101",
            value=0.45,
            context_bit=1,
        )
        substrate.seed_action_support(
            "n2",
            "xor_mask_0101",
            value=0.45,
            context_bit=1,
        )

        result = substrate.maintain_supports(
            0.03,
            transform_credit={"xor_mask_0101": 0.5},
            context_transform_credit={"xor_mask_0101:context_1": 0.5},
            branch_context_credit={"n2:context_1": 1.0},
            context_bit=1,
        )

        self.assertNotIn("n1:xor_mask_0101:context_1", result["maintained_actions"])
        self.assertIn("n2:xor_mask_0101:context_1", result["maintained_actions"])

    def test_maintenance_prefers_high_context_branch_transform_credit_when_budget_is_tight(self) -> None:
        substrate = ConnectionSubstrate(("n1",))
        substrate.seed_action_support(
            "n1",
            "xor_mask_1010",
            value=0.45,
            context_bit=1,
        )
        substrate.seed_action_support(
            "n1",
            "xor_mask_0101",
            value=0.45,
            context_bit=1,
        )

        result = substrate.maintain_supports(
            0.03,
            transform_credit={"xor_mask_1010": 0.5, "xor_mask_0101": 0.5},
            context_transform_credit={
                "xor_mask_1010:context_1": 0.5,
                "xor_mask_0101:context_1": 0.5,
            },
            branch_transform_credit={
                "n1:xor_mask_1010": 0.5,
                "n1:xor_mask_0101": 0.5,
            },
            context_branch_transform_credit={"n1:xor_mask_0101:context_1": 1.0},
            context_bit=1,
        )

        self.assertIn("n1:xor_mask_0101:context_1", result["maintained_actions"])
        self.assertNotIn("n1:xor_mask_1010:context_1", result["maintained_actions"])

    def test_low_match_context_feedback_demotes_context_action_support(self) -> None:
        substrate = ConnectionSubstrate(("n1",))
        substrate.seed_action_support(
            "n1",
            "rotate_left_1",
            value=0.6,
            context_bit=1,
        )

        before = substrate.contextual_action_support("n1", "rotate_left_1", 1)
        promoted = substrate.record_context_feedback(
            "n1",
            "rotate_left_1",
            1,
            credit_signal=0.5,
            bit_match_ratio=0.5,
        )

        self.assertFalse(promoted)
        self.assertLess(
            substrate.contextual_action_support("n1", "rotate_left_1", 1),
            before,
        )


class TestRoutingEnvironment(unittest.TestCase):
    def test_feedback_propagates_upstream_one_hop_per_tick(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("n1",),
                "n1": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
        )
        env.inject_signal(count=1)
        env.route_signal("n0", "n1", cost=0.05)
        env.route_signal("n1", "sink", cost=0.05)

        before_n0 = env.state_for("n0").atp
        before_n1 = env.state_for("n1").atp

        first_step = env.advance_feedback()
        self.assertEqual(len(first_step), 1)
        self.assertGreater(env.state_for("n1").atp, before_n1)
        self.assertAlmostEqual(env.state_for("n0").atp, before_n0, places=6)

        second_step = env.advance_feedback()
        self.assertEqual(len(second_step), 1)
        self.assertGreater(env.state_for("n0").atp, before_n0)

    def test_packets_expire_when_they_wait_beyond_ttl(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("n1",),
                "n1": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
            packet_ttl=2,
        )
        env.inject_signal(count=1, cycle=0)

        env.tick(1)
        self.assertEqual(len(env.dropped_packets), 0)

        env.tick(2)
        self.assertEqual(len(env.inboxes["n0"]), 0)
        self.assertEqual(len(env.dropped_packets), 1)
        self.assertEqual(env.dropped_packets[0].drop_reason, "ttl_expired")

    def test_source_admission_rate_limits_ingress_to_source_inbox(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
            source_admission_rate=1,
        )
        env.inject_signal(count=4, cycle=0)

        self.assertEqual(len(env.inboxes["n0"]), 1)
        self.assertEqual(len(env.source_buffer), 3)

        env.route_signal("n0", "sink", cost=0.05)
        env.prepare_cycle(1)
        self.assertEqual(len(env.inboxes["n0"]), 1)
        self.assertEqual(len(env.source_buffer), 2)

    def test_adaptive_admission_opens_under_healthy_backlog(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
            source_admission_policy="adaptive",
            source_admission_min_rate=1,
            source_admission_max_rate=3,
        )
        env.inject_signal(count=6, cycle=0)

        self.assertEqual(len(env.inboxes["n0"]), 2)
        self.assertEqual(env.last_source_admission, 2)

    def test_adaptive_admission_closes_when_source_is_dormant(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
            source_admission_policy="adaptive",
            source_admission_min_rate=1,
            source_admission_max_rate=3,
        )
        env.inject_signal(count=6, cycle=0)
        env.inboxes["n0"].clear()
        env.state_for("n0").atp = 0.0

        env.prepare_cycle(1)

        self.assertEqual(len(env.inboxes["n0"]), 0)
        self.assertGreater(len(env.source_buffer), 0)
        self.assertEqual(env.last_source_admission, 0)

    def test_admission_support_strengthens_after_successful_source_feedback(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
            source_admission_policy="adaptive",
            source_admission_min_rate=1,
            source_admission_max_rate=2,
        )
        env.inject_signal(count=1, cycle=0)
        before = env.admission_substrate.support

        env.prepare_cycle(1)
        env.route_signal("n0", "sink", cost=0.05)
        env.advance_feedback()
        env.tick(1)

        self.assertGreater(env.admission_substrate.support, before)
        self.assertGreater(env.last_source_efficiency, 0.0)

    def test_admission_support_weakens_after_unreciprocated_source_spend(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("n1",),
                "n1": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
            source_admission_policy="adaptive",
            source_admission_min_rate=1,
            source_admission_max_rate=2,
        )
        env.inject_signal(count=1, cycle=0)
        env.admission_substrate.support = 0.8
        before = env.admission_substrate.support

        env.prepare_cycle(1)
        env.route_signal("n0", "n1", cost=0.05)
        env.tick(1)

        self.assertLess(env.admission_substrate.support, before)
        self.assertLess(env.last_source_efficiency, 0.0)

    def test_route_signal_prioritizes_stalest_packet_in_local_queue(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
        )
        env.current_cycle = 5
        env.inboxes["n0"] = [
            SignalPacket(
                packet_id="fresh",
                origin="n0",
                target="sink",
                created_cycle=5,
                last_moved_cycle=5,
            ),
            SignalPacket(
                packet_id="stale",
                origin="n0",
                target="sink",
                created_cycle=0,
                last_moved_cycle=1,
            ),
        ]

        env.route_signal("n0", "sink", cost=0.05)

        self.assertEqual(env.delivered_packets[0].packet_id, "stale")

    def test_content_packet_survives_routing_to_sink(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("n1",),
                "n1": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
        )
        env.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[1],
            task_id="task_a",
        )

        env.route_signal("n0", "n1", cost=0.05)
        env.route_signal("n1", "sink", cost=0.05)

        delivered = env.delivered_packets[0]
        self.assertEqual(delivered.input_bits, [1, 0, 1, 1])
        self.assertEqual(delivered.payload_bits, [1, 0, 1, 1])
        self.assertEqual(delivered.context_bit, 1)
        self.assertEqual(delivered.task_id, "task_a")

    def test_route_signal_applies_transform_and_records_trace(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("n1",),
                "n1": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
        )
        env.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[1],
            task_id="task_a",
        )

        result = env.route_signal(
            "n0",
            "n1",
            cost=0.05,
            transform_name="rotate_left_1",
        )

        self.assertTrue(result["success"])
        packet = env.inboxes["n1"][0]
        self.assertEqual(packet.payload_bits, [0, 1, 1, 1])
        self.assertEqual(packet.transform_trace, ["rotate_left_1"])

    def test_runtime_state_restores_packet_content_fields(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
        )
        env.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 1, 0, 0]],
            context_bits=[0],
            task_id="task_a",
        )
        env.inboxes["n0"][0].transform_trace.append("identity")

        restored = RoutingEnvironment(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
        )
        restored.load_runtime_state(env.export_runtime_state())

        packet = restored.inboxes["n0"][0]
        self.assertEqual(packet.payload_bits, [1, 1, 0, 0])
        self.assertEqual(packet.input_bits, [1, 1, 0, 0])
        self.assertEqual(packet.context_bit, 0)
        self.assertEqual(packet.task_id, "task_a")
        self.assertEqual(packet.transform_trace, ["identity"])

    def test_sink_scores_exact_match_and_returns_full_feedback(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
        )
        env.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[0],
            task_id="task_a",
        )

        result = env.route_signal(
            "n0",
            "sink",
            cost=0.05,
            transform_name="rotate_left_1",
        )

        packet = env.delivered_packets[0]
        self.assertTrue(packet.matched_target)
        self.assertEqual(packet.target_bits, [0, 1, 1, 1])
        self.assertEqual(packet.bit_match_ratio, 1.0)
        self.assertAlmostEqual(result["feedback_award"], env.feedback_amount, places=6)
        self.assertEqual(len(env.pending_feedback), 1)
        self.assertAlmostEqual(env.pending_feedback[0].amount, env.feedback_amount, places=6)

    def test_sink_scores_partial_match_with_smaller_feedback(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
        )
        env.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[0],
            task_id="task_a",
        )

        result = env.route_signal(
            "n0",
            "sink",
            cost=0.05,
            transform_name="identity",
        )

        packet = env.delivered_packets[0]
        self.assertFalse(packet.matched_target)
        self.assertAlmostEqual(packet.bit_match_ratio, 0.5, places=6)
        self.assertGreater(result["feedback_award"], 0.0)
        self.assertLess(result["feedback_award"], env.feedback_amount)
        self.assertEqual(len(env.pending_feedback), 1)
        self.assertAlmostEqual(
            env.pending_feedback[0].amount,
            env.feedback_amount * 0.5,
            places=6,
        )

    def test_sink_scores_zero_match_with_no_feedback(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
        )
        env.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 0, 0, 1]],
            context_bits=[0],
            task_id="task_a",
        )

        result = env.route_signal(
            "n0",
            "sink",
            cost=0.05,
            transform_name="xor_mask_0101",
        )

        packet = env.delivered_packets[0]
        self.assertFalse(packet.matched_target)
        self.assertEqual(packet.bit_match_ratio, 0.0)
        self.assertEqual(result["feedback_award"], 0.0)
        self.assertEqual(packet.feedback_award, 0.0)
        self.assertEqual(env.pending_feedback, [])

    def test_sink_scores_task_b_exact_match(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
        )
        env.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[1],
            task_id="task_b",
        )

        result = env.route_signal(
            "n0",
            "sink",
            cost=0.05,
            transform_name="xor_mask_0101",
        )

        packet = env.delivered_packets[0]
        self.assertTrue(packet.matched_target)
        self.assertEqual(packet.target_bits, [1, 1, 1, 0])
        self.assertAlmostEqual(result["feedback_award"], env.feedback_amount, places=6)

    def test_sink_scores_task_c_exact_match(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
        )
        env.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[0],
            task_id="task_c",
        )

        result = env.route_signal(
            "n0",
            "sink",
            cost=0.05,
            transform_name="xor_mask_1010",
        )

        packet = env.delivered_packets[0]
        self.assertTrue(packet.matched_target)
        self.assertEqual(packet.target_bits, [0, 0, 0, 1])
        self.assertAlmostEqual(result["feedback_award"], env.feedback_amount, places=6)

    def test_feedback_pulse_updates_transform_credit_on_returning_node(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
        )
        env.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[0],
            task_id="task_a",
        )
        env.route_signal(
            "n0",
            "sink",
            cost=0.05,
            transform_name="rotate_left_1",
        )

        delivered = env.advance_feedback()
        self.assertEqual(len(delivered), 1)
        observation = env.observe_local("n0")

        self.assertGreater(observation["feedback_credit_rotate_left_1"], 0.0)
        self.assertGreater(observation["last_match_ratio"], 0.0)
        self.assertGreater(observation["last_feedback_amount"], 0.0)

    def test_feedback_credit_is_bound_to_matching_context(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
        )
        env.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[0],
            task_id="task_a",
        )
        env.route_signal(
            "n0",
            "sink",
            cost=0.05,
            transform_name="rotate_left_1",
        )
        env.advance_feedback()

        env.inject_signal(
            count=1,
            cycle=1,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[0],
            task_id="task_a",
        )
        observation_context0 = env.observe_local("n0")
        self.assertGreater(observation_context0["context_feedback_credit_rotate_left_1"], 0.0)

        env.inboxes["n0"].clear()
        env.inject_signal(
            count=1,
            cycle=2,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[1],
            task_id="task_a",
        )
        observation_context1 = env.observe_local("n0")
        self.assertEqual(observation_context1["context_feedback_credit_rotate_left_1"], 0.0)
        self.assertGreater(observation_context1["feedback_credit_rotate_left_1"], 0.0)

    def test_low_match_feedback_relaxes_stale_context_credit(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
        )
        state = env.state_for("n0")
        state.transform_credit["identity"] = 0.9
        state.context_transform_credit["identity:context_0"] = 0.8
        env.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[0],
            task_id="task_a",
        )

        env.route_signal(
            "n0",
            "sink",
            cost=0.05,
            transform_name="identity",
        )
        env.advance_feedback()

        self.assertLess(state.transform_credit["identity"], 0.9)
        self.assertLess(state.context_transform_credit["identity:context_0"], 0.8)
        self.assertLess(state.context_transform_credit["identity:context_0"], 0.3)
        self.assertGreater(state.transform_debt["identity"], 0.0)
        self.assertGreater(state.context_transform_debt["identity:context_0"], 0.0)
        self.assertGreater(state.branch_transform_debt["sink:identity"], 0.0)
        self.assertGreater(state.context_branch_transform_debt["sink:identity:context_0"], 0.0)
        self.assertGreater(state.branch_context_debt["sink:context_0"], 0.0)

    def test_low_match_feedback_without_prior_commitment_does_not_build_large_debt(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
        )
        env.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[0],
            task_id="task_a",
        )

        env.route_signal(
            "n0",
            "sink",
            cost=0.05,
            transform_name="identity",
        )
        env.advance_feedback()
        state = env.state_for("n0")

        self.assertLessEqual(state.transform_debt.get("identity", 0.0), 1e-6)
        self.assertLessEqual(state.context_transform_debt.get("identity:context_0", 0.0), 1e-6)
        self.assertLessEqual(state.branch_transform_debt.get("sink:identity", 0.0), 1e-6)
        self.assertLessEqual(
            state.context_branch_transform_debt.get("sink:identity:context_0", 0.0),
            1e-6,
        )
        self.assertLessEqual(state.branch_context_debt.get("sink:context_0", 0.0), 1e-6)

    def test_good_match_feedback_clears_context_transform_debt(self) -> None:
        env = RoutingEnvironment(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            max_atp=1.0,
        )
        state = env.state_for("n0")
        state.transform_debt["rotate_left_1"] = 0.8
        state.context_transform_debt["rotate_left_1:context_0"] = 0.9
        state.branch_context_debt["sink:context_0"] = 0.7
        env.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[0],
            task_id="task_a",
        )

        env.route_signal(
            "n0",
            "sink",
            cost=0.05,
            transform_name="rotate_left_1",
        )
        env.advance_feedback()

        self.assertLess(state.transform_debt["rotate_left_1"], 0.8)
        self.assertLess(state.context_transform_debt["rotate_left_1:context_0"], 0.9)
        self.assertLess(state.branch_context_debt["sink:context_0"], 0.7)
        self.assertGreater(state.branch_transform_credit["sink:rotate_left_1"], 0.0)
        self.assertGreater(
            state.context_branch_transform_credit["sink:rotate_left_1:context_0"],
            0.0,
        )
        self.assertGreater(state.branch_context_credit["sink:context_0"], 0.0)


class TestNativeSubstrateSystem(unittest.TestCase):
    def test_local_observation_excludes_non_neighbors(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("n1",),
                "n1": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            selector_seed=7,
        )
        observation = system.environment.observe_local("n0")

        self.assertIn("progress_n1", observation)
        self.assertNotIn("progress_sink", observation)

    def test_local_observation_exposes_head_payload_without_target_bits(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("n1",),
                "n1": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            selector_seed=13,
        )
        packet = system.environment.create_packet(
            cycle=0,
            input_bits=[1, 0, 0, 1],
            payload_bits=[1, 1, 0, 1],
            context_bit=1,
            task_id="task_a",
            target_bits=[0, 1, 1, 0],
        )
        packet.transform_trace.append("identity")
        system.environment.inject_packets([packet], cycle=0)

        observation = system.environment.observe_local("n0")

        self.assertEqual(observation["has_packet"], 1.0)
        self.assertEqual(observation["payload_bit_0"], 1.0)
        self.assertEqual(observation["payload_bit_1"], 1.0)
        self.assertEqual(observation["payload_bit_2"], 0.0)
        self.assertEqual(observation["payload_bit_3"], 1.0)
        self.assertEqual(observation["head_has_context"], 1.0)
        self.assertEqual(observation["head_context_bit"], 1.0)
        self.assertGreater(observation["head_transform_depth"], 0.0)
        self.assertNotIn("target_bit_0", observation)

    def test_inject_signal_specs_preserves_task_metadata(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("n1",),
                "n1": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            selector_seed=29,
        )
        system.inject_signal_specs(
            [
                SignalSpec(
                    input_bits=[1, 0, 1, 0],
                    context_bit=1,
                    task_id="task_a",
                )
            ]
        )

        packet = system.environment.inboxes["n0"][0]
        self.assertEqual(packet.input_bits, [1, 0, 1, 0])
        self.assertEqual(packet.payload_bits, [1, 0, 1, 0])
        self.assertEqual(packet.context_bit, 1)
        self.assertEqual(packet.task_id, "task_a")

    def test_available_actions_include_route_transform_variants(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("n1",),
                "n1": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            selector_seed=19,
        )
        system.environment.inject_signal(count=1, cycle=0, packet_payloads=[[1, 0, 0, 1]])

        available = system.agents["n0"].engine.actions.available_actions(history_size=0)

        self.assertIn("route:n1", available)
        self.assertIn("route_transform:n1:identity", available)
        self.assertIn("route_transform:n1:rotate_left_1", available)
        self.assertIn("route_transform:n1:xor_mask_1010", available)
        self.assertIn("route_transform:n1:xor_mask_0101", available)

    def test_route_transform_action_executes_through_backend(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("n1",),
                "n1": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            selector_seed=23,
        )
        system.environment.inject_signal(count=1, cycle=0, packet_payloads=[[1, 0, 1, 0]])

        outcome = system.agents["n0"].engine.actions.execute(
            "route_transform:n1:xor_mask_0101"
        )

        self.assertTrue(outcome.success)
        packet = system.environment.inboxes["n1"][0]
        self.assertEqual(packet.payload_bits, [1, 1, 1, 1])
        self.assertEqual(packet.transform_trace, ["xor_mask_0101"])

    def test_route_transform_execution_uses_context_shaped_cost(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("n1",),
                "n1": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            selector_seed=41,
        )
        system.environment.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[0],
            task_id="task_a",
        )
        system.agents["n0"].substrate.seed_action_support(
            "n1",
            "rotate_left_1",
            value=1.0,
            context_bit=0,
        )

        before_atp = system.environment.state_for("n0").atp
        expected_cost = system.agents["n0"].substrate.use_cost(
            "n1",
            "rotate_left_1",
            0,
        )

        outcome = system.agents["n0"].engine.actions.execute(
            "route_transform:n1:rotate_left_1"
        )

        self.assertTrue(outcome.success)
        self.assertAlmostEqual(outcome.cost_secs, expected_cost, places=6)
        self.assertAlmostEqual(
            before_atp - system.environment.state_for("n0").atp,
            expected_cost,
            places=6,
        )

    def test_dormant_node_only_rests(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("n1",),
                "n1": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            selector_seed=5,
        )
        agent = system.agents["n0"]
        system.environment.state_for("n0").atp = 0.0

        available = agent.engine.actions.available_actions(history_size=0)
        self.assertEqual(available, ["rest"])

    def test_system_smoke_run_records_cycles(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("n1", "n2"),
                "n1": ("n3",),
                "n2": ("n3",),
                "n3": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "n2": 1, "n3": 2, "sink": 3},
            source_id="n0",
            sink_id="sink",
            selector_seed=11,
        )
        system.inject_signal(count=2)
        for _ in range(5):
            report = system.run_global_cycle()

        self.assertEqual(report["cycle"], 5)
        self.assertEqual(system.agents["n0"].cycle, 5)
        self.assertIn("snapshot", report)
        self.assertGreaterEqual(system.environment.snapshot()["delivered_packets"], 1)

    def test_selector_prefers_supported_route_when_packet_waits(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("n1", "n2"),
                "n1": ("sink",),
                "n2": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "n2": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            selector_seed=17,
        )
        system.environment.inject_signal(count=1)
        agent = system.agents["n0"]
        agent.substrate.seed_support(("n1",), value=0.8)

        available = agent.engine.actions.available_actions(history_size=0)
        action, _ = agent.engine.selector.select(available, history=[])

        self.assertEqual(action, "route:n1")

    def test_selector_avoids_context_transform_with_high_feedback_debt(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("n1",),
                "n1": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            selector_seed=53,
        )
        system.environment.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[1],
            task_id="task_b",
        )
        agent = system.agents["n0"]
        agent.substrate.seed_support(("n1",), value=0.8)
        agent.substrate.seed_action_support(
            "n1",
            "xor_mask_1010",
            value=1.0,
            context_bit=1,
        )
        agent.substrate.seed_action_support(
            "n1",
            "xor_mask_0101",
            value=0.45,
            context_bit=1,
        )
        state = system.environment.state_for("n0")
        state.context_transform_debt["xor_mask_1010:context_1"] = 1.0
        state.transform_debt["xor_mask_1010"] = 0.8

        available = agent.engine.actions.available_actions(history_size=0)
        action, _ = agent.engine.selector.select(available, history=[])

        self.assertNotEqual(action, "route_transform:n1:xor_mask_1010")

    def test_selector_avoids_branch_with_high_context_branch_debt(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("n1", "n2"),
                "n1": ("sink",),
                "n2": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "n2": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            selector_seed=59,
        )
        system.environment.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[1],
            task_id="task_b",
        )
        agent = system.agents["n0"]
        agent.substrate.seed_support(("n1", "n2"), value=0.8)
        agent.substrate.seed_action_support(
            "n1",
            "xor_mask_0101",
            value=0.6,
            context_bit=1,
        )
        agent.substrate.seed_action_support(
            "n2",
            "xor_mask_0101",
            value=0.45,
            context_bit=1,
        )
        state = system.environment.state_for("n0")
        state.branch_transform_debt["n1:xor_mask_0101"] = 0.8
        state.context_branch_transform_debt["n1:xor_mask_0101:context_1"] = 1.0

        available = agent.engine.actions.available_actions(history_size=0)
        action, _ = agent.engine.selector.select(available, history=[])

        self.assertNotEqual(action, "route_transform:n1:xor_mask_0101")

    def test_selector_avoids_branch_with_high_context_branch_debt_even_for_alternate_transform(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("n1", "n2"),
                "n1": ("sink",),
                "n2": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "n2": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            selector_seed=61,
        )
        system.environment.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[1],
            task_id="task_b",
        )
        agent = system.agents["n0"]
        agent.substrate.seed_support(("n1", "n2"), value=0.8)
        agent.substrate.seed_action_support(
            "n1",
            "rotate_left_1",
            value=0.65,
            context_bit=1,
        )
        agent.substrate.seed_action_support(
            "n2",
            "xor_mask_0101",
            value=0.40,
            context_bit=1,
        )
        state = system.environment.state_for("n0")
        state.branch_context_debt["n1:context_1"] = 1.0

        available = agent.engine.actions.available_actions(history_size=0)
        action, _ = agent.engine.selector.select(available, history=[])

        self.assertNotEqual(action.split(":")[1], "n1")

    def test_selector_prefers_branch_with_positive_context_credit(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("n1", "n2"),
                "n1": ("sink",),
                "n2": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "n2": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            selector_seed=67,
        )
        system.environment.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[1],
            task_id="task_b",
        )
        agent = system.agents["n0"]
        agent.substrate.seed_support(("n1", "n2"), value=0.6)
        agent.substrate.seed_action_support(
            "n1",
            "xor_mask_0101",
            value=0.45,
            context_bit=1,
        )
        agent.substrate.seed_action_support(
            "n2",
            "xor_mask_0101",
            value=0.45,
            context_bit=1,
        )
        state = system.environment.state_for("n0")
        state.branch_context_credit["n2:context_1"] = 1.0

        available = agent.engine.actions.available_actions(history_size=0)
        action, _ = agent.engine.selector.select(available, history=[])

        self.assertEqual(action.split(":")[1], "n2")

    def test_selector_prefers_transform_with_positive_context_branch_credit(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("n1",),
                "n1": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            selector_seed=71,
        )
        system.environment.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[1],
            task_id="task_b",
        )
        agent = system.agents["n0"]
        agent.substrate.seed_support(("n1",), value=0.7)
        agent.substrate.seed_action_support("n1", "xor_mask_1010", value=0.45, context_bit=1)
        agent.substrate.seed_action_support("n1", "xor_mask_0101", value=0.45, context_bit=1)
        state = system.environment.state_for("n0")
        state.context_branch_transform_credit["n1:xor_mask_0101:context_1"] = 1.0

        available = agent.engine.actions.available_actions(history_size=0)
        action, _ = agent.engine.selector.select(available, history=[])

        self.assertEqual(action, "route_transform:n1:xor_mask_0101")

    def test_consolidation_promotes_route_history_into_substrate(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("n1",),
                "n1": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            selector_seed=3,
        )
        agent = system.agents["n0"]
        edge_key = agent.substrate.edge_key("n1")

        for cycle in range(1, 9):
            agent.engine.memory.record(
                CycleEntry(
                    cycle=cycle,
                    action="route:n1",
                    mode="constraint",
                    state_before={"inbox_load": 1.0},
                    state_after={edge_key: 0.8},
                    dimensions={edge_key: 0.8},
                    coherence=0.82,
                    delta=0.05,
                    gco=GCOStatus.PARTIAL,
                    cost_secs=0.04,
                )
            )

        agent.engine._run_consolidation()
        self.assertGreaterEqual(agent.substrate.support("n1"), 0.32)
        self.assertGreaterEqual(len(agent.substrate.constraint_patterns), 1)

    def test_consolidation_promotes_transform_history_into_action_support(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("n1",),
                "n1": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            selector_seed=33,
        )
        agent = system.agents["n0"]

        for cycle in range(1, 9):
            agent.engine.memory.record(
                CycleEntry(
                    cycle=cycle,
                    action="route_transform:n1:rotate_left_1",
                    mode="constraint",
                    state_before={"head_context_bit": 0.0, "head_has_context": 1.0},
                    state_after={"reward_buffer": 0.8},
                    dimensions={"contextual_fit": 0.8},
                    coherence=0.81,
                    delta=0.06,
                    gco=GCOStatus.PARTIAL,
                    cost_secs=0.04,
                )
            )

        agent.engine._run_consolidation()
        self.assertEqual(
            agent.substrate.action_support("n1", "rotate_left_1"),
            0.0,
        )
        self.assertGreaterEqual(
            agent.substrate.action_support("n1", "rotate_left_1", 0),
            0.24,
        )
        self.assertLess(
            agent.substrate.action_support("n1", "rotate_left_1", 1),
            0.24,
        )

    def test_save_and_load_carryover_restores_node_state(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("n1",),
                "n1": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            selector_seed=9,
        )
        system.inject_signal(count=1)
        system.run_global_cycle()
        system.agents["n0"].substrate.seed_support(("n1",), value=0.55)
        system.environment.state_for("n0").reward_buffer = 0.22

        temp_dir = ROOT / "tests_tmp" / f"carryover_{uuid.uuid4().hex}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            system.save_carryover(temp_dir)

            restored = NativeSubstrateSystem(
                adjacency={
                    "n0": ("n1",),
                    "n1": ("sink",),
                },
                positions={"n0": 0, "n1": 1, "sink": 2},
                source_id="n0",
                sink_id="sink",
                selector_seed=9,
            )
            loaded = restored.load_carryover(temp_dir)

            self.assertTrue(loaded)
            self.assertEqual(restored.global_cycle, system.global_cycle)
            self.assertAlmostEqual(
                restored.agents["n0"].substrate.support("n1"),
                system.agents["n0"].substrate.support("n1"),
                places=6,
            )
            self.assertAlmostEqual(
                restored.environment.state_for("n0").reward_buffer,
                system.environment.state_for("n0").reward_buffer,
                places=6,
            )
            self.assertEqual(
                len(restored.agents["n0"].engine.memory.entries),
                len(system.agents["n0"].engine.memory.entries),
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_substrate_only_carryover_restores_support_without_episodic_history(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("n1",),
                "n1": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            selector_seed=12,
        )
        system.inject_signal(count=1)
        system.run_global_cycle()
        system.agents["n0"].substrate.seed_support(("n1",), value=0.62)

        temp_dir = ROOT / "tests_tmp" / f"substrate_only_{uuid.uuid4().hex}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            system.save_substrate_carryover(temp_dir)
            restored = NativeSubstrateSystem(
                adjacency={
                    "n0": ("n1",),
                    "n1": ("sink",),
                },
                positions={"n0": 0, "n1": 1, "sink": 2},
                source_id="n0",
                sink_id="sink",
                selector_seed=12,
            )
            loaded = restored.load_substrate_carryover(temp_dir)

            self.assertTrue(loaded)
            self.assertAlmostEqual(
                restored.agents["n0"].substrate.support("n1"),
                0.62,
                places=6,
            )
            self.assertEqual(restored.agents["n0"].engine.memory.entries, [])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_substrate_only_carryover_restores_promoted_context_action_support(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("n1",),
                "n1": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            selector_seed=43,
        )
        agent = system.agents["n0"]
        for _ in range(4):
            agent.substrate.record_context_feedback(
                "n1",
                "rotate_left_1",
                0,
                credit_signal=1.0,
                bit_match_ratio=1.0,
            )

        temp_dir = ROOT / "tests_tmp" / f"context_substrate_{uuid.uuid4().hex}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            system.save_substrate_carryover(temp_dir)
            restored = NativeSubstrateSystem(
                adjacency={
                    "n0": ("n1",),
                    "n1": ("sink",),
                },
                positions={"n0": 0, "n1": 1, "sink": 2},
                source_id="n0",
                sink_id="sink",
                selector_seed=43,
            )
            loaded = restored.load_substrate_carryover(temp_dir)

            self.assertTrue(loaded)
            self.assertGreaterEqual(
                restored.agents["n0"].substrate.contextual_action_support(
                    "n1",
                    "rotate_left_1",
                    0,
                ),
                0.24,
            )
            self.assertEqual(
                restored.agents["n0"].substrate.contextual_action_support(
                    "n1",
                    "rotate_left_1",
                    1,
                ),
                0.0,
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_summary_reports_packet_drops_under_strict_ttl(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("n1",),
                "n1": ("sink",),
            },
            positions={"n0": 0, "n1": 1, "sink": 2},
            source_id="n0",
            sink_id="sink",
            selector_seed=21,
            packet_ttl=1,
        )
        system.inject_signal(count=4)
        system.run_global_cycle()

        summary = system.summarize()
        self.assertGreaterEqual(summary["dropped_packets"], 1)
        self.assertGreater(summary["drop_ratio"], 0.0)

    def test_substrate_carryover_restores_admission_support(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            selector_seed=31,
            source_admission_policy="adaptive",
            source_admission_min_rate=1,
            source_admission_max_rate=2,
        )
        system.inject_signal(count=1)
        system.run_global_cycle()
        learned_support = system.environment.admission_substrate.support

        temp_dir = ROOT / "tests_tmp" / f"admission_substrate_{uuid.uuid4().hex}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            system.save_substrate_carryover(temp_dir)
            restored = NativeSubstrateSystem(
                adjacency={
                    "n0": ("sink",),
                },
                positions={"n0": 0, "sink": 1},
                source_id="n0",
                sink_id="sink",
                selector_seed=31,
                source_admission_policy="adaptive",
                source_admission_min_rate=1,
                source_admission_max_rate=2,
            )
            loaded = restored.load_substrate_carryover(temp_dir)

            self.assertTrue(loaded)
            self.assertAlmostEqual(
                restored.environment.admission_substrate.support,
                learned_support,
                places=6,
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_summary_reports_context_breakdown_and_action_supports(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            selector_seed=35,
        )
        system.environment.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[0],
            task_id="task_a",
        )
        system.environment.route_signal(
            "n0",
            "sink",
            cost=0.05,
            transform_name="rotate_left_1",
        )

        summary = system.summarize()

        self.assertIn("context_breakdown", summary)
        self.assertIn("context_0", summary["context_breakdown"])
        self.assertEqual(summary["context_breakdown"]["context_0"]["exact_matches"], 1)
        self.assertIn("final_transform_counts", summary)
        self.assertEqual(summary["final_transform_counts"]["rotate_left_1"], 1)
        self.assertIn("action_supports", summary)
        self.assertIn("context_action_supports", summary)
        self.assertIn("substrate_maintenance", summary)
        self.assertIn("n0", summary["substrate_maintenance"])

    def test_summary_reports_task_diagnostics_for_transform_mismatches(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            selector_seed=39,
        )
        system.environment.inject_signal(
            count=1,
            cycle=0,
            packet_payloads=[[1, 0, 1, 1]],
            context_bits=[0],
            task_id="task_a",
        )
        system.environment.route_signal(
            "n0",
            "sink",
            cost=0.05,
            transform_name="identity",
        )

        summary = system.summarize()
        diagnostics = summary["task_diagnostics"]

        self.assertEqual(diagnostics["overall"]["identity_fallbacks"], 1)
        self.assertEqual(diagnostics["overall"]["wrong_transform_family"], 1)
        self.assertEqual(
            diagnostics["contexts"]["context_0"]["mismatch_transform_counts"]["identity"],
            1,
        )
        self.assertEqual(
            diagnostics["contexts"]["context_0"]["branch_counts"]["sink"],
            1,
        )


class TestScenarioCatalog(unittest.TestCase):
    def test_cvt1_stage1_scenario_is_available(self) -> None:
        scenarios = phase8_scenarios()
        scenario = scenarios["cvt1_task_a_stage1"]

        self.assertGreater(len(scenario.initial_signal_specs), 0)
        self.assertGreater(len(scenario.signal_schedule_specs or {}), 0)
        first_signal = scenario.initial_signal_specs[0]
        self.assertEqual(first_signal.task_id, "task_a")
        self.assertIsNotNone(first_signal.context_bit)

    def test_cvt1_task_b_stage1_scenario_is_available(self) -> None:
        scenarios = phase8_scenarios()
        scenario = scenarios["cvt1_task_b_stage1"]

        self.assertGreater(len(scenario.initial_signal_specs), 0)
        self.assertGreater(len(scenario.signal_schedule_specs or {}), 0)
        first_signal = scenario.initial_signal_specs[0]
        self.assertEqual(first_signal.task_id, "task_b")
        self.assertIsNotNone(first_signal.context_bit)

    def test_cvt1_task_c_stage1_scenario_is_available(self) -> None:
        scenarios = phase8_scenarios()
        scenario = scenarios["cvt1_task_c_stage1"]

        self.assertGreater(len(scenario.initial_signal_specs), 0)
        self.assertGreater(len(scenario.signal_schedule_specs or {}), 0)
        first_signal = scenario.initial_signal_specs[0]
        self.assertEqual(first_signal.task_id, "task_c")
        self.assertIsNotNone(first_signal.context_bit)


class TestTransferHarness(unittest.TestCase):
    def test_transfer_metrics_report_best_rolling_scores(self) -> None:
        system = NativeSubstrateSystem(
            adjacency={
                "n0": ("sink",),
            },
            positions={"n0": 0, "sink": 1},
            source_id="n0",
            sink_id="sink",
            selector_seed=47,
        )
        for cycle in range(8):
            system.environment.inject_signal(
                count=1,
                cycle=cycle,
                packet_payloads=[[1, 0, 1, 1]],
                context_bits=[0],
                task_id="task_a",
            )
            system.environment.route_signal(
                "n0",
                "sink",
                cost=0.05,
                transform_name="rotate_left_1",
            )
            system.global_cycle = cycle + 1

        metrics = transfer_metrics(system)

        self.assertTrue(metrics["criterion_reached"])
        self.assertEqual(metrics["examples_to_criterion"], 8)
        self.assertGreaterEqual(metrics["best_rolling_exact_rate"], 1.0)

    def test_transfer_aggregate_reports_context_and_error_diagnostics(self) -> None:
        results = [
            {
                "cold_task_b": {
                    "summary": {
                        "exact_matches": 1,
                        "mean_bit_accuracy": 0.4,
                        "mean_route_cost": 0.05,
                        "task_diagnostics": {
                            "overall": {
                                "wrong_transform_family": 2,
                                "identity_fallbacks": 1,
                                "stale_context_support_suspicions": 1,
                            },
                            "contexts": {
                                "context_1": {"mean_bit_accuracy": 0.25},
                            },
                        },
                    }
                },
                "warm_full_task_b": {
                    "summary": {
                        "exact_matches": 2,
                        "mean_bit_accuracy": 0.45,
                        "mean_route_cost": 0.04,
                        "task_diagnostics": {
                            "overall": {
                                "wrong_transform_family": 1,
                                "identity_fallbacks": 0,
                                "stale_context_support_suspicions": 0,
                            },
                            "contexts": {
                                "context_1": {"mean_bit_accuracy": 0.5},
                            },
                        },
                    }
                },
                "warm_substrate_task_b": {
                    "summary": {
                        "exact_matches": 3,
                        "mean_bit_accuracy": 0.5,
                        "mean_route_cost": 0.03,
                        "task_diagnostics": {
                            "overall": {
                                "wrong_transform_family": 0,
                                "identity_fallbacks": 0,
                                "stale_context_support_suspicions": 0,
                            },
                            "contexts": {
                                "context_1": {"mean_bit_accuracy": 0.625},
                            },
                        },
                    }
                },
                "delta_full_task_b": {
                    "exact_matches": 1,
                    "mean_bit_accuracy": 0.05,
                    "mean_route_cost": -0.01,
                    "best_rolling_exact_rate": 0.125,
                    "best_rolling_bit_accuracy": 0.125,
                },
                "delta_substrate_task_b": {
                    "exact_matches": 2,
                    "mean_bit_accuracy": 0.1,
                    "mean_route_cost": -0.02,
                    "best_rolling_exact_rate": 0.25,
                    "best_rolling_bit_accuracy": 0.25,
                },
            }
        ]

        aggregate = aggregate_transfer(results)

        self.assertEqual(aggregate["avg_cold_task_b_context_1_bit_accuracy"], 0.25)
        self.assertEqual(aggregate["avg_warm_full_task_b_wrong_transform_family"], 1.0)
        self.assertEqual(aggregate["avg_warm_substrate_task_b_identity_fallbacks"], 0.0)
        self.assertEqual(aggregate["avg_cold_task_b_stale_support_suspicions"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
