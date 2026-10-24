from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from .extensions import source_path as component_source
import traceback
import sys
from typing import Any, Sequence

from .data.workspace import preferred_data_root, remember_data_root
from .diagnostics import start_fatal_fault_capture, write_crash_report
from psychophysics_lab.experiments._internal.registry import list_experiments
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
        print("All adaptive staircases reached their termination criteria." if completed or unfinished else "All planned responses were recorded.")
    elif status == "test_finished":
        print("Experiment test finished; the study's stopping rules were not reached.")
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
    # Portable, TUI-independent first lesson.
    parser.add_argument("--learn", action="store_true",
                        help="Read the standalone start-to-finish authoring tutorial.")
    # The separate USER_env environment is a plain terminal, not another TUI.
    parser.add_argument("--library-list", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--library-test", metavar="NAME", help=argparse.SUPPRESS)
    parser.add_argument("--library-ready", metavar="NAME", help=argparse.SUPPRESS)
    parser.add_argument("--list-stimuli", action="store_true", help="List visual stimuli from the one shared stimulus library.")
    parser.add_argument("--dev-list", action="store_true", help="List manually authored experiment/adaptive drafts.")
    parser.add_argument("--dev-stage", nargs=2, metavar=("KIND", "NAME"),
                        help="Register an existing experiment/adaptive Python file as Draft; never creates files.")
    parser.add_argument("--extensions-enable", type=Path, help="Trust an independent laboratory Python source folder.")
    parser.add_argument("--trust-extension-code", action="store_true", help="Acknowledge that external Python executes with your permissions.")
    parser.add_argument("--extensions-disable", action="store_true", help="Disable laboratory code; built-in components remain available.")
    parser.add_argument("--dev-preview", metavar="STIMULUS", help="Preview/test a stimulus without a physical display.")
    parser.add_argument("--dev-test", metavar="EXPERIMENT", help="Simulate and validate an experiment with a virtual observer.")
    parser.add_argument("--dev-values", type=Path, metavar="JSON", help="Experiment parameters JSON for --dev-test.")
    parser.add_argument("--dev-ready", nargs=2, metavar=("KIND", "NAME"), help="Publish a successfully tested scientific component.")
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Print environment/repository information without opening the TUI.",
    )
    parser.add_argument(
        "--list-experiments",
        action="store_true",
        help="List discovered Python experiments and exit.",
    )
    parser.add_argument("--preview-stimulus", metavar="ID", help="Render a registered stimulus preview without hardware.")
    parser.add_argument("--stimulus-json", type=Path)
    parser.add_argument("--preview-output", type=Path, default=Path("stimulus_preview.png"))
    return parser


