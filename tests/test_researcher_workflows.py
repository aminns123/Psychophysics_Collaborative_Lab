import asyncio
from dataclasses import replace
import importlib.util
import itertools
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from textual.widgets import Button, Collapsible, Input, Static
from psychophysics_lab.adaptive import AdaptiveRun, AdaptiveAlgorithm, AdaptiveSelection, StaircaseConfig, Step
from psychophysics_lab.adaptive.registry import register_algorithm
from psychophysics_lab.adaptive.steps import paired_step
from psychophysics_lab.experiments.contrast_sensitivity import CSF_SPEC
from psychophysics_lab.experiments.responses import LEFT_RIGHT, TWO_INTERVAL, ResponseParadigm
from psychophysics_lab.scaffold import scaffold
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentConfigScreen

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("n_down,ratio", [(1,.2845),(2,.5488),(3,.7393),(4,.8415)])
@pytest.mark.parametrize("up", [.01,.1,.35,1.0])
def test_literature_mapping_and_inverse_in_actual_legacy_log_convention(n_down, ratio, up):
    from Events.adaptiveMethods import _update_probe_weber_contrast
    down = paired_step(known_value=up, calculate="down", n_down=n_down, n_up=1)
    assert down == pytest.approx(up * ratio)
    assert paired_step(known_value=down, calculate="up", n_down=n_down, n_up=1) == pytest.approx(up)
    assert _update_probe_weber_contrast(Step.UP, .1, up, down) == pytest.approx(.1 * 10**up)
    assert _update_probe_weber_contrast(Step.DOWN, .1, up, down) == pytest.approx(.1 * 10**(-down))


@pytest.mark.parametrize("changes", [dict(n_up=2),dict(n_down=5),dict(n_down=True),dict(n_down=2.),
    dict(alternatives=4),dict(parameterization="linear"),dict(parameterization=None),dict(calculate="both"),
    dict(known_value=0),dict(known_value=-1),dict(known_value=float("nan")),dict(known_value=float("inf")),dict(known_value=True)])
def test_unsupported_calculations_fail_without_a_guess(changes):
    args = dict(known_value=.35, calculate="down", n_down=2, n_up=1)
    with pytest.raises(ValueError):
        paired_step(**(args | changes))


def test_legacy_defaults_and_imports_are_preserved():
    from Events.staircase import AdaptiveRun as LegacyRun, StaircaseConfig as LegacyConfig
    assert LegacyRun is AdaptiveRun and LegacyConfig is StaircaseConfig
    assert CSF_SPEC.field_defaults()["logUNIT_UP"] == .35
    assert CSF_SPEC.field_defaults()["logUNIT_DW"] == .5488 * .35
    assert CSF_SPEC.field_defaults()["max_trials"] == 30


def test_response_paradigms_do_not_change_update_rules():
    for answers in itertools.product((0,1), repeat=5):
        snapshots = []
        for paradigm in (LEFT_RIGHT, TWO_INTERVAL):
            run = AdaptiveRun({0: StaircaseConfig(2,1,20)}, 6)
            value = 1.
            for answer in answers:
                correct = paradigm.correct(0, paradigm.decode(paradigm.keys[answer]))
                _, value = run.respond(0, correct, lambda step: value * (0.5 if step == Step.DOWN else 2 if step == Step.UP else 1))
            snapshots.append(run.snapshot())
        assert snapshots[0] == snapshots[1]
    with pytest.raises(ValueError):
        LEFT_RIGHT.decode("ESCAPE")
    with pytest.raises(ValueError):
        ResponseParadigm("ambiguous", ("left","right"), ("x","x"))


