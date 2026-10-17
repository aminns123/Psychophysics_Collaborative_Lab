"""Virtual observer options AFTER shared human/virtual experiment configuration.

The experiment, monitor, condition list, staircase and timing controls are
identical for human and synthetic run choices. This screen adds only model
properties, scenario expectations and random seed(s).
"""
from __future__ import annotations

import json
from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static

from ..config.preflight import validate_setup
from ..config.monitor import load_monitor_profiles
from ..core.simulation_request import SimulationLaunchRequest, parse_parameter, parse_seeds
from psychophysics_lab.experiments._internal.registry import get_experiment
from ..paths import resolve_data_root
from .setup import _nav_bar, _handle_nav, _is_blank_select_value
from simulations.controls import effective_observer_values
from simulations.scenarios import list_scenarios
from simulations.registry import get_simulation


class VirtualObserverOptionsScreen(Screen):
    """One shared experiment configuration, two real execution modes."""

    def __init__(self, request):
        super().__init__()
        self.request = request
        self.scenarios = list_scenarios(request.experiment_id)

    def _observer_defaults(self, scenario):
        values = effective_observer_values(scenario)
        experiment_values = self.request.experiment_values
        # New unified cpd studies must not inherit the old 63/252 legacy
        # reference observer's uncalibrated preferred-condition default.
        if ("preferred_condition" in values and
                self.request.experiment_id == "contrast_sensitivity" and
                experiment_values.get("condition_unit") in {"cycles_per_degree", "degrees_per_cycle"}):
            from .._reference_csf.experiment_definition import resolved_condition_frequencies
            conditions = resolved_condition_frequencies(
                experiment_values["condition_values"], experiment_values["condition_unit"]
            )
            values["preferred_condition"] = conditions[0]
        return values

    def compose(self) -> ComposeResult:
        initial = self.scenarios[0] if self.scenarios else None
        with Vertical(id="fixed-shell"):
            yield Header(show_clock=True)
            yield _nav_bar()
            with Horizontal(classes="buttons"):
                yield Button("Back", id="virtual-back")
                yield Button("Run virtual experiment", id="virtual-run", variant="success",
                             disabled=not bool(self.scenarios))
            yield Static("", id="virtual-status")
        with VerticalScroll(classes="page-body"):
            yield Static(
                "[b]Virtual observer — same configured experiment[/b]\n"
                "All experiment conditions, physical units, adaptive parameters, timing "
                "and monitor profile were chosen on the shared Experiment setup page. "
                "Only simulated observer parameters and random seeds are added here. "
                "No physical display, response keyboard or participant is involved.",
                classes="info-card",
            )
            yield Label("Simulation scenario")
            yield Select(
                [(s.id, s.id) for s in self.scenarios] or [("No scenario available", "__none__")],
                id="virtual-scenario", value=initial.id if initial else "__none__",
                allow_blank=False,
            )
            for i, scenario in enumerate(self.scenarios):
                with Vertical(id=f"virtual-scenario-{i}"):
                    yield Static(f"[b]{scenario.id}[/b]\n{scenario.description}", classes="info-card")
                    yield Label("Random seeds (comma-separated nonnegative whole numbers)")
                    yield Input(value=",".join(str(x) for x in scenario.seeds),
                                id=f"virtual-seeds-{i}")
                    yield Static("[b]Observer-only properties[/b]")
                    for j, (name, value) in enumerate(self._observer_defaults(scenario).items()):
                        from .domain_feedback import observer_domain
                        yield Label(name.replace("_", " ")+" — "+observer_domain(self.request.experiment_id,name,value))
                        yield Input(value=json.dumps(value) if isinstance(value, (dict, list, bool)) else str(value),
                                    id=f"virtual-observer-{i}-{j}")
        yield Footer()

    def on_mount(self) -> None:
        self._show_current()

    def _current(self):
        name = self.query_one("#virtual-scenario", Select).value
        for i, case in enumerate(self.scenarios):
            if case.id == name:
                return i, case
        raise ValueError("Choose a registered virtual-observer scenario.")

    def _show_current(self):
        index, _ = self._current()
        for i in range(len(self.scenarios)):
            self.query_one(f"#virtual-scenario-{i}", Vertical).display = i == index

    def on_select_changed(self, event: Select.Changed):
        if event.select.id == "virtual-scenario" and self.is_mounted:
            self._show_current()

    def _launch_request(self):
        i, scenario = self._current()
        model = get_simulation(self.request.experiment_id)
        observer = {
            key: parse_parameter(self.query_one(f"#virtual-observer-{i}-{j}", Input).value, value)
            for j, (key, value) in enumerate(self._observer_defaults(scenario).items())
        }
        model.observer_factory(**observer)  # Validate true psychometric properties.
        seeds = parse_seeds(self.query_one(f"#virtual-seeds-{i}", Input).value)
        spec = get_experiment(self.request.experiment_id)
        profile = load_monitor_profiles(self.app.repo_root)[self.request.monitor_profile_id]
        values = validate_setup(self.request, spec, profile, mode="simulation").experiment_values
        root = resolve_data_root(self.request.data_root or self.app.data_root, self.app.repo_root)
        return SimulationLaunchRequest(
            experiment_id=self.request.experiment_id, scenario_id=scenario.id,
            data_root=root, seeds=seeds, observer_parameters=observer,
            experiment_values=values, monitor_profile_id=self.request.monitor_profile_id,
            monitor_profile_hash=self.request.monitor_profile_hash,
            stimulus_snapshots=self.request.stimulus_snapshots,
        )

    def on_input_changed(self,event):
        if not self.is_mounted: return
        try:
            self._launch_request()
            self.query_one('#virtual-status',Static).update('Current observer parameters and seed list validate; this is a simulation.')
            event.input.remove_class('invalid-input')
        except (ValueError,TypeError,OverflowError) as exc:
            event.input.add_class('invalid-input')
            self.query_one('#virtual-status',Static).update(str(exc))

    def on_button_pressed(self, event: Button.Pressed):
        if _handle_nav(self, event):
            return
        if event.button.id == "virtual-back":
            event.stop()
            self.app.pop_screen()
        elif event.button.id == "virtual-run":
            event.stop()
            try:
                self.app.exit(self._launch_request())
            except (ValueError, TypeError, OverflowError) as exc:
                self.query_one("#virtual-status", Static).update(f"[red]Virtual run NOT started: {exc}[/red]")
                self.app.notify(str(exc), title="Virtual run not started", severity="error", timeout=8)
