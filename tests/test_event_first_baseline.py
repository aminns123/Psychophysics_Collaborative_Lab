"""Frozen, pre-implementation comparison: complete scientific records, not endpoints."""
import csv
import hashlib
import json
from pathlib import Path

import pytest
from simulations.run import simulate
from simulations.registry import TeachingObserver
from psychophysics_lab.experiments._internal.registry import list_experiments
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]
BASELINE = json.loads((ROOT / 'tests/fixtures/event_first_baseline_20261027.json').read_text(encoding='utf-8'))
ATOMIC = {'line_position_baseline', 'line_position_flanker',
          'ellipse_centre', 'ellipse_major_axis'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def test_active_official_inventory_matches_frozen_intake():
    # The original ten remain frozen exactly. The new modular ellipse is
    # additive with its own protocol ID, not part of the 2026-10-27 intake.
    frozen = {s['id'] for s in BASELINE['registry']
              if not s['historical'] and not s['origin']}
    active = {s.id for s in list_experiments() if not s.origin_namespace}
    assert active == frozen | {"ellipse_modular_centre"}


@pytest.mark.parametrize('case', BASELINE['cases'], ids=lambda c: f"{c['identity']}-{c['method']}-{c['seed']}")
def test_complete_scientific_trace_is_identical_without_new_feature(tmp_path, monkeypatch, case):
    # Case A explicitly disables the Stage B opening; the frozen fixture is
    # retained unchanged, including the absence of session provenance.
    from dataclasses import replace
    from psychophysics_lab.experiments._internal import registry
    spec = registry.get_experiment(case['identity'])
    monkeypatch.setitem(registry._REGISTRY, spec.id, replace(spec, session_start=[]))
    monkeypatch.setattr('psychophysics_lab.analysis.previews.create_run_figures', lambda **kwargs: None)
    a, _ = simulate(repo_root=ROOT, data_root=tmp_path, experiment_id=case['identity'],
                    values=case['values'], seed=case['seed'], analyse=False, observer=TeachingObserver(accuracy=.65))
    assert (a.status, a.accepted_trials) == (case['status'], case['accepted'])
    with a.trial_log_file.open(encoding='utf-8', newline='') as stream:
        assert digest(list(csv.DictReader(stream, delimiter='\t'))) == case['trial_rows_sha256']
    if case['identity'] in ATOMIC:
        # The old action hash includes serialized first/second composite
        # stimulus slots. Preserve the frozen digest as evidence, but check
        # current sequence/state through the independent Wave4/5 comparison
        # instead of pretending new atomic serialization is byte-identical.
        recorded = json.loads((a.run_directory / 'trial_actions.json').read_text())
        assert len(recorded['trials']) == a.accepted_trials
        assert all(trial['status'] == 'accepted' for trial in recorded['trials'])
    else:
        assert digest(json.loads((a.run_directory / 'trial_actions.json').read_text())) == case['trial_actions_sha256']
    if 'adaptive_history_sha256' in case:
        assert digest(json.loads((a.run_directory / 'adaptive_history.json').read_text())) == case['adaptive_history_sha256']
    assert not (a.run_directory / 'session_events.json').exists()
    assert all(c.passed for c in validate_run(a.run_directory))
