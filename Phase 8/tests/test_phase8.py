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

from phase8 import ConnectionSubstrate, NativeSubstrateSystem, RoutingEnvironment, SignalPacket
from real_core.types import CycleEntry, GCOStatus


class TestConnectionSubstrate(unittest.TestCase):
    def test_investment_reduces_route_cost(self) -> None:
        substrate = ConnectionSubstrate(("n1",))
        baseline = substrate.use_cost("n1")
        first = substrate.invest_connection("n1", atp_budget=1.0)
        second = substrate.invest_connection("n1", atp_budget=1.0)

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertLess(substrate.use_cost("n1"), baseline)


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

        self.assertEqual(len(env.inboxes["n0"]), 3)
        self.assertEqual(env.last_source_admission, 3)

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
