"""Independent finite alternating-side flash task; no imports from official science."""
from psychophysics_lab.researcher import (
    ConfigField, ResponseParadigm, Show, WaitForKey, CollectResponse, Stimulus,
    experiment, legacy_trial_factory,
)

# A1: experimental choices, intentionally unfamiliar parameter names.
FIELDS = (
    ConfigField('trial_count', 'Accepted flashes', 'int', 4, minimum=2, maximum=20),
    ConfigField('gap_from_fixation_deg', 'Flash distance from fixation', 'float', .8,
                minimum=.1, maximum=2., units='degrees', section='Flash protocol'),
    ConfigField('flash_hold_ms', 'Flash exposure', 'int', 80, minimum=10, maximum=500,
                units='ms', section='Flash protocol'),
)
RESPONSES = ResponseParadigm('audit_side', ('toward_left', 'toward_right'), ('Z', 'X'))
SESSION_START = [WaitForKey('ready', key='SPACE', slot='ready_fixation'),
                 Show('settle', slot='ready_fixation', duration=10)]
MEASUREMENT_UNITS = {'flash_x_deg': 'degrees', 'flash_hold_ms': 'ms'}

def trial_events(settings, condition):
    return [Show('fixate', slot='ready_fixation', duration=20),
            Show('flash', duration='flash_hold_ms', stimuli=(Stimulus('target', x_deg=condition['x_deg']),)),
            CollectResponse(actions=RESPONSES.alternatives, slot='ready_fixation')]

def trial_record(run, condition, state):
    return {'measurements': {'flash_x_deg': condition['x_deg'], 'flash_hold_ms': run.values['flash_hold_ms']}}

# A2: fixed chronological alternation; no staircase or hidden condition manager.
def make_conditions(settings):
    return [{'id': i+1, 'value': 'left' if i%2 == 0 else 'right', 'target': i%2,
             'x_deg': (-1 if i%2 == 0 else 1)*settings['gap_from_fixation_deg']}
            for i in range(settings['trial_count'])]

def initialise_experiment(run, conditions):
    run.initialise(expected_trials=len(conditions), resolution={'selection': 'alternating left/right',
                   'condition_definitions': conditions, 'response_goal': len(conditions)})
    return {'next': 0}

def choose_condition(run, conditions, state):
    return conditions[state['next']]

def prepare_stimuli(run, condition, state):
    return {'target': run.stimulus_parameters('target', offset_deg=0),
            'ready_fixation': run.stimulus_parameters('ready_fixation')}

# B: existing execution and recorder only.
def procedure(run):
    conditions = make_conditions(run.values)
    state = initialise_experiment(run, conditions)
    while state['next'] < len(conditions):
        condition = choose_condition(run, conditions, state)
        run.play_trial(trial_events(run.values, condition), target=condition['target'],
            condition=condition['value'], parameters_by_slot=prepare_stimuli(run, condition, state),
            **trial_record(run, condition, state))
        state['next'] += 1
    run.complete()

make_trial = legacy_trial_factory(trial_events)
SPEC = experiment(id='auditlab__alternating_flash', name='Independent alternating flash',
    description='Alternate left/right flashes at a declared distance and exposure.',
    procedure=procedure, fields=FIELDS, responses=RESPONSES, session_start=SESSION_START,
    stimulus_slots={'target': 'simple_line', 'ready_fixation': 'fixation'},
    stimulus_defaults={'target': 'example_stimulus', 'ready_fixation': 'fixation_cross'},
    calibration_requirements=('geometry',), monitor_capabilities=('display_binding', 'resolution'), supports_simulation=True,
    source_paths=('experiments/auditlab__alternating_flash.py',))
