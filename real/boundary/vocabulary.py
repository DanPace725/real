"""
Vocabulary — the agent's available actions organized by metabolic tier.

Each action:
    1. Executes through the Sandbox (against real OS)
    2. Returns a result dict
    3. Creates/modifies Relations in the World graph to record what happened

Actions are organized by metabolic cost tier.  The tier structure reflects
genuine computational cost and is used by the selector to balance the
agent's resource budget.

Unlock conditions based on log maturity: actions emerge as the agent
develops.  `introspect` requires 15 log entries because introspecting
an empty log produces no useful signal.
"""

from __future__ import annotations

import time
import json
import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional
from pathlib import Path

from real.core.primitives import RPPrimitive
from real.core.entity import Entity
from real.core.relation import Relation
from real.core.world import World
from real.boundary.sandbox import Sandbox, TERRAIN_DIR
from real.coherence.memory import EpisodicLog


# ── Metabolic tiers ──────────────────────────────────────────────────

class Tier(str, Enum):
    REFLEX   = "reflex"      # 0.02–0.05  (cheap, fast)
    REGULATE = "regulate"    # 0.05–0.10  (self-management)
    EXPLORE  = "explore"     # 0.10–0.25  (information gathering)
    BUILD    = "build"       # 0.10–0.30  (create/modify)
    SPAWN    = "spawn"       # 0.10–0.60  (expensive, generative)


# ── Action definition ────────────────────────────────────────────────

@dataclass
class ActionDef:
    """
    Definition of an available action.

    Attributes
    ----------
    name : str
        Action identifier.
    tier : Tier
        Metabolic cost tier.
    estimated_cost : float
        Estimated cost (soft prior — replaced by empirical cost from log).
    min_log_entries : int
        Minimum log entries before this action unlocks.
    primitive : RPPrimitive
        Which primitive this action primarily enacts.
    description : str
        What this action does.
    """
    name: str
    tier: Tier
    estimated_cost: float
    min_log_entries: int
    primitive: RPPrimitive
    description: str


# ── Action registry ──────────────────────────────────────────────────

VOCABULARY: list[ActionDef] = [
    # REFLEX tier
    ActionDef("shallow_scan",    Tier.REFLEX,   0.02,  0, RPPrimitive.EPISTEMIC,  "Quick system state read"),
    ActionDef("list_terrain",    Tier.REFLEX,   0.03,  0, RPPrimitive.GEOMETRY,   "List terrain files"),
    ActionDef("read_terrain",    Tier.REFLEX,   0.05,  0, RPPrimitive.EPISTEMIC,  "Read a specific terrain file"),

    # REGULATE tier
    ActionDef("rest",            Tier.REGULATE, 0.05,  0, RPPrimitive.CONSTRAINT, "Pause and consolidate memory"),
    ActionDef("cleanup_temp",    Tier.REGULATE, 0.05,  3, RPPrimitive.CONSTRAINT, "Remove temp files"),

    # EXPLORE tier
    ActionDef("deep_scan",       Tier.EXPLORE,  0.15,  5, RPPrimitive.EPISTEMIC,  "Detailed system state analysis"),
    ActionDef("query_memory",    Tier.EXPLORE,  0.15,  8, RPPrimitive.EPISTEMIC,  "Query episodic log for patterns"),
    ActionDef("compare_state",   Tier.EXPLORE,  0.20, 10, RPPrimitive.EPISTEMIC,  "Compare current to historical state"),

    # BUILD tier
    ActionDef("mark_terrain",    Tier.BUILD,    0.15,  3, RPPrimitive.GEOMETRY,   "Write a terrain mark"),
    ActionDef("write_memory",    Tier.BUILD,    0.15,  5, RPPrimitive.ONTOLOGY,   "Write to persistent memory"),
    ActionDef("checkpoint",      Tier.BUILD,    0.20, 10, RPPrimitive.ONTOLOGY,   "Save full state checkpoint"),
    ActionDef("introspect",      Tier.BUILD,    0.25, 15, RPPrimitive.META,       "Self-model from log analysis"),

    # SPAWN tier (genuinely expensive — real CPU or I/O work)
    ActionDef("digest_log",      Tier.SPAWN,    0.40, 20, RPPrimitive.DYNAMICS,   "CPU-bound: iterative SHA-256 over serialized log"),
    ActionDef("sort_terrain",    Tier.SPAWN,    0.35, 12, RPPrimitive.GEOMETRY,   "I/O-bound: read, sort, and rewrite terrain files"),
]

