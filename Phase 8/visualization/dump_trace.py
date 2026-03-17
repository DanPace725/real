import argparse
import json
import sys
from pathlib import Path

# Adjust path so we can import phase8
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compare_cold_warm import build_system, SCENARIOS

def dump_trace(seed: int, scenario_name: str, out_file: str):
    scenario = SCENARIOS[scenario_name]
    system = build_system(seed, scenario_name)

    if scenario.initial_signal_specs:
        system.inject_signal_specs(scenario.initial_signal_specs)
    elif scenario.initial_packets > 0:
        system.inject_signal(count=scenario.initial_packets)

    trace_data = {
        "scenario": scenario_name,
        "seed": seed,
        "cycles": scenario.cycles,
        "topology": {
            "positions": scenario.positions,
        },
        "frames": []
    }

    for cycle in range(1, scenario.cycles + 1):
        scheduled_specs = (scenario.signal_schedule_specs or {}).get(cycle)
        if scheduled_specs:
            system.inject_signal_specs(scheduled_specs)
        else:
            scheduled = scenario.packet_schedule.get(cycle, 0)
            if scheduled > 0:
                system.inject_signal(count=scheduled)
        
        report = system.run_global_cycle()
        
        # Extract per-cycle info
        frame = {
            "cycle": cycle,
            "nodes": {},
            "adjacency": system.environment.adjacency,
            "packets": [],
            "feedback": report.get("feedback", [])
        }

        # Node stats
        for node_id, state in system.environment.node_states.items():
            frame["nodes"][node_id] = {
                "atp": state.atp,
                "max_atp": state.max_atp,
            }
        
        # In-flight packets
        for node_id, inbox in system.environment.inboxes.items():
            for p in inbox:
                frame["packets"].append({
                    "id": p.packet_id,
                    "location": node_id,
                    "target": p.target,
                    "path_len": len(p.edge_path),
                    "context_bit": p.context_bit
                })

        # Delivered packets
        for p in system.environment.delivered_packets:
            if getattr(p, "delivered_cycle", None) == cycle:
                frame["packets"].append({
                     "id": p.packet_id,
                     "location": "delivered",
                     "target": p.target,
                     "path_len": len(p.edge_path),
                     "context_bit": p.context_bit
                })

        trace_data["frames"].append(frame)

    out_path = Path(__file__).parent / out_file
    with open(out_path, "w") as f:
        json.dump(trace_data, f, indent=2)
    print(f"Trace saved to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=51)
    parser.add_argument("--scenario", type=str, default="branch_pressure")
    parser.add_argument("--out", type=str, default="trace.json")
    args = parser.parse_args()
    
    dump_trace(args.seed, args.scenario, args.out)
