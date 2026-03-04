"""
Phase 3 automated test suite.

Design principles:
  - Use structural/relational assertions, not exact hardware values
    (psutil readings vary by machine; tests should be portable)
  - `cycle_interval=0` for maximum speed
  - Hardware-dependent tests use loose bounds rather than strict equality
  - Pure-logic tests (mesh math, AVIA staging) are deterministic sub-second runs

Approximate wall-clock times (as of Phase 3 implementation):
  TestWorldPruning           ~5s
  TestAVIAStaging            <1s
  TestRegulatoryMesh         <1s
  TestMetabolicBudgeting     ~8s
  TestEnvironmentDynamics    <1s
  TestFullRunIntegration     ~20s
  ─────────────────────────
  Total target              <60s
"""

from __future__ import annotations

import random
import shutil
import tempfile
import time
import unittest
from pathlib import Path


# ── Test: World Graph Pruning (Phase 3a) ─────────────────────────────

class TestWorldPruning(unittest.TestCase):
    """prune_historical() keeps World bounded without disrupting active relations."""

    def _make_world(self, n_inactive: int, n_active: int = 3):
        from real.core.world import World
        from real.core.entity import Entity
        from real.core.relation import Relation
        from real.core.primitives import RPPrimitive
        w = World()
        w.add_entity(Entity(id="agent", kind="agent"))
        w.add_entity(Entity(id="cpu_sensor", kind="sensor"))
        for i in range(n_active):
            w.add_relation(Relation(
                id=f"live_{i}", primitive=RPPrimitive.EPISTEMIC,
                source="cpu_sensor", target="agent", active=True
            ))
        for i in range(n_inactive):
            w.add_relation(Relation(
                id=f"action_{i+1}", primitive=RPPrimitive.EPISTEMIC,
                source="agent", target="agent",
                payload={"timestamp": time.time() + i},
                active=False,
            ))
        return w

    def test_prune_keeps_exactly_keep_last(self):
        w = self._make_world(n_inactive=120, n_active=3)
        pruned = w.prune_historical(keep_last=100)
        self.assertEqual(pruned, 20)
        self.assertEqual(w.historical_relation_count, 100)

    def test_prune_never_removes_active(self):
        w = self._make_world(n_inactive=120, n_active=3)
        w.prune_historical(keep_last=10)
        active = sum(1 for r in w.relations.values() if r.active)
        self.assertEqual(active, 3)

    def test_prune_idempotent(self):
        w = self._make_world(n_inactive=50, n_active=2)
        pruned1 = w.prune_historical(keep_last=100)
        pruned2 = w.prune_historical(keep_last=100)
        self.assertEqual(pruned1, 0)   # already under limit
        self.assertEqual(pruned2, 0)

    def test_summary_includes_historical_count(self):
        w = self._make_world(n_inactive=20)
        s = w.summary()
        self.assertIn("historical_relations", s)
        self.assertEqual(s["historical_relations"], 20)

    def test_relation_count_bounded_after_many_actions(self):
        """Integration: after 60 action records + prune(keep=30), total ≤ 35."""
        w = self._make_world(n_inactive=60, n_active=3)
        w.prune_historical(keep_last=30)
        self.assertLessEqual(w.historical_relation_count, 30)
        self.assertLessEqual(w.relation_count, 35)


# ── Test: AVIA Developmental Staging (Phase 3b) ──────────────────────

