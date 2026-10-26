"""Constant-stimuli CSF is opt-in; adaptive settings and canonical trial schema stay intact."""
from collections import Counter
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from psychophysics_lab.experiments import contrast_sensitivity as csf
from psychophysics_lab.data.trials import TRIAL_COLUMNS, TRIAL_SCHEMA_VERSION


def values(**changes):
    return csf.SPEC.normalise_values({
        "contrast_method": "constant_stimuli",
        "frequencies_cpd": "2,4,8",
        "fixed_contrasts": "0.02,0.04,0.08,0.16",
        "fixed_repetitions": 10,
        **changes,
    })


def test_method_defaults_to_existing_adaptive_path():
    settings = csf.SPEC.normalise_values({})
    assert settings["contrast_method"] == "adaptive"
    assert csf.make_conditions(settings) == [
        {"id": i, "frequency_cpd": frequency, "repeat": repeat}
        for i, (frequency, repeat) in enumerate(
            [(f, r) for f in (2., 8.) for r in range(1, 5)], 1)
    ]
    assert not list(csf.validate_settings(settings))


def test_condition_level_repetition_counts_target_balancing_and_determinism():
    settings = values()
    first = csf.make_fixed_schedule(settings, 9)
    assert first == csf.make_fixed_schedule(settings, 9)
    assert first != csf.make_fixed_schedule(settings, 10)
    assert len(first) == 3 * 4 * 10
    cells = Counter((row["frequency_cpd"], row["contrast"]) for row in first)
    assert set(cells.values()) == {10}
    for cell in cells:
        targets = Counter(row["target"] for row in first
                          if (row["frequency_cpd"], row["contrast"]) == cell)
        assert targets == {0: 5, 1: 5}
    assert {row["frequency_cpd"] for row in first} == {2., 4., 8.}
    assert not list(csf.validate_settings(settings))


def test_odd_repetitions_balance_targets_with_at_most_one_extra():
    plan = csf.make_fixed_schedule(values(fixed_repetitions=7), 1)
    for frequency in (2., 4., 8.):
        for contrast in (.02, .04, .08, .16):
            sides = Counter(t["target"] for t in plan
                            if t["frequency_cpd"] == frequency and t["contrast"] == contrast)
            assert abs(sides[0]-sides[1]) <= 1


@pytest.mark.parametrize("bad", ["", "0.2,,0.4", "nan", "inf", "1.1",
                                  "-0.1", "0.1,0.1", "abc"])
def test_invalid_contrasts_are_rejected_before_acquisition(bad):
    settings = values(fixed_contrasts=bad)
    assert list(csf.validate_settings(settings))
    with pytest.raises(ValueError):
        csf.make_fixed_schedule(settings, 1)


def test_digital_background_headroom_and_zero_contrast_catch_level():
    settings = values(background_intensity=.3, fixed_contrasts="0,0.2,0.6")
    plan = csf.make_fixed_schedule(settings, 2)
    assert len(plan) == 90
    assert 0. in {trial["contrast"] for trial in plan}
    assert not list(csf.validate_settings(settings))
    bad = values(background_intensity=.3, fixed_contrasts="0.7")
    assert "between 0 and" in next(iter(csf.validate_settings(bad)))


def test_planned_count_exceeding_declared_ceiling_needs_explicit_change():
    settings = values(max_trials=20)
    assert "120 trials" in next(iter(csf.validate_settings(settings)))
    with pytest.raises(ValueError, match="max_trials"):
        csf.make_fixed_schedule(settings, 1)


class FakeRun:
    def __init__(self, settings):
        self.values = settings
        self.seed = 17
        self.responses = SimpleNamespace(keys=("LEFT", "RIGHT"))
        self.seen = []
        self.completed = False
        self.resolution = None
        self.saved_resolution = None

    def initialise(self, **kw):
        self.resolution = kw

    def stimulus_parameters(self, slot, **parameters):
        return parameters

    @contextmanager
    def trial(self, timeline, **kwargs):
        self.seen.append(kwargs)
        target = kwargs["target"]
        yield SimpleNamespace(response={"alternative": target, "correct": True})

    def save_resolution(self, **details):
        self.saved_resolution = details

    def complete(self):
        self.completed = True


def test_fixed_procedure_uses_original_timeline_and_canonical_contrast_column():
    run = FakeRun(values(frequencies_cpd="2,4", fixed_contrasts=".05,.1",
                         fixed_repetitions=3))
    csf.procedure(run)
    assert run.completed and len(run.seen) == 12
    assert run.resolution["expected_trials"] == 12
    assert run.saved_resolution["trial_selection_method"] == "constant_stimuli"
    for kwargs in run.seen:
        assert kwargs["condition"] in {2., 4.}
        assert kwargs["record_from_state"] == {
            "presented_display_contrast": "contrast"}
        assert kwargs["state"]["contrast"] in {.05, .1}
        assert kwargs["measurements"]["spatial_frequency_cpd"] == kwargs["condition"]
        assert "staircase_id" not in kwargs["record_from_state"]
        assert kwargs["parameters_by_slot"]["grating"]["contrast"] == kwargs["state"]["contrast"]
    assert TRIAL_SCHEMA_VERSION == 1
    assert "presented_display_contrast" in TRIAL_COLUMNS
    assert "staircase_id" in TRIAL_COLUMNS
    assert "target_alternative" in TRIAL_COLUMNS
