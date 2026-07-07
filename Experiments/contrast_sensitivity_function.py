
import os
import random
import sys
import time
import datetime
from pathlib import Path

import numpy as np
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
    findCPU_fromWeberContrast,
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


# Monitor calibration values. These are not used directly yet, but they are
# useful experiment metadata while this script is being rebuilt.
luminance_500_cdm2 = [19.0, 29, 41, 49, 204, 255, 300, 322, 370, 403, 415]
cpu_luminance_500_cdm2 = [0.24, 0.294, 0.34, 0.374, 0.72, 0.8, 0.86, 0.89, 0.95, 0.98, 0.99]

# listLum   = [0.3,1.0,2.6 ,5.5,  10.0, 10.2, 15.0, 20,25, 26.15,30,38,       46, 49, 50, 100 ,200,245,300,350]
# listCPULum= [0.006, 0.06, 0.1, 0.14, 0.189, 0.19, 0.259, 0.26, 0.286,  0.29,0.35,0.38, 0.39, 0.392, 0.54, 0.735,0.8,0.89,0.95]


participant_names = os.listdir(DATA_SAVE_DIR)
new_or_old = ['NEW', 'OLD']
prompt_options = {'NEW_or_OLD': new_or_old, 'Name': participant_names}
boolDict = funcs.optionPrompt(prompt_options)

"""
    Below you can set:
        1. the monitor refresh rate.
        2. screen pixel width and height.
        3. the screen width and height in meters.
        4. the pixel per degree (ppd) for x and y.
        5. the viewing distance from subject to screen in meters.
        6. the aspect ratio of the screen.
        7. the pixel to meter ratio.
        8. the center of the screen in pixels (cx, cy).

"""

# ------------------------------ Monitor geometry ------------------------------

monitor_refresh_rate     = 60
pyglet_wakeup_rate_check = 180
print("Window vsync is on, target refresh:", pyglet.options['vsync'])
print('monitor_refresh_rate:', monitor_refresh_rate)

pixel_width             = win.width
pixel_height            = win.height
screen_width_pixel      = pixel_width
screen_height_pixel     = pixel_height
aspect_ratio            = screen_width_pixel/screen_height_pixel

metre_width             = 596.2e-3 # 610e-3
metre_height            = 335.3e-3 # 350e-3
screen_width_m          = metre_width
screen_height_m         = metre_height

cx, cy                  = win.width // 2, win.height // 2

print('win.width (pixel)', win.width, 'win.height (pixel)', win.height)
pixel_metre_ratio   = funcs.ratio_PIXEL_Meter(win.width, metre_width) # <- seems to give correct answer.

viewing_distance_m = 1.0

fov_x_deg = 2 * np.degrees(np.arctan((screen_width_m / 2) / viewing_distance_m))
fov_y_deg = 2 * np.degrees(np.arctan((screen_height_m / 2) / viewing_distance_m))

ppd_x     = screen_width_pixel / fov_x_deg
ppd_y     = screen_height_pixel / fov_y_deg

win.set_logger(record_event)

ratio3dw1up = 0.7393


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


# ------------------------------ Initialize dictionary parameters ------------------------------

experiment_params = {
    'distance_To_Monitor':  100e-2,
    'win_widthy_Pixel':     win.width,
    'win_widthx_Pixel':     win.height,
    'win_widthy_Meter':     metre_height,
    'win_widthx_Meter':     metre_width,
    'aspect_ratio':         aspect_ratio,
    'Pixel Per Inch':       164,
    'Pixel width (m)':      pixel_metre_ratio,
    'Pixel Pitch (mm)':     '0.155*0.155',
    'bkg_intensity':        float(newDict['Screen_intensity']),
    'max_intensity':        1.0,
    'time_Stimulus':        250,
    'reversalN':            0.0,
    'rateDW':               0.5,
    'correctTick':          0,
    'count_Reversals':      0,
    'probe_LR':             0,
    'human_LR':             0,
    'posY':                 0,
    'rateUP':               0.5,
    'probe_pos (m)':        0.0,
    'text':                 -1,
    'reversePOINT':         1,
    'trialPOINT':           int(newDict['trialPOINT']),
    'nDW':                  2,
    'nUP':                  1,
    'start_weber_Contrast': float(newDict['start_Cw']),
    'number_trials':        10,
    'terminationINDEX':     9,
    'stepDWUP':             0.005,
    'logUNIT_UP':           0.19,
    'logUNIT_DW':           ratio3dw1up * 0.19,
    'condRule':             2,
    'preReversalStepDW':    0.2,
    'Reversal_or_Trial':    1,
    'limit_Trial_Run':      100,
    'max_monitor_cdm2':     500,
    'frame_capture':        61.0,
    'bkg_monitor_cdm2':     newDict['Luminance'],
    'date_created':         today,
}

