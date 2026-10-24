"""Review reports selected adaptive settings and the experiment's own run plan."""
from pathlib import Path
import pytest
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.config.stimulus_parameters import resolve_stimuli
from psychophysics_lab.ui.settings_review import describe_settings, review_rows
from psychophysics_lab.ui.review_files import targets_for_rows

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('identity', ['contrast_sensitivity', 'line_position_baseline', 'ellipse_centre'])
def test_review_adaptive_settings_and_resolved_rules_follow_selected_values(identity):
    spec = get_experiment(identity)
    values = spec.normalise_values({'n_down': 3, 'n_up': 2, 'logUNIT_UP': .21,
        'logUNIT_DW': .07, 'reversal_termination': 6, 'initial_one_down_limit': 2})
    snapshots = resolve_stimuli(spec, values, repo_root=ROOT)
    description = describe_settings(spec, values, snapshots)
    rows = review_rows(spec, values, snapshots, description)
    fields = {field.key: field for field in spec.fields}
    for key in spec.adaptive.controls:
        assert ('Adaptive', fields[key].display_label, str(values[key])) in [row[:3] for row in rows]
    plan = {(group, label): value for group, label, value, _ in rows}
    assert plan['Run plan', 'adaptive_rule / n_down'] == '3'
    assert plan['Run plan', 'adaptive_rule / n_up'] == '2'
    assert plan['Run plan', 'adaptive_rule / log_up'] == '0.21'
    assert plan['Run plan', 'adaptive_rule / log_down'] == '0.07'
    assert plan['Run plan', 'adaptive_rule / reversal_limit'] == '6'
    assert plan['Run plan', 'adaptive_rule / initial_one_down_limit'] == '2'
    assert any(group == 'Run plan' and 'threshold' in label for group, label, *_ in rows)
    targets = targets_for_rows(spec, snapshots, description, rows,
                              {'experiment': None, 'stimuli': {}}, ROOT)
    step_row = next(i for i, row in enumerate(rows) if row[:2] == ('Adaptive', fields['logUNIT_UP'].display_label))
    assert targets[step_row]['kind'] == 'experiment_json'
    assert targets[step_row]['key'] == 'logUNIT_UP'
    resolved_row = next(i for i, row in enumerate(rows) if row[:2] == ('Run plan', 'adaptive_rule / log_up'))
    assert targets[resolved_row]['kind'] == 'python'
    assert 'initialise_experiment' in targets[resolved_row]['path'].read_text(encoding='utf-8').splitlines()[targets[resolved_row]['line']-1]


def test_review_handles_procedures_without_planning_metadata():
    spec = get_experiment('example_experiment')
    values = spec.field_defaults()
    snapshots = resolve_stimuli(spec, values, repo_root=ROOT)
    description = describe_settings(spec, values, snapshots)
    description.pop('resolution', None)
    rows = review_rows(spec, values, snapshots, description)
    assert rows
    assert not any(row[0] == 'Run plan' for row in rows)
