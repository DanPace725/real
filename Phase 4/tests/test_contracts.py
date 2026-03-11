from __future__ import annotations

import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from domains.hardware.adapter import (
    HardwareActionBackend,
    HardwareCoherenceModel,
    HardwareObservationAdapter,
)
from domains.llm_api.adapter import make_llm_api_bundle
from domains.repo_health.adapter import (
    RepoHealthActionBackend,
    RepoHealthCoherenceModel,
    RepoHealthObservationAdapter,
)
from real_core.engine import RealCoreEngine
from real_core.mesh import TiltRegulatoryMesh
from real_core.session import SessionHistory
from run_experiment import run_from_config


class TestGeneralizedEngine(unittest.TestCase):
    def test_engine_records_cycles_hardware(self) -> None:
        engine = RealCoreEngine(
            observer=HardwareObservationAdapter(seed=11),
            actions=HardwareActionBackend(),
            coherence=HardwareCoherenceModel(),
            domain_name="hardware",
        )
        summary = engine.run_session(cycles=8)
        self.assertEqual(summary.cycles, 8)
        self.assertEqual(len(engine.memory.entries), 8)
        self.assertGreaterEqual(summary.mean_coherence, 0.0)
        self.assertLessEqual(summary.mean_coherence, 1.0)

    def test_engine_records_cycles_repo_health(self) -> None:
        repo_root = ROOT.parent / "Phase 2"
        engine = RealCoreEngine(
            observer=RepoHealthObservationAdapter(root_path=repo_root),
            actions=RepoHealthActionBackend(root_path=repo_root),
            coherence=RepoHealthCoherenceModel(),
            domain_name="repo_health",
        )
        summary = engine.run_session(cycles=6)
        self.assertEqual(summary.cycles, 6)
        self.assertEqual(len(engine.memory.entries), 6)
        self.assertGreaterEqual(summary.final_coherence, 0.0)
        self.assertLessEqual(summary.final_coherence, 1.0)

    def test_engine_records_cycles_llm_api_synthetic(self) -> None:
        observer, actions, coherence = make_llm_api_bundle(seed=3, mode="synthetic")
        engine = RealCoreEngine(
            observer=observer,
            actions=actions,
            coherence=coherence,
            domain_name="llm_api",
        )
        summary = engine.run_session(cycles=10)
        self.assertEqual(summary.cycles, 10)
        self.assertEqual(len(engine.memory.entries), 10)
        self.assertGreaterEqual(summary.mean_coherence, 0.0)
        self.assertLessEqual(summary.mean_coherence, 1.0)

    def test_engine_records_cycles_llm_api_replay(self) -> None:
        trace_path = ROOT / "experiments" / "llm_api_sample_trace.jsonl"
        observer, actions, coherence = make_llm_api_bundle(
            mode="replay",
            trace_input_path=trace_path,
            loop_replay=False,
            strict_action_match=False,
            observation_noise=0.0,
        )
        engine = RealCoreEngine(
            observer=observer,
            actions=actions,
            coherence=coherence,
            domain_name="llm_api",
        )
        summary = engine.run_session(cycles=6)
        self.assertEqual(summary.cycles, 6)
        self.assertEqual(len(engine.memory.entries), 6)
        first = engine.memory.entries[0]
        self.assertIn("token_load", first.state_after)
        self.assertGreaterEqual(first.state_after["token_load"], 0.0)

    def test_selector_mode_is_recorded(self) -> None:
        engine = RealCoreEngine(
            observer=HardwareObservationAdapter(seed=4),
            actions=HardwareActionBackend(),
            coherence=HardwareCoherenceModel(),
            domain_name="hardware",
        )
        entry = engine.run_cycle(1)
        self.assertIn(entry.mode, {"fluctuation", "constraint", "guided"})


class TestRegulatoryMesh(unittest.TestCase):
    def test_mesh_bounds_target(self) -> None:
        mesh = TiltRegulatoryMesh()
        dims = {
            "continuity": 0.9,
            "vitality": 0.95,
            "contextual_fit": 0.85,
            "differentiation": 0.10,
            "accountability": 0.20,
            "reflexivity": 0.05,
        }
        out = mesh.apply(dims)
        self.assertLessEqual(out["accountability"], out["continuity"])
        self.assertLessEqual(out["reflexivity"], out["vitality"])
        self.assertLessEqual(out["differentiation"], out["contextual_fit"])


