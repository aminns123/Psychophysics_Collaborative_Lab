import os
import datetime
import json

import Functions.functionsForUse as funcs

from Events.adaptiveMethods import (
    findCPU_fromWeberContrast,
)


# ------------------------------ Experiment setup ------------------------------



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
    current_time = datetime.datetime.now()
    today        = f'{current_time.year}_{current_time.month}_{current_time.day}'

    # ------------------------------ Monitor geometry ------------------------------

    monitor_refresh_rate     = 60
    pyglet_wakeup_rate_check = 180

    


    # ------------------------------ Initialize dictionary parameters ------------------------------



    ratio4dw1up = 0.8415
    ratio3dw1up = 0.7393
    ratio2dw1up = 0.5488

    timeFixate          = 250
    timeInterval        = 250
    timeT               = 0
    timeAB              = 200
    viewing_distance_m  = 1.0
    reversal_termination= setupDict['reversal_termination']

    experiment_params = {
        'background_intensity': float(setupDict['Screen_intensity']),
        'max_intensity': 1.0,
        'max_monitor_cdm2': float(setupDict['Background_Luminance']),
        'starting_screen_intensity': float(setupDict['starting_screen_intensity']),
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


    dict_all_dicts = {
        'experiment_params': experiment_params,
        'staircase_params': staircase_params,
    }

    with open(data_save_repository+"/"+"user_experiment_config.json", "w") as f:
        json.dump(dict_all_dicts, f, indent=4)


    # ------------------------------ Files and timing ------------------------------


    UPDW_Rule           = 'DW'+str(int(staircase_params['nDW']))+'_UP'+str(int(staircase_params['nUP']))
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
    filename_parameters = folderParams+"/Records_Parameters"+".json"
    filename_Conditions = folderParams+"/Records_condition"+".json"


    filename_everything, _ = funcs.CheckFileName(folderName,filename_everything)
    filename_response_main = filename_everything

    starting_screen_intensity = experiment_params['starting_screen_intensity']
    starting_weber_contrast = findCPU_fromWeberContrast(
        experiment_params['max_intensity'],
        experiment_params['background_intensity'],
        experiment_params['starting_screen_intensity'],
    )
    
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

    condition_list = [2,4,6,8]

    columnsSet = {
        'condition_list': condition_list,
        'staircase_Identities': [range(len(condition_list))],
        'stimulus_condition': [],
        'probe_Alternative_Choice': [],
        'human_Alternative_Choice': [],
        'total_Reversals': [],
        'staircase_Identity': [],
        'starting_contrast': [starting_weber_contrast for _ in range(len(condition_list))],
        'correct_responses': [0 for _ in range(len(condition_list))],
        'now_weber_contrast': [starting_weber_contrast for _ in range(len(condition_list))],
        'now_screen_intensity': [],
        'update_screen_intensity': [],
        'update_weber_contrast':[],
        'reversal_termination':[reversal_termination for _ in range(len(condition_list))],
        'nDW': [staircase_params['nDW']],
        'nUP': [staircase_params['nUP']],
        'logUNIT_UP': [staircase_params['logUNIT_UP']],
        'logUNIT_DW': [staircase_params['logUNIT_DW']],
    }

    column_titles   = ['stimulus_condition', 
                       'probe_Alternative_Choice', 
                       'human_Alternative_Choice', 
                       'staircase_Identity', 
                       'probe_weber_contrast', 
                       'probe_screen_intensity']

    funcs.create_JSON(filename_Conditions, columnsSet)
    funcs.create_JSON(filename_parameters, value_params)
    funcs.create_Text_columns(filename_response_main, column_titles)

    return filename_Conditions, filename_parameters, filename_response_main

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