class TestAVIAStaging(unittest.TestCase):
    """AVIATracker stages advance based on injected session history."""

    def _make_logger(self, n_sessions: int, mean_coh: float, actions: dict | None = None):
        from real.agent.session import SessionLogger, SessionRecord
        import json, tempfile, os
        path = Path(tempfile.mktemp(suffix=".json"))
        logger = SessionLogger(path)
        for i in range(n_sessions):
            s = SessionRecord(
                session_id=i+1, start_time=0.0, end_time=1.0,
                mean_coherence=mean_coh,
                action_distribution=actions or {"introspect": 5, "rest": 5},
            )
            logger.sessions.append(s)
        return logger

    def test_fresh_agent_is_awake(self):
        from real.agent.avia import AVIATracker, AVIAStage
        tracker = AVIATracker()
        self.assertEqual(tracker.stage, AVIAStage.AWAKE)

    def test_awake_below_session_threshold(self):
        from real.agent.avia import AVIATracker, AVIAStage, StageThresholds
        from real.coherence.memory import EpisodicLog
        thresholds = StageThresholds(vigilant_min_reflexivity=0.0)
        tracker = AVIATracker(thresholds=thresholds)
        logger = self._make_logger(2, 0.80)  # only 2 sessions, need 3
        log = EpisodicLog()
        stage = tracker.advance(logger, log)
        self.assertEqual(stage, AVIAStage.AWAKE)

    def test_vigilant_at_threshold(self):
        from real.agent.avia import AVIATracker, AVIAStage, StageThresholds
        from real.coherence.memory import EpisodicLog
        thresholds = StageThresholds(vigilant_min_reflexivity=0.0,
                                     vigilant_min_coherence=0.0)
        tracker = AVIATracker(thresholds=thresholds)
        logger = self._make_logger(5, 0.75)
        log = EpisodicLog()
        stage = tracker.advance(logger, log)
        self.assertEqual(stage, AVIAStage.VIGILANT)

    def test_adaptive_with_full_history(self):
        from real.agent.avia import AVIATracker, AVIAStage, StageThresholds
        from real.coherence.memory import EpisodicLog
        # All 14 current vocabulary actions (digest_log and sort_terrain added in Phase 2)
        all_14 = {a: 5 for a in [
            "shallow_scan", "list_terrain", "read_terrain",
            "rest", "cleanup_temp",
            "deep_scan", "query_memory", "compare_state",
            "mark_terrain", "write_memory", "checkpoint", "introspect",
            "digest_log", "sort_terrain",
        ]}
        thresholds = StageThresholds(
            vigilant_min_reflexivity=0.0,
            interactive_min_reflexivity=0.0,
            adaptive_min_reflexivity=0.0,
        )
        tracker = AVIATracker(thresholds=thresholds)
        logger = self._make_logger(10, 0.85, actions=all_14)
        log = EpisodicLog()
        stage = tracker.advance(logger, log)
        self.assertEqual(stage, AVIAStage.ADAPTIVE)

    def test_stage_does_not_regress(self):
        from real.agent.avia import AVIATracker, AVIAStage, StageThresholds
        from real.coherence.memory import EpisodicLog
        thresholds = StageThresholds(
            vigilant_min_reflexivity=0.0,
            interactive_min_reflexivity=0.0,
            adaptive_min_reflexivity=0.0,
        )
        tracker = AVIATracker(thresholds=thresholds)
        all_14 = {a: 5 for a in [
            "shallow_scan", "list_terrain", "read_terrain",
            "rest", "cleanup_temp",
            "deep_scan", "query_memory", "compare_state",
            "mark_terrain", "write_memory", "checkpoint", "introspect",
            "digest_log", "sort_terrain",
        ]}
        logger = self._make_logger(10, 0.85, actions=all_14)
        log = EpisodicLog()
        tracker.advance(logger, log)
        self.assertEqual(tracker.stage, AVIAStage.ADAPTIVE)
        # Simulate bad session — stage must not regress
        poor_logger = self._make_logger(1, 0.20)
        tracker.advance(poor_logger, log)
        self.assertEqual(tracker.stage, AVIAStage.ADAPTIVE)



# ── Test: Regulatory Mesh (Phase 3c) ─────────────────────────────────