class TestConfigRunner(unittest.TestCase):
    def test_runs_hardware_config(self) -> None:
        config = ROOT / "experiments" / "example_hardware.toml"
        result = run_from_config(config)
        self.assertEqual(result["domain"], "hardware")
        self.assertIn("mean_coherence", result)
        self.assertGreaterEqual(result["mean_coherence"], 0.0)
        self.assertLessEqual(result["mean_coherence"], 1.0)
        self.assertIn("session_id", result)

    def test_runs_repo_health_config(self) -> None:
        config = ROOT / "experiments" / "example_repo_health.toml"
        result = run_from_config(config)
        self.assertEqual(result["domain"], "repo_health")
        self.assertIn("gco_counts", result)
        self.assertEqual(sum(result["gco_counts"].values()), result["cycles"])

    def test_runs_llm_api_config(self) -> None:
        config = ROOT / "experiments" / "example_llm_api.toml"
        result = run_from_config(config)
        self.assertEqual(result["domain"], "llm_api")
        self.assertIn("mean_coherence", result)
        self.assertGreaterEqual(result["mean_coherence"], 0.0)
        self.assertLessEqual(result["mean_coherence"], 1.0)

    def test_llm_api_replay_captures_trace_output(self) -> None:
        temp_root = ROOT / "tests_tmp" / f"trace_{uuid.uuid4().hex}"
        temp_root.mkdir(parents=True, exist_ok=True)

        try:
            trace_in = ROOT / "experiments" / "llm_api_sample_trace.jsonl"
            trace_out = temp_root / "captured.jsonl"
            config_path = temp_root / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        'domain = "llm_api"',
                        "",
                        "[session]",
                        "cycles = 5",
                        'consolidate_on_action = "rest"',
                        "",
                        "[selector]",
                        "exploration_rate = 0.4",
                        "stagnation_window = 5",
                        "stagnation_threshold = 0.005",
                        "guided_threshold = 10",
                        "budget_mode = true",
                        "",
                        "[mesh]",
                        "enabled = true",
                        "viability_floor = 0.757",
                        "parametric_wall = 0.289",
                        "",
                        "[memory]",
                        "maxlen = 500",
                        "",
                        "[history]",
                        "enabled = false",
                        "",
                        "[domain_config]",
                        "mode = \"replay\"",
                        f'trace_input_path = "{trace_in.as_posix()}"',
                        f'trace_output_path = "{trace_out.as_posix()}"',
                        "strict_action_match = false",
                        "loop_replay = true",
                        "observation_noise = 0.0",
                    ]
                ),
                encoding="utf-8",
            )

            _ = run_from_config(config_path)
            self.assertTrue(trace_out.exists())
            lines = [ln for ln in trace_out.read_text(encoding="utf-8").splitlines() if ln.strip()]
            self.assertGreaterEqual(len(lines), 1)
            sample = json.loads(lines[0])
            self.assertIn("action", sample)
            self.assertIn("request_tokens", sample)
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

    def test_session_history_persists_across_runs(self) -> None:
        temp_root = ROOT / "tests_tmp" / f"history_{uuid.uuid4().hex}"
        temp_root.mkdir(parents=True, exist_ok=True)

        try:
            history_path = temp_root / "session_history.json"
            config_path = temp_root / "temp_config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        'domain = "llm_api"',
                        "",
                        "[session]",
                        "cycles = 5",
                        'consolidate_on_action = "rest"',
                        "",
                        "[selector]",
                        "exploration_rate = 0.4",
                        "stagnation_window = 5",
                        "stagnation_threshold = 0.005",
                        "guided_threshold = 10",
                        "budget_mode = true",
                        "",
                        "[mesh]",
                        "enabled = true",
                        "viability_floor = 0.757",
                        "parametric_wall = 0.289",
                        "",
                        "[memory]",
                        "maxlen = 500",
                        "",
                        "[history]",
                        "enabled = true",
                        f'path = "{history_path.as_posix()}"',
                        "",
                        "[domain_config]",
                        "seed = 13",
                        "mode = \"synthetic\"",
                    ]
                ),
                encoding="utf-8",
            )

            first = run_from_config(config_path)
            second = run_from_config(config_path)
            self.assertEqual(first["session_id"], 1)
            self.assertEqual(second["session_id"], 2)
            self.assertEqual(second.get("session_history_count"), 2)

            history = SessionHistory(history_path)
            self.assertEqual(history.count, 2)
            self.assertEqual(history.latest.session_id, 2)
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
