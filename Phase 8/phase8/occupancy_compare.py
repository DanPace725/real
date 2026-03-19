from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable

from occupancy_baseline import get_preset, run_experiment

from .occupancy import build_occupancy_episodes_from_preset
from .occupancy_execution import (
    DEFAULT_CYCLES_PER_TIMESTEP,
    DEFAULT_DRAIN_CYCLES,
    DEFAULT_FEEDBACK_AMOUNT,
    build_occupancy_execution_system,
    run_occupancy_episode,
    summarize_occupancy_results,
)


@dataclass(frozen=True)
class OccupancyComparisonConfig:
    preset_name: str = 'synth_v1_default'
    selector_seed: int = 0
    cycles_per_timestep: int = DEFAULT_CYCLES_PER_TIMESTEP
    drain_cycles: int = DEFAULT_DRAIN_CYCLES
    feedback_amount: float = DEFAULT_FEEDBACK_AMOUNT
    max_train_episodes: int | None = None
    max_eval_episodes: int | None = None


@dataclass(frozen=True)
class OccupancyComparisonResult:
    config: OccupancyComparisonConfig
    split_index: int
    baseline_result: Dict[str, Any]
    baseline_metrics: Dict[str, float]
    real_train_summary: Dict[str, float]
    real_eval_summary: Dict[str, float]
    eval_minus_baseline: Dict[str, float]
    train_episodes: int
    eval_episodes: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            'config': asdict(self.config),
            'split_index': self.split_index,
            'baseline_result': dict(self.baseline_result),
            'baseline_metrics': dict(self.baseline_metrics),
            'real_train_summary': dict(self.real_train_summary),
            'real_eval_summary': dict(self.real_eval_summary),
            'eval_minus_baseline': dict(self.eval_minus_baseline),
            'train_episodes': self.train_episodes,
            'eval_episodes': self.eval_episodes,
        }


@dataclass(frozen=True)
class OccupancyComparisonSeriesResult:
    preset_name: str
    selector_seeds: tuple[int, ...]
    baseline_result: Dict[str, Any]
    runs: tuple[OccupancyComparisonResult, ...]
    aggregate_train_summary: Dict[str, float]
    aggregate_eval_summary: Dict[str, float]
    aggregate_eval_minus_baseline: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'preset_name': self.preset_name,
            'selector_seeds': list(self.selector_seeds),
            'baseline_result': dict(self.baseline_result),
            'runs': [run.to_dict() for run in self.runs],
            'aggregate_train_summary': dict(self.aggregate_train_summary),
            'aggregate_eval_summary': dict(self.aggregate_eval_summary),
            'aggregate_eval_minus_baseline': dict(self.aggregate_eval_minus_baseline),
        }



def _split_index(example_count: int, train_fraction: float) -> int:
    if example_count < 2:
        raise ValueError('Need at least 2 examples to create a train/test split')
    proposed = int(example_count * max(0.0, min(1.0, train_fraction)))
    return max(1, min(example_count - 1, proposed))



def _subset_episodes(
    config: OccupancyComparisonConfig,
    *,
    baseline_result: Dict[str, Any] | None = None,
) -> tuple[int, list[Any], list[Any], Dict[str, Any]]:
    preset = get_preset(config.preset_name)
    baseline = dict(baseline_result) if baseline_result is not None else run_experiment(preset.config).to_dict()

    episodes = build_occupancy_episodes_from_preset(config.preset_name)
    split_index = _split_index(len(episodes), preset.config.train_fraction)
    train_episodes = list(episodes[:split_index])
    eval_episodes = list(episodes[split_index:])
    if config.max_train_episodes is not None:
        train_episodes = train_episodes[: config.max_train_episodes]
    if config.max_eval_episodes is not None:
        eval_episodes = eval_episodes[: config.max_eval_episodes]
    return split_index, train_episodes, eval_episodes, baseline



