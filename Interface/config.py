import os
import random
import sys
import datetime
from pathlib import Path
import json
import numpy as np
import pyglet
import time

import Functions.functionsForUse as funcs



from Events.adaptiveMethods import (
    findCPU_fromWeberContrast,
)


# ------------------------------ Experiment setup ------------------------------



current_time = datetime.datetime.now()
today = f'{current_time.year}_{current_time.month}_{current_time.day}'
print("Today date is: ", today)


# Monitor calibration values. These are not used directly yet, but they are
# useful experiment metadata while this script is being rebuilt.
luminance_500_cdm2      = [19.0, 29, 41, 49, 204, 255, 300, 322, 370, 403, 415]
cpu_luminance_500_cdm2  = [0.24, 0.294, 0.34, 0.374, 0.72, 0.8, 0.86, 0.89, 0.95, 0.98, 0.99]

# listLum   = [0.3,1.0,2.6 ,5.5,  10.0, 10.2, 15.0, 20,25, 26.15,30,38,       46, 49, 50, 100 ,200,245,300,350]
# listCPULum= [0.006, 0.06, 0.1, 0.14, 0.189, 0.19, 0.259, 0.26, 0.286,  0.29,0.35,0.38, 0.39, 0.392, 0.54, 0.735,0.8,0.89,0.95]

