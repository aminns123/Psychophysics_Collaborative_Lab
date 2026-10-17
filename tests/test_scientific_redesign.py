"""Scientific semantics and failure limits, independently of live display hardware."""

import ctypes
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from psychophysics_lab.analysis.primary import estimate
from psychophysics_lab.core.presentation import (
    render_values,
    render_pixels,
    FloatingTexture,
)
from psychophysics_lab.core.photometric_transfer import commands_for_luminance
from psychophysics_lab.experiments._internal.registry import (
    list_experiments,
    get_experiment,
)
from psychophysics_lab.stimuli.registry import get_stimulus
from simulations.psychometric import PsychometricObserver
from simulations.recovery import recover, operating_point

ROOT = Path(__file__).resolve().parents[1]
RULE = dict(
    version=1,
    value_column="presented_display_contrast",
    retained_reversals=2,
    within_staircase="median",
    across_staircases="arithmetic_mean",
)


def rows(identity, values, complete=True, condition="A"):
    return [
        dict(
            staircase_id=str(identity),
            stimulus_condition=condition,
            reversal="1",
            staircase_complete=str(int(complete and i == len(values) - 1)),
            presented_display_contrast=str(value),
            next_display_contrast=str(value * 10),
        )
        for i, value in enumerate(values)
    ]


def test_normal_catalogs_hide_history_and_explicit_replay_remains_available():
    from simulations.registry import list_simulations
    from simulations.scenarios import list_scenarios

    assert all(not spec.historical for spec in list_experiments())
    assert all(
        not get_experiment(spec.experiment_id).historical for spec in list_simulations()
    )
    assert all(not get_experiment(s.experiment_id).historical for s in list_scenarios())
    for identity in (
        "base_flanker",
        "indirect_flanker",
        "ellipse_2d",
        "contrast_sensitivity",
    ):
        assert get_experiment(identity).historical
    assert list_scenarios("contrast_sensitivity")  # explicit compatibility request


def test_every_normal_protocol_declares_its_scientific_interpretation():
    for spec in list_experiments():
        assert {
            "version",
            "response",
            "quantity",
            "conditions",
            "adaptive",
            "stopping",
            "exclusions",
            "estimator",
        } <= spec.scientific_spec.keys(), spec.id


@pytest.mark.parametrize(
    "identity,required",
    [
        ("line_position_baseline", "probe_vertical_offset_deg"),
        ("line_position_flanker", "flanker_cpd"),
        ("ellipse_centre", "ring_increment"),
        ("ellipse_major_axis", "ring_increment"),
    ],
)
def test_unspecified_study_choices_are_required(identity, required):
    spec = get_experiment(identity)
    assert spec.field_defaults()[required] is None
    with pytest.raises(ValueError):
        spec.normalise_values(spec.field_defaults())


def test_ellipse_intervals_preserve_the_actual_discrimination():
    from psychophysics_lab.experiments import ellipse_centre as e

    settings = e.SPEC.field_defaults() | {"ring_increment": 0.1}
    condition = e.make_conditions(settings)[0] | {"contrast": 0.02, "target": 1}

    class Run:
        values = settings

        def stimulus_parameters(self, slot, **parameters):
            defaults = {
                f.key: f.default for f in get_stimulus("detection_scene").parameters
            }
            return defaults | parameters

    images = e.prepare_stimuli(Run(), condition, {})
    assert images["first"]["ring_present"] and images["second"]["ring_present"]
    assert not images["first"]["probe_present"] and images["second"]["probe_present"]
    assert images["second"]["probe_y_deg"] == images["second"]["ring_y_deg"] == 0.6
    assert [
        p.duration_ms
        for p in e.make_trial(settings, condition).resolve(settings).phases
    ] == [500, 250, 250, 250, 0]


def test_small_contrasts_survive_scientific_raster_but_preview_is_explicitly_eight_bit():
    stimulus = get_stimulus("thesis_csf_grating")
    defaults = {f.key: f.default for f in stimulus.parameters}
    a, b = defaults | {"contrast": 0.001}, defaults | {"contrast": 0.0001}
    assert not np.array_equal(render_values(stimulus, a), render_values(stimulus, b))
    assert np.array_equal(render_pixels(stimulus, a), render_pixels(stimulus, b))
    assert stimulus.floating_raster


def test_thin_probe_preserves_integrated_area_and_ring_never_silently_clips():
    stimulus = get_stimulus("detection_scene")
    defaults = {f.key: f.default for f in stimulus.parameters} | {
        "probe_x_deg": 1.0,
        "probe_y_deg": 1.0,
        "contrast": 0.02,
    }
    difference = render_values(stimulus, defaults) - render_values(
        stimulus, defaults | {"probe_present": False}
    )
    assert difference.sum() * (14 / 256) ** 2 == pytest.approx(
        0.013 * 0.133 * 0.02, rel=1e-6
    )
    with pytest.raises(ValueError, match="gamut"):
        stimulus.validate_parameters(
            defaults | {"ring_present": True, "ring_increment": 0.49}
        )
    with pytest.raises(ValueError, match="inner axes"):
        stimulus.validate_parameters(
            defaults
            | {"ring_present": True, "ring_radius_deg": 0.17, "aspect_ratio": 0.5}
        )


