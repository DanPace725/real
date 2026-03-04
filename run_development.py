"""
Long developmental run - 3 sessions showing the developmental arc.
Output written to dev_report.txt.
"""
import sys
import time
from pathlib import Path
from real.agent.loop import REALAgent

REPORT_PATH = Path(__file__).parent / "dev_report.txt"
out = open(REPORT_PATH, "w", encoding="utf-8")

def log(msg=""):
    print(msg)
    out.write(msg + "\n")

def run_session(session_num, cycles, interval=0.15):
    log(f"\n{'='*60}")
    log(f"  SESSION {session_num}")
    log(f"{'='*60}")
    
    agent = REALAgent(cycle_limit=cycles, cycle_interval=interval, verbose=False)
    agent.run()
    
    session = agent.session_logger.latest
    log(f"  Cycles: {session.total_cycles}")
    log(f"  Mean coherence: {session.mean_coherence:.3f}")
    log(f"  Final coherence: {session.final_coherence:.3f}")
    log(f"  GCO: STABLE={session.gco_stable_count}  PARTIAL={session.gco_partial_count}  DEGRADED={session.gco_degraded_count}  CRITICAL={session.gco_critical_count}")
    log(f"  Exploration ratio: {session.exploration_ratio:.0%}")
    log(f"  Actions used: {sorted(session.action_distribution.keys())}")
    log(f"  Action counts: {dict(sorted(session.action_distribution.items(), key=lambda x: -x[1]))}")
    log(f"  Tier counts: {dict(session.tier_distribution)}")
    log(f"  Compute: {session.total_compute_secs:.4f}s")
    log(f"  Log size: {agent.log.size}")
    log(f"  World: {agent.world.entity_count} entities, {agent.world.relation_count} relations")
    return agent


# Session 1: 40 cycles (early development)
a1 = run_session(1, cycles=40, interval=0.15)

# Session 2: 40 cycles (mid development)
a2 = run_session(2, cycles=40, interval=0.15)

# Session 3: 20 cycles (maturing)
a3 = run_session(3, cycles=20, interval=0.15)

# Developmental report
dev = a3.session_logger.developmental_summary()
log(f"\n{'='*60}")
log(f"  DEVELOPMENTAL ARC")
log(f"{'='*60}")
log(f"  Total sessions: {dev['sessions']}")
log(f"  Total cycles:   {dev['total_cycles']}")

log(f"\n  Coherence trend:")
for i, c in enumerate(dev.get("coherence_trend", []), 1):
    bar = "#" * int(c * 40)
    log(f"    Session {i}: {c:.3f}  {bar}")

log(f"\n  Exploration trend:")
for i, e in enumerate(dev.get("exploration_trend", []), 1):
    bar = "#" * int(e * 40)
    log(f"    Session {i}: {e:.0%}   {bar}")

log(f"\n  Vocabulary growth:")
for i, v in enumerate(dev.get("vocabulary_growth", []), 1):
    log(f"    Session {i}: {v} distinct actions")

# Check for self-model
model_path = Path.home() / ".real_sandbox" / "memory" / "self_model_summary.txt"
if model_path.exists():
    log(f"\n{'='*60}")
    log(f"  AGENT SELF-MODEL")
    log(f"{'='*60}")
    log(model_path.read_text(encoding="utf-8"))

log(f"\n{'='*60}")
log("DONE")
out.close()
print(f"\nFull report written to: {REPORT_PATH}")
