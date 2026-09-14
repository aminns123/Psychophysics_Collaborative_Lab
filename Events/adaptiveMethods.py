"""
Adaptive psychophysical methods (ADM staircase).

This module implements contrast staircases for adaptive threshold experiments.
Trial history remains in its legacy six-column format. Pure independent
response state and lifecycle live in Events.staircase; this module adapts the
existing CSF trial/file interface to those mechanisms.
"""

import math

import Functions.functionsForUse as funcs
from Events.staircase import ResponseStreak, Step
from Events.display_contrast import normalized_display_contrast, display_contrast_to_screen_intensity

DEFAULT_PRE_REVERSAL_RATE = 0.3
LEFT_RESPONSE = 0
RIGHT_RESPONSE = 1


# -----------------------------------------------------------------------------
# Contrast conversion
# -----------------------------------------------------------------------------

def convert_screen_intensity_history_to_weber_contrast_list(contrast_cpu, background_crt, max_crt, 
                                                            log_function=math.log10,
                                                            apply_log=False):
    """
    Legacy name: convert digital intensities to normalized display contrast.

    C_disp = (I_n - I_b) / (I_M - I_b), NOT conventional Weber contrast.

    Parameters
    ----------
    contrast_cpu : list
        Luminance values in CPU units.
    background_crt, max_crt : float
        Background and maximum luminance used for normalisation.
    log_function : callable
        Log transform applied when ``apply_log`` is True (default: log10).
    apply_log : bool
        When True, return log-transformed Weber contrast.
    """
    span = max_crt - background_crt
    if span == 0:
        raise ValueError("max_crt and background_crt must be different")

    weber_values = []
    for value in contrast_cpu:
        weber = normalized_display_contrast(value,
            background_intensity=background_crt, maximum_intensity=max_crt)
        if apply_log:
            weber = log_function(weber)
        weber_values.append(weber)
    return weber_values

def convert_weber_contrast_to_screenIntensity(max_Intensity, background_Intensity, weber_contrast):
    """Legacy compatibility name: invert normalized display contrast."""
    return display_contrast_to_screen_intensity(weber_contrast,
        background_intensity=background_Intensity, maximum_intensity=max_Intensity)

# -----------------------------------------------------------------------------
# Staircase step rules
# -----------------------------------------------------------------------------


def count_reversals_HighLow(contrast_list):
    """
    Count direction reversals in a contrast sequence.

    Returns
    -------
    tuple
        (reversal_count, trial_indices, contrast_at_reversals)
    """
    if len(contrast_list) <= 1:
        return 0, [0], [0]

    reversal_indices = []
    reversal_contrasts = []

    if contrast_list[1] - contrast_list[0] < 0:
        direction = -1
    elif contrast_list[1] - contrast_list[0] > 0:
        direction = 1
    else:
        direction = 0

    for index in range(1, len(contrast_list) - 1):
        delta = contrast_list[index + 1] - contrast_list[index]
        if delta < 0:
            new_direction = -1
        elif delta > 0:
            new_direction = 1
        else:
            continue

        if direction == 0:
            direction = new_direction
            continue

        if new_direction != direction:
            direction = new_direction
            reversal_indices.append(index)
            reversal_contrasts.append(contrast_list[index])

    return len(reversal_indices), reversal_indices, reversal_contrasts

def retrieve_staircase_weber_contrasts(adm_list, contrast_list, adm_id_now):
    """Return contrast values for all trials belonging to ``adm_id_now``."""
    return [
        contrast_list[index]
        for index, adm_id in enumerate(adm_list)
        if int(adm_id) == adm_id_now
    ]

# -----------------------------------------------------------------------------
# Staircase orchestration (``conditions`` and helpers)
# -----------------------------------------------------------------------------

def _beep(frequency, duration_ms):
    """
    Play an optional feedback tone.

    The experiment was written on Windows, where ``winsound`` is available.
    Public/shared use may happen on other systems, so missing audio support
    should not crash the staircase logic.
    """
    try:
        import winsound
    except ImportError:
        return

    winsound.Beep(int(frequency), int(duration_ms))

