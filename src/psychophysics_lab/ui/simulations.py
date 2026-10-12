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
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static, Collapsible

from ..core.simulation_request import SimulationLaunchRequest, parse_parameter, parse_seeds
from ..paths import resolve_data_root
from ..adaptive.steps import paired_step, NOTICE
from ..experiments.registry import get_experiment
from ..config.preflight import compatible
from simulations.registry import get_simulation
from simulations.controls import effective_experiment_values, effective_observer_values
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

    def _compose_experiment_field(self, index: int, number: int, field, value) -> ComposeResult:
        """Render the exact same registered field for human and synthetic runs."""
        yield Label(field.label)
        widget_id = f"sim-experiment-value-{index}-{number}"
        if field.kind == "choice":
            yield Select(
                [(str(choice), choice) for choice in field.choices],
                value=value if value in field.choices else Select.BLANK,
                allow_blank=value is None,
                id=widget_id,
                disabled=not field.editable,
            )
        else:
            yield Input(
                value=_value_text(value), id=widget_id, disabled=not field.editable
            )
        if field.help_text:
            yield Static(field.help_text, classes="field-help")

    def compose(self) -> ComposeResult:
        first = self.experiment_ids[0] if self.experiment_ids else "__none__"
        scenarios = self._scenarios_for(first)
        first_scenario = scenarios[0].id if scenarios else "__none__"
        with Vertical(id="fixed-shell"):
            yield Header(show_clock=True)
            yield _nav_bar()
            with Horizontal(classes="buttons"):
                yield Button("Adaptive algorithm", id="sim-edit-adaptive",
                             disabled=not any(get_experiment(exp).adaptive for exp in self.experiment_ids))
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
            yield Label("Display profile (metadata only; no hardware is used)")
            compatible_profiles = {
                key: value for key, value in self.app.monitor_profiles.items()
                if compatible(get_experiment(first), value)
            } if self.experiment_ids else {}
            preferred = get_simulation(first).monitor_profile_id if self.experiment_ids else "__none__"
            profile_selection = preferred if preferred in compatible_profiles else next(iter(compatible_profiles), "__none__")
            yield Select(
                [(p.display_name, p.id) for p in compatible_profiles.values()]
                if compatible_profiles else [("No qualified profiles", "__none__")],
                value=profile_selection, allow_blank=False, id="sim-profile",
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
                    experiment = get_experiment(scenario.experiment_id)
                    experiment_values = effective_experiment_values(scenario)
                    adaptive = experiment.adaptive
                    adaptive_controls = set(adaptive.controls) if adaptive else set()
                    if adaptive_controls:
                        with Collapsible(
                            title="Adaptive algorithm — n-down/n-up rules, step sizes and reversals",
                            collapsed=False, id=f"sim-adaptive-{index}",
                        ):
                            yield Static(
                                "Same controls as Run: consecutive correct answers step DOWN; "
                                "consecutive incorrect answers step UP. Response counts and "
                                "log step magnitudes are independent. Changes apply to this "
                                "virtual run and are saved with its trial records.",
                                classes="field-help",
                            )
                            for number, field in enumerate(experiment.fields):
                                if field.key in adaptive_controls:
                                    yield from self._compose_experiment_field(
                                        index, number, field, experiment_values[field.key]
                                    )
                            if adaptive.step_calculator:
                                yield Static(NOTICE, classes="field-help")
                                with Horizontal(classes="buttons"):
                                    yield Button("Calculate down from up", id=f"sim-calculate-down-{index}")
                                    yield Button("Calculate up from down", id=f"sim-calculate-up-{index}")
                                yield Static("", id=f"sim-step-status-{index}", markup=False)
                    with Collapsible(
                        title="Other experiment settings — same controls as Run",
                        collapsed=True, id=f"sim-other-{index}",
                    ):
                        for number, field in enumerate(experiment.fields):
                            if field.key not in adaptive_controls:
                                yield from self._compose_experiment_field(
                                    index, number, field, experiment_values[field.key]
                                )
                    with Collapsible(title="Virtual observer (simulation-only properties)", collapsed=False):
                        for number, (key, value) in enumerate(effective_observer_values(scenario).items()):
                            yield Label(key.replace("_", " "))
                            yield Input(value=_value_text(value), id=f"sim-observer-{index}-{number}")
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
        # An experiment without an adaptive algorithm has no staircase controls.
        jump = self.query_one("#sim-edit-adaptive", Button)
        jump.disabled = (
            selected is None
            or not bool(getattr(get_experiment(selected[1].experiment_id).adaptive, "controls", ()))
        )
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
            if exp in self.experiment_ids:
                available = {
                    key: value for key, value in self.app.monitor_profiles.items()
                    if compatible(get_experiment(exp), value)
                }
                profile_selector = self.query_one("#sim-profile", Select)
                profile_selector.set_options(
                    [(p.display_name, p.id) for p in available.values()]
                    if available else [("No qualified profiles", "__none__")]
                )
                preferred = get_simulation(exp).monitor_profile_id
                profile_selector.value = preferred if preferred in available else next(iter(available), "__none__")
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
        profile_id = str(self.query_one("#sim-profile", Select).value)
        if profile_id not in self.app.monitor_profiles:
            raise ValueError("Select a registered display profile, even for a headless simulation.")
        if not compatible(get_experiment(scenario.experiment_id), self.app.monitor_profiles[profile_id]):
            raise ValueError("This display profile is not qualified for that experiment.")
        data = resolve_data_root(self.query_one("#sim-data-root", Input).value,
                                 self.app.repo_root)
        seeds = parse_seeds(self.query_one(f"#sim-seeds-{index}", Input).value)
        observer = {
            key: parse_parameter(
                self.query_one(f"#sim-observer-{index}-{number}", Input).value, value
            )
            for number, (key, value) in enumerate(effective_observer_values(scenario).items())
        }
        experiment = get_experiment(scenario.experiment_id)
        values = {}
        for number, field in enumerate(experiment.fields):
            widget = self.query_one(f"#sim-experiment-value-{index}-{number}")
            raw = widget.value
            if field.kind == "choice" and _is_blank_select_value(raw):
                raw = None
            values[field.key] = field.coerce(raw)
        # Validate the model and experiment configuration before offering the
        # final launch confirmation. No run directory is created at this stage.
        from simulations.registry import get_simulation
        model = get_simulation(scenario.experiment_id)
        model.observer_factory(**observer)
        get_experiment(scenario.experiment_id).normalise_values(
            dict(model.defaults) | values
        )
        return SimulationLaunchRequest(
            experiment_id=scenario.experiment_id,
            scenario_id=scenario.id,
            data_root=data,
            seeds=seeds,
            observer_parameters=observer,
            experiment_values=values,
            monitor_profile_id=profile_id,
        )

    def _calculate_step(self, button_id: str) -> None:
        _, _, direction, text_index = button_id.split("-", 3)
        index, scenario = self._current()
        if int(text_index) != index:
            raise ValueError("Choose an active scenario before calculating steps.")
        experiment = get_experiment(scenario.experiment_id)
        fields = list(experiment.fields)
        by_key = {field.key: (number, field) for number, field in enumerate(fields)}
        if not experiment.adaptive or not experiment.adaptive.step_calculator:
            raise ValueError("This experiment has not declared a step-size calculator.")
        def setting(key):
            number, field = by_key[key]
            return field.coerce(self.query_one(f"#sim-experiment-value-{index}-{number}", Input).value)
        target = "logUNIT_DW" if direction == "down" else "logUNIT_UP"
        known = "logUNIT_UP" if direction == "down" else "logUNIT_DW"
        new_value = paired_step(
            known_value=setting(known), calculate=direction,
            n_down=setting("n_down"), n_up=setting("n_up"),
            alternatives=len(experiment.response_paradigm.alternatives) if experiment.response_paradigm else None,
            parameterization=experiment.adaptive.step_parameterization,
        )
        number, field = by_key[target]
        if not field.editable:
            raise ValueError("The experiment fixes this step magnitude.")
        self.query_one(f"#sim-experiment-value-{index}-{number}", Input).value = repr(new_value)
        self.query_one(f"#sim-step-status-{index}", Static).update(
            f"Calculated {target} = {new_value:.8g}. This is an optional relation, not an automatic optimum."
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if _handle_nav(self, event):
            return
        if event.button.id == "sim-edit-adaptive":
            event.stop()
            try:
                index, scenario = self._current()
                experiment = get_experiment(scenario.experiment_id)
                if experiment.adaptive is None or not experiment.adaptive.controls:
                    raise ValueError("The selected experiment has no adaptive algorithm controls.")
                # An explicit editor is discoverable and works even when the
                # inline settings are far below the viewport or already open.
                self.app.push_screen(AdaptiveAlgorithmScreen(self, index, scenario.experiment_id))
            except (ValueError, TypeError) as exc:
                self.query_one("#sim-status", Static).update(str(exc))
            return
        if (event.button.id or "").startswith("sim-calculate-"):
            event.stop()
            try:
                self._calculate_step(event.button.id)
            except (ValueError, TypeError, KeyError) as exc:
                index, _ = self._current()
                self.query_one(f"#sim-step-status-{index}", Static).update(str(exc))
            return
        if event.button.id != "sim-review":
            return
        event.stop()
        try:
            self.app.push_screen(SimulationReviewScreen(self._request()))
        except (ValueError, TypeError, OverflowError) as exc:
            self.query_one("#sim-status", Static).update(f"[red]{exc}[/red]")



class AdaptiveAlgorithmScreen(Screen):
    """Focused editor for the current experiment's adaptive parameters.

    The selection is controlled by ExperimentSpec. This editor does not
    silently switch algorithms or write experiment files: Apply copies
    validated values into the same widgets used by simulation Review/Run.
    Cancel retains the previous settings.
    """

    def __init__(self, source: SimulationsScreen, scenario_index: int, experiment_id: str):
        super().__init__()
        self.source = source
        self.scenario_index = scenario_index
        self.experiment = get_experiment(experiment_id)
        if not self.experiment.adaptive or not self.experiment.adaptive.controls:
            raise ValueError("The selected experiment has no adaptive settings.")
        controls = set(self.experiment.adaptive.controls)
        self.fields = tuple(
            (number, field)
            for number, field in enumerate(self.experiment.fields)
            if field.key in controls
        )

    def _input(self, number: int):
        return self.query_one(f"#adaptive-value-{number}")

    def _values(self) -> dict:
        values = {}
        for number, field in self.fields:
            widget = self._input(number)
            raw = widget.value
            if field.kind == "choice" and _is_blank_select_value(raw):
                raw = None
            values[field.key] = field.coerce(raw)
        return values

    def compose(self) -> ComposeResult:
        from ..adaptive.registry import get_algorithm

        selection = self.experiment.adaptive
        algorithm = get_algorithm(selection.algorithm_id)
        with Vertical(id="fixed-shell"):
            yield Header(show_clock=True)
            yield _nav_bar()
            with Horizontal(classes="buttons"):
                yield Button("Cancel", id="adaptive-cancel")
                yield Button("Apply adaptive settings", id="adaptive-apply", variant="primary")
        with VerticalScroll(classes="page-body", id="adaptive-editor-body"):
            yield Static(
                f"[b]Adaptive algorithm[/b]\\n"
                f"Experiment: {self.experiment.display_name}\\n"
                f"Algorithm: {algorithm.id}\\n"
                f"{algorithm.description}\\n\\n"
                "Change the same adaptive parameters used for human acquisition. "
                "No changes are applied to your simulation until you select "
                "Apply adaptive settings.",
                classes="info-card",
            )
            for number, field in self.fields:
                source_widget = self.source.query_one(
                    f"#sim-experiment-value-{self.scenario_index}-{number}"
                )
                yield Label(field.label)
                if field.kind == "choice":
                    yield Select(
                        [(str(choice), choice) for choice in field.choices],
                        value=source_widget.value,
                        id=f"adaptive-value-{number}",
                        allow_blank=field.default is None,
                        disabled=not field.editable,
                    )
                else:
                    yield Input(
                        value=str(source_widget.value),
                        id=f"adaptive-value-{number}",
                        disabled=not field.editable,
                    )
                if field.help_text:
                    yield Static(field.help_text, classes="field-help")
            if selection.step_calculator:
                yield Static(NOTICE, classes="field-help")
                with Horizontal(classes="buttons"):
                    yield Button("Calculate down from up", id="adaptive-calculate-down")
                    yield Button("Calculate up from down", id="adaptive-calculate-up")
            yield Static("", id="adaptive-editor-status", markup=False)
        yield Footer()

    def _calculate(self, direction: str) -> None:
        selection = self.experiment.adaptive
        fields = {field.key: (number, field) for number, field in self.fields}
        def setting(key):
            number, field = fields[key]
            return field.coerce(self._input(number).value)
        target = "logUNIT_DW" if direction == "down" else "logUNIT_UP"
        known = "logUNIT_UP" if direction == "down" else "logUNIT_DW"
        number, field = fields[target]
        if not field.editable:
            raise ValueError("The selected experiment fixes that step magnitude.")
        value = paired_step(
            known_value=setting(known), calculate=direction,
            n_down=setting("n_down"), n_up=setting("n_up"),
            alternatives=len(self.experiment.response_paradigm.alternatives)
            if self.experiment.response_paradigm else None,
            parameterization=selection.step_parameterization,
        )
        self._input(number).value = repr(value)
        self.query_one("#adaptive-editor-status", Static).update(
            f"Calculated {target} = {value:.8g}; this is an optional literature relation."
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if _handle_nav(self, event):
            return
        if event.button.id == "adaptive-cancel":
            event.stop()
            self.app.pop_screen()
            return
        if event.button.id in {"adaptive-calculate-down", "adaptive-calculate-up"}:
            event.stop()
            try:
                direction = event.button.id.removeprefix("adaptive-calculate-")
                self._calculate(direction)
            except (ValueError, TypeError, KeyError) as exc:
                self.query_one("#adaptive-editor-status", Static).update(str(exc))
            return
        if event.button.id == "adaptive-apply":
            event.stop()
            try:
                changed = self._values()
                # Same experiment-level validation as the human Run page.
                # Preserve ALL other fields of the selected simulation.
                proposal = {}
                for number, field in enumerate(self.experiment.fields):
                    source_field = self.source.query_one(
                        f"#sim-experiment-value-{self.scenario_index}-{number}"
                    )
                    raw = source_field.value
                    if field.kind == "choice" and _is_blank_select_value(raw):
                        raw = None
                    proposal[field.key] = field.coerce(raw)
                proposal.update(changed)
                self.experiment.normalise_values(proposal)
            except (ValueError, TypeError, KeyError) as exc:
                self.query_one("#adaptive-editor-status", Static).update(str(exc))
                return
            for number, field in self.fields:
                widget = self.source.query_one(
                    f"#sim-experiment-value-{self.scenario_index}-{number}"
                )
                value = changed[field.key]
                widget.value = value if field.kind == "choice" else str(value)
            self.source.query_one("#sim-status", Static).update(
                "Adaptive algorithm updated. Review Simulation to confirm the saved rules."
            )
            self.app.pop_screen()


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
                f"Display profile (unverified headless metadata): {request.monitor_profile_id}\n"
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
