"""
REAL Dashboard — visualize agent developmental progress.

Reads session_history.json and episodic_log.json from the sandbox,
generates an interactive HTML dashboard, and opens it in the browser.

Usage:
    python dashboard.py
"""

import json
import os
import sys
import webbrowser
import tempfile
from pathlib import Path

SANDBOX = Path(os.environ.get("REAL_SANDBOX", Path.home() / ".real_sandbox"))
MEMORY = SANDBOX / "memory"

def load_sessions():
    path = MEMORY / "session_history.json"
    if not path.exists():
        print(f"No session history found at {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_log():
    path = MEMORY / "episodic_log.json"
    if not path.exists():
        return {"entries": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_self_model():
    path = MEMORY / "self_model.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_html(sessions, log, self_model):
    sessions_json = json.dumps(sessions)
    log_json = json.dumps(log)
    model_json = json.dumps(self_model)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>REAL Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Inter', sans-serif;
    background: #0a0e1a;
    color: #e0e6f0;
    min-height: 100vh;
    padding: 24px;
  }}

  h1 {{
    font-size: 28px;
    font-weight: 700;
    background: linear-gradient(135deg, #60a5fa, #a78bfa, #f472b6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
  }}

  .subtitle {{
    color: #64748b;
    font-size: 14px;
    margin-bottom: 28px;
  }}

  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
    gap: 20px;
    margin-bottom: 24px;
  }}

  .card {{
    background: linear-gradient(145deg, #111827, #1e293b);
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  }}

  .card h2 {{
    font-size: 14px;
    font-weight: 500;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 14px;
  }}

  .stat-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid #1e293b;
  }}

  .stat-row:last-child {{ border-bottom: none; }}

  .stat-label {{ color: #94a3b8; font-size: 13px; }}
  .stat-value {{ font-weight: 600; font-size: 15px; }}
  .stat-good {{ color: #34d399; }}
  .stat-warn {{ color: #fbbf24; }}
  .stat-bad {{ color: #f87171; }}

  .wide {{ grid-column: 1 / -1; }}

  .dim-bar {{
    display: flex;
    align-items: center;
    margin-bottom: 8px;
    gap: 10px;
  }}

  .dim-bar .label {{
    width: 120px;
    font-size: 12px;
    color: #94a3b8;
    text-align: right;
  }}

  .dim-bar .bar-bg {{
    flex: 1;
    height: 20px;
    background: #1e293b;
    border-radius: 4px;
    overflow: hidden;
    position: relative;
  }}

  .dim-bar .bar-fill {{
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s ease;
  }}

  .dim-bar .bar-value {{
    width: 50px;
    font-size: 13px;
    font-weight: 600;
    text-align: right;
  }}

  .threshold-line {{
    position: absolute;
    top: 0;
    bottom: 0;
    width: 2px;
    background: rgba(251, 191, 36, 0.6);
    z-index: 2;
  }}

  canvas {{ max-height: 280px; }}

  .gco-badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
  }}

  .gco-STABLE {{ background: #065f46; color: #34d399; }}
  .gco-PARTIAL {{ background: #713f12; color: #fbbf24; }}
  .gco-DEGRADED {{ background: #7f1d1d; color: #f87171; }}
  .gco-CRITICAL {{ background: #450a0a; color: #fca5a5; }}
</style>
</head>
<body>

<h1>REAL \u2014 Agent Dashboard</h1>
<div class="subtitle" id="meta"></div>

<div class="grid">
  <div class="card" id="overview-card">
    <h2>Overview</h2>
    <div id="overview"></div>
  </div>

  <div class="card">
    <h2>Latest Dimension Scores</h2>
    <div id="dimensions"></div>
  </div>

  <div class="card wide">
    <h2>Coherence Trend Across Sessions</h2>
    <canvas id="coherenceChart"></canvas>
  </div>

  <div class="card">
    <h2>GCO Distribution (Latest Session)</h2>
    <canvas id="gcoChart"></canvas>
  </div>

  <div class="card">
    <h2>Exploration vs Exploitation</h2>
    <canvas id="explorationChart"></canvas>
  </div>

  <div class="card wide">
    <h2>Action Distribution (Latest Session)</h2>
    <canvas id="actionChart"></canvas>
  </div>

  <div class="card">
    <h2>Tier Usage (Latest Session)</h2>
    <canvas id="tierChart"></canvas>
  </div>

  <div class="card" id="model-card">
    <h2>Agent Self-Model</h2>
    <div id="selfmodel"></div>
  </div>
</div>

<script>
const sessions = {sessions_json};
const log = {log_json};
const selfModel = {model_json};

const dimColors = {{
  continuity:      '#60a5fa',
  vitality:        '#34d399',
  contextual_fit:  '#a78bfa',
  differentiation: '#f472b6',
  accountability:  '#fbbf24',
  reflexivity:     '#fb923c',
}};

const tierColors = {{
  reflex:   '#60a5fa',
  regulate: '#34d399',
  explore:  '#a78bfa',
  build:    '#fbbf24',
  spawn:    '#f472b6',
}};

// Meta
const total = sessions.length;
const totalCycles = sessions.reduce((s, x) => s + x.total_cycles, 0);
document.getElementById('meta').textContent =
  total + ' sessions | ' + totalCycles + ' total cycles | Sandbox: ' + '{str(SANDBOX).replace(chr(92), "/")}';

// Overview
const latest = sessions[sessions.length - 1];
const first = sessions[0];
function statClass(v) {{ return v >= 0.75 ? 'stat-good' : v >= 0.55 ? 'stat-warn' : 'stat-bad'; }}

let overviewHTML = '';
const stats = [
  ['Sessions', total, ''],
  ['Total Cycles', totalCycles, ''],
  ['Latest Mean Coherence', latest.mean_coherence.toFixed(3), statClass(latest.mean_coherence)],
  ['Latest Final Coherence', latest.final_coherence.toFixed(3), statClass(latest.final_coherence)],
  ['Exploration Ratio', (latest.exploration_ratio * 100).toFixed(0) + '%', ''],
  ['Consolidations', latest.consolidation_count, ''],
  ['Compute Time', latest.total_compute_secs.toFixed(4) + 's', ''],
];
stats.forEach(([label, value, cls]) => {{
  overviewHTML += '<div class="stat-row"><span class="stat-label">' + label +
    '</span><span class="stat-value ' + cls + '">' + value + '</span></div>';
}});
document.getElementById('overview').innerHTML = overviewHTML;

// Dimensions - from latest log entries
const entries = log.entries || [];
let latestDims = {{}};
if (entries.length > 0) {{
  latestDims = entries[entries.length - 1].dimension_scores || {{}};
}}

let dimHTML = '';
const gcoThreshold = 0.65;
Object.entries(latestDims).forEach(([dim, score]) => {{
  const pct = (score * 100).toFixed(1);
  const color = dimColors[dim] || '#60a5fa';
  const thresholdLeft = (gcoThreshold * 100).toFixed(1);
  dimHTML += '<div class="dim-bar">' +
    '<span class="label">' + dim + '</span>' +
    '<div class="bar-bg">' +
    '<div class="bar-fill" style="width:' + pct + '%;background:' + color + '"></div>' +
    '<div class="threshold-line" style="left:' + thresholdLeft + '%"></div>' +
    '</div>' +
    '<span class="bar-value ' + statClass(score) + '">' + score.toFixed(3) + '</span>' +
    '</div>';
}});
document.getElementById('dimensions').innerHTML = dimHTML;

// Coherence trend chart
const ctx1 = document.getElementById('coherenceChart').getContext('2d');
new Chart(ctx1, {{
  type: 'line',
  data: {{
    labels: sessions.map((_, i) => 'S' + (i + 1)),
    datasets: [
      {{
        label: 'Mean Coherence',
        data: sessions.map(s => s.mean_coherence),
        borderColor: '#60a5fa',
        backgroundColor: 'rgba(96,165,250,0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 5,
      }},
      {{
        label: 'Final Coherence',
        data: sessions.map(s => s.final_coherence),
        borderColor: '#34d399',
        backgroundColor: 'rgba(52,211,153,0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 5,
      }},
      {{
        label: 'GCO Threshold',
        data: sessions.map(() => gcoThreshold),
        borderColor: 'rgba(251,191,36,0.4)',
        borderDash: [5, 5],
        pointRadius: 0,
        fill: false,
      }}
    ]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }},
    scales: {{
      x: {{ ticks: {{ color: '#64748b' }}, grid: {{ color: '#1e293b' }} }},
      y: {{ min: 0.4, max: 1.0, ticks: {{ color: '#64748b' }}, grid: {{ color: '#1e293b' }} }}
    }}
  }}
}});

// GCO chart
const ctx2 = document.getElementById('gcoChart').getContext('2d');
new Chart(ctx2, {{
  type: 'doughnut',
  data: {{
    labels: ['STABLE', 'PARTIAL', 'DEGRADED', 'CRITICAL'],
    datasets: [{{
      data: [
        latest.gco_stable_count,
        latest.gco_partial_count,
        latest.gco_degraded_count,
        latest.gco_critical_count
      ],
      backgroundColor: ['#065f46', '#713f12', '#7f1d1d', '#450a0a'],
      borderColor: ['#34d399', '#fbbf24', '#f87171', '#fca5a5'],
      borderWidth: 2,
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }}, position: 'bottom' }} }}
  }}
}});

// Exploration trend
const ctx3 = document.getElementById('explorationChart').getContext('2d');
new Chart(ctx3, {{
  type: 'bar',
  data: {{
    labels: sessions.map((_, i) => 'S' + (i + 1)),
    datasets: [{{
      label: 'Exploration %',
      data: sessions.map(s => (s.exploration_ratio * 100)),
      backgroundColor: 'rgba(167,139,250,0.6)',
      borderColor: '#a78bfa',
      borderWidth: 1,
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }},
    scales: {{
      x: {{ ticks: {{ color: '#64748b' }}, grid: {{ color: '#1e293b' }} }},
      y: {{ min: 0, max: 100, ticks: {{ color: '#64748b' }}, grid: {{ color: '#1e293b' }} }}
    }}
  }}
}});

// Action distribution
const ctx4 = document.getElementById('actionChart').getContext('2d');
const actionNames = Object.keys(latest.action_distribution).sort();
const actionColors = actionNames.map((_, i) => {{
  const hue = (i * 30) % 360;
  return 'hsl(' + hue + ', 70%, 60%)';
}});
new Chart(ctx4, {{
  type: 'bar',
  data: {{
    labels: actionNames,
    datasets: [{{
      label: 'Count',
      data: actionNames.map(a => latest.action_distribution[a]),
      backgroundColor: actionColors,
      borderWidth: 0,
      borderRadius: 4,
    }}]
  }},
  options: {{
    responsive: true,
    indexAxis: 'y',
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ color: '#64748b' }}, grid: {{ color: '#1e293b' }} }},
      y: {{ ticks: {{ color: '#94a3b8', font: {{ size: 11 }} }}, grid: {{ display: false }} }}
    }}
  }}
}});

// Tier chart
const ctx5 = document.getElementById('tierChart').getContext('2d');
const tierNames = Object.keys(latest.tier_distribution);
new Chart(ctx5, {{
  type: 'polarArea',
  data: {{
    labels: tierNames,
    datasets: [{{
      data: tierNames.map(t => latest.tier_distribution[t]),
      backgroundColor: tierNames.map(t => {{
        const c = tierColors[t] || '#888';
        return c + '88';
      }}),
      borderColor: tierNames.map(t => tierColors[t] || '#888'),
      borderWidth: 2,
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }}, position: 'bottom' }} }},
    scales: {{ r: {{ ticks: {{ color: '#64748b' }}, grid: {{ color: '#1e293b' }} }} }}
  }}
}});

// Self-model
let modelHTML = '';
if (selfModel && selfModel.entries_analyzed) {{
  const m = selfModel;
  const modelStats = [
    ['Entries Analyzed', m.entries_analyzed, ''],
    ['Dominant Action', m.dominant_action, ''],
    ['Action Diversity', (m.action_diversity * 100).toFixed(0) + '%', ''],
    ['Coherence Mean', m.coherence_mean.toFixed(4), statClass(m.coherence_mean)],
    ['Trajectory', (m.coherence_trajectory >= 0 ? '+' : '') + m.coherence_trajectory.toFixed(4),
      m.coherence_trajectory >= 0 ? 'stat-good' : 'stat-bad'],
    ['Strongest Dim', m.strongest_dimension, 'stat-good'],
    ['Weakest Dim', m.weakest_dimension, 'stat-bad'],
    ['GCO Proximity', (m.gco_proximate_fraction * 100).toFixed(0) + '%', ''],
  ];
  modelStats.forEach(([label, value, cls]) => {{
    modelHTML += '<div class="stat-row"><span class="stat-label">' + label +
      '</span><span class="stat-value ' + cls + '">' + value + '</span></div>';
  }});
}} else {{
  modelHTML = '<div class="stat-row"><span class="stat-label">No self-model yet (run introspect)</span></div>';
}}
document.getElementById('selfmodel').innerHTML = modelHTML;
</script>
</body>
</html>"""


def main():
    sessions = load_sessions()
    log = load_log()
    self_model = load_self_model()

    html = build_html(sessions, log, self_model)

    # Write to temp file and open in browser
    out_path = SANDBOX / "dashboard.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Dashboard written to: {out_path}")

    webbrowser.open(out_path.as_uri())
    print("Opened in browser.")


if __name__ == "__main__":
    main()
