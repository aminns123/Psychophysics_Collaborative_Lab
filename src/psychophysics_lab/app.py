from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Sequence

from .data.workspace import preferred_data_root, remember_data_root
from .experiments.registry import list_experiments
from .paths import default_data_root, find_repo_root, resolve_data_root


def _diagnose(repo_root: Path) -> int:
    fallback_data_root = default_data_root(repo_root)
    initial_data_root = preferred_data_root(repo_root, fallback_data_root)
    try:
        initial_data_root = resolve_data_root(initial_data_root, repo_root)
    except ValueError:
        initial_data_root = fallback_data_root.resolve()
    print("PsyCoLab — Psychophysics Collaborative Lab")
    print(f"Repository: {repo_root}")
    print(f"Data root:   {initial_data_root}")
    for package in ("numpy", "pyglet", "textual"):
        try:
            found = version(package)
        except PackageNotFoundError:
            found = "NOT INSTALLED"
        print(f"{package:8s}: {found}")
    print("Experiments:")
    for spec in list_experiments():
        print(f"  - {spec.id}: {spec.display_name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="psycolab",
        description="PsyCoLab — Psychophysics Collaborative Lab",
    )
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Print environment/repository information without opening the TUI.",
    )
    parser.add_argument(
        "--list-experiments",
        action="store_true",
        help="List explicitly registered experiments and exit.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = find_repo_root()

    if args.diagnose:
        return _diagnose(repo_root)

    if args.list_experiments:
        for spec in list_experiments():
            print(f"{spec.id}\t{spec.display_name}")
        return 0

    fallback_data_root = default_data_root(repo_root)
    initial_data_root = preferred_data_root(repo_root, fallback_data_root)
    try:
        initial_data_root = resolve_data_root(initial_data_root, repo_root)
    except ValueError:
        initial_data_root = resolve_data_root(fallback_data_root, repo_root)
    initial_data_root.mkdir(parents=True, exist_ok=True)

    # Deliberately import Textual only for the interactive path.
    from .ui.setup import run_setup_tui

    request = run_setup_tui(repo_root=repo_root, data_root=initial_data_root)
    if request is None:
        return 0

    selected_data_root = Path(request.data_root).expanduser().resolve() if request.data_root else initial_data_root
    try:
        remember_data_root(repo_root, selected_data_root)
    except OSError as exc:
        print(f"Warning: could not remember the selected data folder locally: {exc}")

    # Pyglet/OpenGL imports happen only inside run_request, after Textual exits.
    from .core.runner import run_request

    artifacts = run_request(request, repo_root=repo_root, data_root=selected_data_root)

    print("\nPsyCoLab session finished.")
    print(f"Run folder:      {artifacts.run_directory}")
    print(f"Canonical trials:{artifacts.trial_log_file}")
    print(f"Legacy response: {artifacts.response_file}")
    print(f"Session manifest:{artifacts.manifest_file}")
    return 0