def test_float_upload_declares_float_storage_and_refuses_eight_bit_fallback(
    monkeypatch,
):
    uploaded = []
    gl = SimpleNamespace(
        GLuint=ctypes.c_uint,
        GL_TEXTURE_2D=1,
        GL_TEXTURE_MIN_FILTER=2,
        GL_TEXTURE_MAG_FILTER=3,
        GL_NEAREST=4,
        GL_UNPACK_ALIGNMENT=5,
        GL_LUMINANCE32F_ARB=6,
        GL_LUMINANCE=7,
        GL_FLOAT=8,
        gl_info=SimpleNamespace(have_extension=lambda _: True),
        glGenTextures=lambda *a: None,
        glBindTexture=lambda *a: None,
        glTexParameteri=lambda *a: None,
        glPixelStorei=lambda *a: None,
        glTexImage2D=lambda *a: uploaded.append(a),
    )
    monkeypatch.setitem(sys.modules, "pyglet", SimpleNamespace(gl=gl))
    FloatingTexture(np.ones((2, 2), dtype=np.float32))
    assert uploaded[0][2] == gl.GL_LUMINANCE32F_ARB and uploaded[0][7] == gl.GL_FLOAT
    gl.gl_info.have_extension = lambda _: False
    with pytest.raises(ValueError, match="no 8-bit fallback"):
        FloatingTexture(np.ones((2, 2), dtype=np.float32))


def test_frame_count_and_transition_interval_are_recorded(monkeypatch):
    from test_action_presentation import fake_presentation
    from psychophysics_lab.researcher import Show

    display, _, _ = fake_presentation(monkeypatch, key=None)
    display.refresh_rate_hz = 100
    display._rendered = {"one": [], "two": []}
    clock = {"now": 0.0, "flips": 0}

    def flip():
        clock["flips"] += 1
        clock["now"] += 0.03 if clock["flips"] == 3 else 0.01

    display.window.flip = flip
    display.window.dispatch_events = lambda: None
    monkeypatch.setattr(
        "psychophysics_lab.core.presentation.time.perf_counter", lambda: clock["now"]
    )
    first, second = {}, {}
    display.play_phase(Show("one", duration=20), first)
    display.play_phase(Show("two", duration=10), second)
    assert first["requested_frames"] == 2 and clock["flips"] == 3
    assert first["actual_display_duration_s"] == pytest.approx(0.04)
    assert first["frame_intervals_s"] == pytest.approx([0.01, 0.03])
    assert first["dropped_frame_intervals"] == 1


def test_measured_transfer_interpolates_without_inventing_or_clipping_evidence():
    assert commands_for_luminance([10, 25], [0, 0.5, 1], [0, 20, 40]) == pytest.approx(
        [0.25, 0.625]
    )
    with pytest.raises(ValueError, match="outside"):
        commands_for_luminance([50], [0, 0.5, 1], [0, 20, 40])
    with pytest.raises(ValueError, match="increasing"):
        commands_for_luminance([10], [0, 0.5, 1], [0, 20, 19])


def test_primary_uses_presented_reversals_and_requires_all_repeats():
    data = rows(1, [0.9, 0.01, 0.09]) + rows(2, [0.1, 0.3])
    result = estimate(data, RULE, {"A": [1, 2]}, "completed")
    assert result["condition_thresholds"]["A"]["threshold"] == pytest.approx(0.125)
    geom = estimate(
        data, RULE | {"within_staircase": "geometric_mean"}, {"A": [1, 2]}, "completed"
    )
    assert geom["staircase_thresholds"]["1"] == pytest.approx(0.03)
    assert not estimate(data, RULE, {"A": [1, 2, 3]}, "completed")[
        "condition_thresholds"
    ]
    assert not estimate(data, RULE, {"A": [1, 2]}, "failed")["condition_thresholds"]


def test_psychometric_observer_has_known_threshold_and_strength_dependence():
    observer = PsychometricObserver(threshold=0.02, lapse=0.03)
    assert observer.probability(0.02) == pytest.approx(observer.threshold_probability)
    assert observer.probability(0) == 0.5
    assert (
        observer.probability(0.001)
        < observer.probability(0.02)
        < observer.probability(0.2)
        < 0.97
    )


def test_seeded_recovery_reports_bias_variability_and_boundary_censoring():
    result = recover(seeds=30, lapse=0)
    assert result == recover(seeds=30, lapse=0)
    assert result["successful_runs"] >= 28
    assert abs(result["median_log10_bias"]) < 0.15
    low, high = result["between_run_16_84_percentiles"]
    assert low < high
    boundary = recover(seeds=10, threshold=0.8)
    assert boundary["boundary_runs"] == 10 and boundary["median_estimate"] is None
    assert operating_point(4, 1, 0.36, 0.30294) == pytest.approx(0.8584, abs=0.0001)
    with pytest.raises(ValueError):
        operating_point(4, 2, 0.36, 0.30294)


