"""Lesson 3: the same left/right question at distance × length cells, with a custom soft-edged line and optional cues.

One independent finite teaching track per distance × length cell. This is NOT a threshold study.
"""
import random
from math import log10
from psychophysics_lab.methods.contrast import (
    AdaptiveContrastMethod, ConstantContrastMethod, fixed_level_schedule,
    parse_fixed_strengths, run_contrast_experiment,
)
from psychophysics_lab.methods.teaching import teaching_method_fields, teaching_adaptive_fields, fixed_teaching_record
from psychophysics_lab.researcher import (
    ConfigField, AdaptiveSelection, StaircaseConfig, Step, UpdateAdaptive,
    ResponseParadigm, Show, Stimulus, CollectResponse, WaitForKey, Beep,
    experiment, legacy_trial_factory,
)
from psychophysics_lab.adaptive.steps import bounded_log_step

# PART A1 — EXPERIMENTAL CHOICES
# TRY CHANGING: distance × length factors. Each cell has its own finite track.
# TRY CHANGING: enable requested audio, then inspect event plans; this is not audio timing qualification.
# Edit the independent LearningLine class in the local stimulus_library.py.
# DO NOT CONFUSE: a richer teaching study with a validated threshold protocol.
FIELDS = (
    ConfigField('eccentricities_deg','Left/right distances','text','1,2',units='degrees'),
    ConfigField('trial_count','Finite adaptive response goal','int',16,minimum=1,maximum=500),
    ConfigField('lengths_deg','Line lengths','text','.6,1.2',units='degrees'),
    ConfigField('edge_deg','Custom line edge transition','float',.01,units='degrees',minimum=.002,maximum=.02),
    ConfigField('retention_ms','Post-stimulus gap','int',150,units='ms',minimum=1),
    ConfigField('audio_cues','Request audio cues','choice',0,choices=(0,1)),
    ConfigField('line_width_deg','Line width','float',.08,units='degrees',minimum=.02,maximum=.2),
    ConfigField('fixation_ms','Fixation','int',300,units='ms',minimum=1),
    ConfigField('stimulus_ms','Line exposure','int',200,units='ms',minimum=1),
) + teaching_method_fields(strengths='0,.1,.3',label='Digital line increment above 0.5') + teaching_adaptive_fields()
RESPONSES = ResponseParadigm('lesson_side',('left','right'),('F','J'))
STIMULUS_SLOTS = {'target':'learning_line','fixation':'fixation'}
STIMULUS_DEFAULTS = {'target':'demolab__learning_line','fixation':'fixation_cross'}
SESSION_START = [WaitForKey('ready',key='SPACE',slot='fixation',instructions='Press SPACE when ready'),
                 Show('settle',slot='fixation',duration=1000)]

def trial_events(settings, condition):
    x=(-1 if condition['target']==0 else 1)*condition['eccentricity_deg']
    return [Show('fixation',slot='fixation',duration='fixation_ms'),
            Show('line',stimuli=(Stimulus('target',x_deg=x),),duration='stimulus_ms',beep=Beep(550,35) if settings['audio_cues'] else None),
            Show('retention',slot='fixation',duration='retention_ms'),
            CollectResponse(actions=RESPONSES.alternatives,slot='fixation',beep=Beep(750,35) if settings['audio_cues'] else None)]

MEASUREMENT_UNITS = {'eccentricity_deg':'degrees','line_x_deg':'degrees','line_length_deg':'degrees',
    'line_width_deg':'degrees','requested_exposure_ms':'ms','requested_edge_deg':'degrees','requested_audio':'boolean audio request, not measured timing','requested_increment':'digital I_line - 0.5','target_side':'left or right',
    'fixed_repeat':'presentation within a condition/strength cell','presented_display_contrast':'digital I_line - 0.5'}

REVIEW_INACTIVE_FIELDS = {
    'adaptive': ('fixed_contrasts', 'fixed_repetitions'),
    'constant_stimuli': ('starting_strength', 'n_down', 'n_up', 'down_factor', 'up_factor', 'trial_count'),
}


