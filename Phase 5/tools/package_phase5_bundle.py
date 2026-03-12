from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import zipfile

EXCLUDE_DIRS = {"__pycache__", ".ipynb_checkpoints", "dist"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}


def iter_files(root: Path):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in EXCLUDE_SUFFIXES:
            continue
        yield p


def add_tree(zf: zipfile.ZipFile, root: Path, arc_root: str, *, include_results: bool) -> list[str]:
    added: list[str] = []
    for file_path in iter_files(root):
        rel = file_path.relative_to(root)

        # Optionally skip large result artifacts from default bundle.
        if not include_results:
            rel_parts = set(rel.parts)
            if "results" in rel_parts:
                continue

        arcname = str(Path(arc_root) / rel)
        zf.write(file_path, arcname)
        added.append(arcname)
    return added


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Colab-friendly Phase 5 bundle zip")
    parser.add_argument(
        "--phase5-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Path to Phase 5 root",
    )
    parser.add_argument(
        "--phase4-root",
        type=Path,
        default=None,
        help="Path to Phase 4 root (default: sibling of Phase 5)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output zip path (default: <phase5>/dist/phase5_colab_bundle_<timestamp>.zip)",
    )
    parser.add_argument(
        "--include-results",
        action="store_true",
        help="Include experiments/*/results artifacts in bundle",
    )
    parser.add_argument(
        "--skip-phase4",
        action="store_true",
        help="Do not include Phase 4 files",
    )
    args = parser.parse_args()

    phase5_root = args.phase5_root.resolve()
    if not phase5_root.exists():
        raise FileNotFoundError(f"Phase 5 root not found: {phase5_root}")

    phase2_root = phase5_root.parent
    phase4_root = (args.phase4_root.resolve() if args.phase4_root else (phase2_root / "Phase 4").resolve())

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output.resolve() if args.output else (phase5_root / "dist" / f"phase5_colab_bundle_{timestamp}.zip")
    output.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "phase5_root": str(phase5_root),
        "phase4_root": str(phase4_root),
        "include_results": bool(args.include_results),
        "skip_phase4": bool(args.skip_phase4),
        "files": [],
    }

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        manifest["files"].extend(
            add_tree(
                zf,
                phase5_root,
                "Phase 5",
                include_results=args.include_results,
            )
        )

        if not args.skip_phase4:
            if not phase4_root.exists():
                raise FileNotFoundError(f"Phase 4 root not found: {phase4_root}")
            manifest["files"].extend(
                add_tree(
                    zf,
                    phase4_root,
                    "Phase 4",
                    include_results=args.include_results,
                )
            )

        zf.writestr("bundle_manifest.json", json.dumps(manifest, indent=2))

    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"Created bundle: {output}")
    print(f"Files: {len(manifest['files'])}")
    print(f"Size: {size_mb:.2f} MB")


if __name__ == "__main__":
    main()
