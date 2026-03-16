"""Session runner with full per-cycle logging for Phase 1 instrumentation.

Orchestrates the environment → substrate → agent → coherence loop.
Logs every cycle's state for later analysis. Supports multi-session
experiments with optional slow-layer carryover between sessions.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .agent import SubstrateAgent
from .environment import SignalEnvironment, TestCoherenceModel
from .substrate import DIMENSIONS, MemorySubstrate, SubstrateConfig


@dataclass
class CycleLog:
    cycle: int
    action: str
    cost: float
    coherence: float
    delta: float
    gco: str
    dimensions: dict[str, float]
    substrate_snapshot: dict
    budget_remaining: float
    true_signals: dict[str, float]


@dataclass
class SessionLog:
    session_id: int
    cycles: int
    mean_coherence: float
    final_coherence: float
    gco_counts: dict[str, int]
    final_substrate: dict
    action_counts: dict[str, int]
    cycle_logs: list[CycleLog] = field(default_factory=list)


class SessionRunner:
    """Runs sessions with full per-cycle logging."""

    def __init__(
        self,
        substrate_config: Optional[SubstrateConfig] = None,
        cycles_per_session: int = 50,
        session_budget: float = 5.0,
        seed: Optional[int] = None,
        carry_slow_layer: bool = False,
    ):
        self.substrate_config = substrate_config or SubstrateConfig()
        self.cycles_per_session = cycles_per_session
        self.session_budget = session_budget
        self.seed = seed
        self.carry_slow_layer = carry_slow_layer
        self.coherence_model = TestCoherenceModel()
        self.session_logs: list[SessionLog] = []
        self._carried_slow: Optional[dict] = None

    def run_session(self, session_id: int = 1) -> SessionLog:
        env_seed = (
            (self.seed + session_id) if self.seed is not None else None
        )
        env = SignalEnvironment(seed=env_seed)
        substrate = MemorySubstrate(
            config=SubstrateConfig(
                slow_decay=self.substrate_config.slow_decay,
                bistable_threshold=self.substrate_config.bistable_threshold,
                write_base_cost=self.substrate_config.write_base_cost,
                maintain_base_cost=self.substrate_config.maintain_base_cost,
                neighbor_discount=self.substrate_config.neighbor_discount,
                coupling_window=self.substrate_config.coupling_window,
                accelerated_decay_factor=self.substrate_config.accelerated_decay_factor,
            )
        )

        if self._carried_slow is not None:
            substrate.load_slow(self._carried_slow)

        agent = SubstrateAgent(
            substrate=substrate,
            session_budget=self.session_budget,
            rng=random.Random(env_seed),
        )
        agent.reset_budget()

        cycle_logs: list[CycleLog] = []
        history: list[dict] = []
        action_history: list[str] = []
        action_counts: dict[str, int] = {}
        prior_coherence: Optional[float] = None
        gco_counts = {"STABLE": 0, "PARTIAL": 0, "DEGRADED": 0, "CRITICAL": 0}
        coherence_sum = 0.0

        for cycle in range(1, self.cycles_per_session + 1):
            env.tick()
            observation = env.observe(substrate)
            substrate.update_fast(observation)

            action = agent.select_action()
            cost = agent.execute_action(action)
            action_history.append(action)
            action_counts[action] = action_counts.get(action, 0) + 1

            observation_after = env.observe(substrate)
            substrate.update_fast(observation_after)

            dimensions = self.coherence_model.score(
                observation_after, history, action, action_history
            )
            coherence = self.coherence_model.composite(dimensions)
            delta = (
                0.0
                if prior_coherence is None
                else coherence - prior_coherence
            )
            gco = self.coherence_model.gco_status(dimensions, coherence)

            agent.coherence = coherence
            agent.dimensions = dimensions
            prior_coherence = coherence

            history.append(
                {
                    "cycle": cycle,
                    "action": action,
                    "observation": observation_after,
                    "dimensions": dimensions,
                    "coherence": coherence,
                    "delta": delta,
                    "gco": gco,
                }
            )

            gco_counts[gco] += 1
            coherence_sum += coherence

            substrate.tick()

            cycle_logs.append(
                CycleLog(
                    cycle=cycle,
                    action=action,
                    cost=cost,
                    coherence=coherence,
                    delta=delta,
                    gco=gco,
                    dimensions=dimensions,
                    substrate_snapshot=substrate.snapshot(),
                    budget_remaining=agent.budget_remaining,
                    true_signals=dict(env.signals),
                )
            )

        mean_coherence = coherence_sum / max(1, self.cycles_per_session)
        last_coherence = cycle_logs[-1].coherence if cycle_logs else 0.0

        if self.carry_slow_layer:
            self._carried_slow = substrate.save_slow()

        session_log = SessionLog(
            session_id=session_id,
            cycles=self.cycles_per_session,
            mean_coherence=mean_coherence,
            final_coherence=last_coherence,
            gco_counts=gco_counts,
            final_substrate=substrate.snapshot(),
            action_counts=action_counts,
            cycle_logs=cycle_logs,
        )
        self.session_logs.append(session_log)
        return session_log

    def run_experiment(
        self,
        sessions: int = 10,
        output_dir: Optional[Path] = None,
    ) -> list[SessionLog]:
        logs = []
        for i in range(1, sessions + 1):
            log = self.run_session(session_id=i)
            logs.append(log)
            _print_session_line(log)

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            for log in logs:
                path = output_dir / f"session_{log.session_id:03d}.json"
                with open(path, "w") as f:
                    json.dump(_serialize_log(log), f, indent=2)
            summary_path = output_dir / "experiment_summary.json"
            with open(summary_path, "w") as f:
                json.dump(_serialize_summary(logs), f, indent=2)
            print(f"\nLogs written to {output_dir}")

        return logs


# ----------------------------------------------------------------------
# Printing
# ----------------------------------------------------------------------


def _print_session_line(log: SessionLog):
    top_actions = sorted(
        log.action_counts.items(), key=lambda x: x[1], reverse=True
    )[:3]
    actions_str = ", ".join(f"{a}={c}" for a, c in top_actions)
    print(
        f"  Session {log.session_id:>2}:  "
        f"coherence={log.mean_coherence:.3f}  "
        f"final={log.final_coherence:.3f}  "
        f"active={log.final_substrate['active_count']}  "
        f"coupling={log.final_substrate['coupling_score']:.3f}  "
        f"GCO={log.gco_counts}  "
        f"[{actions_str}]"
    )


# ----------------------------------------------------------------------
# Serialization
# ----------------------------------------------------------------------


def _serialize_log(log: SessionLog) -> dict:
    return {
        "session_id": log.session_id,
        "cycles": log.cycles,
        "mean_coherence": log.mean_coherence,
        "final_coherence": log.final_coherence,
        "gco_counts": log.gco_counts,
        "final_substrate": log.final_substrate,
        "action_counts": log.action_counts,
        "cycle_logs": [
            {
                "cycle": cl.cycle,
                "action": cl.action,
                "cost": cl.cost,
                "coherence": cl.coherence,
                "delta": cl.delta,
                "gco": cl.gco,
                "dimensions": cl.dimensions,
                "substrate_snapshot": cl.substrate_snapshot,
                "budget_remaining": cl.budget_remaining,
                "true_signals": cl.true_signals,
            }
            for cl in log.cycle_logs
        ],
    }


def _serialize_summary(logs: list[SessionLog]) -> dict:
    coherences = [l.mean_coherence for l in logs]
    couplings = [l.final_substrate["coupling_score"] for l in logs]
    actives = [l.final_substrate["active_count"] for l in logs]
    total_gco = {"STABLE": 0, "PARTIAL": 0, "DEGRADED": 0, "CRITICAL": 0}
    for l in logs:
        for k, v in l.gco_counts.items():
            total_gco[k] += v
    total_cycles = sum(total_gco.values())
    return {
        "sessions": len(logs),
        "coherence_range": [min(coherences), max(coherences)],
        "coherence_mean": sum(coherences) / len(coherences),
        "coupling_range": [min(couplings), max(couplings)],
        "coupling_mean": sum(couplings) / len(couplings),
        "active_range": [min(actives), max(actives)],
        "active_mean": sum(actives) / len(actives),
        "gco_distribution": {
            k: v / max(total_cycles, 1) for k, v in total_gco.items()
        },
    }


# ----------------------------------------------------------------------
# CLI entry point
# ----------------------------------------------------------------------


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Phase 7 — Memory Substrate Experiment"
    )
    parser.add_argument("--sessions", type=int, default=10)
    parser.add_argument("--cycles", type=int, default=50)
    parser.add_argument("--budget", type=float, default=5.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--carry-slow", action="store_true")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    print("=" * 64)
    print("  Phase 7 — Memory Substrate Experiment")
    print("=" * 64)
    print(
        f"  Sessions: {args.sessions}   Cycles: {args.cycles}   "
        f"Budget: {args.budget}   Carry slow: {args.carry_slow}"
    )
    print()

    runner = SessionRunner(
        cycles_per_session=args.cycles,
        session_budget=args.budget,
        seed=args.seed,
        carry_slow_layer=args.carry_slow,
    )
    output_dir = Path(args.output) if args.output else None
    logs = runner.run_experiment(sessions=args.sessions, output_dir=output_dir)

    print()
    print("-" * 64)
    coherences = [l.mean_coherence for l in logs]
    couplings = [l.final_substrate["coupling_score"] for l in logs]
    actives = [l.final_substrate["active_count"] for l in logs]
    print(
        f"  Coherence: {min(coherences):.3f} – {max(coherences):.3f}  "
        f"(mean {sum(coherences)/len(coherences):.3f})"
    )
    print(
        f"  Coupling:  {min(couplings):.3f} – {max(couplings):.3f}  "
        f"(mean {sum(couplings)/len(couplings):.3f})"
    )
    print(
        f"  Active:    {min(actives)} – {max(actives)}  "
        f"(mean {sum(actives)/len(actives):.1f})"
    )
    total_gco = {"STABLE": 0, "PARTIAL": 0, "DEGRADED": 0, "CRITICAL": 0}
    for l in logs:
        for k, v in l.gco_counts.items():
            total_gco[k] += v
    total_cycles = sum(total_gco.values())
    print(
        "  GCO: "
        + "  ".join(
            f"{k}={v/total_cycles:.0%}" for k, v in total_gco.items()
        )
    )
    print("-" * 64)


if __name__ == "__main__":
    main()
