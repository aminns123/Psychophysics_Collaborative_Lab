"""TUI-to-synthetic-pipeline integration without display or participant input."""
from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from textual.widgets import Button, Input, Select, Static, Collapsible

from psychophysics_lab.core.simulation_request import (
    SimulationLaunchRequest, parse_parameter, parse_seeds,
)
from psychophysics_lab.ui.setup import PsyCoLabSetupApp
from psychophysics_lab.ui.simulations import SimulationsScreen, SimulationReviewScreen, AdaptiveAlgorithmScreen

ROOT = Path(__file__).resolve().parents[1]


def test_typed_virtual_launch_rejects_invalid_or_ambiguous_values(tmp_path):
    assert parse_seeds("0, 2,42") == (0, 2, 42)
    assert parse_parameter("0.15", 0.1) == .15
    assert parse_parameter("5", 1) == 5
    assert parse_parameter("true", False) is True
    assert parse_parameter("hello", "hi") == "hello"
    for seeds in ("", ",", "1,,2", "a", "-1", "2.2"):
        with pytest.raises(ValueError):
            parse_seeds(seeds)
    for actual, example in (("NaN", 1.), ("inf", 1.), ("1.2", 1), ("no", True)):
        with pytest.raises(ValueError):
            parse_parameter(actual, example)
    with pytest.raises(ValueError, match="unique"):
        SimulationLaunchRequest("contrast_sensitivity", "csf_baseline",
                                tmp_path, (1, 1))
    with pytest.raises(ValueError, match="1–128"):
        SimulationLaunchRequest("contrast_sensitivity", "csf_baseline",
                                tmp_path, tuple(range(129)))


@pytest.mark.parametrize("size", [(80, 24), (100, 30)])
def test_tui_simulation_navigation_review_and_typed_handoff(tmp_path, monkeypatch, size):
    async def scenario():
        data_root = tmp_path / "local_psychophysics_data"
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=data_root)
        captured = []
        monkeypatch.setattr(app, "exit", lambda result=None: captured.append(result))
        async with app.run_test(size=size) as pilot:
            app.query_one("#nav-simulations", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, SimulationsScreen)
            screen = app.screen
            assert screen.query_one("#sim-experiment", Select).value == "contrast_sensitivity"
            assert screen.query_one("#sim-scenario", Select).value == "csf_baseline"
            nav = screen.query_one("#hub-nav")
            for button in nav.query(Button):
                assert button.region.x >= 0
                assert button.region.right <= size[0]

            screen.query_one("#sim-seeds-0", Input).value = "7,8"
            # Baseline CSF scenario declares 'threshold' as the first observer parameter.
            screen.query_one("#sim-observer-0-0", Input).value = "0.08"
            screen.query_one("#sim-review", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, SimulationReviewScreen)
            assert "0.08" in str(app.screen.query_one("#sim-review-summary", Static).render())
            app.screen.query_one("#sim-run", Button).press()
            await pilot.pause()
            assert len(captured) == 1
            request = captured[0]
            assert isinstance(request, SimulationLaunchRequest)
            assert request.experiment_id == "contrast_sensitivity"
            assert request.scenario_id == "csf_baseline"
            assert request.seeds == (7, 8)
            assert request.observer_parameters["threshold"] == pytest.approx(.08)
            assert request.data_root == data_root.resolve()
            assert not data_root.exists()  # Review and confirmation never execute in the TUI.
    asyncio.run(scenario())


def test_tui_invalid_observer_and_invalid_seed_block_review(tmp_path):
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "human")
        async with app.run_test(size=(80, 24)) as pilot:
            app.query_one("#nav-simulations", Button).press()
            await pilot.pause()
            screen = app.screen
            screen.query_one("#sim-seeds-0", Input).value = "1,x"
            screen.query_one("#sim-review", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, SimulationsScreen)
            assert "Seeds must" in str(screen.query_one("#sim-status", Static).render())
            screen.query_one("#sim-seeds-0", Input).value = "123"
            screen.query_one("#sim-observer-0-0", Input).value = "-0.1"
            screen.query_one("#sim-review", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, SimulationsScreen)
            assert "threshold" in str(screen.query_one("#sim-status", Static).render())
    asyncio.run(scenario())


def test_tui_scenario_change_shows_experiment_owned_inputs(tmp_path):
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "external")
        async with app.run_test(size=(100, 30)) as pilot:
            app.query_one("#nav-simulations", Button).press()
            await pilot.pause()
            screen = app.screen
            screen.query_one("#sim-scenario", Select).value = "csf_short_censored"
            await pilot.pause()
            index = next(i for i, item in enumerate(screen.scenarios)
                         if item.id == "csf_short_censored")
            assert screen.query_one(f"#sim-panel-{index}").display
            assert not screen.query_one("#sim-panel-0").display
            screen.query_one("#sim-review", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, SimulationReviewScreen)
            assert app.screen.request.experiment_values["max_trials"] == 1
    asyncio.run(scenario())


def test_tui_receives_and_displays_last_simulation_report(tmp_path):
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "external",
                               simulation_summary="Latest simulation: PASSED")
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            assert "PASSED" in str(app.query_one("#last-simulation", Static).render())
            app.query_one("#nav-simulations", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, SimulationsScreen)
            assert "PASSED" in str(app.screen.query_one("#sim-latest", Static).render())
    asyncio.run(scenario())


