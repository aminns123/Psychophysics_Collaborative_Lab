
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

PROJECT_PARENT = Path(__file__).resolve().parents[3]
WORKING_DIR = PROJECT_PARENT / 'psychophysics_experiments_git'
DATA_SAVE_DIR = PROJECT_PARENT / 'Psychophysics_DATA_2024'

print('WORKING_DIR', WORKING_DIR)

os.chdir(WORKING_DIR)
sys.path.append(str(WORKING_DIR))

print('============== CWD ===============================')
print('cwd:', os.getcwd())
print('============== FILES ===============================')
print(os.listdir('.'))
print('============== FILES ===============================')


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
        experiment_params['nUP'],
        fileArrayCondition,
        fileParamsMain,
        filename_params,
        fileParamsPosition,
        fileADM_indexing,
        fileADM_condition,
        path_main,
        keys_for_trial or [],
        mouse=False,
    )


# ------------------------------ Trial sequence ------------------------------

alternative_forced_choice = {
    '2AFC_choice': [-0.5, 0.5],  
    'nan_row__': [0.0]
}

path_main       = filename_ADM_main
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

experiment_title    = [make_text_label(f'{experiment_type}\n', (cx, cy))]
welcome_line        = [make_text_label('Press SPACE when ready.', (cx, cy - 50))]
farewell_line       = [make_text_label('Experiment over!', (cx, cy - 50))]

trials = [
    Trial_small('Start', experiment_title, 5 * 1000, keys_default, mouse=False),
    Trial_small('Start', welcome_line, 0, keys_default, mouse=False),
]

fakeProbe = Dot_stairCase_centre(
    experiment_params['bkg_intensity'],
    filename_params,
    path_main,
    (cx, cy),
    Params(**kwargs_fakeFIX),
)
centreDOT = Dot_stairCase_centre(
    experiment_params['bkg_intensity'],
    filename_params,
    path_main,
    (cx, cy),
    Params(**kwargs_fixate),
)
probeStimulus = Grating_ADM(
    posCentre,
    fileParamsMain,
    filename_params,
    fileADM_condition,
    path_main,
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
