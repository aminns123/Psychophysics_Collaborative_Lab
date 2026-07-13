import os
import datetime
import json

import Functions.functionsForUse as funcs

from Events.adaptiveMethods import (
    _to_weber,
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
        'background_intensity': 	float(setupDict['Background_Screen_intensity']),
        'max_intensity': 			1.0,
        'max_monitor_cdm2': 		float(setupDict['Max_monitor_Luminance']),
        'starting_probe_intensity': float(setupDict['starting_probe_intensity']),
        'timeFixate':   			timeFixate,
        'timeInterval':	 			timeInterval,
        'timeAB':       			timeAB,
        'timeT':        			timeT,
        'viewing_distance_m': 		viewing_distance_m,
        'number_trials':			10*3
    }

    staircase_params = {
        'trialPOINT':           int(setupDict['trialPOINT']),
        'n_dw':                 2,
        'n_up':                 1,
        'number_trials':        10,
        'terminationINDEX':     9,
        'logUNIT_UP':           0.35,
        'logUNIT_DW':           ratio2dw1up * 0.35,
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


    UPDW_Rule           = 'DW'+str(int(staircase_params['n_dw']))+'_UP'+str(int(staircase_params['n_up']))
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

    starting_probe_intensity = experiment_params['starting_probe_intensity']
    starting_weber_contrast  = _to_weber(
        experiment_params['starting_probe_intensity'],
        experiment_params['max_intensity'],
        experiment_params['background_intensity'],
    )

    background_intensity 		= experiment_params['background_intensity']
    background_weber_contrast 	= _to_weber(
        background_intensity,
        experiment_params['max_intensity'],
        experiment_params['background_intensity'],
    )
    max_intensity 		= experiment_params['max_intensity']
    max_weber_contrast 	= _to_weber(
        max_intensity,
        experiment_params['max_intensity'],
        experiment_params['background_intensity'],
    )

    flat_dict = {}

    for subdict in dict_all_dicts.values():
        flat_dict.update(subdict)
    value_params = flat_dict.copy()    
    value_params.update({'background_weber_contrast':background_weber_contrast,
                         'max_weber_contrast':max_weber_contrast})


    deg1PCD        = 31.5 
    condition_list = [2*deg1PCD,8*deg1PCD] # ,4*deg1PCD,6*deg1PCD,

    columnsSet = {
        'condition_list': condition_list,
        'staircase_Identities': list(range(len(condition_list))),
        'probe_Alternative_Choice': [0 for _ in range(len(condition_list))],
        'human_Alternative_Choice': [0 for _ in range(len(condition_list))],
        'staircase_Identity_active': [0],
        'stimulus_choice_active': [0], 
        'total_Reversals':  [0 for _ in range(len(condition_list))],
        'starting_contrast': [starting_weber_contrast for _ in range(len(condition_list))],
        'correct_responses': [0 for _ in range(len(condition_list))],
        'weber_contrast_active': [starting_weber_contrast for _ in range(len(condition_list))],
        'staircase_intensity_active': [starting_probe_intensity for _ in range(len(condition_list))], 
        'reversal_termination':[reversal_termination for _ in range(len(condition_list))],
        'n_dw': [staircase_params['n_dw']],
        'n_up': [staircase_params['n_up']],
        'logUNIT_UP': [staircase_params['logUNIT_UP']],
        'logUNIT_DW': [staircase_params['logUNIT_DW']],
        'count_down_terminate':[0],
        'terminate_bool':[0],
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