def test_full_pipeline_primary_matches_posthoc_and_keeps_protocol_description(tmp_path):
    from simulations.run import simulate
    from psychophysics_lab.analysis.thresholds import analyse_thresholds

    artifacts, _ = simulate(
        repo_root=ROOT,
        data_root=tmp_path,
        experiment_id="csf_thesis",
        seed=5,
        values={
            "frequencies_cpd": "2",
            "staircases_per_condition": 1,
            "reversal_termination": 4,
            "threshold_reversals": 2,
            "max_trials": 500,
            "starting_contrast": 0.02,
        },
        analyse=False,
    )
    assert artifacts.status == "completed"
    saved = json.loads(
        (artifacts.run_directory / "primary_thresholds.json").read_text()
    )
    result = analyse_thresholds(
        data_root=tmp_path, run_directory=artifacts.run_directory, create_plot=False
    )
    later = json.loads(result.summary_json.read_text())
    assert saved == later
    resolved = json.loads(
        (artifacts.run_directory / "resolved_experiment.json").read_text()
    )
    assert "reversal_contrasts" in resolved and "scientific_specification" in resolved
    with pytest.raises(ValueError, match="exploratory=True"):
        analyse_thresholds(
            data_root=tmp_path,
            run_directory=artifacts.run_directory,
            last_n_reversals=1,
        )
    exploratory = analyse_thresholds(
        data_root=tmp_path,
        run_directory=artifacts.run_directory,
        last_n_reversals=1,
        exploratory=True,
        create_plot=False,
    )
    assert (
        json.loads(exploratory.summary_json.read_text())["analysis_role"]
        == "exploratory"
    )


def test_primary_rejects_misattributed_conditions():
    with pytest.raises(ValueError, match="staircase/condition"):
        estimate(
            rows(1, [0.01, 0.02], condition="wrong"), RULE, {"A": [1]}, "completed"
        )


@pytest.mark.parametrize(
    "identity",
    [
        "line_position_baseline",
        "line_position_flanker",
        "ellipse_major_axis",
        "ellipse_centre",
    ],
)
def test_new_protocols_finish_and_reproduce_primary_analysis(tmp_path, identity):
    from simulations.run import simulate
    from psychophysics_lab.analysis.thresholds import analyse_thresholds

    class ScriptedObserver:
        def simulation_parameters(self):
            return {"pattern": "four correct, one incorrect"}

        def probability_correct(self, condition, state, stimuli):
            return 0.0 if state["staircase_trial_index"] % 5 == 0 else 1.0

    values = {
        "staircases_per_condition": 1,
        "reversal_termination": 4,
        "threshold_reversals": 2,
        "max_trials": 200,
    }
    if identity.startswith("line_"):
        values.update(positions_deg="0", probe_vertical_offset_deg=0.5)
        if identity.endswith("flanker"):
            values["flanker_cpd"] = 2.0
    else:
        values.update(aspect_ratios="1", ring_increment=0.1)
        if identity == "ellipse_major_axis":
            values["positions_deg"] = "0"
    artifacts, _ = simulate(
        repo_root=ROOT,
        data_root=tmp_path,
        experiment_id=identity,
        values=values,
        observer=ScriptedObserver(),
        analyse=False,
    )
    assert artifacts.status == "completed"
    saved = json.loads(
        (artifacts.run_directory / "primary_thresholds.json").read_text()
    )
    assert saved["condition_thresholds"]
    result = analyse_thresholds(
        data_root=tmp_path, run_directory=artifacts.run_directory, create_plot=False
    )
    assert saved == json.loads(result.summary_json.read_text())
    assert all(
        s.reversal_count == 4 and s.retained_count == 2
        for s in result.staircase_thresholds
    )


def test_normal_simulation_uses_shared_configuration(tmp_path):
    import asyncio
    from textual.widgets import Button, Select
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp
    async def check():
        app = PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path)
        async with app.run_test(size=(100,40)) as pilot:
            app.open_hub_page("simulations")
            await pilot.pause()
            assert app.run_intent == "simulation"
            assert app.screen.query_one("#run-intent",Select).value == "simulation"
            assert not app.screen.query_one("#nav-simulations",Button).display
            assert not get_experiment(str(app.screen.query_one("#experiment",Select).value)).historical
    asyncio.run(check())


def test_finalisation_failure_revokes_a_previously_computed_primary_result(
    tmp_path, monkeypatch
):
    from simulations.run import simulate
    from psychophysics_lab.researcher import RunContext

    def fail_cleanup(self):
        raise RuntimeError("injected cleanup failure")

    monkeypatch.setattr(RunContext, "close", fail_cleanup)
    artifacts, _ = simulate(
        repo_root=ROOT,
        data_root=tmp_path,
        experiment_id="csf_thesis",
        seed=5,
        values={
            "frequencies_cpd": "2",
            "staircases_per_condition": 1,
            "reversal_termination": 4,
            "threshold_reversals": 2,
            "max_trials": 500,
            "starting_contrast": 0.02,
        },
        analyse=False,
    )
    assert artifacts.status == "error"
    saved = json.loads(
        (artifacts.run_directory / "primary_thresholds.json").read_text()
    )
    assert saved["run_status"] == "error" and not saved["condition_thresholds"]