def test_registered_custom_algorithm_is_selected_by_experiment(monkeypatch):
    from psychophysics_lab.adaptive import registry
    from psychophysics_lab.researcher import experiment, RunContext, ConfigField
    monkeypatch.setattr(registry, "_REGISTRY", dict(registry._REGISTRY))
    register_algorithm(AdaptiveAlgorithm("custom", "Test alternative", lambda *, level: {"level":level}, ("level",)))
    spec = experiment(id="custom_task", name="Custom", description="Test", procedure=lambda run:None,
        fields=(ConfigField("level","Level","float",default=.2),), adaptive=AdaptiveSelection("custom", ("level",)), responses=TWO_INTERVAL)
    context = RunContext(spec.field_defaults(), None, spec, ROOT)
    assert context.adaptive(level=.3) == {"level":.3}
    assert context.responses is TWO_INTERVAL
    with pytest.raises(ValueError, match="unsupported"):
        replace(spec, adaptive=AdaptiveSelection("custom", ("n_up",)))
    with pytest.raises(ValueError, match="already"):
        register_algorithm(registry.get_algorithm("custom"))


def test_scaffold_is_valid_python_and_never_overwrites(tmp_path):
    for directory in ("stimuli", "experiments"):
        (tmp_path/"src"/"psychophysics_lab"/directory).mkdir(parents=True)
    paths = scaffold(tmp_path, "orientation_task")
    before = [p.read_bytes() for p in paths]
    for p in paths:
        compile(p.read_text(),str(p),"exec")
    with pytest.raises(ValueError, match="new files"):
        scaffold(tmp_path,"orientation_task")
    assert [p.read_bytes() for p in paths] == before
    for name in ("../escape", "class", "UPPER", "a/b", ""):
        with pytest.raises(ValueError):
            scaffold(tmp_path, name)


def test_contribution_loading_is_explicit_and_atomic(monkeypatch):
    from psychophysics_lab import contributions
    from psychophysics_lab.experiments import contributions as loader, registry
    from psychophysics_lab.stimuli import registry as stimuli
    monkeypatch.setattr(loader,"_loaded",False)
    monkeypatch.setattr(registry,"_REGISTRY",dict(registry._REGISTRY))
    monkeypatch.setattr(stimuli,"_REGISTRY",dict(stimuli._REGISTRY))
    monkeypatch.setattr(contributions,"EXPERIMENT_MODULES",("extension_a", "missing_extension"))
    def load(name):
        if name == "missing_extension":
            raise ImportError("missing")
        return SimpleNamespace(SPEC=replace(CSF_SPEC,id="extension_a"))
    monkeypatch.setattr(loader.importlib,"import_module",load)
    with pytest.raises(ImportError):
        loader.load_contributions()
    assert "extension_a" not in registry._REGISTRY
    monkeypatch.setattr(contributions,"EXPERIMENT_MODULES",("extension_a",))
    loader.load_contributions()
    loader.load_contributions()
    assert registry.get_experiment("extension_a").id == "extension_a"


@pytest.mark.parametrize("size", [(80,24),(100,30)])
def test_small_screen_navigation_and_opt_in_calculation(tmp_path,size):
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"human")
        async with app.run_test(size=size) as pilot:
            app.query_one("#participant",Input).value="S001"
            app.query_one("#configure",Button).press()
            await pilot.pause()
            screen=app.screen
            assert isinstance(screen,ExperimentConfigScreen)
            assert len(screen.query("#calculate-up")) == len(screen.query("#calculate-down")) == 1
            nav=screen.query_one("#hub-nav")
            before=nav.region
            adaptive = next(c for c in screen.query(Collapsible) if c.title == "Adaptive settings")
            adaptive.collapsed=False
            await pilot.pause()
            down=screen.query_one("#field-logUNIT-DW",Input)
            initial=down.value
            screen.query_one("#field-n-down",Input).value="3"
            await pilot.pause()
            assert down.value == initial
            screen.query_one("#calculate-down",Button).press()
            await pilot.pause()
            assert float(down.value) == pytest.approx(.35*.7393)
            screen.query_one("#field-n-up",Input).value="2"
            await pilot.pause()
            saved=down.value
            screen.query_one("#calculate-down",Button).press()
            await pilot.pause()
            assert down.value == saved
            assert "supports only" in str(screen.query_one("#step-status",Static).render())
            screen.query_one("#config-body").scroll_end(animate=False)
            await pilot.pause()
            assert nav.region == before
            for button in nav.query(Button):
                assert 0 <= button.region.x and button.region.right <= size[0]
            assert screen.query_one("#review",Button).region.y < size[1]
    asyncio.run(scenario())