def _main(
    argv: Sequence[str] | None = None,
    *,
    diagnostic_context: dict[str, Any] | None = None,
) -> int:
    # Windows redirected stdout can use cp1252 instead of the console's Unicode
    # writer. Preserve that encoding, replacing only unrepresentable characters.
    # StringIO/captured streams may not implement reconfigure.
    for stream in (sys.stdout, sys.stderr):
        if callable(getattr(stream, "reconfigure", None)):
            stream.reconfigure(errors="backslashreplace")
    args = build_parser().parse_args(argv)
    repo_root = find_repo_root()
    if args.extensions_enable or args.extensions_disable:
        from .extensions import configure
        if args.extensions_enable and args.extensions_disable:
            raise ValueError("Choose enable or disable, not both.")
        configure(repo_root, args.extensions_enable, trusted=args.trust_extension_code)
        print("Laboratory extensions configured. Restart PsyCoLab; software readiness is not hardware qualification.")
        return 0
    if diagnostic_context is not None:
        diagnostic_context["repo_root"] = repo_root

    if args.learn:
        # The Markdown guide is readable in terminals, editors and GitHub alike.
        print((repo_root / "docs" / "LEARN_PSYCOLAB.md").read_text(encoding="utf-8"))
        return 0

    if args.list_stimuli:
        from .stimuli.registry import list_stimuli
        for spec in list_stimuli():
            if spec.render is not None:
                print(f"{spec.id:28} {spec.display_name}")
        return 0

    if args.library_list:
        from psychophysics_lab.experiments._internal.library_builder import inventory
        for record in inventory(repo_root):
            print(f"{record['id']:32} {record['status']}")
        return 0

    if args.library_test:
        from psychophysics_lab.experiments._internal.library_builder import test_design
        path = test_design(repo_root, args.library_test)
        print(f"PASS: validated synthetic run saved to {path}")
        return 0

    if args.library_ready:
        from psychophysics_lab.experiments._internal.library_builder import mark_ready
        path = mark_ready(repo_root, args.library_ready)
        print(f"READY: {path} (software-tested only; normal human preflight still required).")
        print("Restart PsyCoLab to refresh its experiment catalogue.")
        return 0

    if args.dev_stage:
        from .authoring import stage
        kind, name = args.dev_stage
        if kind not in {"experiment", "adaptive"}:
            raise ValueError("Add stimuli directly to stimulus_library.py; --dev-stage supports experiment/adaptive only.")
        item = stage(repo_root, kind, name)
        print(f"DRAFT: {item.kind} {item.name}; run --dev-test NAME, then --dev-ready KIND NAME.")
        return 0

    if args.dev_list:
        from .experiments._internal.contributions import load_contributions
        load_contributions()
        from .authoring import inventory, fingerprint
        from . import extensions
        for row in extensions.inventory(repo_root):
            print(f"{row['kind']:10} {row['id']:28} {row['status']} (laboratory)")
        for item in inventory(repo_root):
            if item.kind == "stimulus":
                continue
            try:
                tested = bool(item.tested_fingerprint and item.tested_fingerprint == fingerprint(repo_root, item))
            except (OSError, ValueError):
                tested = False
            print(f"{item.kind:10} {item.name:28} {item.status:8} {'tested' if tested else 'test needed'}")
        return 0

    if args.dev_ready:
        from .authoring import publish
        kind, identity = args.dev_ready
        if kind not in {"stimulus", "experiment", "adaptive"}:
            raise ValueError("Valid kinds are stimulus, experiment, adaptive.")
        from . import extensions
        current = extensions.configured(repo_root)
        if current and identity.startswith(current[1] + "__"):
            extensions.publish(repo_root, kind, identity)
            print(f"READY: {kind} {identity} (software only). Restart PsyCoLab.")
            return 0
        item = publish(repo_root, kind, identity)
        print(f"READY: {item.kind} {item.name} (software-tested; NOT calibrated for human runs).")
        print("Restart the main PsyCoLab TUI to refresh the experiment catalogue.")
        return 0

    if args.dev_preview:
        from .development import execute_user_action
        return execute_user_action(repo_root, "preview", args.dev_preview, {})

    if args.dev_test:
        import json
        from .development import execute_user_action
        values = json.loads(args.dev_values.read_text(encoding="utf-8")) if args.dev_values else {}
        if not isinstance(values, dict):
            raise ValueError("Experiment settings JSON must be an object.")
        return execute_user_action(repo_root, "test", args.dev_test, values)

    if args.dev_values:
        raise ValueError("--dev-values requires --dev-test.")

    if args.preview_stimulus:
        from .stimuli.registry import get_stimulus
        from .config.stimulus_parameters import load_parameters, document_for
        from .core.presentation import preview_stimulus
        stimulus = get_stimulus(args.preview_stimulus)
        if args.stimulus_json:
            selected = load_parameters(args.stimulus_json, stimulus)
        elif stimulus.default_config:
            selected = load_parameters(component_source(repo_root, stimulus, stimulus.default_config), stimulus)
        else:
            selected = {"document": document_for(stimulus)}
        if args.preview_output.exists():
            raise ValueError("Preview output already exists; choose a new --preview-output.")
        preview_stimulus(stimulus.id, selected["document"]["parameters"], args.preview_output)
        print(args.preview_output)
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
    # Refresh resumes in a clean interpreter; scientific modules are never hot-reloaded.
    from .ui.refresh import read_refresh_state, RefreshRequest, launch_refreshed
    refresh_state = read_refresh_state(repo_root)
    if refresh_state is not None:
        initial_data_root = resolve_data_root(refresh_state["data_root"], repo_root)
    initial_data_root.mkdir(parents=True, exist_ok=True)

    # First normal launch supplies a usable sibling starter, much like the
    # default external data folder. Preparing files never trusts/loads them.
    # Existing or deliberately selected laboratory source is never modified.
    from .extensions import initialise_default
    try:
        initialise_default(repo_root, data_root=initial_data_root)
    except (OSError, ValueError) as exc:
        print(f"Laboratory starter not changed: {exc}. Built-in experiments remain available.")

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
        if refresh_state is not None:
            launch_options["refresh_state"] = refresh_state
            refresh_state = None
        if geometry_summary is not None:
            launch_options["geometry_summary"] = geometry_summary
        action = run_setup_tui(repo_root=repo_root, data_root=initial_data_root,
                               **launch_options)
        simulation_summary = None
        geometry_summary = None
        if isinstance(action, RefreshRequest):
            return launch_refreshed(action, repo_root)
        if action is None:
            if recoverable_failures:
                print(f"PsyCoLab exited after recovery from {recoverable_failures} failed operation(s); those attempts did not complete successfully.")
            else:
                print("PsyCoLab exited normally.")
            return 0

        from .core.presentation_testing import PresentationTestRequest,run_presentation_test
        if isinstance(action,PresentationTestRequest):
            from .config.local import config_root
            from .core.presentation_testing import MARKER
            test_root=config_root(repo_root).parent/'psycolab_presentation_tests'
            if diagnostic_context is not None:
                diagnostic_context['data_root']=test_root
                diagnostic_context['phase']='uncalibrated_presentation_test'
            try:
                artifacts=run_presentation_test(action,repo_root=repo_root)
            except Exception as exc:
                recoverable_failures+=1
                print(f'Uncalibrated presentation did not complete: {exc}')
                # Never allocate an unmarked folder merely to log a preflight
                # failure, and never write a presentation log into human data.
                report=write_crash_report(exc,repo_root=repo_root,data_root=test_root,phase='uncalibrated_presentation_test') if (test_root/MARKER).is_file() else None
                simulation_summary=f'[red]UNCALIBRATED presentation failed: {exc}[/red]\n'+(f'Test diagnostic: {report}' if report else 'No test run/report was created before preflight completed.')
            else:
                _print_run_summary(artifacts)
                if artifacts.status=='error': recoverable_failures+=1
                simulation_summary='UNCALIBRATED presentation status: '+artifacts.status+'. Output: '+str(artifacts.run_directory)+'. These are not human experimental records.'
            continue

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
                        stimulus_snapshots=action.stimulus_snapshots,
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

        from .core.precision_session import PrecisionSessionRequest
        if isinstance(action, PrecisionSessionRequest):
            selected_data_root = resolve_data_root(
                Path(action.data_root).expanduser().resolve() if action.data_root else initial_data_root, repo_root)
            from .core.precision_session import run_precision_session
            try:
                report_path = run_precision_session(action, repo_root=repo_root, data_root=selected_data_root)
            except (Exception, KeyboardInterrupt) as exc:
                recoverable_failures += 1
                report = write_crash_report(exc, repo_root=repo_root, data_root=selected_data_root, phase="output_precision")
                geometry_summary = f"Output precision test interrupted: {exc}. Saved readings remain local. Diagnostic: {report}"
            else:
                geometry_summary = f"Output precision evidence saved: {report_path}. Return to Output precision to review the readings and record your assessment. No automatic physical verification."
            print(geometry_summary)
            initial_data_root = selected_data_root
            continue

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
            except (Exception, KeyboardInterrupt) as exc:
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
                    "Open pilot/test JSON, then import at least two real intensity/cd/m² "
                    "pairs into the monitor profile and SAVE. Method, date and notes "
                    "are optional. Measurements remain physically UNVERIFIED until reviewed."
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
            except (Exception, KeyboardInterrupt) as exc:
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
                guidance = ("Measure the displayed ruler and record its physical length in Calibrate."
                            if action.test_kind in {"size", "position"} else
                            "Review the saved diagnostic; software presentation does not verify physical timing or contrast.")
                geometry_summary = (
                    f"[green]Fullscreen calibration finished.[/green]\n"
                    f"Report: {artifacts.report_file}\n"
                    + guidance
                )
                # Restore the saved calibration subsection. Only an explicit
                # Next/Return action advances or leaves this workflow.
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
            fatal_capture.close(clean_exit=exit_code in {0, 75, 130})  # 75: internal refresh handoff