def _to_weber(value, background_cpu, max_cpu):
    """Legacy compatibility name for C_disp; this is not Weber contrast."""
    return normalized_display_contrast(value,
        background_intensity=background_cpu, maximum_intensity=max_cpu)

def _count_staircase_reversals(adm_ids, contrast_values, current_adm_id, background, maximum):
    """Count staircase reversals for trials belonging to the current ADM."""
    adm_contrasts   = retrieve_staircase_weber_contrasts(adm_ids, contrast_values, current_adm_id)
    weber_contrasts = convert_screen_intensity_history_to_weber_contrast_list(adm_contrasts, background, maximum)
    return count_reversals_HighLow(weber_contrasts)[0]

def _weber_contrast_to_cpu_intensity(probe_weber_contrast, params):
    """Convert Weber contrast back to CPU luminance, clamped to background."""
    background      = params["background_intensity"]
    probe_intensity = convert_weber_contrast_to_screenIntensity(
        params["max_intensity"], background, probe_weber_contrast
    )
    return max(probe_intensity, background)

# -----------------------------------------------------------------------------
# Event logging and response handling
# -----------------------------------------------------------------------------

def record_event(event, time, trial, args):
    """
    Route experiment events to the appropriate trial handler.

    Stimulus trials log probe parameters; response trials record the subject
    choice and update the staircase.
    """
    if trial is None:
        return
    if event == "TRIAL":
        if trial.name == "new_condition":
            trial.state_new_condition_for_stimulus()
        elif trial.name == "response":
            trial.response_recorded = False
    elif event == "KEY" and trial.name == "response":
        # The engine logs keys before applying the trial's accepted-key filter.
        if len(args) >= 2 and args[1] in trial.keys:
            subject_response(trial, args)


def _key_to_response(key):
    """Map keyboard input to a binary 2AFC response (0 = left/down, 1 = right/up)."""
    key = str(key).upper()
    print('---------- KEY -------------')
    print(key)
    print('____________________________')
    if key in ("LSHIFT", "LEFT", "DOWN"):
        return LEFT_RESPONSE
    if key in ("RSHIFT", "RIGHT", "UP"):
        return RIGHT_RESPONSE
    raise ValueError(f"Unrecognised response key: {key}")


