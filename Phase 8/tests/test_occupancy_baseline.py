from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from occupancy_baseline import (
    BinaryMLP,
    ExperimentConfig,
    TrainingConfig,
    build_windowed_dataset,
    evaluate_binary_predictions,
    get_preset,
    list_presets,
    load_csv_dataset,
    run_experiment,
    save_result,
)
from occupancy_baseline.generate_dataset import generate_rows


class TestOccupancyBaselineDataset(unittest.TestCase):
    def test_windowed_dataset_flattens_recent_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "occupancy.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "temperature",
                        "humidity",
                        "light",
                        "co2",
                        "humidity_ratio",
                        "occupancy",
                    ],
                )
                writer.writeheader()
                for row in [
                    (20.0, 30.0, 100.0, 400.0, 0.1, 0),
                    (20.5, 31.0, 110.0, 420.0, 0.1, 0),
                    (21.0, 35.0, 250.0, 600.0, 0.2, 1),
                    (21.2, 36.0, 260.0, 650.0, 0.2, 1),
                ]:
                    writer.writerow(
                        {
                            "temperature": row[0],
                            "humidity": row[1],
                            "light": row[2],
                            "co2": row[3],
                            "humidity_ratio": row[4],
                            "occupancy": row[5],
                        }
                    )

            dataset = load_csv_dataset(csv_path)
            windowed = build_windowed_dataset(dataset, window_size=3, flatten=True)

            self.assertEqual(dataset.size, 4)
            self.assertEqual(windowed.size, 2)
            self.assertEqual(windowed.input_dim, 15)
            self.assertEqual(list(windowed.labels), [1, 1])

            structured = build_windowed_dataset(dataset, window_size=3, flatten=False)
            self.assertEqual(structured.size, 2)
            self.assertEqual(structured.input_dim, 15)
            self.assertEqual(len(structured.features[0]), 3)
            self.assertEqual(len(structured.features[0][0]), 5)

    def test_checked_in_synthetic_benchmark_loads(self) -> None:
        csv_path = ROOT / 'occupancy_baseline' / 'data' / 'occupancy_synth_v1.csv'
        dataset = load_csv_dataset(csv_path)
        self.assertEqual(dataset.size, 14 * 24 * 4)
        self.assertEqual(dataset.input_dim, 5)


class TestOccupancyBaselineModel(unittest.TestCase):
    def test_mlp_learns_simple_separable_pattern(self) -> None:
        features = [
            [0.0, 0.0],
            [0.1, 0.2],
            [0.9, 0.8],
            [1.0, 1.0],
        ]
        labels = [0, 0, 1, 1]

        model = BinaryMLP(
            input_dim=2,
            config=TrainingConfig(hidden_size=6, learning_rate=0.2, epochs=300, seed=1),
        )
        model.train(features, labels)
        predictions = model.predict(features)
        metrics = evaluate_binary_predictions(labels, predictions)

        self.assertGreaterEqual(metrics["accuracy"], 0.99)


class TestOccupancyExperiment(unittest.TestCase):
    def test_experiment_can_save_json_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "occupancy.csv"
            output_path = Path(tmpdir) / "result.json"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "temperature",
                        "humidity",
                        "light",
                        "co2",
                        "humidity_ratio",
                        "occupancy",
                    ],
                )
                writer.writeheader()
                for row in [
                    (20.0, 30.0, 80.0, 400.0, 0.1, 0),
                    (20.2, 30.5, 90.0, 420.0, 0.1, 0),
                    (21.0, 35.0, 250.0, 600.0, 0.2, 1),
                    (21.3, 35.5, 270.0, 640.0, 0.2, 1),
                    (20.1, 30.1, 85.0, 410.0, 0.1, 0),
                    (21.1, 35.1, 260.0, 620.0, 0.2, 1),
                ]:
                    writer.writerow(
                        {
                            "temperature": row[0],
                            "humidity": row[1],
                            "light": row[2],
                            "co2": row[3],
                            "humidity_ratio": row[4],
                            "occupancy": row[5],
                        }
                    )

            result = run_experiment(
                ExperimentConfig(
                    csv_path=str(csv_path),
                    window_size=3,
                    hidden_size=6,
                    learning_rate=0.1,
                    epochs=60,
                    seed=2,
                    train_fraction=0.75,
                )
            )
            save_result(result, output_path)
            payload = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(payload["config"]["window_size"], 3)
            self.assertEqual(payload["windowed_examples"], 4)
            self.assertEqual(payload["train_examples"], 3)
            self.assertEqual(payload["test_examples"], 1)
            self.assertIn("accuracy", payload["metrics"])

    def test_checked_in_synthetic_benchmark_runs_end_to_end(self) -> None:
        csv_path = ROOT / 'occupancy_baseline' / 'data' / 'occupancy_synth_v1.csv'
        result = run_experiment(
            ExperimentConfig(
                csv_path=str(csv_path),
                window_size=5,
                hidden_size=12,
                learning_rate=0.05,
                epochs=40,
                seed=0,
                train_fraction=0.8,
            )
        )
        self.assertEqual(result.dataset_rows, 14 * 24 * 4)
        self.assertGreater(result.windowed_examples, 100)
        self.assertGreaterEqual(result.metrics['accuracy'], 0.70)


class TestOccupancyGenerator(unittest.TestCase):
    def test_generator_is_deterministic_for_fixed_seed(self) -> None:
        first = generate_rows(seed=7, days=2)
        second = generate_rows(seed=7, days=2)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 2 * 24 * 4)


class TestOccupancyPresets(unittest.TestCase):
    def test_default_preset_points_at_checked_in_benchmark(self) -> None:
        preset = get_preset('synth_v1_default')
        self.assertTrue(preset.config.csv_path.endswith('occupancy_synth_v1.csv'))
        self.assertEqual(preset.config.window_size, 5)
        self.assertEqual(preset.config.epochs, 60)

    def test_list_presets_includes_default(self) -> None:
        names = [preset.name for preset in list_presets()]
        self.assertIn('synth_v1_default', names)


if __name__ == "__main__":
    unittest.main()
