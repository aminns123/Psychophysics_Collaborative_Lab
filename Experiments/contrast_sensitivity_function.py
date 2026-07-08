
import random
import numpy as np
import datetime
from pathlib import Path
import json

import pyglet

import Functions.functionsForUse as funcs

from Events.stimuliC import (
    Dot_stairCase_centre, 
    Grating_ADM
)
from libC import (
    ExpWindow, 
    Params, 
    key, 
    run
)
from Events.adaptiveMethods import (
    Trials_read_write_staircase_conditions,
    Trial_small,
    record_event,
)


# ------------------------------ Experiment setup ------------------------------

def run_experiment(filename_Conditions, file_params_Stimulus, file_response_record, data_save_repository):
    """
    Run the experiment by setting up the window, stimuli, and trial sequence.
    """

    with open(data_save_repository+"/"+"user_experiment_config.json", "r") as f:
        dict_all_dicts = json.load(f)


    experiment_params       = dict_all_dicts['experiment_params']
    # ------------------------------ Window setup ------------------------------
    pyglet.options['vsync'] = True
    pyglet.options['double_buffer'] = True
    win = ExpWindow(fullscreen=True)


    pixel_width             = win.width
    pixel_height            = win.height
    screen_width_pixel      = pixel_width
    screen_height_pixel     = pixel_height
    aspect_ratio            = screen_width_pixel/screen_height_pixel
    monitor_refresh_rate    = 60

    metre_width             = 596.2e-3 # 610e-3
    metre_height            = 335.3e-3 # 350e-3
    screen_width_m          = metre_width
    screen_height_m         = metre_height

    cx, cy                  = win.width // 2, win.height // 2

    pixel_metre_ratio   = funcs.ratio_PIXEL_Meter(win.width, metre_width) # <- seems to give correct answer.
    viewing_distance_m  = experiment_params['viewing_distance_m']

    fov_x_deg = 2 * np.degrees(np.arctan((screen_width_m / 2) / viewing_distance_m))
    fov_y_deg = 2 * np.degrees(np.arctan((screen_height_m / 2) / viewing_distance_m))

    ppd_x     = screen_width_pixel / fov_x_deg
    ppd_y     = screen_height_pixel / fov_y_deg

    monitor_screen_params = {
        'monitor_refresh_rate': monitor_refresh_rate,
        'screen_width_pixel': screen_width_pixel,
        'screen_height_pixel': screen_height_pixel,
        'screen_width_m': screen_width_m,
        'screen_height_m': screen_height_m,
        'aspect_ratio': aspect_ratio,
        'pixel_metre_ratio': pixel_metre_ratio,
        'fov_x_deg': fov_x_deg,
        'fov_y_deg': fov_y_deg,
        'ppd_x': ppd_x,
        'ppd_y': ppd_y,
        'center_x_pixel': cx,
        'center_y_pixel': cy,
        'window_width_pixel': win.width,
        'window_height_pixel': win.height,
    }

    cx, cy                      = monitor_screen_params['cx'], monitor_screen_params['cy']
    monitor_refresh_rate        = monitor_screen_params['monitor_refresh_rate']
    pyglet_wakeup_rate_check    = monitor_screen_params['pyglet_wakeup_rate_check']
    timeFixate                  = monitor_screen_params['timeFixate']
    timeInterval                = monitor_screen_params['timeInterval']
    timeAB                      = monitor_screen_params['timeAB']
    timeT                       = monitor_screen_params['timeT']

    # ------------------------------ Stimulus parameters ------------------------------


    kwargs_fixate= {
        'c':                    experiment_params['background_intensity']+0.09,  # should be 0.33 or less not 0.45 +0.08
        'sigma':   	            0.035,  # 0.035 || should be 0.01 or less not 0.02
        'fs':                   0.0,
        'phi':                  0.0,
        'edge':                 2.0,#2
        'res':                  64,
        'msg':                  'Experiment over! ----- Press: Esc'
    }

    kwargs_fake_Fixate= {
        'c':                    experiment_params['background_intensity'],  # should be 0.33 or less not 0.45
        'sigma':   	            0.00001,  # should be 0.01 or less not 0.02
        'fs':                   0.0,
        'phi':                  0.0,
        'edge':                 2.0,
        'res':                  64,
        'msg':                  '-- Experiment over! -- Press: Esc --'
    }

    kwargs_grating =  {
        'width':                100,
        'fs':                   40,
        'ph':                   0.0,
        'speed':                0.0,
        'contr':                0.018,
        'theta':                0.0,
        'bg':                   experiment_params['background_intensity'], 
        'box':                  False,
        'Lbg':                  25,
        'Lmin':                 0.0, 
        'Lmax':                 25,
        'gamma':                0.0,
        'BRTRR':                1.2,
        'flanker_width': 		5.0, # arc angle in degree
        'flanker_displacement': 3.0,
        'probe_displacement_dx':0.4,
        'probe_displacement_dy':0.3,# was 0.2, 0.0
    }

    # ------------------------------ Experiment setup ------------------------------


    # ------------------------------ local Functions ------------------------------

    def _make_text_label(message, position, font_size=24):
        """Create a centered pyglet label for instruction screens."""
        return pyglet.text.Label(
            message,
            x=position[0],
            y=position[1],
            anchor_x='center',
            anchor_y='center',
            font_size=font_size,
        )

    def _make_adm_trial(name, stimuli, duration_ms, position, keys_for_trial=None):
        """Create a Trial_ADMs with the shared files used by this experiment."""
        return Trials_read_write_staircase_conditions(
            name,
            stimuli,
            duration_ms,
            position,
            filename_Conditions,
            file_params_Stimulus,
            file_response_record,
            keys_for_trial or [],
            mouse=False,
        )


    # ------------------------------ Trial sequence ------------------------------

    grating_displacement = funcs.convertArcangleTOPixel(0.5, experiment_params['viewing_distance_m'], pixel_metre_ratio) 

    alternative_forced_choice = {
        '2AFC_choice': [-grating_displacement, grating_displacement],  
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

    experiment_title    = [_make_text_label('Contrast Sensitivity Function\n', (cx, cy))]
    welcome_line        = [_make_text_label('Press SPACE when ready.', (cx, cy - 50))]
    farewell_line       = [_make_text_label('Experiment over!', (cx, cy - 50))]

    trials = [
        Trial_small('Start', experiment_title, 5 * 1000, keys_default, mouse=False),
        Trial_small('Start', welcome_line, 0, keys_default, mouse=False),
    ]

    fakeProbe = Dot_stairCase_centre(
        experiment_params['bkg_intensity'],
        filename_Conditions
        (cx, cy),
        Params(**kwargs_fake_Fixate),
    )
    centreDOT = Dot_stairCase_centre(
        experiment_params['bkg_intensity'],
        filename_Conditions
        (cx, cy),
        Params(**kwargs_fixate),
    )
    probeStimulus = Grating_ADM(
        posCentre,
        filename_Conditions,
        Params(**kwargs_grating),
    )

    fake_probe_trial = [fakeProbe]
    probe_trial      = [probeStimulus]
    fixation_trial   = [centreDOT]

    # ------------------------------ Trial loop ------------------------------
    fixateDOT = _make_adm_trial(
        'fixation',
        fixation_trial,
        timeFixate,
        [cx, cy],
    )
    fixate_state_new_condition = _make_adm_trial(
        'new_condition',
        fake_probe_trial,
        timeInterval,
        [cx, cy],
    )
    fixateInterval = _make_adm_trial(
        'fixation',
        fake_probe_trial,
        timeInterval,
        [cx, cy],
    )
    fixateRESPONSE = _make_adm_trial(
        'responses',
        fixation_trial,
        timeT,
        [cx, cy],
        response_keys,
    )

    trial_exps = [fixateDOT]
    for _ in range(experiment_params['number_trials']):

        posX = random.choice(alternative_forced_choice['2AFC_choice'])

        stimulusPROBE = _make_adm_trial(
            'stimuli',
            probe_trial,
            timeAB,
            [cx+posX, cy],
        )    

        sequence = [
            fixateDOT,
            fixate_state_new_condition,
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

    # ------------------------------- Finish experiment run -------------------------------

    funcs.removeZeroRow(file_response_record)
    funcs.correctFileSpacings(file_response_record)