kwargs_fixate= {
    'c':                    experiment_params['bkg_intensity']+0.09,  # should be 0.33 or less not 0.45 +0.08
    'sigma':   	            0.035,  # 0.035 || should be 0.01 or less not 0.02
    'fs':                   0.0,
    'phi':                  0.0,
    'edge':                 2.0,#2
    'res':                  64,
    'msg':                  'Experiment over! ----- Press: Esc'
}

kwargs_fakeFIX= {
    'c':                    experiment_params['bkg_intensity'],  # should be 0.33 or less not 0.45
    'sigma':   	            0.00001,  # should be 0.01 or less not 0.02
    'fs':                   0.0,
    'phi':                  0.0,
    'edge':                 2.0,
    'res':                  64,
    'msg':                  '-- Experiment over! -- Press: Esc --'
}


# ------------------------------ Files and timing ------------------------------

timeFixate      = 250
timeInterval    = 250
timeT           = 0
timeAB          = 200

experiment_type = (
    f"{UPDW_Rule}/{experimentNAME}/"
    f"max_cdm2_{int(experiment_params['max_monitor_cdm2'])}/"
    f"{bkg_intensityFolder}"
)

folderName      = f"{saveTO_folder}/{ParticipentName}/{experiment_type}/{today}"
folderParams    = f"{folderName}/parameters"
funcs.check_folder_exist([folderName, folderParams])

filename_everything = '_experiment.txt'
filename_params     = folderParams+"/Records_Params"+".txt"
fileParamsMain      = folderParams+"/Records_ParamsMain"+".txt"
fileParamsPosition  = folderParams+"/Records_position"+".txt"
fileADM_indexing    = folderParams+"/Records_ADMINDEX"+".txt"
fileArrayCondition  = folderParams+"/Records_conditionArray"+".txt"
fileADM_condition   = folderParams+"/Records_ADM_Condition"+".txt"

experiment_title    = [make_text_label(f'{experiment_type}\n', (cx, cy))]
welcome_line        = [make_text_label('Press SPACE when ready.', (cx, cy - 50))]
farewell_line       = [make_text_label('Experiment over!', (cx, cy - 50))]

keys_none = []
keys_default = [
    key.SPACE,
    key.LEFT,
    key.RIGHT,
    key.UP,
    key.DOWN,
    key.LSHIFT,
    key.RSHIFT,
]

trials = [
    Trial_small('Start', experiment_title, 5 * 1000, keys_default, mouse=False),
    Trial_small('Start', welcome_line, 0, keys_default, mouse=False),
]

filename_everything, indexEXP = funcs.CheckFileName(folderName,filename_everything)
file_paramsStimulus           = folderParams+'/'+str(indexEXP)+'_file_Stimulus_' +'.txt'
filename_ADM_main             = filename_everything

cStart = findCPU_fromWeberContrast(
    experiment_params['max_intensity'],
    experiment_params['bkg_intensity'],
    experiment_params['start_weber_Contrast'],
)
probeStart      = cStart
terminateBOOL   = 0

