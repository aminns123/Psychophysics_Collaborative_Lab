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
    archived = {
        "line_position_baseline": "9ffa7a908b68e0b05b264aec4bb97ad48da6d9d4",
        "line_position_flanker": "e583fde32713d1794c5343309c7b412c9446f15b",
        "ellipse_centre": "4860552bbbe3677ebf74b792b083e307307a0d85",
        "ellipse_major_axis": "2a18b66c398f7d86bedbe1b3c77151737a53d20b",
    }
    import hashlib
    for identity in PROTOCOLS:
        raw = (ROOT / "src/psychophysics_lab/experiments" /
               (identity + ".py")).read_bytes().replace(b"\r\n", b"\n")
        if identity in archived:
            # #207 intentionally replaced the composite protocols. The exact
            # pre-207 source is immutable evidence, not the current authoring
            # representation; source-only reversibility no longer applies.
            old = (ROOT / "outdated_code/pre_atomic_207/src/psychophysics_lab/experiments" /
                   (identity + ".py")).read_bytes().replace(b"\r\n", b"\n")
            digest = hashlib.sha1(f"blob {len(old)}\0".encode() + old).hexdigest()
            assert digest == archived[identity]
            assert old != raw
            continue
        restored = historical_one_map_source(ROOT, identity, raw)
        assert restored != raw
        assert b"STIMULUS_SLOTS" in restored
        assert b"STIMULUS_DEFAULTS" in restored
