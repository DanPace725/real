"""Test the two new costly actions."""
import time
from real.agent.loop import REALAgent

# Run enough to unlock both (digest_log needs 20 entries, sort_terrain needs 12)
a = REALAgent(cycle_limit=25, cycle_interval=0, verbose=False)
a.run()

# Test digest_log
print("=== digest_log (CPU-bound) ===")
t0 = time.perf_counter()
r = a.executor.execute("digest_log")
t1 = time.perf_counter()
print(f"  Success: {r['success']}")
print(f"  Entries: {r.get('entries_digested')}")
print(f"  Iterations: {r.get('iterations')}")
print(f"  Cost: {t1-t0:.4f}s")

# Test sort_terrain
print("\n=== sort_terrain (I/O-bound) ===")
t0 = time.perf_counter()
r = a.executor.execute("sort_terrain")
t1 = time.perf_counter()
print(f"  Success: {r['success']}")
print(f"  Sorted: {r.get('sorted')} files")
print(f"  Cost: {t1-t0:.4f}s")

# Compare to baseline
print("\n=== Metabolic comparison ===")
t0 = time.perf_counter()
a.executor.execute("shallow_scan")
baseline = time.perf_counter() - t0

t0 = time.perf_counter()
a.executor.execute("digest_log")
d_cost = time.perf_counter() - t0

t0 = time.perf_counter()
a.executor.execute("sort_terrain")
s_cost = time.perf_counter() - t0

print(f"  shallow_scan: {baseline:.4f}s (baseline)")
print(f"  digest_log:   {d_cost:.4f}s ({d_cost/max(baseline,0.0001):.0f}x)")
print(f"  sort_terrain: {s_cost:.4f}s ({s_cost/max(baseline,0.0001):.0f}x)")
print("\nSTATUS: OK")
