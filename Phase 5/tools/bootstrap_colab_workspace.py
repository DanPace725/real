from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import zipfile


def maybe_mount_drive() -> None:
    try:
        from google.colab import drive  # type: ignore
    except Exception:
        print("google.colab not available; skipping drive mount")
        return

    drive.mount("/content/drive", force_remount=False)


def ensure_clean_dir(path: Path, clear: bool) -> None:
    if clear and path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def symlink_force(target: Path, link_path: Path) -> None:
    if link_path.exists() or link_path.is_symlink():
        if link_path.is_symlink() or link_path.is_file():
            link_path.unlink()
        else:
            shutil.rmtree(link_path)
    link_path.symlink_to(target, target_is_directory=True)


def pip_install(requirements: list[str]) -> None:
    cmd = ["python", "-m", "pip", "install", "-q", *requirements]
    print("Installing dependencies:", " ".join(requirements))
    subprocess.check_call(cmd)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap Phase 5 workspace in Colab")
    parser.add_argument("--bundle", type=Path, required=True, help="Path to phase5_colab_bundle_*.zip")
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=Path("/content/workspace/real_phase5"),
        help="Extraction workspace root",
    )
    parser.add_argument(
        "--mount-drive",
        action="store_true",
        help="Mount Google Drive at /content/drive before extraction",
    )
    parser.add_argument(
        "--clear-workspace",
        action="store_true",
        help="Delete existing workspace root before extraction",
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install runtime deps for Phase 5 notebooks",
    )
    parser.add_argument(
        "--link-content",
        action="store_true",
        help="Create /content/Phase 5 and /content/Phase 4 symlinks to extracted folders",
    )
    args = parser.parse_args()

    if args.mount_drive:
        maybe_mount_drive()

    bundle = args.bundle.resolve()
    if not bundle.exists():
        raise FileNotFoundError(f"Bundle not found: {bundle}")

    workspace_root = args.workspace_root.resolve()
    ensure_clean_dir(workspace_root, clear=args.clear_workspace)

    with zipfile.ZipFile(bundle, "r") as zf:
        zf.extractall(workspace_root)

    phase5_root = workspace_root / "Phase 5"
    phase4_root = workspace_root / "Phase 4"

    if not (phase5_root / "plan.md").exists():
        raise RuntimeError(f"Extracted workspace missing Phase 5/plan.md in {workspace_root}")

    if args.link_content:
        symlink_force(phase5_root, Path("/content/Phase 5"))
        if phase4_root.exists():
            symlink_force(phase4_root, Path("/content/Phase 4"))

    if args.install_deps:
        pip_install([
            "torch",
            "transformer-lens",
            "matplotlib",
            "numpy",
        ])

    print("\nBootstrap complete")
    print(f"Workspace root: {workspace_root}")
    print(f"Phase 5 root:   {phase5_root}")
    print(f"Phase 4 root:   {phase4_root if phase4_root.exists() else '(not included)'}")
    print("\nRecommended next step in notebook Cell 1:")
    print("  exec(open('/content/Phase 5/colab_setup.py').read())")


if __name__ == "__main__":
    main()