def _metric_deltas(real_summary: Dict[str, float], baseline_metrics: Dict[str, float]) -> Dict[str, float]:
    deltas: Dict[str, float] = {}
    for key, baseline_value in baseline_metrics.items():
        if key in real_summary:
            deltas[key] = real_summary[key] - float(baseline_value)
    return deltas



def _mean_summary(summaries: Iterable[Dict[str, float]]) -> Dict[str, float]:
    summary_list = list(summaries)
    if not summary_list:
        return {}
    keys = sorted({key for summary in summary_list for key in summary})
    return {
        key: mean(float(summary.get(key, 0.0)) for summary in summary_list)
        for key in keys
    }



def compare_occupancy_baseline_and_real(
    config: OccupancyComparisonConfig | None = None,
    *,
    baseline_result: Dict[str, Any] | None = None,
) -> OccupancyComparisonResult:
    config = config or OccupancyComparisonConfig()
    split_index, train_episodes, eval_episodes, baseline = _subset_episodes(config, baseline_result=baseline_result)

    system = build_occupancy_execution_system(selector_seed=config.selector_seed)
    train_results = [
        run_occupancy_episode(
            system,
            episode,
            cycles_per_timestep=config.cycles_per_timestep,
            drain_cycles=config.drain_cycles,
            feedback_amount=config.feedback_amount,
        )
        for episode in train_episodes
    ]
    eval_results = [
        run_occupancy_episode(
            system,
            episode,
            cycles_per_timestep=config.cycles_per_timestep,
            drain_cycles=config.drain_cycles,
            feedback_amount=0.0,
        )
        for episode in eval_episodes
    ]

    baseline_metrics = {
        key: float(value)
        for key, value in baseline.get('metrics', {}).items()
        if isinstance(value, (int, float))
    }
    real_train_summary = summarize_occupancy_results(train_results)
    real_eval_summary = summarize_occupancy_results(eval_results)

    return OccupancyComparisonResult(
        config=config,
        split_index=split_index,
        baseline_result=baseline,
        baseline_metrics=baseline_metrics,
        real_train_summary=real_train_summary,
        real_eval_summary=real_eval_summary,
        eval_minus_baseline=_metric_deltas(real_eval_summary, baseline_metrics),
        train_episodes=len(train_episodes),
        eval_episodes=len(eval_episodes),
    )



def compare_occupancy_baseline_and_real_series(
    *,
    selector_seeds: Iterable[int],
    config: OccupancyComparisonConfig | None = None,
) -> OccupancyComparisonSeriesResult:
    seed_tuple = tuple(selector_seeds)
    if not seed_tuple:
        raise ValueError('Need at least one selector seed for a comparison series')

    base_config = config or OccupancyComparisonConfig()
    _, _, _, baseline_result = _subset_episodes(base_config)
    runs = tuple(
        compare_occupancy_baseline_and_real(
            OccupancyComparisonConfig(
                preset_name=base_config.preset_name,
                selector_seed=seed,
                cycles_per_timestep=base_config.cycles_per_timestep,
                drain_cycles=base_config.drain_cycles,
                feedback_amount=base_config.feedback_amount,
                max_train_episodes=base_config.max_train_episodes,
                max_eval_episodes=base_config.max_eval_episodes,
            ),
            baseline_result=baseline_result,
        )
        for seed in seed_tuple
    )
    first = runs[0]
    return OccupancyComparisonSeriesResult(
        preset_name=base_config.preset_name,
        selector_seeds=seed_tuple,
        baseline_result=dict(baseline_result),
        runs=runs,
        aggregate_train_summary=_mean_summary(run.real_train_summary for run in runs),
        aggregate_eval_summary=_mean_summary(run.real_eval_summary for run in runs),
        aggregate_eval_minus_baseline=_mean_summary(run.eval_minus_baseline for run in runs),
    )



def save_occupancy_comparison(
    result: OccupancyComparisonResult | OccupancyComparisonSeriesResult,
    output_path: str | Path,
) -> Path:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True), encoding='utf-8')
    return destination