def run_configure_experiment(NAME, data_save_repository, setupDict):
    """
    Configure the experiment by creating necessary files and writing initial values.
    """
    participant_names = os.listdir(data_save_repository)

    with open(data_save_repository+"/"+NAME+"/"+"experiment_defined.json", "r") as f:
        setupDict = json.load(f)
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

    


    # ------------------------------ Initialize dictionary parameters ------------------------------



    ratio4dw1up = 0.8415
    ratio3dw1up = 0.7393
    ratio2dw1up = 0.5488

    timeFixate          = 250
    timeInterval        = 250
    timeT               = 0
    timeAB              = 200
    startFlicker_index  = 0
    viewing_distance_m  = 1.0


    experiment_params = {
        'background_intensity': float(setupDict['Screen_intensity']),
        'max_intensity': 1.0,
        'max_monitor_cdm2': float(setupDict['Luminance']),
        'start_weber_Contrast': float(setupDict['start_Cw']),
        'timeFixate':   timeFixate,
        'timeInterval': timeInterval,
        'timeAB':       timeAB,
        'timeT':        timeT,
        'viewing_distance_m': viewing_distance_m,
    }

    staircase_params = {
        'trialPOINT':           int(setupDict['trialPOINT']),
        'nDW':                  4,
        'nUP':                  1,
        'number_trials':        10,
        'terminationINDEX':     9,
        'logUNIT_UP':           0.19,
        'logUNIT_DW':           ratio4dw1up * 0.19,
        'preReversalStepDW':    0.2,
        'Reversal_or_Trial':    1,
        'limit_Trial_Run':      100,
    }

    kwargs_fixate= {
        'c':                    experiment_params['background_intensity']+0.09,  # should be 0.33 or less not 0.45 +0.08
        'sigma':   	            0.035,  # 0.035 || should be 0.01 or less not 0.02
        'fs':                   0.0,
        'phi':                  0.0,
        'edge':                 2.0,#2
        'res':                  64,
        'msg':                  'Experiment over! ----- Press: Esc'
    }

    kwargs_fakeFIX= {
        'c':                    experiment_params['background_intensity'],  # should be 0.33 or less not 0.45
        'sigma':   	            0.00001,  # should be 0.01 or less not 0.02
        'fs':                   0.0,
        'phi':                  0.0,
        'edge':                 2.0,
        'res':                  64,
        'msg':                  '-- Experiment over! -- Press: Esc --'
    }

    dict_all_dicts = {
        'experiment_params': experiment_params,
        'staircase_params': staircase_params,
        'kwargs_fixate': kwargs_fixate,
        'kwargs_fakeFIX': kwargs_fakeFIX
    }

    with open(data_save_repository+"/"+"user_experiment_config.json", "w") as f:
        json.dump(dict_all_dicts, f, indent=4)


    # ------------------------------ Files and timing ------------------------------


    UPDW_Rule           = 'DW'+str(int(staircase_params['nDW']+1))+'_UP'+str(int(staircase_params['nUP']))
    experimentNAME      = setupDict['Experiment_Type']
    bkg_intensityFolder = 'Background_Intensity_'+str(experiment_params['background_intensity'])

    experiment_type = (
        f"{UPDW_Rule}/{experimentNAME}/"
        f"max_cdm2_{int(experiment_params['max_monitor_cdm2'])}/"
        f"{bkg_intensityFolder}"
    )

    folderName      = f"{data_save_repository}/{NAME}/{experiment_type}/{today}"
    folderParams    = f"{folderName}/parameters"
    funcs.check_folder_exist([folderName, folderParams])

    filename_everything = '_experiment.txt'
    filename_params     = folderParams+"/Records_Params"+".json"
    fileParamsPosition  = folderParams+"/Records_position"+".txt"
    fileADM_indexing    = folderParams+"/Records_ADMINDEX"+".txt"
    fileArrayCondition  = folderParams+"/Records_conditionArray"+".txt"
    fileADM_condition   = folderParams+"/Records_ADM_Condition"+".txt"


    filename_everything, indexEXP = funcs.CheckFileName(folderName,filename_everything)
    file_paramsStimulus           = folderParams+'/'+str(indexEXP)+'_file_Stimulus_' +'.txt'
    filename_response_main        = filename_everything

    cStart = findCPU_fromWeberContrast(
        experiment_params['max_intensity'],
        experiment_params['background_intensity'],
        experiment_params['start_weber_Contrast'],
    )
    probeStart      = cStart
    terminateBOOL   = 0

    value_params = dict_all_dicts.copy()    



    columnADM = [
        'condition', 
        'ADM index'
    ]
    columnADM_condition = [
        'condition', 
        'condition value', 
        'BOOL condition', 
        'adm ID'
    ]
    columnsSet = {
        'condition': [],
        'probe_Alternative_Choice': [],
        'human_Alternative_Choice': [],
        'count_Reversals': [],
        'stairID': [],
        'rateDW': [],
        'COMP_intensity': [],
        'rateUP': [],
        'countReverseTick': [],
        'startValue': [],
        'correctTicks': [],
        'newContrast': [],
        'probe position Y': [],
        'nDW': [],
        'weber contrast': [],
        'grating sf': [],
    }

    valuePosition   = [0.0]
    condition_list  = [2,4,6,8,10]

    funcs.create_JSON(filename_response_main, columnsSet)
    funcs.create_JSON(filename_params, value_params)
    
    """
    funcs.create_Text(fileParamsPosition, valuePosition)
    funcs.create_Text_academic(fileADM_indexing, columnADM)
    funcs.create_Text(fileArrayCondition, condition_list)
    funcs.create_Text_academic(fileADM_condition, columnADM_condition)

    bool_general, bool_fs, bool_x, omegaf = 0, 1, 0, 1.0


    condition_names     = ['frequency', 'position_', 'general__', 'nan_row__']
    condition_values    = [omegaf, 0.0, 0.0, 0.0]
    condition_enabled   = [bool_fs, bool_x, bool_general, 0.0]

    adm_condition_table = funcs.readText_toList(fileADM_condition)
    adm_condition_table[0].extend(condition_names)
    adm_condition_table[1].extend(condition_values)
    adm_condition_table[2].extend(condition_enabled)
    adm_condition_table[3].extend([0 for _ in condition_names])

    # Remove the placeholder row created by ``create_Text_academic``.
    for column in adm_condition_table:
        column.pop(0)
    funcs.write_toText(fileADM_condition, adm_condition_table)
    """