def subject_response(trial, args):
    """
    Record a subject's 2AFC response and update stored trial / staircase data.

    Writes updated trial history and parameter files via ``funcs``.
    _________________________________________________________
    @ all this file needs to do is:
        1. decide to step up or step down the probes contrast
            i) how many of the last responses (including now) are correct?
            ii) step up or step down?
        2. store history of responses and stimulus conditions
    ---------------------------------------------------------

        CPU intensity
                ↓
        convert to Weber contrast
                ↓
        perform staircase
                ↓
        convert back
                ↓
        display CPU intensity 

        or

        Weber
        ↓
        (staircase operates entirely here)
        ↓
        CPU (once)
        ↓
        Display

    """
    if not args or getattr(trial, "response_recorded", False):
        return

    params              = funcs.read_JSON(trial.file_parameters_Stimulus)
    background_intensity= params['background_intensity']
    stetp_up            = params['logUNIT_UP']
    stetp_dw            = params['logUNIT_DW']

    data_responses      = funcs.readText_toList(trial.file_response_record)

    stimulus_condition_history       = data_responses[0]
    probe_Alternative_Choice_history = data_responses[1]
    human_Alternative_Choice_history = data_responses[2]
    staircase_Identity_history       = data_responses[3]
    probe_weber_contrast_history     = data_responses[4]
    probe_screen_intensity_history   = data_responses[5]

    duration            = 500

    conditions_data             = funcs.read_JSON(trial.file_experiment_Conditions)
    staircase_id                = conditions_data['staircase_Identity_active'][0]  
    stimulus_condition          = conditions_data['condition_list'][staircase_id]
    staircase_intensity_active  = conditions_data['staircase_intensity_active'][staircase_id]  
    probe_weber_contrast = normalized_display_contrast(staircase_intensity_active,
        background_intensity=background_intensity, maximum_intensity=params['max_intensity'])
    probe_choice                = conditions_data['probe_Alternative_Choice'][staircase_id]


    response = _key_to_response(args[0])
    probe_Alternative_Choice_history.append(probe_choice)
    human_Alternative_Choice_history.append(response)

    print('------------- SUBJECT RESPONSE --------------------')
    print('probe_choice: ', probe_choice)
    print('subject_response: ', response)

    if probe_choice == response:
        _beep(1000, duration)
    else:
        _beep(300, duration)

    
    # Response state is explicit and independent of the legacy sentinel/history.
    def update_value(step):
        contrast = _update_probe_weber_contrast(step, probe_weber_contrast, stetp_up, stetp_dw)
        return _weber_contrast_to_cpu_intensity(contrast, params)

    step, new_probe_screen_intensity = trial.adaptive_run.respond(
        staircase_id, probe_choice == response, update_value)
    # Preserve the legacy six-column post-update quantities and their mathematics.
    new_probe_weber_contrast = _update_probe_weber_contrast(
        step, probe_weber_contrast, stetp_up, stetp_dw)

    stimulus_condition_history.append(stimulus_condition)
    staircase_Identity_history.append(staircase_id)
    probe_weber_contrast_history.append(new_probe_weber_contrast)
    probe_screen_intensity_history.append(new_probe_screen_intensity)

    data_responses[0] = stimulus_condition_history
    data_responses[1] = probe_Alternative_Choice_history
    data_responses[2] = human_Alternative_Choice_history
    data_responses[3] = staircase_Identity_history
    data_responses[4] = probe_weber_contrast_history
    data_responses[5] = probe_screen_intensity_history

    conditions_data['staircase_intensity_active'][staircase_id] = new_probe_screen_intensity
    conditions_data['total_Reversals'][staircase_id] = trial.adaptive_run.states[staircase_id].reversal_count
    conditions_data['active_staircase_ids'] = list(trial.adaptive_run.active_ids)
    conditions_data['terminate_bool'] = [int(trial.adaptive_run.status != 'running')]
    funcs.create_JSON(trial.file_experiment_Conditions, conditions_data)

    funcs.write_toText(trial.file_response_record, data_responses)
    trial.response_recorded = True

def _get_single_staircase_history(data_responses, staircase_id):
    #stimulus_condition_history       = data_responses[0]
    probe_Alternative_Choice_history = data_responses[1]
    human_Alternative_Choice_history = data_responses[2]
    staircase_Identity_history       = data_responses[3]
    #probe_weber_contrast_history     = data_responses[4]
    #probe_screen_intensity_history   = data_responses[5]

    list_find  = staircase_Identity_history
    value_find = staircase_id
    indices    = [i for i, x in enumerate(list_find) if x == value_find]

    staircase_stimulus_choice = [probe_Alternative_Choice_history[i] for i in indices]
    staircase_subject_choice  = [human_Alternative_Choice_history[i] for i in indices]
    return staircase_stimulus_choice, staircase_subject_choice

def _check_responses_history(staircase_stimulus_choice, staircase_subject_choice, probe_choice, n_dw, n_up):
    """Compatibility helper: replay a complete single-staircase response history.

    The caller must include the current response exactly once and exclude any
    placeholder row. Live experiments use explicit AdaptiveRun state instead.
    probe_choice is retained for call compatibility; history supplies correctness.
    """
    if len(staircase_stimulus_choice) != len(staircase_subject_choice):
        raise ValueError("Stimulus and response histories must have equal lengths")
    streak = ResponseStreak()
    step = Step.HOLD
    for stimulus, response in zip(staircase_stimulus_choice, staircase_subject_choice):
        step = streak.respond(stimulus == response, n_dw, n_up)
    return step


