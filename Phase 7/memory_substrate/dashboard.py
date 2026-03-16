"""Phase 2 visualization: four-signal dashboard and topology snapshots.

Generates an HTML report from experiment session logs showing:
  1. Four derived signals over time (coupling, maintenance, trail-following, self-model)
  2. Slow-layer state heatmap across cycles and sessions
  3. Session trajectory summary
  4. Graph snapshots of slow-layer topology at key moments
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .substrate import DIMENSIONS

SIGNAL_WINDOW = 10


# ------------------------------------------------------------------
# Signal computation
# ------------------------------------------------------------------

@dataclass
class CycleSignals:
    cycle: int
    session: int
    coupling_strength: float
    maintenance_ratio: float
    trail_following_ratio: float
    self_model_accuracy: float


def compute_signals(
    session: dict, session_id: int
) -> list[CycleSignals]:
    cycles = session["cycle_logs"]
    signals = []

    for i, cyc in enumerate(cycles):
        window = cycles[max(0, i - SIGNAL_WINDOW + 1) : i + 1]

        coupling = cyc["substrate_snapshot"]["coupling_score"]
        maint_ratio = _maintenance_ratio(window)
        trail_ratio = _trail_following_ratio(window)
        self_model = _self_model_accuracy(cyc)

        signals.append(CycleSignals(
            cycle=cyc["cycle"],
            session=session_id,
            coupling_strength=coupling,
            maintenance_ratio=maint_ratio,
            trail_following_ratio=trail_ratio,
            self_model_accuracy=self_model,
        ))

    return signals


def _maintenance_ratio(window: list[dict]) -> float:
    if not window:
        return 0.0
    maintains = sum(1 for c in window if c["action"] == "maintain")
    return maintains / len(window)


def _trail_following_ratio(window: list[dict]) -> float:
    trail = 0
    explore = 0
    for c in window:
        snap = c["substrate_snapshot"]
        action = c["action"]
        if action == "maintain":
            trail += 1
        elif action.startswith("invest_"):
            dim = action[len("invest_"):]
            if snap["active"].get(dim, False):
                trail += 1
            else:
                explore += 1
        elif action == "explore":
            explore += 1
    total = trail + explore
    return trail / max(total, 1)


def _self_model_accuracy(cyc: dict) -> float:
    """Rank correlation between slow-layer values and coherence dimension scores."""
    slow = cyc["substrate_snapshot"]["slow"]
    dims = cyc["dimensions"]

    slow_vals = [slow.get(d, 0.0) for d in DIMENSIONS]
    dim_vals = [dims.get(d, 0.0) for d in DIMENSIONS]

    return _spearman(slow_vals, dim_vals)


def _spearman(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 3:
        return 0.0
    rx = _ranks(xs)
    ry = _ranks(ys)
    d_sq = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return 1.0 - (6.0 * d_sq) / (n * (n * n - 1))


def _ranks(vals: list[float]) -> list[float]:
    indexed = sorted(enumerate(vals), key=lambda x: x[1])
    ranks = [0.0] * len(vals)
    for rank, (idx, _) in enumerate(indexed):
        ranks[idx] = rank + 1.0
    return ranks


# ------------------------------------------------------------------
# Graph snapshot
# ------------------------------------------------------------------

@dataclass
class GraphSnapshot:
    label: str
    session: int
    cycle: int
    nodes: dict[str, float]
    active: dict[str, bool]
    edges: list[tuple[str, str, float]]


def extract_graph_snapshots(
    sessions: list[dict], every_n_cycles: int = 25
) -> list[GraphSnapshot]:
    snapshots = []
    for session in sessions:
        sid = session["session_id"]
        cycles = session["cycle_logs"]
        for cyc in cycles:
            c = cyc["cycle"]
            if c == 1 or c % every_n_cycles == 0 or c == len(cycles):
                snap = cyc["substrate_snapshot"]
                nodes = snap["slow"]
                active = snap["active"]
                edges = []
                dims = list(DIMENSIONS)
                for i in range(len(dims)):
                    for j in range(i + 1, len(dims)):
                        d1, d2 = dims[i], dims[j]
                        if active.get(d1, False) and active.get(d2, False):
                            weight = min(nodes.get(d1, 0), nodes.get(d2, 0))
                            edges.append((d1, d2, weight))
                snapshots.append(GraphSnapshot(
                    label=f"S{sid} C{c}",
                    session=sid,
                    cycle=c,
                    nodes=nodes,
                    active=active,
                    edges=edges,
                ))
    return snapshots


# ------------------------------------------------------------------
# HTML generation
# ------------------------------------------------------------------

def generate_dashboard(
    sessions: list[dict],
    output_path: Path,
    title: str = "Memory Substrate Dashboard",
):
    all_signals = []
    for session in sessions:
        sid = session["session_id"]
        sigs = compute_signals(session, sid)
        all_signals.extend(sigs)

    snapshots = extract_graph_snapshots(sessions, every_n_cycles=25)

    session_summaries = []
    for session in sessions:
        sid = session["session_id"]
        session_signals = [s for s in all_signals if s.session == sid]
        session_summaries.append({
            "session": sid,
            "coherence": session["mean_coherence"],
            "active": session["final_substrate"]["active_count"],
            "coupling": statistics.mean(s.coupling_strength for s in session_signals) if session_signals else 0,
            "maintenance": statistics.mean(s.maintenance_ratio for s in session_signals) if session_signals else 0,
            "trail_follow": statistics.mean(s.trail_following_ratio for s in session_signals) if session_signals else 0,
            "self_model": statistics.mean(s.self_model_accuracy for s in session_signals) if session_signals else 0,
            "stable_pct": session["gco_counts"].get("STABLE", 0) / max(sum(session["gco_counts"].values()), 1),
        })

    # Build chart data
    chart_labels = [f"S{s.session}C{s.cycle}" for s in all_signals]
    coupling_data = [round(s.coupling_strength, 4) for s in all_signals]
    maint_data = [round(s.maintenance_ratio, 4) for s in all_signals]
    trail_data = [round(s.trail_following_ratio, 4) for s in all_signals]
    model_data = [round(s.self_model_accuracy, 4) for s in all_signals]

    # Build heatmap data: sessions × dimensions, slow-layer values at end of session
    heatmap = []
    for session in sessions:
        last_cycle = session["cycle_logs"][-1] if session["cycle_logs"] else None
        if last_cycle:
            row = {d: round(last_cycle["substrate_snapshot"]["slow"].get(d, 0), 3) for d in DIMENSIONS}
            heatmap.append({"session": session["session_id"], **row})

    # Build graph SVG data
    graph_svgs = _build_graph_svgs(snapshots[:20])

    html = _render_html(
        title=title,
        chart_labels=json.dumps(chart_labels),
        coupling_data=json.dumps(coupling_data),
        maint_data=json.dumps(maint_data),
        trail_data=json.dumps(trail_data),
        model_data=json.dumps(model_data),
        session_summaries=session_summaries,
        heatmap=heatmap,
        graph_svgs=graph_svgs,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"Dashboard written to {output_path}")


HEX_POSITIONS = {
    "continuity":     (150, 40),
    "vitality":       (260, 100),
    "contextual_fit": (260, 210),
    "differentiation":(150, 270),
    "accountability": (40, 210),
    "reflexivity":    (40, 100),
}

DIM_SHORT = {
    "continuity": "CON",
    "vitality": "VIT",
    "contextual_fit": "CTX",
    "differentiation": "DIF",
    "accountability": "ACC",
    "reflexivity": "REF",
}


def _build_graph_svgs(snapshots: list[GraphSnapshot]) -> list[dict]:
    results = []
    for snap in snapshots:
        edges_svg = ""
        for d1, d2, w in snap.edges:
            x1, y1 = HEX_POSITIONS[d1]
            x2, y2 = HEX_POSITIONS[d2]
            opacity = max(0.15, min(0.9, w))
            edges_svg += (
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                f'stroke="#64748b" stroke-width="{max(1, w * 4):.1f}" '
                f'stroke-opacity="{opacity:.2f}"/>\n'
            )

        nodes_svg = ""
        for dim in DIMENSIONS:
            x, y = HEX_POSITIONS[dim]
            val = snap.nodes.get(dim, 0.0)
            active = snap.active.get(dim, False)
            r = 18 + val * 12
            fill = f"hsl({120 * val:.0f}, 70%, 45%)" if active else "#374151"
            border = "#10b981" if active else "#6b7280"
            nodes_svg += (
                f'<circle cx="{x}" cy="{y}" r="{r:.0f}" '
                f'fill="{fill}" stroke="{border}" stroke-width="2"/>\n'
                f'<text x="{x}" y="{y + 4}" text-anchor="middle" '
                f'fill="white" font-size="11" font-weight="bold">'
                f'{DIM_SHORT[dim]}</text>\n'
            )

        svg = (
            f'<svg viewBox="0 0 300 310" width="200" height="206">\n'
            f'{edges_svg}{nodes_svg}</svg>'
        )
        results.append({"label": snap.label, "svg": svg})
    return results


def _render_html(
    title: str,
    chart_labels: str,
    coupling_data: str,
    maint_data: str,
    trail_data: str,
    model_data: str,
    session_summaries: list[dict],
    heatmap: list[dict],
    graph_svgs: list[dict],
) -> str:
    session_rows = ""
    for s in session_summaries:
        bar_w = int(s["stable_pct"] * 100)
        session_rows += f"""<tr>
            <td>{s['session']}</td>
            <td>{s['coherence']:.3f}</td>
            <td>{s['active']}</td>
            <td>{s['coupling']:.3f}</td>
            <td>{s['maintenance']:.0%}</td>
            <td>{s['trail_follow']:.0%}</td>
            <td>{s['self_model']:.2f}</td>
            <td><div class="bar" style="width:{bar_w}%">{s['stable_pct']:.0%}</div></td>
        </tr>"""

    heatmap_html = '<table class="heatmap"><tr><th>Session</th>'
    for d in DIMENSIONS:
        heatmap_html += f'<th>{DIM_SHORT[d]}</th>'
    heatmap_html += "</tr>"
    for row in heatmap:
        heatmap_html += f'<tr><td>{row["session"]}</td>'
        for d in DIMENSIONS:
            val = row.get(d, 0)
            hue = int(120 * val)
            light = 25 + int(30 * val)
            heatmap_html += f'<td style="background:hsl({hue},70%,{light}%);color:#fff">{val:.2f}</td>'
        heatmap_html += "</tr>"
    heatmap_html += "</table>"

    graphs_html = '<div class="graph-grid">'
    for g in graph_svgs:
        graphs_html += f'<div class="graph-card"><div class="graph-label">{g["label"]}</div>{g["svg"]}</div>'
    graphs_html += '</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
:root {{ --bg: #0f172a; --card: #1e293b; --text: #e2e8f0; --border: #334155;
         --accent: #38bdf8; --green: #10b981; --amber: #f59e0b; --rose: #f43f5e; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg);
        color: var(--text); padding: 2rem; line-height: 1.5; }}
h1 {{ font-size: 1.5rem; margin-bottom: 0.5rem; color: var(--accent); }}
h2 {{ font-size: 1.1rem; margin: 2rem 0 0.75rem; color: var(--text); border-bottom: 1px solid var(--border); padding-bottom: 0.3rem; }}
.subtitle {{ color: #94a3b8; font-size: 0.85rem; margin-bottom: 2rem; }}
.chart-container {{ background: var(--card); border-radius: 8px; padding: 1.5rem; margin-bottom: 2rem; }}
canvas {{ max-height: 320px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 0.82rem; }}
th, td {{ padding: 6px 10px; text-align: center; border-bottom: 1px solid var(--border); }}
th {{ background: var(--card); color: #94a3b8; font-weight: 600; position: sticky; top: 0; }}
td {{ color: var(--text); }}
tr:hover td {{ background: rgba(56,189,248,0.06); }}
.heatmap td {{ font-size: 0.78rem; font-weight: 600; min-width: 52px; }}
.bar {{ background: var(--green); height: 18px; border-radius: 3px; color: #fff;
        font-size: 0.72rem; line-height: 18px; text-align: center; min-width: 28px; }}
.graph-grid {{ display: flex; flex-wrap: wrap; gap: 12px; }}
.graph-card {{ background: var(--card); border-radius: 8px; padding: 10px; text-align: center; }}
.graph-label {{ font-size: 0.75rem; color: #94a3b8; margin-bottom: 4px; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="subtitle">Four-signal coupling dashboard &mdash; Phase 2 visualization</div>

<h2>Four Derived Signals</h2>
<div class="chart-container">
<canvas id="signalChart"></canvas>
</div>

<h2>Session Trajectory</h2>
<table>
<tr><th>Session</th><th>Coherence</th><th>Active</th><th>Coupling</th>
    <th>Maint %</th><th>Trail %</th><th>Self-Model</th><th>STABLE</th></tr>
{session_rows}
</table>

<h2>Slow-Layer State (End of Session)</h2>
{heatmap_html}

<h2>Topology Snapshots</h2>
{graphs_html}

<script>
const ctx = document.getElementById('signalChart').getContext('2d');
new Chart(ctx, {{
  type: 'line',
  data: {{
    labels: {chart_labels},
    datasets: [
      {{ label: 'Coupling Strength', data: {coupling_data},
         borderColor: '#38bdf8', backgroundColor: 'rgba(56,189,248,0.1)',
         borderWidth: 1.5, pointRadius: 0, tension: 0.3, fill: true }},
      {{ label: 'Maintenance Ratio', data: {maint_data},
         borderColor: '#f59e0b', borderWidth: 1.5, pointRadius: 0, tension: 0.3 }},
      {{ label: 'Trail-Following', data: {trail_data},
         borderColor: '#10b981', borderWidth: 1.5, pointRadius: 0, tension: 0.3 }},
      {{ label: 'Self-Model Accuracy', data: {model_data},
         borderColor: '#f43f5e', borderWidth: 1.5, pointRadius: 0, tension: 0.3 }}
    ]
  }},
  options: {{
    responsive: true,
    interaction: {{ mode: 'index', intersect: false }},
    scales: {{
      x: {{ display: false }},
      y: {{ min: -0.2, max: 1.1, grid: {{ color: '#1e293b' }},
            ticks: {{ color: '#94a3b8' }} }}
    }},
    plugins: {{
      legend: {{ labels: {{ color: '#e2e8f0', usePointStyle: true, pointStyle: 'line' }} }}
    }}
  }}
}});
</script>
</body>
</html>"""


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Phase 2 — Dashboard generator")
    parser.add_argument("input_dir", type=str)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_path = Path(args.output) if args.output else input_dir / "dashboard.html"

    session_files = sorted(input_dir.glob("session_*.json"))
    sessions = []
    for f in session_files:
        with open(f) as fh:
            sessions.append(json.load(fh))

    print(f"Loaded {len(sessions)} sessions from {input_dir}")
    generate_dashboard(sessions, output_path)


if __name__ == "__main__":
    main()