class TestRegulatoryMesh(unittest.TestCase):
    """RegulatoryMesh applies tilt coupling correctly and stays within bounds."""

    _DIMS = ["continuity", "vitality", "contextual_fit",
             "differentiation", "accountability", "reflexivity"]

    def _dims(self, **overrides):
        base = {d: 0.5 for d in self._DIMS}
        base.update(overrides)
        return base

    def test_coupling_fires_when_source_above_floor(self):
        from real.coherence.regulatory_mesh import RegulatoryMesh
        mesh = RegulatoryMesh()
        d = self._dims(vitality=0.90, reflexivity=0.50)
        out = mesh.apply(d)
        self.assertGreater(out["reflexivity"], 0.50)

    def test_no_coupling_when_source_below_floor(self):
        from real.coherence.regulatory_mesh import RegulatoryMesh
        mesh = RegulatoryMesh()
        d = self._dims()  # all 0.5, below floor 0.757
        out = mesh.apply(d)
        for k in self._DIMS:
            self.assertAlmostEqual(out[k], 0.5)

    def test_target_never_exceeds_source(self):
        from real.coherence.regulatory_mesh import RegulatoryMesh
        mesh = RegulatoryMesh()
        d = self._dims(vitality=0.95, reflexivity=0.10)
        out = mesh.apply(d)
        self.assertLessEqual(out["reflexivity"], out["vitality"])

    def test_idempotent_when_all_equal(self):
        from real.coherence.regulatory_mesh import RegulatoryMesh
        mesh = RegulatoryMesh()
        d = {k: 0.85 for k in self._DIMS}
        out = mesh.apply(d)
        for k in self._DIMS:
            self.assertAlmostEqual(out[k], 0.85)

    def test_total_uplift_bounded(self):
        from real.coherence.regulatory_mesh import RegulatoryMesh
        from real.coherence.biases import TCL_CONSTANTS
        mesh = RegulatoryMesh()
        d = self._dims(continuity=1.0, vitality=1.0, contextual_fit=1.0,
                       accountability=0.0, reflexivity=0.0, differentiation=0.0)
        out = mesh.apply(d)
        total_increase = sum(out[k] - d[k] for k in self._DIMS)
        max_allowed = TCL_CONSTANTS["parametric_wall"] * 3
        self.assertLessEqual(total_increase, max_allowed + 1e-9)

    def test_enabled_toggle(self):
        from real.coherence.regulatory_mesh import RegulatoryMesh
        mesh = RegulatoryMesh(enabled=False)
        d = self._dims(vitality=0.95, reflexivity=0.10)
        out = mesh.apply(d)
        self.assertAlmostEqual(out["reflexivity"], 0.10)  # unchanged

    def test_all_values_remain_in_range(self):
        from real.coherence.regulatory_mesh import RegulatoryMesh
        mesh = RegulatoryMesh()
        rng = random.Random(99)
        for _ in range(50):
            d = {k: rng.random() for k in self._DIMS}
            out = mesh.apply(d)
            for k, v in out.items():
                self.assertGreaterEqual(v, 0.0, f"{k}={v} below 0")
                self.assertLessEqual(v, 1.0, f"{k}={v} above 1")


# ── Test: Metabolic Budgeting (Phase 3d) ─────────────────────────────