# Name → ActionDef lookup
ACTIONS_BY_NAME: dict[str, ActionDef] = {a.name: a for a in VOCABULARY}


# ── Action executor ──────────────────────────────────────────────────

class ActionExecutor:
    """
    Executes actions through the sandbox and records results in the World.

    Flow: sandbox.execute() → real effect → world.add_relation(what_happened)
    """

    def __init__(
        self,
        sandbox: Sandbox,
        world: World,
        log: EpisodicLog | None = None,
        agent_id: str = "agent",
    ) -> None:
        self.sandbox = sandbox
        self.world = world
        self.log = log
        self.agent_id = agent_id
        self._relation_counter = 0

    def available_actions(self, log_size: int) -> list[ActionDef]:
        """Actions unlocked at current log maturity."""
        return [a for a in VOCABULARY if log_size >= a.min_log_entries]

    def execute(
        self,
        action_name: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute an action and record the result in the World graph.

        Returns a result dict including wall-clock cost.
        """
        params = params or {}
        action_def = ACTIONS_BY_NAME.get(action_name)
        if not action_def:
            return {"success": False, "error": f"Unknown action: {action_name}"}

        t0 = time.perf_counter()
        result = self._dispatch(action_name, params)
        elapsed = time.perf_counter() - t0

        result["action"] = action_name
        result["compute_cost_secs"] = elapsed
        result["tier"] = action_def.tier.value

        # Record in World as a relation
        self._record_in_world(action_def, params, result)

        self.sandbox.action_count += 1
        return result

    def _dispatch(self, action: str, params: dict) -> dict:
        """Route action to sandbox operation."""
        if action == "shallow_scan":
            state = self.sandbox.read_system_state(0)
            return {"success": True, "state": state.to_dict()}

        elif action == "list_terrain":
            files = self.sandbox.list_terrain()
            return {"success": True, "files": files, "count": len(files)}

        elif action == "read_terrain":
            name = params.get("name", "")
            content = self.sandbox.read_terrain(name)
            return {"success": content is not None, "content": content}

        elif action == "rest":
            # Rest is handled by the agent loop (triggers consolidation)
            return {"success": True, "mode": "rest"}

        elif action == "cleanup_temp":
            removed = self.sandbox.cleanup_temp()
            return {"success": True, "removed": removed}

        elif action == "deep_scan":
            state = self.sandbox.read_system_state(0)
            stats = self.sandbox.sandbox_stats()
            return {"success": True, "state": state.to_dict(), "sandbox": stats}

        elif action == "mark_terrain":
            name = params.get("name", f"mark_{time.time():.0f}")
            content = params.get("content", "")
            ok = self.sandbox.mark_terrain(name, content)
            return {"success": ok}

        elif action == "write_memory":
            name = params.get("name", "")
            data = params.get("data", "")
            ok = self.sandbox.save_memory(name, data)
            return {"success": ok}

        elif action == "checkpoint":
            data = json.dumps(self.world.to_dict(), indent=2)
            ok = self.sandbox.save_memory("checkpoint.json", data)
            return {"success": ok, "world_entities": self.world.entity_count}

        elif action == "query_memory":
            return self._query_memory(params)

        elif action == "compare_state":
            return self._compare_state(params)

        elif action == "introspect":
            return self._introspect(params)

        elif action == "digest_log":
            return self._digest_log(params)

        elif action == "sort_terrain":
            return self._sort_terrain(params)

        else:
            return {"success": False, "error": f"Not implemented: {action}"}

    # ── Implemented actions ─────────────────────────────────────────────

    def _query_memory(self, params: dict) -> dict:
        """
        P5 Epistemic — query episodic log for patterns.

        Returns trail summaries, dimension rankings, and action efficiency.
        The agent is looking at its own history to find what worked.
        """
        if not self.log or self.log.size < 3:
            return {"success": False, "reason": "insufficient_log_data"}

        query_type = params.get("query", "trails")

        if query_type == "best_by_dimension":
            rankings = self.log.best_actions_by_dimension()
            return {
                "success": True,
                "query": query_type,
                "rankings": {
                    dim: [(a, round(s, 4)) for a, s in pairs[:5]]
                    for dim, pairs in rankings.items()
                },
            }

        elif query_type == "trends":
            window = params.get("window", 10)
            trends = self.log.dimension_trends(window=window)
            return {"success": True, "query": query_type, "trends": trends}

        else:
            # Default: trail summary (most useful general query)
            trails = self.log.action_trail_summary()
            return {"success": True, "query": "trails", "trails": trails}

    def _compare_state(self, params: dict) -> dict:
        """
        P5 Epistemic — compare current system state to historical baselines.

        Reads REAL system state right now and computes drift from the
        distribution of past state_after readings in the log.
        """
        if not self.log or self.log.size < 5:
            return {"success": False, "reason": "insufficient_history"}

        # Read real current state
        current = self.sandbox.read_system_state(0)
        current_dict = current.to_dict()

        # Compare against historical baselines from the log
        drift = self.log.state_comparison(current_dict)

        # Also include dimension trends
        trends = self.log.dimension_trends(window=5)

        # Find which fields have drifted most
        significant_drifts = {
            k: v for k, v in drift.items()
            if isinstance(v, dict) and abs(v.get("normalized_drift", 0)) > 0.3
        }

        return {
            "success": True,
            "current_state": current_dict,
            "drift": drift,
            "significant_drifts": list(significant_drifts.keys()),
            "dimension_trends": trends,
        }

    def _introspect(self, params: dict) -> dict:
        """
        P6 Meta — build a self-model from the agent's own log.

        This is the highest-level action: the agent examining its own
        behavioral patterns, identifying strengths and weaknesses, and
        characterizing its developmental stage.

        Results are written to persistent memory so they survive sessions.
        """
        if not self.log or self.log.size < 10:
            return {"success": False, "reason": "insufficient_log_data"}

        # Build self-model from log
        model = self.log.build_self_model()

        # Persist the introspection result
        model_json = json.dumps(model, indent=2)
        self.sandbox.save_memory("self_model.json", model_json)

        # Also write a human-readable summary
        summary_lines = [
            f"=== REAL Agent Self-Model ===",
            f"Entries analyzed: {model.get('entries_analyzed', 0)}",
            f"Consolidations: {model.get('consolidations', 0)}",
            f"",
            f"Behavioral Profile:",
            f"  Dominant action: {model.get('dominant_action', '?')}",
            f"  Action diversity: {model.get('action_diversity', 0):.0%}",
            f"",
            f"Coherence:",
            f"  Mean: {model.get('coherence_mean', 0):.4f}",
            f"  Trajectory: {model.get('coherence_trajectory', 0):+.4f}",
            f"  GCO proximity: {model.get('gco_proximate_fraction', 0):.0%}",
            f"",
            f"Dimensions:",
            f"  Strongest: {model.get('strongest_dimension', '?')}",
            f"  Weakest: {model.get('weakest_dimension', '?')}",
        ]
        for dim, avg in model.get("dimension_averages", {}).items():
            summary_lines.append(f"    {dim}: {avg:.4f}")
        summary_lines.extend([
            f"",
            f"Metabolic:",
            f"  Total compute: {model.get('total_compute_secs', 0):.4f}s",
            f"  Mean per cycle: {model.get('mean_compute_per_cycle', 0):.5f}s",
        ])

        summary = "\n".join(summary_lines)
        self.sandbox.save_memory("self_model_summary.txt", summary)

        return {
            "success": True,
            "model": model,
            "persisted": ["self_model.json", "self_model_summary.txt"],
        }

    def _digest_log(self, params: dict) -> dict:
        """
        P2 Dynamics — CPU-bound computational work on the agent's own data.

        Serializes the episodic log, then runs iterative SHA-256 hashing.
        This is NOT crypto — it's genuine computational work performed on
        the agent's own experience.  The output is a compact digest stored
        as a terrain marker.

        The number of hash iterations scales with log size, so the cost
        grows as the agent accumulates more experience.  This is the
        metabolic cost of "digesting" experience.
        """
        if not self.log or self.log.size < 5:
            return {"success": False, "reason": "insufficient_log_data"}

        # Serialize the log entries to bytes
        log_data = json.dumps(
            [{"c": e.cycle, "a": e.action, "s": e.coherence_score,
              "d": e.delta_coherence, "ds": e.dimension_scores}
             for e in self.log.entries],
            separators=(",", ":")
        ).encode("utf-8")

        # Iterative hashing — cost scales with log size
        # Base: 5000 iterations. +500 per log entry. Genuinely expensive.
        iterations = 5000 + (self.log.size * 500)
        digest = hashlib.sha256(log_data).digest()
        for _ in range(iterations):
            digest = hashlib.sha256(digest).digest()

        hex_digest = digest.hex()

        # Store the digest as a terrain marker
        marker_name = f"digest_{int(time.time())}"
        marker_content = json.dumps({
            "digest": hex_digest,
            "entries_digested": self.log.size,
            "iterations": iterations,
            "timestamp": time.time(),
        })
        self.sandbox.mark_terrain(marker_name, marker_content)

        return {
            "success": True,
            "digest": hex_digest[:16] + "...",
            "entries_digested": self.log.size,
            "iterations": iterations,
        }

    def _sort_terrain(self, params: dict) -> dict:
        """
        P3 Geometry — I/O-bound: read, sort, and rewrite all terrain files.

        Reads every terrain file, computes a sorting metric (by timestamp
        extracted from filename, then by file size), and rewrites them
        with an index prefix.  This is genuine disk I/O work — the agent
        encounters a different metabolic signature than CPU-bound work.

        CPU-heavy digest_log spikes vitality scoring one way.
        I/O-heavy sort_terrain spikes it differently (memory pressure,
        file system latency).
        """
        terrain_dir = TERRAIN_DIR
        if not terrain_dir.exists():
            return {"success": False, "reason": "no_terrain_dir"}

        # Read all terrain files
        files = []
        for p in terrain_dir.iterdir():
            if p.is_file():
                try:
                    content = p.read_text(encoding="utf-8")
                    stat = p.stat()
                    files.append({
                        "name": p.name,
                        "content": content,
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                        "path": p,
                    })
                except (OSError, UnicodeDecodeError):
                    continue

        if not files:
            return {"success": True, "sorted": 0, "reason": "no_files"}

        # Sort by modification time, then by size
        files.sort(key=lambda f: (f["mtime"], f["size"]))

        # Rewrite each file with a sort-order prefix in content
        for i, f in enumerate(files):
            new_content = f"[{i:04d}] {f['content']}"
            try:
                f["path"].write_text(new_content, encoding="utf-8")
            except OSError:
                continue

        return {
            "success": True,
            "sorted": len(files),
            "order": [f["name"] for f in files],
        }

    # ── World recording ───────────────────────────────────────────────

    def _record_in_world(self, action_def: ActionDef, params: dict, result: dict) -> None:
        """Create a relation in the World to represent what happened."""
        self._relation_counter += 1
        rel_id = f"action_{self._relation_counter}"

        # Determine target entity (terrain, memory, or self)
        target = params.get("name", self.agent_id)
        if not self.world.has_entity(target):
            target = self.agent_id  # fall back to self-referential

        rel = Relation(
            id=rel_id,
            primitive=action_def.primitive,
            source=self.agent_id,
            target=target,
            payload={
                "action": action_def.name,
                "tier": action_def.tier.value,
                "success": result.get("success", False),
                "cost_secs": result.get("compute_cost_secs", 0),
                "timestamp": time.time(),
            },
            active=False,  # historical record, not active relation
        )
        self.world.add_relation(rel)