def trial_measurements(settings, condition):
    # TRY CHANGING: add a scalar and explicit unit, then check the per-trial journal.
    return {'eccentricity_deg':condition['eccentricity_deg'],
        'line_x_deg':(-1 if condition['target']==0 else 1)*condition['eccentricity_deg'],
        'line_length_deg':condition['length_deg'],'line_width_deg':settings['line_width_deg'],
        'requested_exposure_ms':settings['stimulus_ms'],'requested_increment':condition['contrast'],'requested_edge_deg':settings['edge_deg'],'requested_audio':bool(settings['audio_cues']),'target_side':RESPONSES.alternatives[condition['target']]}

# PART A2 — SCIENTIFIC METHODS
# DO NOT CONFUSE: a distance × length cell is a condition; left/right is a target alternative;
# an adaptive track has its own response history; a fixed repeat has no staircase.
def make_conditions(settings):
    distances=parse_fixed_strengths(settings['eccentricities_deg'],minimum=.2,maximum=2.)
    lengths=parse_fixed_strengths(settings['lengths_deg'],minimum=.2,maximum=1.5)
    cells=[{'value':f'ecc={distance:g};length={length:g}','eccentricity_deg':distance,'length_deg':length}
           for distance in distances for length in lengths]
    return [dict(c,id=i+1) for i,c in enumerate(cells)]

def make_fixed_schedule(settings, seed):
    levels=parse_fixed_strengths(settings['fixed_contrasts'],maximum=.5)
    conditions=make_conditions(settings)
    count=len(conditions)*len(levels)*settings['fixed_repetitions']
    if count>settings['max_trials']:raise ValueError('Fixed plan exceeds max_trials; no truncation is performed.')
    return fixed_level_schedule(conditions,levels,settings['fixed_repetitions'],seed=seed,condition_field='value')

