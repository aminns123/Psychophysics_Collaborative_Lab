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
    from .config.local import config_root
    print(f"Local config: {config_root(repo_root, initial_data_root)}")
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


def _print_run_summary(artifacts: Any) -> None:
    """Print a clear scientific end state after run finalisation has completed."""
    status = str(getattr(artifacts, "status", "returned"))
    accepted = int(getattr(artifacts, "accepted_trials", 0))
    completed = tuple(getattr(artifacts, "completed_staircase_ids", ()))
    unfinished = tuple(getattr(artifacts, "unfinished_staircase_ids", ()))

    print("\n" + "=" * 60)
    if status == "completed":
        print("PsyCoLab experiment completed successfully.")
        print("All adaptive staircases reached their termination criteria.")
    elif status == "max_trials_reached":
        print("PsyCoLab experiment ended at the response safety ceiling.")
        print("Not all adaptive staircases reached their termination criteria.")
    elif status == "aborted_by_user":
        print("PsyCoLab experiment ended by user (Escape).")
        print("All accepted responses up to the abort were preserved.")
    elif status == "aborted":
        print("PsyCoLab experiment ended before its completion criteria were met.")
    else:
        print(f"PsyCoLab experiment ended with status: {status}")

    print(f"Accepted responses: {accepted}")
    if completed or unfinished:
        print(f"Completed staircases: {list(completed)}")
        print(f"Unfinished staircases: {list(unfinished)}")
    if status == "error":
        print("Acquisition failed. Inspect the manifest and surviving trial records.")
    else:
        print("Run records finalised; physical stimulus/timing validation remains separate.")
    print(f"Run folder:       {artifacts.run_directory}")
    print(f"Canonical trials: {artifacts.trial_log_file}")
    readable = artifacts.run_directory / "trials_readable.txt"
    if readable.exists():
        print(f"Readable trials:  {readable}")
    print(f"Session manifest: {artifacts.manifest_file}")
    print("=" * 60)


