from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import traceback
from typing import Any, Sequence

from .data.workspace import preferred_data_root, remember_data_root
from .diagnostics import start_fatal_fault_capture, write_crash_report
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


def _main(
    argv: Sequence[str] | None = None,
    *,
    diagnostic_context: dict[str, Any] | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    repo_root = find_repo_root()
    if diagnostic_context is not None:
        diagnostic_context["repo_root"] = repo_root

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
    if diagnostic_context is not None:
        diagnostic_context["data_root"] = initial_data_root
        diagnostic_context["phase"] = "tui_setup"

    # Deliberately import Textual only for the interactive path.
    from .ui.setup import run_setup_tui

    request = run_setup_tui(repo_root=repo_root, data_root=initial_data_root)
    if request is None:
        return 0

    selected_data_root = (
        Path(request.data_root).expanduser().resolve()
        if request.data_root
        else initial_data_root
    )
    if diagnostic_context is not None:
        diagnostic_context["data_root"] = selected_data_root
        diagnostic_context["phase"] = "post_tui_experiment_launch"

    try:
        remember_data_root(repo_root, selected_data_root)
    except OSError as exc:
        print(f"Warning: could not remember the selected data folder locally: {exc}")

    # Pyglet/OpenGL imports happen only inside run_request, after Textual exits.
    from .core.runner import run_request

    artifacts = run_request(request, repo_root=repo_root, data_root=selected_data_root)

    if diagnostic_context is not None:
        diagnostic_context["phase"] = "finished"
    print("\nPsyCoLab session finished.")
    print(f"Run folder:       {artifacts.run_directory}")
    print(f"Canonical trials: {artifacts.trial_log_file}")
    print(f"Legacy response:  {artifacts.response_file}")
    print(f"Session manifest: {artifacts.manifest_file}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run PsyCoLab with both Python- and native-failure diagnostics.

    Ordinary exceptions are printed and written to a timestamped crash report.
    A best-effort ``faulthandler`` trace also remains if Python terminates because
    of a lower-level/native fault. The batch launcher receives a non-zero code so
    the terminal pauses instead of disappearing immediately.
    """
    context: dict[str, Any] = {
        "repo_root": None,
        "data_root": None,
        "phase": "application_startup",
    }
    fatal_capture = start_fatal_fault_capture()
    exit_code: int | None = None

    try:
        exit_code = _main(argv, diagnostic_context=context)
        return exit_code
    except KeyboardInterrupt:
        exit_code = 130
        print("\nPsyCoLab cancelled by user.")
        return exit_code
    except Exception as exc:
        exit_code = 1
        print("\nPsyCoLab encountered an error and stopped before continuing.")
        traceback.print_exception(type(exc), exc, exc.__traceback__)
        report = write_crash_report(
            exc,
            repo_root=context.get("repo_root"),
            data_root=context.get("data_root"),
            phase=str(context.get("phase") or "unknown"),
        )
        if report is not None:
            print(f"\nCrash report saved to: {report}")
        else:
            print("\nPsyCoLab could not write a crash-report file.")
        print("The Windows launcher will pause so this message remains visible.")
        return exit_code
    finally:
        if fatal_capture is not None:
            fatal_capture.close(clean_exit=exit_code in {0, 130})