value_params = [
    cStart,
    experiment_params['probe_LR'],
    experiment_params['human_LR'],
    experiment_params['probe_pos (m)'],
    probeStart,
    experiment_params['reversalN'],
    experiment_params['rateDW'],
    experiment_params['correctTick'],
    experiment_params['text'],
    experiment_params['count_Reversals'],
    experiment_params['rateUP'],
    experiment_params['posY'],
    experiment_params['bkg_intensity'],
    experiment_params['max_intensity'],
    experiment_params['reversePOINT'],
    experiment_params['nDW'],
    experiment_params['nUP'],
    experiment_params['distance_To_Monitor'],
    pixel_metre_ratio,
    experiment_params['terminationINDEX'],
    terminateBOOL,
    experiment_params['stepDWUP'],
    experiment_params['condRule'],
    experiment_params['logUNIT_UP'],
    experiment_params['logUNIT_DW'],
    experiment_params['limit_Trial_Run'],
    0,
    0,
    experiment_params['preReversalStepDW'],
    experiment_params['Reversal_or_Trial'],
    experiment_params['trialPOINT'],
    monitor_refresh_rate,
    1.0,
    time.perf_counter(),
    startFlicker_index,
]

columnADM = ['condition', 'ADM index']
columnADM_condition = ['condition', 'condition value', 'BOOL condition', 'adm ID']
columnsSet = [
    'probe position X',
    'probe_LR',
    'human_LR',
    'count_Reversals',
    'stairID',
    'rateDW',
    'COMP_intensity',
    'rateUP',
    'countReverseTick',
    'startValue',
    'correctTicks',
    'newContrast',
    'probe position Y',
    'nDW',
    'weber contrast',
    'grating sf',
]

value_params = [float(x) for x in value_params]

funcs.create_Text_academic(filename_ADM_main, columnsSet)
funcs.create_Text(filename_params, value_params)
funcs.create_Text(fileParamsMain, valueMain)
funcs.create_Text(fileParamsPosition, valuePosition)
funcs.create_Text_academic(fileADM_indexing, columnADM)
funcs.create_Text(fileArrayCondition, condition_list)
funcs.create_Text_academic(fileADM_condition, columnADM_condition)

condition_names = ['frequency', 'position_', 'general__', 'nan_row__']
condition_values = [omegaf, 0.0, 0.0, 0.0]
condition_enabled = [bool_fs, bool_x, bool_general, 0.0]

adm_condition_table = funcs.readText_toList(fileADM_condition)
adm_condition_table[0].extend(condition_names)
adm_condition_table[1].extend(condition_values)
adm_condition_table[2].extend(condition_enabled)
adm_condition_table[3].extend([0 for _ in condition_names])

# Remove the placeholder row created by ``create_Text_academic``.
for column in adm_condition_table:
    column.pop(0)
funcs.write_toText(fileADM_condition, adm_condition_table)


# ------------------------------ Trial sequence ------------------------------

nUP, intID, admCount, param = funcs.randomIndex_ADMs(
    index,
    adms,
    nUPList,
    admCount,
    param,
)

nNew = param[4]
vertical_direction = random.choice([-1, 1, nNew])

path_main = filename_ADM_main
posCentre = [cx, cy]

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
probe_trial     = [probeStimulus]
fixation_trial  = [centreDOT]


def make_adm_trial(name, stimuli, duration_ms, position, keys_for_trial=None):
    """Create a Trial_ADMs with the shared files used by this experiment."""
    return Trial_ADMs(
        name,
        stimuli,
        duration_ms,
        position,
        nUP,
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

for _ in range(NTotaltrials):

    posX = random.choice(positionX)

    fixateInterval = make_adm_trial(
        'fixation',
        fake_probe_trial,
        timeInterval,
        [cx, cy],
    )
    stimulusPROBE = make_adm_trial(
        'stimuli',
        probe_trial,
        timeAB,
        [posX, cy],
    )
    fixateDOT = make_adm_trial(
        'fixation',
        fixation_trial,
        timeFixate,
        [cx, cy],
    )

    response_keys = [key.RIGHT, key.LEFT, key.RSHIFT, key.LSHIFT]
    fixateRESPONSE = make_adm_trial(
        'responses',
        fixation_trial,
        timeT,
        [cx, cy],
        response_keys,
    )

    sequence = [
        fixateDOT,
        fixateInterval,
        stimulusPROBE,
        fixateInterval,
        fixateRESPONSE,
    ]

    trial_exps = [fixateDOT]
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