def _print_geometry_summary(artifacts: Any) -> None:
    print("\n" + "=" * 60)
    print("PsyCoLab display geometry check finished.")
    print(f"Fullscreen resolution: {artifacts.resolution_px[0]} x {artifacts.resolution_px[1]} px")
    print(f"Intended ruler length: {artifacts.intended_length_mm:.3f} mm")
    print(f"Realised pixel-rounded length: {artifacts.realised_length_mm:.3f} mm")
    print(f"Realised visual angle: {artifacts.realised_visual_angle_deg:.5f} deg")
    print(f"Diagnostic report: {artifacts.report_file}")
    print("Return to Calibrate to inspect stage progress; ruler tests accept a physical measurement. Software completion never certifies the display.")
    print("=" * 60)


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
    parser.add_argument("--scaffold", metavar="NAME", help="Create stimulus and experiment contributor templates; never overwrites files.")
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

    if args.scaffold:
        from .scaffold import scaffold
        for path in scaffold(repo_root, args.scaffold):
            print(path)
        print("Next: implement the procedure and add its module and stimulus module to src/psychophysics_lab/contributions.py. See docs/RESEARCHER_QUICKSTART.md.")
        return 0

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

    # The hub may close for fullscreen display checks or headless scenarios.
    # Real participants and virtual observers must never execute inside the
    # active Textual event loop.
    simulation_summary: str | None = None
    geometry_summary: str | None = None
    recoverable_failures = 0
    while True:
        if diagnostic_context is not None:
            diagnostic_context["data_root"] = initial_data_root
            diagnostic_context["phase"] = "tui_setup"

        from .ui.setup import run_setup_tui

        launch_options = {"simulation_summary": simulation_summary}
        if geometry_summary is not None:
            launch_options["geometry_summary"] = geometry_summary
        action = run_setup_tui(repo_root=repo_root, data_root=initial_data_root,
                               **launch_options)
        simulation_summary = None
        geometry_summary = None
        if action is None:
            if recoverable_failures:
                print(f"PsyCoLab exited after recovery from {recoverable_failures} failed operation(s); those attempts did not complete successfully.")
            else:
                print("PsyCoLab exited normally.")
            return 0

        from .core.simulation_request import SimulationLaunchRequest
        if isinstance(action, SimulationLaunchRequest):
            selected_data_root = resolve_data_root(action.data_root, repo_root)
            if diagnostic_context is not None:
                diagnostic_context["data_root"] = selected_data_root
                diagnostic_context["phase"] = "synthetic_simulation"
            # Do NOT update the last human setup or machine monitor preferences.
            # Scenario execution uses the real pipeline with a reserved
            # synthetic participant, after the Textual window has closed.
            from simulations.scenarios import run_scenario
            from simulations.progress import simulation_heartbeat
            try:
                with simulation_heartbeat(
                    f"Testing {action.experiment_id} / {action.scenario_id} "
                    f"({len(action.seeds)} virtual run(s))"
                ):
                    result = run_scenario(
                        experiment_id=action.experiment_id,
                        scenario_id=action.scenario_id,
                        data_root=selected_data_root,
                        repo_root=repo_root,
                        seeds=action.seeds,
                        observer_parameters=action.observer_parameters,
                        experiment_values=action.experiment_values,
                        monitor_profile_id=action.monitor_profile_id,
                        monitor_profile_hash=action.monitor_profile_hash,
                    )
            except Exception as exc:
                recoverable_failures += 1
                # Full trace is preserved once in the diagnostic file.
                print(f"Operation did not complete: {exc}")
                report = write_crash_report(
                    exc, repo_root=repo_root, data_root=selected_data_root,
                    phase="synthetic_simulation",
                )
                print(f"Diagnostic report: {report}" if report else "No diagnostic report could be written.")
                simulation_summary = (
                    f"[red]Simulation failed: {exc}[/red]\n"
                    + (f"Crash report: {report}" if report else "No crash report could be written.")
                )
                print("Synthetic simulation failed; returning to the PsyCoLab TUI.")
            else:
                status = "[green]PASSED[/green]" if result.passed else "[red]FAILED CHECKS[/red]"
                simulation_summary = (
                    f"Latest simulation: {status}\n"
                    f"Scenario: {result.experiment_id} / {result.scenario_id}\n"
                    f"Synthetic runs: {len(result.runs)}\n"
                    f"Report: {result.report_file}"
                )
                print(f"Simulation {'PASSED' if result.passed else 'FAILED CHECKS'}: {result.report_file}")
            initial_data_root = selected_data_root
            continue

        from .core.geometry_check import GeometryCheckRequest
        from .core.luminance_session import LuminanceSessionRequest

        if isinstance(action, LuminanceSessionRequest):
            selected_data_root = resolve_data_root(
                Path(action.data_root).expanduser().resolve()
                if action.data_root else initial_data_root, repo_root
            )
            if diagnostic_context is not None:
                diagnostic_context["data_root"] = selected_data_root
                diagnostic_context["phase"] = "interactive_luminance_measurement"
            from .core.luminance_session import run_interactive_luminance
            try:
                artifacts = run_interactive_luminance(
                    action, repo_root=repo_root, data_root=selected_data_root
                )
            except Exception as exc:
                # Partial observations already entered are retained locally
                # even when the GPU/window closes unexpectedly.
                recoverable_failures += 1
                # Full trace is preserved once in the diagnostic file.
                print(f"Operation did not complete: {exc}")
                report = write_crash_report(
                    exc, repo_root=repo_root, data_root=selected_data_root,
                    phase="interactive_luminance_measurement"
                )
                print(f"Diagnostic report: {report}" if report else "No diagnostic report could be written.")
                geometry_summary = (
                    f"[red]Luminance session interrupted: {exc}[/red]\n"
                    + (f"Diagnostic error report: {report}" if report
                       else "Previously saved measurements remain in calibration_sessions/.")
                )
            else:
                geometry_summary = (
                    f"[{'green' if artifacts.status == 'completed' else 'yellow'}]Interactive luminance session {artifacts.status}.[/]\n"
                    f"Recorded individual measurements: {artifacts.readings_count} "
                    f"at {artifacts.measured_commands} digital commands.\n"
                    f"Raw readings: {artifacts.session_file}\n"
                    f"Editable mean JSON: {artifacts.pilot_json_file}\n"
                    "Open pilot/test JSON, enter real photometer method and notes, "
                    "and import into the monitor profile when ready. "
                    "The results remain UNVERIFIED."
                )
                if artifacts.export_warning:
                    geometry_summary += f"\n[yellow]{artifacts.export_warning}[/yellow]"
                print(f"Luminance measurements: {artifacts.session_file}")
                print(f"Editable pilot JSON: {artifacts.pilot_json_file}")
            initial_data_root = selected_data_root
            continue

        if isinstance(action, GeometryCheckRequest):
            selected_data_root = (
                Path(action.data_root).expanduser().resolve()
                if action.data_root
                else initial_data_root
            )
            selected_data_root = resolve_data_root(selected_data_root, repo_root)
            try:
                remember_data_root(repo_root, selected_data_root)
            except OSError as exc:
                print(f"Warning: could not remember the selected data folder locally: {exc}")

            if diagnostic_context is not None:
                diagnostic_context["data_root"] = selected_data_root
                diagnostic_context["phase"] = "display_geometry_check"

            from .core.geometry_check import run_geometry_check

            try:
                artifacts = run_geometry_check(
                    action, repo_root=repo_root, data_root=selected_data_root,
                )
            except Exception as exc:
                # Display drivers, monitor bindings or actual fullscreen modes
                # can change between preview and launch. These are recoverable
                # diagnostic failures, not reasons to terminate the launcher.
                recoverable_failures += 1
                # Full trace is preserved once in the diagnostic file.
                print(f"Operation did not complete: {exc}")
                report = write_crash_report(
                    exc, repo_root=repo_root, data_root=selected_data_root,
                    phase="display_geometry_check",
                )
                print(f"Diagnostic report: {report}" if report else "No diagnostic report could be written.")
                geometry_summary = (
                    f"[red]Fullscreen calibration did not start or complete: {exc}[/red]\n"
                    + (f"Diagnostic report: {report}" if report
                       else "No diagnostic log was written.")
                )
                print("Fullscreen calibration failed; returning to Calibrate.")
            else:
                _print_geometry_summary(artifacts)
                geometry_summary = (
                    f"[green]Fullscreen calibration finished.[/green]\n"
                    f"Report: {artifacts.report_file}\n"
                    "Measure the displayed ruler and record its length in Calibrate."
                )
            initial_data_root = selected_data_root
            continue

        selected_data_root = (
            Path(action.data_root).expanduser().resolve()
            if action.data_root
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

        artifacts = run_request(action, repo_root=repo_root, data_root=selected_data_root)

        if diagnostic_context is not None:
            diagnostic_context["phase"] = "finished"
        _print_run_summary(artifacts)
        return 1 if artifacts.status == "error" else 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run PsyCoLab with both Python- and native-failure diagnostics."""
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