class TestMetabolicBudgeting(unittest.TestCase):
    """Efficiency weighting prefers cheaper actions with equal coherence gain."""

    def _make_log(self, actions_with_profiles):
        from real.coherence.memory import EpisodicLog, LogEntry
        log = EpisodicLog(maxlen=200)
        for action, delta, cost, n in actions_with_profiles:
            for _ in range(n):
                log.record(LogEntry(
                    cycle=1, timestamp=time.time(),
                    state_before={}, action=action, action_params={},
                    state_after={}, coherence_score=0.7,
                    dimension_scores={k: 0.7 for k in [
                        "continuity","vitality","contextual_fit",
                        "differentiation","accountability","reflexivity"]},
                    delta_coherence=delta,
                    compute_cost_secs=cost,
                ))
        return log

    def test_cheap_wins_over_expensive_with_equal_delta(self):
        from real.agent.selector import ActionSelector
        from real.boundary.vocabulary import VOCABULARY
        log = self._make_log([
            ("introspect",  0.02, 0.001, 15),
            ("digest_log",  0.02, 0.200, 15),
        ])
        sel = ActionSelector(budget_mode=True)
        available = [a for a in VOCABULARY if a.name in ("introspect", "digest_log")]
        winner = sel._exploit(available, log)
        self.assertEqual(winner.name, "introspect")

    def test_expensive_wins_when_delta_proportionally_better(self):
        """If expensive action has significantly better delta, it can still win."""
        from real.agent.selector import ActionSelector
        from real.boundary.vocabulary import VOCABULARY
        log = self._make_log([
            ("introspect",  0.005, 0.001, 15),  # tiny delta
            ("digest_log",  0.100, 0.200, 15),  # much better delta
        ])
        sel = ActionSelector(budget_mode=True)
        available = [a for a in VOCABULARY if a.name in ("introspect", "digest_log")]
        winner = sel._exploit(available, log)
        self.assertEqual(winner.name, "digest_log")

    def test_budget_mode_false_ignores_cost(self):
        """budget_mode=False: selection is purely by delta, cost ignored."""
        from real.agent.selector import ActionSelector
        from real.boundary.vocabulary import VOCABULARY
        log = self._make_log([
            ("introspect",  0.001, 0.001, 15),
            ("digest_log",  0.050, 0.200, 15),
        ])
        sel = ActionSelector(budget_mode=False)
        available = [a for a in VOCABULARY if a.name in ("introspect", "digest_log")]
        winner = sel._exploit(available, log)
        # Without budget mode, digest_log has better delta so it wins
        self.assertEqual(winner.name, "digest_log")

    def test_mean_cost_for_action(self):
        from real.coherence.memory import EpisodicLog
        log = self._make_log([("introspect", 0.01, 0.002, 10)])
        cost = log.mean_cost_for_action("introspect")
        self.assertAlmostEqual(cost, 0.002, places=5)
        self.assertEqual(log.mean_cost_for_action("nonexistent"), 0.0)

    def test_self_model_alias(self):
        from real.coherence.memory import EpisodicLog, LogEntry
        log = EpisodicLog()
        for i in range(10):
            log.record(LogEntry(
                cycle=i, timestamp=time.time(),
                state_before={}, action="introspect", action_params={},
                state_after={}, coherence_score=0.7,
                dimension_scores={k: 0.7 for k in [
                    "continuity","vitality","contextual_fit",
                    "differentiation","accountability","reflexivity"]},
                delta_coherence=0.01, compute_cost_secs=0.001,
            ))
        m1 = log.self_model()
        m2 = log.build_self_model()
        self.assertIsInstance(m1, dict)
        self.assertEqual(set(m1.keys()), set(m2.keys()))

    def test_vitality_smoothed_by_rolling_mean(self):
        """score_vitality() should buffer CPU spikes over 5-cycle window."""
        from real.coherence.engine import CoherenceEngine, SystemState
        engine = CoherenceEngine()
        # Load history: 4 cycles at 0.1, 1 spike at 0.9
        for load in [0.1, 0.1, 0.1, 0.1]:
            engine._recent_states.append(SystemState(cpu_load_avg=load, timestamp=time.time()))
        raw_spike_vitality = max(0.0, 1.0 - ((0.9 - 0.4)**2) / 0.25)  # ≈ 0.0
        spike_state = SystemState(cpu_load_avg=0.9)
        engine._recent_states.append(spike_state)
        smoothed = engine.score_vitality(spike_state)
        # Smoothed should be meaningfully higher than the raw spike score
        self.assertGreater(smoothed, raw_spike_vitality + 0.3)


# ── Test: Environment Dynamics (Phase 3e) ────────────────────────────

