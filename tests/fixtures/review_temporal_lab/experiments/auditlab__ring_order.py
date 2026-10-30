"""Independent before/after-cue annulus task; finite software acceptance example.

Scientific conditions are cue gaps in ms. The cue is the visible word CUE,
shown with fixation for 10 ms (requested software duration, not photon timing).
Target alternatives are temporal order,
not different conditions or staircase tracks. Digital annulus increment above
0.5 is adjusted by the installed finite teaching rule; no threshold is claimed.
"""
from psychophysics_lab.researcher import (
    ConfigField, AdaptiveSelection, ResponseParadigm, Show, WaitForKey,
    CollectResponse, Stimulus, experiment, legacy_trial_factory,
)
from psychophysics_lab.methods.contrast import ConstantContrastMethod, fixed_level_schedule, parse_fixed_strengths
from psychophysics_lab.methods.teaching import (
    TeachingAdaptiveMethod, teaching_method_fields, teaching_adaptive_fields,
    fixed_teaching_record, review_teaching_adaptive,
)

# A1: laboratory science; no official experiment imports.
FIELDS = (
    ConfigField('cue_gaps_ms', 'Cue gaps', 'text', '20,40', units='ms', section='Temporal conditions'),
    ConfigField('ring_x_deg', 'Annulus horizontal position', 'float', .7, minimum=-2., maximum=2., units='degrees'),
    ConfigField('flash_ms', 'Annulus exposure', 'int', 30, minimum=1, maximum=200, units='ms'),
    ConfigField('trial_count', 'Accepted adaptive responses', 'int', 4, minimum=1),
) + teaching_method_fields(strengths='0.1,0.2', label='Annulus digital increment') + teaching_adaptive_fields()
RESPONSES = ResponseParadigm('annulus_order', ('before_cue','after_cue'), ('B','A'))
SESSION_START = [WaitForKey('ready',key='SPACE',slot='cue'), Show('settle',slot='cue',duration=10)]
MEASUREMENT_UNITS = {'cue_gap_ms':'ms', 'annulus_x_deg':'degrees', 'annulus_radius_deg':'degrees',
                     'requested_flash_ms':'ms', 'requested_increment':'digital increment above 0.5',
                     'target_order':'0=before, 1=after', 'fixed_repeat':'count within gap and increment',
                     'presented_display_contrast':'digital increment above 0.5'}
REVIEW_INACTIVE_FIELDS = {
    'adaptive': ('fixed_contrasts','fixed_repetitions'),
    'constant_stimuli': ('starting_strength','trial_count','n_down','n_up','down_factor','up_factor'),
}

def trial_events(settings, condition):
    annulus = Show('annulus', stimuli=(Stimulus('ring',x_deg=settings['ring_x_deg']),), duration='flash_ms')
    cue = Show('cue',slot='cue',duration=10,instructions='CUE')
    gap = Show('gap',slot='cue',duration=condition['gap_ms'])
    sequence = [annulus,gap,cue] if condition['target']==0 else [cue,gap,annulus]
    return [Show('fixation',slot='cue',duration=20), *sequence,
            CollectResponse(actions=RESPONSES.alternatives,slot='cue')]

def trial_measurements(run, condition):
    return {'cue_gap_ms':condition['gap_ms'], 'annulus_x_deg':run.values['ring_x_deg'],
            'annulus_radius_deg':run.stimulus_parameters('ring')['radius_deg'],
            'requested_flash_ms':run.values['flash_ms'], 'requested_increment':condition['contrast'],
            'target_order':condition['target']}

def trial_record(run, condition, state=None):
    return {'measurements':trial_measurements(run,condition)}

# A2: conditions, balanced orders, declared installed strength policies.
def gaps(settings):
    values = parse_fixed_strengths(settings['cue_gaps_ms'],minimum=5,maximum=200)
    if any(value != int(value) for value in values):
        raise ValueError('Cue gaps must be whole milliseconds.')
    return tuple(int(value) for value in values)

def make_conditions(settings):
    levels = gaps(settings)
    return [{'value':levels[i%len(levels)], 'gap_ms':levels[i%len(levels)],
             'target':(i//len(levels))%2} for i in range(settings['trial_count'])]

def choose_condition(run, conditions, state):
    return conditions[run.accepted_trials]

def make_fixed_schedule(settings, seed):
    conditions = [{'value':gap,'gap_ms':gap} for gap in gaps(settings)]
    schedule = fixed_level_schedule(conditions,parse_fixed_strengths(settings['fixed_contrasts'],maximum=.5),
                                    settings['fixed_repetitions'],seed=seed,condition_field='gap_ms')
    if len(schedule)>settings['max_trials']:
        raise ValueError('Fixed plan exceeds the selected safety ceiling.')
    return schedule

def prepare_stimuli(run, condition, state):
    return {'ring':run.stimulus_parameters('ring',intensity=.5+condition['contrast']),
            'cue':run.stimulus_parameters('cue')}

def fixed_record(run, condition):
    record = fixed_teaching_record(run,condition)
    record['measurements'].update(trial_measurements(run,condition))
    return record

def fixed_method(run):
    schedule=make_fixed_schedule(run.values,run.seed)
    return ConstantContrastMethod(run,schedule=schedule,condition_field='value',record=fixed_record,
        resolution={'trial_selection_method':'constant_stimuli','planned_trials':len(schedule),
                    'schedule':schedule,'condition_definitions':[{'value':gap,'gap_ms':gap} for gap in gaps(run.values)],
                    'response_analysis':'Accuracy by cue gap and digital increment; no threshold fit.'})

def validate_settings(settings):
    try:
        gaps(settings)
        if settings['contrast_method']=='constant_stimuli':
            make_fixed_schedule(settings,0)
        elif settings['starting_strength']>.5 or settings['trial_count']>settings['max_trials']:
            raise ValueError('Starting strength must be <=0.5 and trial_count <= max_trials.')
    except ValueError as error:
        yield str(error)

# B: existing methods, canonical trial context, recorder and registration.
def procedure(run):
    method=(fixed_method(run) if run.values['contrast_method']=='constant_stimuli' else
            TeachingAdaptiveMethod(run,make_conditions=make_conditions,choose=choose_condition,maximum=.5))
    while not method.is_finished:
        condition=method.next_trial()
        record=method.trial_record(condition)
        record['measurements'].update(trial_measurements(run,condition))
        with run.trial(trial_events(run.values,condition),target=condition['target'],condition=condition['value'],
                       parameters_by_slot=prepare_stimuli(run,condition,method.state),**record) as trial:
            assert trial.response['correct']==(trial.response['alternative']==condition['target'])
            method.accept_response(condition,trial.response,trial)
    method.complete()

make_trial=legacy_trial_factory(trial_events)
SPEC=experiment(id='auditlab__ring_order',name='Laboratory annulus before/after cue',description=__doc__,
    procedure=procedure,fields=FIELDS,responses=RESPONSES,session_start=SESSION_START,
    stimulus_slots={'ring':'audit_annulus','cue':'fixation'},
    stimulus_defaults={'ring':'auditlab__annulus','cue':'fixation_cross'},
    adaptive=AdaptiveSelection('consecutive_up_down',controls=('n_down','n_up','down_factor','up_factor','max_trials')),
    validator=validate_settings,method_planner=make_fixed_schedule,
    method_reviewer={'adaptive':lambda run:review_teaching_adaptive(run,make_conditions,choose_condition),
                     'constant_stimuli':fixed_method},
    supports_simulation=True,calibration_requirements=('geometry',),monitor_capabilities=('display_binding','resolution'),
    source_paths=('experiments/auditlab__ring_order.py',))
