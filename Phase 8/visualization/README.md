# Phase 8: Substrate Visualization

This folder contains a simple, web-based visualization tool to observe the Phase 8 "ecology of computational actors" in action without modifying any underlying core mechanics.

## Architecture

The visualization is split into two parts:

1. **`dump_trace.py`**: A Python script that spins up a `NativeSubstrateSystem`, injects packets according to a predefined scenario workload (e.g. `branch_pressure`), and runs the `run_global_cycle()` loop. At each cycle, it extracts:
   - The graph topology (nodes, positions, adjacency)
   - Node ATP levels (Metabolic boundaries)
   - Packet flows (Action transformation)
   - ATP feedback pulses
   It outputs all this data to `trace.json`.

2. **`index.html`**: A standalone, premium web application built with HTML, CSS, and Canvas. It provides a file uploader to load `trace.json` securely from your local machine and visualizes the network dynamically.

## Usage

1. Open a terminal in this directory.
2. Run the trace generator:
   ```bash
   python dump_trace.py --scenario branch_pressure --cycles 20
   ```
   This will generate a `trace.json` file in the same directory.
3. Open `index.html` in your favorite modern web browser (Chrome, Edge, Firefox, Safari).
   - *Note: Since everything is contained in one file, no web server is needed. Double-click or drag-and-drop the file into your browser.*
4. Click **"Load Trace"** and select the generated `trace.json` file.
5. Use the playback controls at the bottom to play, pause, or scrub through the simulation cycles!

## Visual Mapping

* **Nodes**: Dark circles representing Active Agents. The green "meter" around the edge represents the current ATP level (Primitive 1 & Primitive 2).
* **Edges**: The structural connections forming the substrate. Packets travel along these lines.
* **Flows (Glow)**: Packets are rendered as glowing dots moving through the network. Odd contexts (`1`) glow purple; Even contexts (`0`) glow gold.
* **Feedback (Bright Blue Line)**: When an agent produces a coherent outcome, a feedback pulse travels backward through the graph, strengthening the edges and depositing ATP. This illustrates the consolidation of the Slow Layer Memory Substrate (Primitive 6).
* **Death (Red)**: If a node runs out of ATP entirely, its border flashes red.
