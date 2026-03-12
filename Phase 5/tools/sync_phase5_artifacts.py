from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil


def copy_tree_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Phase 5 experiment artifacts to a persistent location")
    parser.add_argument(
        "--phase5-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Phase 5 root",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        required=True,
        help="Destination root for synced artifacts",
    )
    parser.add_argument(
        "--zip",
        action="store_true",
        help="Also create a zip archive of the synced folder",
    )
    args = parser.parse_args()

    phase5_root = args.phase5_root.resolve()
    dest_root = args.dest.resolve()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sync_root = dest_root / f"phase5_artifacts_{stamp}"

    sources = [
        phase5_root / "experiments" / "m0" / "results",
        phase5_root / "experiments" / "m1" / "live",
    ]

    copied = []
    for src in sources:
        rel = src.relative_to(phase5_root)
        dst = sync_root / rel
        if copy_tree_if_exists(src, dst):
            copied.append((src, dst))

    if not copied:
        raise RuntimeError("No artifact directories were found to sync")

    print(f"Synced to: {sync_root}")
    for src, dst in copied:
        print(f"  {src} -> {dst}")

    if args.zip:
        archive_base = dest_root / f"phase5_artifacts_{stamp}"
        archive_path = shutil.make_archive(str(archive_base), "zip", root_dir=sync_root)
        print(f"Created archive: {archive_path}")


if __name__ == "__main__":
    main()
