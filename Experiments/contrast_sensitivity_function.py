
import os
import random
import sys
import datetime
from pathlib import Path
import json

import pyglet

import Functions.functionsForUse as funcs

from Events.stimuliC import (
    Dot_stairCase_centre, 
    Grating_ADM
)
from Events.libC import (
    ExpWindow, 
    Params, 
    key, 
    run
)
from Events.adaptiveMethods import (
    Trial_ADMs,
    Trial_small,
    record_event,
)
from Interface.main import (
    data_save_repository,
    NAME
)

with open(data_save_repository+"/"+"user_experiment_config.json", "r") as f:
    dict_all_dicts = json.load(f)

with open(data_save_repository+"/"+NAME+"/"+"experiment_defined.json", "r") as f:
    setupDict = json.load(f)

monitor_screen_params   = dict_all_dicts['monitor_screen_params']
experiment_params       = dict_all_dicts['experiment_params']
staircase_params        = dict_all_dicts['staircase_params']
kwargs_fixate           = dict_all_dicts['kwargs_fixate']
kwargs_fakeFIX          = dict_all_dicts['kwargs_fakeFIX']

# ------------------------------ Experiment setup ------------------------------

cx, cy                      = monitor_screen_params['cx'], monitor_screen_params['cy']
monitor_refresh_rate        = monitor_screen_params['monitor_refresh_rate']
pyglet_wakeup_rate_check    = monitor_screen_params['pyglet_wakeup_rate_check']
timeFixate                  = monitor_screen_params['timeFixate']
timeInterval                = monitor_screen_params['timeInterval']
timeAB                      = monitor_screen_params['timeAB']
timeT                       = monitor_screen_params['timeT']
# ------------------------------ Experiment setup ------------------------------

pyglet.options['vsync'] = True
pyglet.options['double_buffer'] = True
win = ExpWindow(fullscreen=True)


current_time = datetime.datetime.now()
today = f'{current_time.year}_{current_time.month}_{current_time.day}'
print("Today date is: ", today)


# ------------------------------ local Functions ------------------------------

def make_text_label(message, position, font_size=24):
    """Create a centered pyglet label for instruction screens."""
    return pyglet.text.Label(
        message,
        x=position[0],
        y=position[1],
        anchor_x='center',
        anchor_y='center',
        font_size=font_size,
    )

def make_adm_trial(name, stimuli, duration_ms, position, keys_for_trial=None):
    """Create a Trial_ADMs with the shared files used by this experiment."""
    return Trial_ADMs(
        name,
        stimuli,
        duration_ms,
        position,
        file_params_Stimulus,
        file_response_record,
        keys_for_trial or [],
        mouse=False,
    )


# ------------------------------ Trial sequence ------------------------------

alternative_forced_choice = {
    '2AFC_choice': [-0.5, 0.5],  
    'nan_row__': [0.0]
}

posCentre       = [cx, cy]
response_keys   = [key.RIGHT, key.LEFT]
keys_none       = []
keys_default    = [
    key.SPACE,
    key.LEFT,
    key.RIGHT,
    key.UP,
    key.DOWN,
    key.LSHIFT,
    key.RSHIFT,
]

win.set_logger(record_event)




# ------------------------------ Stimuli ------------------------------

experiment_title    = [make_text_label(f'{setupDict["Experiment_Type"]}\n', (cx, cy))]
welcome_line        = [make_text_label('Press SPACE when ready.', (cx, cy - 50))]
farewell_line       = [make_text_label('Experiment over!', (cx, cy - 50))]

trials = [
    Trial_small('Start', experiment_title, 5 * 1000, keys_default, mouse=False),
    Trial_small('Start', welcome_line, 0, keys_default, mouse=False),
]

fakeProbe = Dot_stairCase_centre(
    experiment_params['bkg_intensity'],
    file_params_Stimulus,
    file_response_record,
    (cx, cy),
    Params(**kwargs_fakeFIX),
)
centreDOT = Dot_stairCase_centre(
    experiment_params['bkg_intensity'],
    file_params_Stimulus,
    file_response_record,
    (cx, cy),
    Params(**kwargs_fixate),
)
probeStimulus = Grating_ADM(
    posCentre,
    file_params_Stimulus,
    file_response_record,
    Params(**experiment_params),
)

fake_probe_trial = [fakeProbe]
probe_trial      = [probeStimulus]
fixation_trial   = [centreDOT]

# ------------------------------ Trial loop ------------------------------
fixateDOT = make_adm_trial(
    'fixation',
    fixation_trial,
    timeFixate,
    [cx, cy],
)
fixateInterval = make_adm_trial(
    'fixation',
    fake_probe_trial,
    timeInterval,
    [cx, cy],
)
fixateRESPONSE = make_adm_trial(
    'responses',
    fixation_trial,
    timeT,
    [cx, cy],
    response_keys,
)

trial_exps = [fixateDOT]
for _ in range(experiment_params['number_trials']):

    posX = random.choice(alternative_forced_choice['2AFC_choice'])

    stimulusPROBE = make_adm_trial(
        'stimuli',
        probe_trial,
        timeAB,
        [posX, cy],
    )    

    sequence = [
        fixateDOT,
        fixateInterval,
        stimulusPROBE,
        fixateInterval,
        fixateRESPONSE,
    ]

    trial_exps += sequence

trials += trial_exps
trials += [Trial_small('End', farewell_line, 0, keys_none, mouse=False)]

pyglet.clock.schedule_interval(lambda dt: None, 1/pyglet_wakeup_rate_check)
# pyglet.clock.schedule_interval(update, 1/60.0)  # match monitor refresh

win.set_trials(trials)
run(refresh_rate=monitor_refresh_rate)

experiment_params.update({
    'nDW': experiment_params['nDW'] + 1,
    'Probe_Height_Deg': lengthDegree,
    'Probe_width_Deg': widthDegree,
    'nan': 0,
})
funcs.write_dictionary_toText(file_paramsStimulus, **experiment_params)
funcs.removeZeroRow(path_main)
funcs.correctFileSpacings(path_main)
