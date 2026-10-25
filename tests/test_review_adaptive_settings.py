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
    # Preserve the required study-specific selections and the scientific
    # constraint that retained reversals cannot exceed those collected.
    # These are synthetic review-only selections, not human-run defaults.
    selected = {'n_down': 3, 'n_up': 2, 'logUNIT_UP': .21,
                'logUNIT_DW': .07, 'reversal_termination': 6,
                'threshold_reversals': 4, 'initial_one_down_limit': 2}
    study_inputs = {
        'contrast_sensitivity': {},
        'line_position_baseline': {
            'probe_vertical_offset_deg': .2, 'positions_deg': '0',
        },
        'ellipse_centre': {'ring_increment': .1},
    }
    selected.update(study_inputs[identity])
    # Each study receives only fields it actually declares. Do not weaken
    # the spec's rejection of unknown inputs or invent required study defaults.
    assert set(selected) <= {field.key for field in spec.fields}
    values = spec.normalise_values(selected)
    snapshots = resolve_stimuli(spec, values, repo_root=ROOT)
    description = describe_settings(spec, values, snapshots)
    rows = review_rows(spec, values, snapshots, description)
    fields = {field.key: field for field in spec.fields}
    for key in spec.adaptive.controls:
        assert ('Adaptive', fields[key].display_label, str(values[key])) in [row[:3] for row in rows]
    # Each actual configurable staircase input occurs only once, in the
    # editable Adaptive section. Don't repeat it under Run plan.
    adaptive_keys = ('n_down', 'n_up', 'logUNIT_UP', 'logUNIT_DW',
                     'reversal_termination', 'initial_one_down_limit')
    for key in adaptive_keys:
        matches = [row for row in rows if row[0] == 'Adaptive' and
                   row[1] == fields[key].display_label]
        assert len(matches) == 1
        assert matches[0][2] == str(values[key])
    duplicated_rule_keys = {
        'adaptive_rule / algorithm', 'adaptive_rule / n_down',
        'adaptive_rule / n_up', 'adaptive_rule / log_up',
        'adaptive_rule / log_down', 'adaptive_rule / reversal_limit',
        'adaptive_rule / initial_one_down_limit', 'adaptive_rule / max_trials',
    }
    assert not any(group == 'Run plan' and label in duplicated_rule_keys
                   for group, label, *_ in rows)
    assert not any(group == 'Adaptive scale' and label == 'Response rule'
                   for group, label, *_ in rows)
    estimator = description['resolution']['primary_estimator']
    threshold_rows = {(group, label): value for group, label, value, _ in rows}
    assert threshold_rows[('Threshold estimation', 'Within-staircase method')] == estimator['within_staircase']
    assert threshold_rows[('Threshold estimation', 'Across-staircase method')] == estimator['across_staircases']
    assert threshold_rows[('Threshold estimation', 'Retained reversals')] == str(values['threshold_reversals'])
    targets = targets_for_rows(spec, snapshots, description, rows,
                              {'experiment': None, 'stimuli': {}}, ROOT)
    step_row = next(i for i, row in enumerate(rows) if row[:2] == ('Adaptive', fields['logUNIT_UP'].display_label))
    assert targets[step_row]['kind'] == 'experiment_json'
    assert targets[step_row]['key'] == 'logUNIT_UP'
    resolved_row = next(i for i, row in enumerate(rows)
                        if row[:2] == ('Threshold estimation', 'Within-staircase method'))
    assert targets[resolved_row]['kind'] == 'python'
    assert 'def primary_rule' in targets[resolved_row]['path'].read_text(encoding='utf-8').splitlines()[targets[resolved_row]['line']-1]


def test_review_handles_procedures_without_planning_metadata():
    spec = get_experiment('example_experiment')
    values = spec.field_defaults()
    snapshots = resolve_stimuli(spec, values, repo_root=ROOT)
    description = describe_settings(spec, values, snapshots)
    description.pop('resolution', None)
    rows = review_rows(spec, values, snapshots, description)
    assert rows
    assert not any(row[0] == 'Run plan' for row in rows)


def test_review_keeps_explicit_resolved_differences():
    """A different effective rule must not be silently hidden as a duplicate."""
    spec = get_experiment('contrast_sensitivity')
    values = spec.field_defaults()
    snapshots = resolve_stimuli(spec, values, repo_root=ROOT)
    description = describe_settings(spec, values, snapshots)
    description['resolution']['adaptive_rule']['n_down'] = values['n_down'] + 1
    rows = review_rows(spec, values, snapshots, description)
    assert any(group == 'Run plan' and label == 'Effective adaptive_rule / n_down'
               and value == str(values['n_down'] + 1)
               for group, label, value, _ in rows)