def _update_probe_weber_contrast(integer, weber_contrast, stetp_up, stetp_dw):

    def _increase_contrast():
        return weber_contrast*pow(10, stetp_up)

    def _decrease_contrast():
        return weber_contrast*pow(10, -stetp_dw)
    
    if integer == 0:
        return _decrease_contrast()
    elif integer == 1:
        return _increase_contrast()
    else:
        return weber_contrast

# -----------------------------------------------------------------------------
# Trial classes
# -----------------------------------------------------------------------------

class Trial_small:
    """Simple timed trial (instructions, fixation, etc.)."""

    def __init__(self, name, stimuli, duration_ms, keys=None, mouse=False):
        self.stimuli = stimuli
        self.T = duration_ms
        self.name = name
        self.keys = keys or []
        self.mouse = mouse

    def draw(self, win):
        win.clear()
        for stim in self.stimuli:
            stim.draw()

    def __str__(self):
        return self.name

    def default(self):
        return {
            "type": "Trial",
            "name": self.name,
            "keys": self.keys,
            "mouse": self.mouse,
            "stimuli": self.stimuli,
        }


class Trials_read_write_staircase_conditions:
    """Adaptive trial that assigns ADM conditions and logs probe parameters."""

    def __init__(
        self,
        name,
        stimuli,
        duration_ms,
        pos,
        file_experiment_Conditions,
        file_parameters_Stimulus,
        file_response_record,
        keys=None,
        mouse=False,
    ):
        self.stimuli        = stimuli
        self.T              = duration_ms
        self.name           = name
        self.keys           = keys or []
        self.mouse          = mouse
        self.pos            = pos
        self.file_experiment_Conditions = file_experiment_Conditions
        self.file_parameters_Stimulus   = file_parameters_Stimulus
        self.file_response_record       = file_response_record

    def state_new_condition_for_stimulus(self):
        """states new condition for stimulus, to be passed over to stimulus.py file"""
        import random

        data_params         = funcs.read_JSON(self.file_parameters_Stimulus)
        background_intensity= data_params["background_intensity"]
        max_intensity       = data_params["max_intensity"]


        data_conditions = funcs.read_JSON(self.file_experiment_Conditions)
        # Keep condition arrays and identities stable; select only unfinished IDs.
        new_id = self.adaptive_run.select(random.choice)
        probe_screen_intensity = data_conditions['staircase_intensity_active'][new_id]

        state1, state2 = data_conditions['2AFC_choice']

        stimulus_choice_active   = self.pos[0]  
        if stimulus_choice_active == state2:
            value_response = RIGHT_RESPONSE
        elif stimulus_choice_active == state1:
            value_response = LEFT_RESPONSE

        _beep(550, self.T)

        """save updated conditions"""

        probe_weber_contrast = convert_screen_intensity_history_to_weber_contrast_list(
                                        [probe_screen_intensity], 
                                        background_intensity, 
                                        max_intensity)[0]

        data_conditions['probe_Alternative_Choice'][new_id]     = value_response
        data_conditions['staircase_Identity_active']            = [new_id]
        data_conditions['weber_contrast_active'][new_id]        = probe_weber_contrast
        data_conditions['staircase_intensity_active'][new_id]   = probe_screen_intensity
        data_conditions['stimulus_choice_active']               = [stimulus_choice_active]
        data_conditions['terminate_bool'] = [int(self.adaptive_run.status != 'running')]
        data_conditions['active_staircase_ids'] = list(self.adaptive_run.active_ids)

        print('--------- NEW STATE ------------')
        print('probe_screen_intensity: ', probe_screen_intensity)
        print('stimulus_choice_active: ', stimulus_choice_active)

        funcs.create_JSON(self.file_experiment_Conditions, data_conditions)

        # ----------------- END --------------------

    def draw(self, win):
        win.clear()
        for stim in self.stimuli:
            stim.draw()

    def __str__(self):
        return self.name

    def default(self):
        return {
            "type": "Trial_New",
            "name": self.name,
            "keys": self.keys,
            "mouse": self.mouse,
            "stimuli": self.stimuli,
            "pos": self.pos,
        }