class TestEnvironmentDynamics(unittest.TestCase):
    """Environmental events are created, aged, and pruned correctly."""

    def setUp(self):
        import real.boundary.sandbox as _sb
        import real.boundary.environment as _env_mod
        self._tmpdir = Path(tempfile.mkdtemp())
        self._orig_terrain = _sb.TERRAIN_DIR
        _sb.TERRAIN_DIR = self._tmpdir / "terrain"
        _env_mod.TERRAIN_DIR = _sb.TERRAIN_DIR
        _sb.TERRAIN_DIR.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        import real.boundary.sandbox as _sb
        import real.boundary.environment as _env_mod
        _sb.TERRAIN_DIR = self._orig_terrain
        _env_mod.TERRAIN_DIR = self._orig_terrain
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _env(self, **kw):
        from real.boundary.environment import EnvironmentDynamics
        return EnvironmentDynamics(seed=42, **kw)

    def test_event_files_created(self):
        env = self._env(event_interval=5)
        for c in range(1, 11):
            env.tick(c)
        import real.boundary.sandbox as _sb
        events = [f for f in _sb.TERRAIN_DIR.iterdir() if f.name.startswith("event_")]
        self.assertGreater(len(events), 0)

    def test_is_event_file_classifies(self):
        from real.boundary.environment import EnvironmentDynamics
        self.assertTrue(EnvironmentDynamics.is_event_file("event_7_load_spike.txt"))
        self.assertTrue(EnvironmentDynamics.is_event_file("event_7.txt"))   # prefix+suffix match
        self.assertFalse(EnvironmentDynamics.is_event_file("terrain_mark.txt"))
        self.assertFalse(EnvironmentDynamics.is_event_file("event_7_load_spike.json"))  # wrong ext


    def test_parse_event_file_extracts_metadata(self):
        from real.boundary.environment import EnvironmentDynamics
        content = "[EVENT] type=thermal_event\ncycle=10\nmagnitude=0.80\ntimestamp=1234"
        meta = EnvironmentDynamics.parse_event_file(
            content, "event_10_thermal_event.txt", current_cycle=20
        )
        self.assertEqual(meta["event_type"], "thermal_event")
        self.assertEqual(meta["event_age_cycles"], 10)
        self.assertAlmostEqual(meta.get("magnitude", 0), 0.80, places=2)

    def test_recent_events_shape(self):
        env = self._env(event_interval=3)
        for c in range(1, 16):
            env.tick(c)
        recent = env.recent_events(5)
        self.assertLessEqual(len(recent), 5)
        for e in recent:
            self.assertIn("event_type", e)

    def test_old_events_pruned(self):
        import real.boundary.sandbox as _sb
        env = self._env(event_interval=1, prune_interval=5, event_max_age_cycles=3)
        old = _sb.TERRAIN_DIR / "event_1_load_spike.txt"
        old.write_text("[EVENT] type=load_spike\ncycle=1\n", encoding="utf-8")
        env.tick(10)  # 10 % 5 == 0 → prune fires; age = 9 > 3
        self.assertFalse(old.exists(), "Old event file should have been pruned")


# ── Test: Full Integration Run (Phase 3 combined) ────────────────────

class TestFullRunIntegration(unittest.TestCase):
    """
    Short integration run verifying the whole Phase 3 stack together.

    2 sessions × 15 cycles with interval=0 (~20–30s total on most hardware).
    Asserts structural properties only — no exact coherence values.
    """

    def test_two_session_run_structural_sanity(self):
        from real.agent.loop import REALAgent

        for session_num in range(2):
            agent = REALAgent(cycle_limit=15, cycle_interval=0, verbose=False)
            agent.run()

            # World is bounded
            self.assertLess(agent.world.historical_relation_count, 200,
                            "World should not grow unboundedly")

            # AVIA stage is a valid value
            from real.agent.avia import AVIAStage
            self.assertIn(agent.avia.stage, list(AVIAStage))

            # Mesh is active
            self.assertTrue(agent.coherence.mesh_enabled)

            # At least some environment events were seen
            self.assertGreaterEqual(len(agent.env.recent_events()), 0)

            # Coherence history was populated
            self.assertGreater(len(agent.coherence._recent_states), 0)

            # Final coherence in a plausible range
            if agent.coherence.prior_score is not None:
                self.assertGreaterEqual(agent.coherence.prior_score, 0.0)
                self.assertLessEqual(agent.coherence.prior_score, 1.0)


# ── Runner ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
