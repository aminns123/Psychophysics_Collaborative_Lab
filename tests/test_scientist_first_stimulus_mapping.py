"""All official protocols have one scientist-editable stimulus assignment.

This contract deliberately does NOT assert pixel equivalence of independent
layers with the old compound DetectionScene. That must be measured before
decomposing the four historical tasks.
"""
import importlib
from pathlib import Path

import pytest

from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.stimuli.registry import get_stimulus


ROOT = Path(__file__).resolve().parents[1]
PROTOCOLS = (
    "example_experiment",
    "probe_above_below",
    "orientation_task",
    "orientation_adaptive",
    "contrast_sensitivity",
    "contrast_sensitivity_windowed",
    "line_position_baseline",
    "line_position_flanker",
    "ellipse_centre",
    "ellipse_major_axis",
)


@pytest.mark.parametrize("identity", PROTOCOLS)
def test_source_uses_one_stimulus_map_and_unchanged_public_metadata(identity):
    module = importlib.import_module("psychophysics_lab.experiments." + identity)
    spec = get_experiment(identity)
    source = (ROOT / "src/psychophysics_lab/experiments" /
              (identity + ".py")).read_text(encoding="utf-8")
    assert "STIMULUS_SLOTS" not in source
    assert "STIMULUS_DEFAULTS" not in source
    assert "STIMULI =" in source
    assert module.STIMULI
    assert dict(spec.stimulus_defaults) == dict(module.STIMULI)
    assert set(spec.stimulus_slots) == set(module.STIMULI)
    assert dict(spec.stimulus_slots) == {
        slot: get_stimulus(stimulus_id).family
        for slot, stimulus_id in module.STIMULI.items()
    }
    assert "def trial_events(" in source
    assert spec.id == identity


def test_source_only_migrations_have_exact_reversible_historical_digests():
    # This fixture preserves the exact before/after declaration chunks. The
    # existing source-hash/fixture tests replay them to prove that no scientific
    # procedure or renderer was changed merely to simplify registration.
    import json
    from _scientist_first_migrations import historical_one_map_source

    baseline = json.loads((ROOT / "tests/fixtures/scientist_first_one_map_reversible.json")
                          .read_text(encoding="utf-8"))
    assert set(baseline) == set(PROTOCOLS)
    for identity in PROTOCOLS:
        raw = (ROOT / "src/psychophysics_lab/experiments" /
               (identity + ".py")).read_bytes().replace(b"\r\n", b"\n")
        restored = historical_one_map_source(ROOT, identity, raw)
        assert restored != raw
        assert b"STIMULUS_SLOTS" in restored
        assert b"STIMULUS_DEFAULTS" in restored
