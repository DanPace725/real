from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Sequence

from occupancy_baseline import build_windowed_dataset, get_preset, load_csv_dataset

from .models import SignalSpec

OCCUPANCY_TASK_ID = "occupancy_v1"
SENSOR_CHANNELS = (
    "temperature",
    "humidity",
    "light",
    "co2",
    "humidity_ratio",
)
SOURCE_NODE_IDS = tuple(f"src_{channel}" for channel in SENSOR_CHANNELS)
OCCUPIED_SINK_ID = "sink_occ"
EMPTY_SINK_ID = "sink_empty"
RECENT_CONTEXT_START = 3


@dataclass(frozen=True)
class OccupancyPacketSpec:
    source_id: str
    signal: SignalSpec
    timestep_index: int
    feature_name: str
    feature_value: float
    label: int


@dataclass(frozen=True)
class OccupancyEpisode:
    example_index: int
    label: int
    source_id: str
    target_sink_id: str
    timestep_packets: tuple[tuple[OccupancyPacketSpec, ...], ...]

    @property
    def packet_count(self) -> int:
        return sum(len(group) for group in self.timestep_packets)



def occupancy_bridge_topology() -> tuple[Dict[str, tuple[str, ...]], Dict[str, int], tuple[str, str]]:
    adjacency = {
        "src_temperature": ("thermal",),
        "src_humidity": ("thermal", "mixed_context"),
        "src_light": ("illumination", "mixed_context"),
        "src_co2": ("air_quality", "mixed_context"),
        "src_humidity_ratio": ("air_quality", "thermal"),
        "thermal": ("evidence_occ", "evidence_empty"),
        "illumination": ("evidence_occ", "evidence_empty"),
        "air_quality": ("evidence_occ", "evidence_empty"),
        "mixed_context": ("evidence_occ", "evidence_empty"),
        "evidence_occ": (OCCUPIED_SINK_ID,),
        "evidence_empty": (EMPTY_SINK_ID,),
        OCCUPIED_SINK_ID: (),
        EMPTY_SINK_ID: (),
    }
    positions = {
        "src_temperature": 0,
        "src_humidity": 0,
        "src_light": 0,
        "src_co2": 0,
        "src_humidity_ratio": 0,
        "thermal": 1,
        "illumination": 1,
        "air_quality": 1,
        "mixed_context": 1,
        "evidence_occ": 2,
        "evidence_empty": 2,
        OCCUPIED_SINK_ID: 3,
        EMPTY_SINK_ID: 3,
    }
    return adjacency, positions, (OCCUPIED_SINK_ID, EMPTY_SINK_ID)



def _bucket_one_hot(value: float) -> list[int]:
    if value < -1.0:
        return [1, 0, 0, 0]
    if value < 0.0:
        return [0, 1, 0, 0]
    if value < 1.0:
        return [0, 0, 1, 0]
    return [0, 0, 0, 1]



def _target_sink(label: int) -> str:
    return OCCUPIED_SINK_ID if int(label) == 1 else EMPTY_SINK_ID



def _signal_for_feature(
    feature_name: str,
    feature_value: float,
    *,
    timestep_index: int,
    label: int,
) -> SignalSpec:
    return SignalSpec(
        input_bits=_bucket_one_hot(feature_value),
        payload_bits=_bucket_one_hot(feature_value),
        context_bit=1 if timestep_index >= RECENT_CONTEXT_START else 0,
        task_id=OCCUPANCY_TASK_ID,
        target_bits=_bucket_one_hot(float(label)),
    )



def build_occupancy_episodes_from_preset(preset_name: str = "synth_v1_default") -> tuple[OccupancyEpisode, ...]:
    preset = get_preset(preset_name)
    dataset = load_csv_dataset(preset.config.csv_path, normalize=preset.config.normalize)
    windowed = build_windowed_dataset(dataset, window_size=preset.config.window_size, flatten=False)
    episodes = []
    feature_count = len(SENSOR_CHANNELS)
    for example_index, (window_rows, label) in enumerate(zip(windowed.features, windowed.labels)):
        timestep_packets = []
        for timestep_index, row in enumerate(window_rows):
            packets = []
            for feature_index, feature_name in enumerate(SENSOR_CHANNELS):
                feature_value = float(row[feature_index])
                packets.append(
                    OccupancyPacketSpec(
                        source_id=f"src_{feature_name}",
                        signal=_signal_for_feature(
                            feature_name,
                            feature_value,
                            timestep_index=timestep_index,
                            label=int(label),
                        ),
                        timestep_index=timestep_index,
                        feature_name=feature_name,
                        feature_value=feature_value,
                        label=int(label),
                    )
                )
            if len(packets) != feature_count:
                raise ValueError("Unexpected feature count while building occupancy packets")
            timestep_packets.append(tuple(packets))
        episodes.append(
            OccupancyEpisode(
                example_index=example_index,
                label=int(label),
                source_id="occupancy_episode_source",
                target_sink_id=_target_sink(int(label)),
                timestep_packets=tuple(timestep_packets),
            )
        )
    return tuple(episodes)



def occupancy_episode_summary(episodes: Iterable[OccupancyEpisode]) -> dict[str, int]:
    episode_list = list(episodes)
    return {
        "episodes": len(episode_list),
        "occupied_examples": sum(1 for episode in episode_list if episode.label == 1),
        "empty_examples": sum(1 for episode in episode_list if episode.label == 0),
        "packets": sum(episode.packet_count for episode in episode_list),
        "timesteps_per_episode": len(episode_list[0].timestep_packets) if episode_list else 0,
        "sensor_channels": len(SENSOR_CHANNELS),
    }