def test_outer_app_runs_simulation_only_after_tui_has_returned(tmp_path, monkeypatch):
    from psychophysics_lab import app as app_module
    from psychophysics_lab.ui import setup as tui_module
    from simulations import scenarios

    data_root = tmp_path / "local_psychophysics_data"
    request = SimulationLaunchRequest(
        "contrast_sensitivity", "csf_short_censored", data_root,
        (11,), observer_parameters={"threshold": 0.1, "preferred_condition": 63.0},
        experiment_values={"max_trials": 1},
    )
    calls = []
    results = [request, None]

    def fake_tui(*, repo_root, data_root, simulation_summary=None):
        calls.append(("tui", simulation_summary))
        return results.pop(0)

    def fake_simulate(**kwargs):
        calls.append(("simulate", kwargs))
        return SimpleNamespace(experiment_id=kwargs["experiment_id"],
                               scenario_id=kwargs["scenario_id"], passed=True,
                               runs=(object(),), report_file=data_root / "summary.json")

    monkeypatch.setattr(tui_module, "run_setup_tui", fake_tui)
    monkeypatch.setattr(scenarios, "run_scenario", fake_simulate)
    monkeypatch.setattr(app_module, "find_repo_root", lambda: ROOT)
    monkeypatch.setattr(app_module, "preferred_data_root", lambda repo, fallback: data_root)
    monkeypatch.setattr(app_module, "remember_data_root",
                        lambda *args: pytest.fail("Synthetic run must not overwrite human data preferences"))
    assert app_module._main([]) == 0
    assert [event[0] for event in calls] == ["tui", "simulate", "tui"]
    assert calls[1][1]["seeds"] == (11,)
    assert "PASSED" in calls[2][1]


@pytest.mark.parametrize("size", [(80, 24), (100, 30)])
def test_adaptive_button_opens_editor_and_applies_settings_to_review(tmp_path, size):
    """Button must open a separate editor, not silently scroll an already-open panel."""
    from psychophysics_lab.experiments.registry import get_experiment

    async def scenario():
        data_root = tmp_path / "local_psychophysics_data"
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=data_root)
        async with app.run_test(size=size) as pilot:
            app.query_one("#nav-simulations", Button).press()
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SimulationsScreen)
            index, selected = screen._current()
            fields = {f.key: n for n, f in enumerate(get_experiment(selected.experiment_id).fields)}
            def source(key):
                return screen.query_one(f"#sim-experiment-value-{index}-{fields[key]}", Input)

            assert screen.query_one("#sim-edit-adaptive", Button).label.plain == "Adaptive algorithm"
            screen.query_one("#sim-edit-adaptive", Button).press()
            await pilot.pause()
            editor = app.screen
            assert isinstance(editor, AdaptiveAlgorithmScreen)
            assert "consecutive_up_down" in str(editor.query_one("#adaptive-editor-body").render())

            def edit(key):
                return editor.query_one(f"#adaptive-value-{fields[key]}", Input)

            for key in ("n_down", "n_up", "logUNIT_UP", "logUNIT_DW",
                        "reversal_termination", "max_trials"):
                assert not edit(key).disabled
            edit("n_down").value = "3"
            edit("n_up").value = "1"
            edit("logUNIT_UP").value = "0.22"
            edit("logUNIT_DW").value = "0.16"
            edit("reversal_termination").value = "14"
            edit("max_trials").value = "250"
            editor.query_one("#adaptive-apply", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, SimulationsScreen)
            assert source("n_down").value == "3"
            assert source("logUNIT_DW").value == "0.16"

            screen.query_one("#sim-review", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, SimulationReviewScreen)
            values = app.screen.request.experiment_values
            assert values["n_down"] == 3
            assert values["n_up"] == 1
            assert values["logUNIT_UP"] == pytest.approx(.22)
            assert values["logUNIT_DW"] == pytest.approx(.16)
            assert values["reversal_termination"] == 14
            assert values["max_trials"] == 250
            assert not data_root.exists()  # Editing never creates actual data.
    asyncio.run(scenario())


def test_adaptive_editor_cancel_invalid_input_and_step_calculator(tmp_path):
    from psychophysics_lab.experiments.registry import get_experiment

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "local_psychophysics_data")
        async with app.run_test(size=(80, 24)) as pilot:
            app.query_one("#nav-simulations", Button).press()
            await pilot.pause()
            parent = app.screen
            index, current = parent._current()
            keys = {field.key: n for n, field in enumerate(get_experiment(current.experiment_id).fields)}
            def source(key):
                return parent.query_one(f"#sim-experiment-value-{index}-{keys[key]}", Input)

            old_n_down = source("n_down").value
            parent.query_one("#sim-edit-adaptive", Button).press()
            await pilot.pause()
            editor = app.screen
            assert isinstance(editor, AdaptiveAlgorithmScreen)
            editor.query_one(f"#adaptive-value-{keys['n_down']}", Input).value = "3"
            editor.query_one("#adaptive-cancel", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, SimulationsScreen)
            assert source("n_down").value == old_n_down

            parent.query_one("#sim-edit-adaptive", Button).press()
            await pilot.pause()
            editor = app.screen
            n_down = editor.query_one(f"#adaptive-value-{keys['n_down']}", Input)
            n_down.value = "0"
            editor.query_one("#adaptive-apply", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, AdaptiveAlgorithmScreen)
            assert "n-down" in str(editor.query_one("#adaptive-editor-status", Static).render())
            assert source("n_down").value == old_n_down

            n_down.value = "3"
            editor.query_one(f"#adaptive-value-{keys['logUNIT_UP']}", Input).value = "0.4"
            editor.query_one("#adaptive-calculate-down", Button).press()
            await pilot.pause()
            expected = .4 * .7393
            calculated = editor.query_one(f"#adaptive-value-{keys['logUNIT_DW']}", Input)
            assert float(calculated.value) == pytest.approx(expected)
            editor.query_one("#adaptive-apply", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, SimulationsScreen)
            assert float(source("logUNIT_DW").value) == pytest.approx(expected)
    asyncio.run(scenario())