def initialise_experiment(run, conditions):
    # SCIENTIFIC DECISION: cycle cells and sides, then shuffle this finite order.
    # Strengths are NOT precomputed; the current track supplies them after each answer.
    order=[(i%len(conditions),(i//len(conditions))%2) for i in range(run.values['trial_count'])]
    random.Random(f'{run.seed}:lesson_order').shuffle(order)
    run.initialise(expected_trials=len(order),resolution={'condition_definitions':conditions,
        'response_goal':len(order),'scheduled_cells_and_targets':order,'random_seed':run.seed,'measurement_units':MEASUREMENT_UNITS,
        'strength_definition':'I_line = 0.5 + increment; not optical contrast',
        'stopping':'Finite accepted-response goal; not reversal convergence','scientific_estimator':None})
    algorithm=run.adaptive({c['id']:StaircaseConfig(run.values['n_down'],run.values['n_up'],len(order)+1)
        for c in conditions},run.values['max_trials'],starting_values={c['id']:run.values['starting_strength'] for c in conditions},
        response_goal=len(order))
    return {'adaptive':algorithm,'order':order,'contrasts':{c['id']:run.values['starting_strength'] for c in conditions}}

def choose_condition(run, conditions, state):
    index,target=state['order'][run.accepted_trials]
    c=conditions[index]
    return dict(c,target=target,contrast=state['contrasts'][c['id']])

def prepare_stimuli(run, condition, state):
    # DO NOT CONFUSE: digital increment, absolute command and measured luminance.
    return {'target':run.stimulus_parameters(length_deg=condition['length_deg'],edge_deg=run.values['edge_deg'],
        width_deg=run.values['line_width_deg'],intensity=.5+condition['contrast'])}

def interpret_response(condition, response):
    assert response['correct']==(response['alternative']==condition['target'])
    return response

def next_strength(values, response, step):
    # Shared counters decide step; the shared bounded numerical method executes it.
    exponent=-values['log_down'] if step==Step.DOWN else values['log_up'] if step==Step.UP else 0
    return bounded_log_step(values['contrast'],exponent,maximum=.5)

def update_experiment(run, condition, state, response, trial):
    identity=condition['id']
    trial.apply(UpdateAdaptive(state['adaptive'],identity,next_strength,state_key='next_contrast'),
                run.staircase_record_action(state['adaptive'],identity))
    state['contrasts'][identity]=trial.state['next_contrast']
    return state

def is_finished(run, conditions, state):
    return run.accepted_trials>=run.values['trial_count']

def finish_experiment(run, conditions, state):
    # SCIENTIFIC DECISION: response/accuracy and histories only. No threshold claim.
    run.complete()

def adaptive_method(run):
    return AdaptiveContrastMethod(run,make_conditions=make_conditions,initialise=initialise_experiment,
        select=choose_condition,record=trial_record,update=update_experiment,finished=is_finished,finish=finish_experiment)

def fixed_method(run):
    schedule=make_fixed_schedule(run.values,run.seed)
    return ConstantContrastMethod(run,schedule=schedule,condition_field='value',record=fixed_record,
        resolution={'trial_selection_method':'constant_stimuli','schedule':schedule,
            'condition_definitions':make_conditions(run.values),'planned_trials':len(schedule),
            'measurement_units':MEASUREMENT_UNITS,'strength_definition':'I_line = 0.5 + increment',
            'scientific_estimator':None,'response_analysis':'Accuracy by condition and increment; no threshold fit.'})

def validate_settings(settings):
    try:
        conditions=make_conditions(settings)
        if settings['edge_deg']>settings['line_width_deg']/2:raise ValueError('Edge transition must fit within half the line width.')
        if settings['contrast_method']=='constant_stimuli':make_fixed_schedule(settings,0)
        elif not 0<=settings['starting_strength']<=.5 or not 2*len(conditions)<=settings['trial_count']<=settings['max_trials']:
            raise ValueError('Adaptive goal must cover both sides of every cell, fit max_trials, and start within [0,.5].')
    except ValueError as error:yield str(error)

# PART B — FRAMEWORK INTEGRATION
# FRAMEWORK CONNECTION: one existing method adapter, RunContext and recorder.
def trial_record(run, condition, state):
    return run.adaptive_trial_record(state['adaptive'],condition['id'],contrast=condition['contrast'],maximum=.5,
        log_up=log10(run.values['up_factor']),log_down=-log10(run.values['down_factor']),
        measurements=trial_measurements(run.values,condition),
        instructions='   '.join(f'{alt}: {key}' for alt,key in zip(run.responses.alternatives,run.responses.keys)))

def fixed_record(run, condition):
    record=fixed_teaching_record(run,condition)
    record['measurements'].update(trial_measurements(run.values,condition))
    return record

def procedure(run):
    return run_contrast_experiment(run,methods={'adaptive':lambda:adaptive_method(run),
        'constant_stimuli':lambda:fixed_method(run)},prepare_stimuli=prepare_stimuli,
        trial_events=trial_events,interpret_response=interpret_response)

make_trial=legacy_trial_factory(trial_events)
SPEC=experiment(id='demolab__lesson3_study',name='Lesson 3 — local factorial study',description=__doc__,
    procedure=procedure,fields=FIELDS,responses=RESPONSES,session_start=SESSION_START,
    stimulus_slots=STIMULUS_SLOTS,stimulus_defaults=STIMULUS_DEFAULTS,
    adaptive=AdaptiveSelection('consecutive_up_down',controls=('n_down','n_up','down_factor','up_factor','max_trials')),
    method_planner=make_fixed_schedule,method_reviewer={'constant_stimuli':fixed_method},validator=validate_settings,
    stimulus_parameter_controls={'target':{'edge_deg':'edge_deg','width_deg':'line_width_deg'}},
    supports_simulation=True,calibration_requirements=('geometry',),monitor_capabilities=('display_binding','resolution'),
    source_paths=('experiments/demolab__lesson3_study.py',))
