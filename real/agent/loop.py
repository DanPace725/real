"""
REAL Agent loop — the main execution cycle.

The causal phase ordering is:

    1. READ SYSTEM     — sandbox reads real hardware state
    2. SELECT ACTION   — CFAR selector picks from available vocabulary
    3. EXECUTE         — sandbox performs the action against real OS
    4. READ SYSTEM     — sandbox reads state AFTER action
    5. SCORE           — coherence engine evaluates real state
    6. UPDATE MODEL    — evaluator processes the World graph
    7. RECORD          — episodic log captures the cycle
    8. CONSOLIDATE     — if REST, three-tier memory consolidation

The ordering matters: score AFTER action, not before.  The agent
evaluates the *consequences* of what it did.

Run: python -m real.agent.loop --cycles 50
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

from real.core.primitives import RPPrimitive
from real.core.entity import Entity
from real.core.relation import Relation
from real.core.world import World
from real.core.evaluator import Evaluator
from real.coherence.engine import CoherenceEngine
from real.coherence.memory import EpisodicLog, LogEntry
from real.coherence.biases import THRESHOLDS
from real.boundary.sandbox import Sandbox, SANDBOX_DIR, MEMORY_DIR
from real.boundary.vocabulary import ActionExecutor
from real.boundary.environment import EnvironmentDynamics
from real.agent.avia import AVIATracker
from real.agent.selector import ActionSelector, SelectionMode
from real.agent.session import SessionLogger


class REALAgent:
    """
    The REAL agent.

    Orchestrates the cycle of perceiving, acting, evaluating, and learning,
    all grounded in real hardware readings.
    """

    def __init__(
        self,
        cycle_limit: int = 100,
        cycle_interval: float = 1.0,
        verbose: bool = True,
    ) -> None:
        # ── Configuration ─────────────────────────────────────────────
        self.cycle_limit = cycle_limit
        self.cycle_interval = cycle_interval
        self.verbose = verbose

        # ── Core substrate ────────────────────────────────────────────
        self.world = World()
        self.evaluator = Evaluator()

        # ── Coherence evaluation ──────────────────────────────────────
        self.coherence = CoherenceEngine()
        self.log = EpisodicLog(maxlen=500)
        self.coherence.set_log(self.log)  # wire log for reflexivity scoring

        # ── Boundary ──────────────────────────────────────────────────
        self.sandbox = Sandbox()
        self.executor = ActionExecutor(self.sandbox, self.world, log=self.log, agent_id="agent")
        self.selector = ActionSelector()
        self.env = EnvironmentDynamics()

        # ── Session tracking ──────────────────────────────────────────
        self.session_logger = SessionLogger(
            MEMORY_DIR / "session_history.json"
        )

        # ── Developmental stage ───────────────────────────────────────
        self.avia = AVIATracker()

        # ── Agent state ───────────────────────────────────────────────
        self.cycle: int = 0
        self.running: bool = False
        self.exploration_count: int = 0
        self.exploitation_count: int = 0

    # ── Initialization ────────────────────────────────────────────────

    def _init_world(self) -> None:
        """Seed the World graph with the agent entity and sensor entities."""
        # The agent itself
        agent = Entity(
            id="agent",
            kind="agent",
            state={"status": "initializing", "session": self.session_logger.session_count + 1},
            tags={"physical", "self"},
        )
        self.world.add_entity(agent)

        # System sensor entities (represent real hardware)
        cpu = Entity(id="cpu_sensor", kind="sensor", tags={"physical", "hardware"})
        mem = Entity(id="mem_sensor", kind="sensor", tags={"physical", "hardware"})
        self.world.add_entity(cpu)
        self.world.add_entity(mem)

        # Agent observes sensors (epistemic relations)
        self.world.add_relation(Relation(
            id="observe_cpu", primitive=RPPrimitive.EPISTEMIC,
            source="cpu_sensor", target="agent",
            payload={"observe_fields": ["cpu_load", "cpu_freq", "cpu_temp"]},
        ))
        self.world.add_relation(Relation(
            id="observe_mem", primitive=RPPrimitive.EPISTEMIC,
            source="mem_sensor", target="agent",
            payload={"observe_fields": ["mem_used", "mem_pressure"]},
        ))

        # Agent is constrained by hardware (constraint relation)
        self.world.add_relation(Relation(
            id="hardware_constraint", primitive=RPPrimitive.CONSTRAINT,
            source="cpu_sensor", target="agent",
            payload={"field": "cpu_load", "max": 1.0, "min": 0.0},
        ))

    def _load_prior_log(self) -> None:
        """Load episodic log from prior sessions if available."""
        log_path = MEMORY_DIR / "episodic_log.json"
        loaded = self.log.load(log_path)
        if loaded > 0 and self.verbose:
            print(f"  Loaded {loaded} entries from prior log")

    # ── Main loop ─────────────────────────────────────────────────────

    def run(self) -> None:
        """Run the agent for cycle_limit cycles."""
        self._init_world()
        self._load_prior_log()

        session = self.session_logger.new_session()
        self.running = True

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"  REAL Agent — Session {session.session_id}")
            print(f"  Cycles: {self.cycle_limit}  Interval: {self.cycle_interval}s")
            print(f"  Sandbox: {SANDBOX_DIR}")
            print(f"  Prior sessions: {self.session_logger.session_count - 1}")
            print(f"  Log entries: {self.log.size}")
            print(f"  Developmental stage: {self.avia.stage.value}")
            print(f"{'='*60}\n")

        coherence_sum = 0.0

        try:
            for self.cycle in range(1, self.cycle_limit + 1):
                self.coherence.cycle_number = self.cycle

                # Environment tick: generate events, mark decay, prune stale
                self.env.tick(self.cycle)

                # Phase 1: Read real system state BEFORE action
                state_before = self.sandbox.read_system_state(self.cycle)

                # Update sensor entities with real readings
                cpu = self.world.get_entity("cpu_sensor")
                if cpu:
                    cpu.state.update({
                        "cpu_load": state_before.cpu_load_avg,
                        "cpu_freq": state_before.cpu_freq_ratio,
                        "cpu_temp": state_before.cpu_temp_ratio,
                    })
                mem = self.world.get_entity("mem_sensor")
                if mem:
                    mem.state.update({
                        "mem_used": state_before.memory_used_ratio,
                        "mem_pressure": state_before.memory_pressure,
                    })

                # Phase 2: Select action
                available = self.executor.available_actions(self.log.size)
                action_def, mode = self.selector.select(available, self.log)

                if mode == SelectionMode.FLUCTUATION:
                    self.exploration_count += 1
                else:
                    self.exploitation_count += 1

                # Phase 3: Execute through sandbox (real OS effect)
                result = self.executor.execute(action_def.name)

                # Phase 4: Read real system state AFTER action
                state_after = self.sandbox.read_system_state(self.cycle)
                self.coherence.read_state()  # feed to coherence engine history

                # Phase 5: Score coherence from REAL state
                dimensions = self.coherence.score_all(state_after)
                composite = self.coherence.composite_score(dimensions)
                gco = self.coherence.gco_status(dimensions)
                delta = composite - (self.coherence.prior_score or composite)
                self.coherence.prior_score = composite

                # Phase 6: Update internal world model
                agent_entity = self.world.get_entity("agent")
                if agent_entity:
                    agent_entity.state.update({
                        "status": gco.lower(),
                        "coherence": composite,
                        "cycle": self.cycle,
                    })
                eval_cost = self.evaluator.step(self.world)

                # Phase 7: Record in episodic log
                entry = LogEntry(
                    cycle=self.cycle,
                    timestamp=time.time(),
                    state_before=state_before.to_dict(),
                    action=action_def.name,
                    action_params={},
                    state_after=state_after.to_dict(),
                    coherence_score=composite,
                    dimension_scores=dimensions,
                    delta_coherence=delta,
                    compute_cost_secs=result.get("compute_cost_secs", 0) + eval_cost,
                )
                self.log.record(entry)

                # Phase 8: Consolidate if rest
                if action_def.name == "rest" and self.log.size > 40:
                    pruned = self.log.consolidate()
                    session.consolidation_count += 1
                    world_pruned = 0
                    if self.world.historical_relation_count > 50:
                        world_pruned = self.world.prune_historical(keep_last=100)
                    if self.verbose:
                        world_msg = f", world pruned {world_pruned}" if world_pruned else ""
                        print(f"  [REST] Consolidated log: pruned {pruned} entries{world_msg}")


                # Update session stats
                coherence_sum += composite
                session.action_distribution[action_def.name] = \
                    session.action_distribution.get(action_def.name, 0) + 1
                session.tier_distribution[action_def.tier.value] = \
                    session.tier_distribution.get(action_def.tier.value, 0) + 1

                if gco == "STABLE":
                    session.gco_stable_count += 1
                elif gco == "PARTIAL":
                    session.gco_partial_count += 1
                elif gco == "DEGRADED":
                    session.gco_degraded_count += 1
                else:
                    session.gco_critical_count += 1

                # Print cycle summary
                if self.verbose:
                    mode_char = {"fluctuation": "F", "constraint": "C", "guided": "G"}.get(mode.value, "?")
                    guided_info = ""
                    if mode == SelectionMode.GUIDED and self.selector._weakest_dim:
                        guided_info = f"  [{self.selector._weakest_dim}]"
                    print(
                        f"  [{self.cycle:3d}] {mode_char} {action_def.name:<16s} "
                        f"→ {composite:.3f} ({delta:+.3f})  "
                        f"GCO:{gco:<8s} "
                        f"ATP:{result.get('compute_cost_secs', 0):.4f}s"
                        f"{guided_info}"
                    )

                self.coherence.advance_cycle()

                # Wait between cycles
                if self.cycle_interval > 0 and self.cycle < self.cycle_limit:
                    time.sleep(self.cycle_interval)

        except KeyboardInterrupt:
            if self.verbose:
                print(f"\n  Interrupted at cycle {self.cycle}")

        # ── Session close ─────────────────────────────────────────────
        session.total_cycles = self.cycle
        session.mean_coherence = coherence_sum / max(self.cycle, 1)
        session.final_coherence = self.coherence.prior_score or 0.0
        session.total_compute_secs = self.evaluator.total_compute_secs
        total_modes = self.exploration_count + self.exploitation_count
        session.exploration_ratio = (
            self.exploration_count / max(total_modes, 1)
        )

        self.session_logger.close_session(session)

        # Advance developmental stage after session data is finalised
        self.avia.advance(self.session_logger, self.log)

        # Save episodic log
        log_result = self.log.save(MEMORY_DIR / "episodic_log.json")

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"  Session {session.session_id} complete")
            print(f"  Cycles: {session.total_cycles}")
            print(f"  Mean coherence: {session.mean_coherence:.3f}")
            print(f"  Final coherence: {session.final_coherence:.3f}")
            print(f"  GCO distribution: "
                  f"STABLE={session.gco_stable_count} "
                  f"PARTIAL={session.gco_partial_count} "
                  f"DEGRADED={session.gco_degraded_count} "
                  f"CRITICAL={session.gco_critical_count}")
            print(f"  Exploration ratio: {session.exploration_ratio:.1%}")
            print(f"  Total compute: {session.total_compute_secs:.3f}s")
            print(f"  Log: {log_result}")
            print(f"  World: {self.world.entity_count} entities, "
                  f"{self.world.relation_count} relations")
            # AVIA stage report
            summary = self.avia.stage_summary()
            stage_line = f"  Developmental stage: {summary['stage']}"
            if self.avia.advanced_this_session:
                stage_line += f"  *** STAGE ADVANCE ***"
            print(stage_line)
            m = summary.get("metrics", {})
            print(f"    coherence={m.get('mean_coherence', 0):.3f}  "
                  f"reflexivity={m.get('reflexivity', 0):.3f}  "
                  f"diversity={m.get('action_diversity', 0):.0%}  "
                  f"sessions={m.get('n_sessions', 0)}")
            dev = self.session_logger.developmental_summary()
            if dev["sessions"] > 1:
                print(f"  Coherence trend: {dev['coherence_trend']}")
            print(f"{'='*60}\n")


# ── CLI entry point ──────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="REAL — Relationally Embedded AI Learning Agent"
    )
    parser.add_argument(
        "--cycles", type=int, default=50,
        help="Number of cycles per session (default: 50)"
    )
    parser.add_argument(
        "--interval", type=float, default=1.0,
        help="Seconds between cycles (default: 1.0)"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-cycle output"
    )
    args = parser.parse_args()

    agent = REALAgent(
        cycle_limit=args.cycles,
        cycle_interval=args.interval,
        verbose=not args.quiet,
    )
    agent.run()


if __name__ == "__main__":
    main()
