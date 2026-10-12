"""Headless virtual-experiment setup integrated into the PsyCoLab TUI.

The TUI only collects/reviews configuration, then exits with a typed
SimulationLaunchRequest. Actual scenarios execute after Textual has closed.
"""
from __future__ import annotations

import json
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static

from ..core.simulation_request import SimulationLaunchRequest, parse_parameter, parse_seeds
from ..paths import resolve_data_root
from .setup import HubPage, _nav_bar, _handle_nav, _is_blank_select_value


def _value_text(value) -> str:
    if isinstance(value, (dict, list, tuple, bool)):
        return json.dumps(value)
    return str(value)


class SimulationsScreen(HubPage):
    page_title = "Simulations"

    def __init__(self) -> None:
        super().__init__()
        from simulations.scenarios import list_scenarios
        self.scenarios = list_scenarios()
        self.experiment_ids = tuple(sorted({s.experiment_id for s in self.scenarios}))

    def _scenarios_for(self, experiment_id: str):
        return [item for item in self.scenarios if item.experiment_id == experiment_id]

    def compose(self) -> ComposeResult:
        first = self.experiment_ids[0] if self.experiment_ids else "__none__"
        scenarios = self._scenarios_for(first)
        first_scenario = scenarios[0].id if scenarios else "__none__"
        with Vertical(id="fixed-shell"):
            yield Header(show_clock=True)
            yield _nav_bar()
            with Horizontal(classes="buttons"):
                yield Button("Review Simulation", id="sim-review", variant="primary",
                             disabled=not bool(self.scenarios))
        with VerticalScroll(classes="page-body", id="sim-body"):
            yield Static(
                "[b]Virtual experiment laboratory[/b]\n"
                "Test the real experiment pipeline using a virtual observer: "
                "no human participant, physical display or audio. "
                "Results appear under reserved synthetic_ participant IDs "
                "in the same external PsyCoLab data repository.",
                classes="info-card",
            )
            yield Label("External data repository (same as human acquisition)")
            yield Input(value=str(self.app.data_root), id="sim-data-root")
            yield Label("Experiment")
            yield Select(
                [(exp, exp) for exp in self.experiment_ids]
                if self.experiment_ids else [("No registered simulations", "__none__")],
                value=first, allow_blank=False, id="sim-experiment",
            )
            yield Label("Simulation scenario")
            yield Select(
                [(scenario.id, scenario.id) for scenario in scenarios]
                if scenarios else [("No scenarios", "__none__")],
                value=first_scenario, allow_blank=False, id="sim-scenario",
            )
            yield Static("", id="sim-description", classes="info-card")
            for index, scenario in enumerate(self.scenarios):
                with Vertical(id=f"sim-panel-{index}", classes="scenario-panel"):
                    yield Label("Random seed(s) — comma-separated; each creates a synthetic run")
                    yield Input(value=",".join(map(str, scenario.seeds)),
                                id=f"sim-seeds-{index}")
                    if scenario.observer_parameters:
                        yield Static("[b]Virtual observer — known model properties[/b]")
                        for number, (key, value) in enumerate(scenario.observer_parameters.items()):
                            yield Label(key.replace("_", " "))
                            yield Input(value=_value_text(value), id=f"sim-observer-{index}-{number}")
                    if scenario.experiment_values:
                        yield Static("[b]Experiment procedure overrides[/b]")
                        for number, (key, value) in enumerate(scenario.experiment_values.items()):
                            yield Label(key.replace("_", " "))
                            yield Input(value=_value_text(value), id=f"sim-experiment-value-{index}-{number}")
            yield Static(
                "The scenario defines the scientific validation and interpretation. "
                "Changing its settings may change expected analysis outcomes; "
                "no simulation is a hardware calibration or a human-subject measurement.",
                classes="field-help",
            )
            if getattr(self.app, "simulation_summary", None):
                yield Static(self.app.simulation_summary, id="sim-latest", classes="info-card")
            yield Static("", id="sim-status")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()

    def _current(self):
        experiment = self.query_one("#sim-experiment", Select).value
        scenario = self.query_one("#sim-scenario", Select).value
        if _is_blank_select_value(experiment) or _is_blank_select_value(scenario):
            raise ValueError("Select an experiment and a simulation scenario.")
        for index, candidate in enumerate(self.scenarios):
            if (candidate.experiment_id, candidate.id) == (str(experiment), str(scenario)):
                return index, candidate
        raise ValueError("Selected simulation scenario is not registered for that experiment.")

    def _refresh(self) -> None:
        selected = None
        try:
            selected = self._current()
        except ValueError:
            pass
        for index in range(len(self.scenarios)):
            matches = selected is not None and index == selected[0]
            self.query_one(f"#sim-panel-{index}", Vertical).display = matches
        if selected:
            _, scenario = selected
            self.query_one("#sim-description", Static).update(
                f"[b]{scenario.id}[/b]\n{scenario.description}\n"
                f"Default seeds: {scenario.seeds}\n"
                f"Analysis expected: {scenario.expect_analysis if scenario.expect_analysis is not None else 'scenario-dependent'}"
            )
        else:
            self.query_one("#sim-description", Static).update("No matching simulation scenario available.")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "sim-experiment":
            exp = str(event.value)
            scenarios = self._scenarios_for(exp)
            selected = self.query_one("#sim-scenario", Select)
            selected.set_options(
                [(scenario.id, scenario.id) for scenario in scenarios]
                if scenarios else [("No scenarios", "__none__")]
            )
            selected.value = scenarios[0].id if scenarios else "__none__"
        if event.select.id in {"sim-experiment", "sim-scenario"} and self.is_mounted:
            try:
                self._refresh()
            except Exception:
                # A Select can signal a change before all panels are mounted.
                pass

    def _request(self) -> SimulationLaunchRequest:
        index, scenario = self._current()
        data = resolve_data_root(self.query_one("#sim-data-root", Input).value,
                                 self.app.repo_root)
        seeds = parse_seeds(self.query_one(f"#sim-seeds-{index}", Input).value)
        observer = {
            key: parse_parameter(
                self.query_one(f"#sim-observer-{index}-{number}", Input).value, value
            )
            for number, (key, value) in enumerate(scenario.observer_parameters.items())
        }
        values = {
            key: parse_parameter(
                self.query_one(f"#sim-experiment-value-{index}-{number}", Input).value, value
            )
            for number, (key, value) in enumerate(scenario.experiment_values.items())
        }
        return SimulationLaunchRequest(
            experiment_id=scenario.experiment_id,
            scenario_id=scenario.id,
            data_root=data,
            seeds=seeds,
            observer_parameters=observer,
            experiment_values=values,
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if _handle_nav(self, event):
            return
        if event.button.id != "sim-review":
            return
        event.stop()
        try:
            self.app.push_screen(SimulationReviewScreen(self._request()))
        except (ValueError, TypeError, OverflowError) as exc:
            self.query_one("#sim-status", Static).update(f"[red]{exc}[/red]")


class SimulationReviewScreen(Screen):
    """A deliberate second action prevents unintended synthetic data writes."""

    def __init__(self, request: SimulationLaunchRequest) -> None:
        super().__init__()
        self.request = request

    def compose(self) -> ComposeResult:
        request = self.request
        with Vertical(id="fixed-shell"):
            yield Header(show_clock=True)
            yield _nav_bar()
            with Horizontal(classes="buttons"):
                yield Button("Back", id="sim-back")
                yield Button("Run Virtual Experiment", id="sim-run", variant="success")
        with VerticalScroll(classes="page-body"):
            yield Static(
                "[b]Review virtual experiment[/b]\n"
                f"Experiment: {request.experiment_id}\n"
                f"Scenario: {request.scenario_id}\n"
                f"Data repository: {request.data_root}\n"
                f"Seeds: {request.seeds}\n"
                f"Observer parameters:\n{json.dumps(request.observer_parameters, indent=2)}\n"
                f"Experiment overrides:\n{json.dumps(request.experiment_values, indent=2)}\n\n"
                "[yellow]SYNTHETIC ONLY[/yellow] — no human responses or hardware "
                "presentation. Simulated runs and reports are written under "
                "the external data repository; human settings are not changed. "
                "The TUI will close while the scenario executes, then reopen.",
                id="sim-review-summary",
            )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if _handle_nav(self, event):
            return
        if event.button.id == "sim-back":
            event.stop()
            self.app.pop_screen()
        elif event.button.id == "sim-run":
            event.stop()
            self.app.exit(self.request)
