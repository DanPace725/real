# REAL Integration Summary (Phase 6)

This document outlines the integration of the Relationally Embedded Allostatic Learning (REAL) algorithm into the Emergence Engine (EE), and the new console commands added to support debugging, telemetry logging, and A/B testing.

## Summary of Integration

### 1. JavaScript Implemention (`real_layer.js`)
* **Core Algorithm Ported:** The original Python-based REAL core (from Phase 4) was rewritten completely in native JavaScript. To keep integration simple to manage and performant, we dropped the Pyodide dependency.
* **Coherence Scorer:** Calculates four core dimensions `[vitality, contextualFit, continuity, accountability]` using EE observations (such as `chi`, `resVisible`, `frustration`, velocity `vx,vy`, and `trailMean`).
    * **Vitality Fix:** Adjusted the chi normalized value to scale appropriately against `CHI_MAX_EXPECTED = 6.0` (as bundle chi runs 40-80, resulting in `obs.chi` values of 2-4). Vitality peaks smoothly and falls to 0 during true starvation.
    * **Contextual Fit Fix:** Uses environmental `resVisible` signals mixed with biological `frustration` instead of max-entropy density spreads, allowing the fit score to meaningfully fluctuate.
    * **Accountability Fix:** A tighter normalizer allows the agent to correctly measure tiny improvements in trail density immediately following exploration.
* **CFA Mode Selector:** Selects between three modes to influence behavior:
    * **Constraints (C):** Triggers during severe energy crisis (`chi` < 15% Max) or Global Closure Operator (GCO) failure. Directs resources toward strong trail following and conservation.
    * **Fluctuation (F):** Triggers during healthy, stable running (`chi` > 40%). Amplifies exploration noise, dampens trail lock-in.
    * **Attention (A):** Focuses precisely on a single bottleneck dimension (e.g. low accountability boosts exploration to drop trails; low continuity stabilizes velocity). Has an 8-tick cooldown.

### 2. Tilt-Coupling in Emergence Engine (`bundle.js`)
* **Agent 1 Only:** REAL is instantiated *only* on the agent with `id === 1`. This isolates testing while keeping the overall simulation running standard adaptive heuristics.
* **Tick Insertion:** `realLayer.tick(obs)` runs immediately after signal context updates and before steering logic.
* **Bias Multipliers:** Instead of overwriting EE's movement vectors, REAL outputs multipliers `[exploreBias, conserveBias, followBias]` that scale the EE's existing heuristics:
    * `this.explorationNoise` is scaled by `exploreBias`.
    * `this.resourceAttractionStrength` is scaled by `conserveBias`.
    * `this.trailFollowingNear` and `this.trailFollowingFar` are scaled by `followBias`.

### 3. State Export and Telemetry (`real_logger.js`)
* **Ring Buffer Log:** Maintains the last 64 ticks of coherence data, chi states, CFA mode selections, and bias outputs in memory for Agent 1.
* **Wrapper Utilities:** Connects `real_layer.js` data with EE's existing export utilities (`stateIO.js` and `metricsTracker.js`).

## Console Commands for Analysis

All REAL exports have been wired into the global `window` object in `app.js` and can be called directly from the browser's developer console while the simulator is running.

### `downloadREALLog()`
* **What it does:** Extracts Agent 1's 64-tick episodic REAL log and downloads it as a `.json` file.
* **Contents:** Current tick, CFA modes, Coherence scores, GCO status, raw `chi` inputs, and active Bias multipliers per tick.
* **Use case:** Checking if REAL is interpreting the environment correctly (e.g., verifying `vitality` isn't stuck at 0 or observing C-mode activation under resource stress).

### `downloadABSnapshot()`
* **What it does:** Takes a complete snapshot of the world state, overall metrics, and the REAL log, bundling them into a single `.json` archive.
* **Contents:**
    1. Agent list with `id`, `chi`, `energy`, `alive`, `position`, etc.
    2. Simulated total ticks.
    3. Aggregate simulation metrics (via `metricsTracker.js`).
    4. The same REAL 64-tick log from `downloadREALLog()`.
* **Use case:** Full A/B testing analysis. Allows offline processing and plotting (e.g. comparing Agent 1's chi trajectory vs standard Agents 2-10).
