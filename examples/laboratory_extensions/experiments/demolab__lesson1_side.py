"""Lesson 1: can you report which side contains a line? Finite discrimination."""
from psychophysics_lab.researcher import (
    ConfigField, ResponseParadigm, Show, Stimulus, CollectResponse, WaitForKey,
    UpdateState, experiment, legacy_trial_factory,
)

# PART A1 — EXPERIMENTAL CHOICES
# TRY CHANGING: geometry in degrees, requested durations in ms, then Test again.
FIELDS = (
    ConfigField('trial_count','Accepted responses','int',8,minimum=1,maximum=200),
    ConfigField('eccentricity_deg','Distance left/right of fixation','float',1.,units='degrees',minimum=.2,maximum=2.),
    ConfigField('line_length_deg','Line length','float',.8,units='degrees',minimum=.2,maximum=1.5),
    ConfigField('line_width_deg','Line width','float',.08,units='degrees',minimum=.02,maximum=.2),
    ConfigField('fixation_ms','Fixation','int',300,units='ms',minimum=1),
    ConfigField('stimulus_ms','Line exposure','int',200,units='ms',minimum=1),
)
# TRY CHANGING: F/J keys (or the generic response-key field in Review).
RESPONSES = ResponseParadigm('lesson_side',('left','right'),('F','J'))
STIMULUS_SLOTS = {'target':'line','fixation':'fixation'}
STIMULUS_DEFAULTS = {'target':'oriented_line','fixation':'fixation_cross'}
# SPACE opens the session once; it is not a scientific response. [] disables it.
SESSION_START = [WaitForKey('ready',key='SPACE',slot='fixation',instructions='Press SPACE when ready'),
                 Show('settle',slot='fixation',duration=1000)]

def trial_events(settings, condition):
    return [Show('fixation',slot='fixation',duration='fixation_ms'),
            Show('line',stimuli=(Stimulus('target',x_deg=condition['x_deg']),),duration='stimulus_ms'),
            CollectResponse(actions=RESPONSES.alternatives,slot='fixation')]

MEASUREMENT_UNITS = {'line_x_deg':'degrees','line_length_deg':'degrees','line_width_deg':'degrees',
                     'requested_exposure_ms':'ms','target_side':'left or right'}

def trial_measurements(settings, condition):
    # TRY CHANGING: add a finite scalar here AND its unit above; no JSON/TSV code.
    return {'line_x_deg':condition['x_deg'],'line_length_deg':settings['line_length_deg'],
            'line_width_deg':settings['line_width_deg'],'requested_exposure_ms':settings['stimulus_ms'],
            'target_side':RESPONSES.alternatives[condition['target']]}

# PART A2 — SCIENTIFIC METHODS
# SCIENTIFIC DECISION: alternate sides, including one extra left trial for odd counts.
# A target alternative is not an independent scientific condition or staircase.
def make_conditions(settings):
    return [{'value':settings['eccentricity_deg'],'target':i%2,
             'x_deg':(-1 if i%2==0 else 1)*settings['eccentricity_deg']}
            for i in range(settings['trial_count'])]

def choose_condition(run, conditions, state):
    return conditions[run.accepted_trials]

def prepare_stimuli(run, condition, state):
    # DO NOT CONFUSE: 0.8 is a digital command, not measured luminance.
    return {'target':run.stimulus_parameters(length_deg=run.values['line_length_deg'],
                 width_deg=run.values['line_width_deg'],intensity=.8)}

def interpret_response(condition, response):
    assert response['correct']==(response['alternative']==condition['target'])
    return response

def count_correct(state, response):
    return state | {'correct_count':state['correct_count']+int(response['correct'])}

def is_finished(run, conditions, state):
    # SCIENTIFIC DECISION: a finite response goal, not a threshold estimator.
    return run.accepted_trials>=len(conditions)

def initialise_experiment(run, conditions):
    run.initialise(expected_trials=len(conditions),resolution={'conditions':conditions,
        'measurement_units':MEASUREMENT_UNITS,'scientific_estimator':None})
    return {'correct_count':0}

# PART B — FRAMEWORK INTEGRATION
def trial_record(run, condition, state):
    return {'state':state,'measurements':trial_measurements(run.values,condition),
            'instructions':'   '.join(f'{alt}: {key}' for alt,key in zip(run.responses.alternatives,run.responses.keys))}

def procedure(run):
    conditions=make_conditions(run.values)
    state=initialise_experiment(run,conditions)
    while not is_finished(run,conditions,state):
        condition=choose_condition(run,conditions,state)
        with run.trial(trial_events(run.values,condition),target=condition['target'],condition=condition['value'],
                       parameters_by_slot=prepare_stimuli(run,condition,state),**trial_record(run,condition,state)) as trial:
            response=interpret_response(condition,trial.response)
            trial.apply(UpdateState(count_correct))
            state=dict(trial.state)
    run.complete()

# FRAMEWORK CONNECTION: discovery and recording use the same public API as official science.
make_trial=legacy_trial_factory(trial_events)
SPEC=experiment(id='demolab__lesson1_side',name='Lesson 1 — simple left/right',description=__doc__,
    procedure=procedure,fields=FIELDS,responses=RESPONSES,session_start=SESSION_START,
    stimulus_slots=STIMULUS_SLOTS,stimulus_defaults=STIMULUS_DEFAULTS,
    stimulus_parameter_controls={'target':{'length_deg':'line_length_deg','width_deg':'line_width_deg'}},
    supports_simulation=True,calibration_requirements=('geometry',),monitor_capabilities=('display_binding','resolution'),
    source_paths=('experiments/demolab__lesson1_side.py',))
