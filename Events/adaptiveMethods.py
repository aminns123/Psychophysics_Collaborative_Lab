"""
Adaptive psychophysical methods (ADM staircase).

This module implements contrast staircases for adaptive threshold experiments.
Trial history and experiment settings are still stored as indexed lists
(legacy format). Named index maps below document that layout so the code can
be migrated to structured config objects later.

Main entry point for staircase updates: ``conditions()``.
"""

import math

import Functions.functionsForUse as funcs

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
    Convert CPU luminance values to Weber contrast.

    Weber contrast = (L - L_background) / (L_max - L_background)

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
        weber = (value - background_crt) / span
        if apply_log:
            weber = log_function(weber)
        weber_values.append(weber)
    return weber_values

def convert_weber_contrast_to_screenIntensity(max_Intensity, background_Intensity, weber_contrast):
    """Convert Weber contrast back to CPU luminance."""
    return ((max_Intensity - background_Intensity) * weber_contrast) + background_Intensity

# -----------------------------------------------------------------------------
# Staircase step rules
# -----------------------------------------------------------------------------

def conditionRateUPDW(current_lum, reference_lum, rate, step, log_unit, rule):
    """
    Compute the next contrast level for an up or down staircase step.

    The ``rule`` selects how ``current_lum`` and ``reference_lum`` are combined.
    See ``CONDITION_RULE`` for valid rule indices.
    """
    rule = int(rule)
    if rule == CONDITION_RULE["weighted_average"]:
        return (current_lum + reference_lum) * rate
    if rule == CONDITION_RULE["additive_step"]:
        return current_lum + step
    if rule == CONDITION_RULE["log_step"]:
        return current_lum * (10 ** log_unit)
    if rule == CONDITION_RULE["log_step_offset"]:
        return current_lum * (10 ** math.log10(1 + log_unit))
    raise ValueError(f"Unknown condition rule: {rule}")

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

def defineReversal_Multi(store_data, step_backs):
    """
    Find trial indices for the last correct and last incorrect response.

    Walks backward through trials for the current ADM ID. The correct index
    is the most recent correct trial; the wrong index is the most recent
    incorrect trial before contrast dropped below the current level.

    Parameters
    ----------
    store_data : list
        Full trial store (see ``STORE_DATA_INDEX``).
    step_backs : unused
        Kept for backward compatibility with older call sites.

    Returns
    -------
    tuple
        (correct_trial_index, wrong_trial_index)
    """
    del step_backs  # legacy parameter, not used

    trials = _parse_store_data(store_data)
    current_adm_id = int(trials["adm_ids"][-1])
    current_contrast = trials["contrast"][-1]

    correct_index = 0
    wrong_index = 0
    trial_index = len(trials["probe_positions"]) - 1

    while trial_index > 0:
        trial_index -= 1
        if int(trials["adm_ids"][trial_index]) != current_adm_id:
            continue

        probe_side = trials["probe_lr"][trial_index]
        response_side = trials["human_lr"][trial_index]

        if probe_side != response_side:
            wrong_index = trial_index
            if trials["contrast"][correct_index] > current_contrast:
                break
        elif probe_side == response_side:
            correct_index = trial_index

    if trial_index == 0:
        correct_index = 1

    return correct_index, wrong_index


def retrieve_staircase_weber_contrasts(adm_list, contrast_list, adm_id_now):
    """Return contrast values for all trials belonging to ``adm_id_now``."""
    return [
        contrast_list[index]
        for index, adm_id in enumerate(adm_list)
        if int(adm_id) == adm_id_now
    ]


# -----------------------------------------------------------------------------
# Trial data utilities
# -----------------------------------------------------------------------------

def check_values(values):
    """Return unique values from ``values``, preserving first-seen order."""
    seen = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen

def findIndex(array_list, target):
    """Return the index of ``target`` in ``array_list`` (integer comparison)."""
    target = int(target)
    for index, value in enumerate(array_list):
        if int(value) == target:
            return index
    return 0

def appendTrials(count_rows):
    """Extract the first column from rows shaped like ``[[value, count], ...]``."""
    return [row[0] for row in count_rows]


def count_values_type(values, unique_values, start_index):
    """
    Count occurrences of each value in ``unique_values``.

    Returns
    -------
    tuple
        (rows of [value, count], total_count)
    """
    counts = []
    total = 0
    for value in unique_values:
        count = sum(1 for item in values[start_index:] if item == value)
        counts.append([value, count])
        total += count
    return counts, total

# -----------------------------------------------------------------------------
# Staircase orchestration (``conditions`` and helpers)
# -----------------------------------------------------------------------------

def _parse_store_data(store_data):
    """Map legacy trial-store list indices to named trial arrays."""
    return {name: store_data[index] for name, index in STORE_DATA_INDEX.items()}

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
    """Convert a single CPU contrast value to Weber contrast."""
    return convert_screen_intensity_history_to_weber_contrast_list([value], background_cpu, max_cpu)[0]

def _count_staircase_reversals(adm_ids, contrast_values, current_adm_id, background, maximum):
    """Count staircase reversals for trials belonging to the current ADM."""
    adm_contrasts   = retrieve_staircase_weber_contrasts(adm_ids, contrast_values, current_adm_id)
    weber_contrasts = convert_screen_intensity_history_to_weber_contrast_list(adm_contrasts, background, maximum)
    return count_reversals_HighLow(weber_contrasts)[0]

def _resolve_condition_threshold(params, total_reversals, adm_trial_count):
    """Pick the active stopping rule based on experiment configuration."""
    if params["condition_mode"] == CONDITION_MODE["trial_count"]:
        return adm_trial_count, params["trial_point"]
    return total_reversals, params["reversal_point"]

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
    if trial.name == "new_condition":
        trial.state_new_condition_for_stimulus()
    elif trial.name == "stimuli":
        pass
    elif event != "MOUSE" and trial.name == "response":
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
    if not args:
        return

    params              = funcs.read_JSON(trial.file_parameters_Stimulus)
    n_up                = params["n_up"]
    n_dw                = params["n_dw"] 
    background_intensity= params['background_intensity']
    max_intensity       = params['max_intensity']
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
    probe_weber_contrast        = _to_weber(staircase_intensity_active, background_intensity, max_intensity)
    probe_choice                = conditions_data['probe_Alternative_Choice'][staircase_id]


    subject_response    = _key_to_response(args[0])
    probe_Alternative_Choice_history.append(probe_choice)
    human_Alternative_Choice_history.append(subject_response)

    print('------------- SUBJECT RESPONSE --------------------')
    print('probe_choice: ', probe_choice)
    print('subject_response: ', subject_response)

    if probe_choice == subject_response:
        _beep(1000, duration)
    else:
        _beep(300, duration)

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
    
    def _check_responses_history(staircase_stimulus_choice, staircase_subject_choice):
        """
        Returns:
            0 -> decrease contrast
            1 -> increase contrast
            2 -> leave contrast unchanged
        """

        # ----- Current response was correct -----
        if probe_choice == subject_response:

            n = min(len(staircase_subject_choice), n_dw)

            recent_stimulus = staircase_stimulus_choice[-n:]
            recent_subject  = staircase_subject_choice[-n:]

            if all(s == r for s, r in zip(recent_stimulus, recent_subject)):
                return 0      # decrease contrast

            return 2          # keep same

        # ----- Current response was incorrect -----
        else:

            n = min(len(staircase_subject_choice), n_up)

            recent_stimulus = staircase_stimulus_choice[-n:]
            recent_subject  = staircase_subject_choice[-n:]

            if all(s != r for s, r in zip(recent_stimulus, recent_subject)):
                return 1      # increase contrast

            return 2          # keep same

    def _update_probe_weber_contrast(integer, weber_contrast):

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

    
    # isolate staircase
    (
    staircase_stimulus_choice, 
    staircase_subject_choice
    ) = _get_single_staircase_history(data_responses, staircase_id)
    # check last responses (do we change contrast of probe?)
    contrast_update_bool        = _check_responses_history(staircase_stimulus_choice, staircase_subject_choice)
    print('contrast_update_bool: ',contrast_update_bool)
    print('probe_weber_contrast: ', probe_weber_contrast)
    print("step_dw:", stetp_dw)

    # update probes: contrast and cpu_intensity
    new_probe_weber_contrast    = _update_probe_weber_contrast(contrast_update_bool, probe_weber_contrast)
    print('new_probe_weber_contras: ',new_probe_weber_contrast)
    new_probe_screen_intensity  = _weber_contrast_to_cpu_intensity(new_probe_weber_contrast, params)

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
    funcs.create_JSON(trial.file_experiment_Conditions, conditions_data)

    funcs.write_toText(trial.file_response_record, data_responses)



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


        data_responses      = funcs.readText_toList(self.file_response_record)
        staircase_Identity_history          = data_responses[3]
        probe_screen_intensity_history      = data_responses[5]


        data_conditions             = funcs.read_JSON(self.file_experiment_Conditions)
        condition_list              = data_conditions['condition_list']
        staircase_Identities        = data_conditions['staircase_Identities']
        #current_staircase_id = data_conditions['staircase_Identity']   
        staircase_intensity_active   = data_conditions['staircase_intensity_active']

        new_id                  = random.choice(staircase_Identities)
        condition_value         = condition_list[new_id]
        probe_screen_intensity  = staircase_intensity_active[new_id]
        terminate_criteria      = data_conditions["reversal_termination"][new_id]
        count_down_terminate    = data_conditions["count_down_terminate"][0]
        terminate_bool          = data_conditions['terminate_bool'][0]
        # ---------------------------------------- # 

        probe_weber_contrast_history = convert_screen_intensity_history_to_weber_contrast_list(
                                        probe_screen_intensity_history, 
                                        background_intensity, 
                                        max_intensity)

        reversal_count               = _count_staircase_reversals(
                                        staircase_Identity_history, 
                                        probe_weber_contrast_history, 
                                        new_id, 
                                        background_intensity, 
                                        max_intensity)

        def _terminate_staircase_bool():
            """Checks if staircase """
            if reversal_count > terminate_criteria:
                if len(condition_list) > 1:
                    remove_value = condition_value
                    if remove_value in condition_list:
                        condition_list.remove(remove_value)
                
                elif len(condition_list) == 1:
                    count_down_terminate += 1
                    if count_down_terminate >= 2:
                        terminate_bool = 1
                    else:
                        terminate_bool = 0
            else:
                pass
        
        
        _terminate_staircase_bool()

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

        data_conditions['condition_list']                       = condition_list
        data_conditions['probe_Alternative_Choice'][new_id]     = value_response
        data_conditions['staircase_Identity_active']            = [new_id]
        data_conditions['weber_contrast_active'][new_id]        = probe_weber_contrast
        data_conditions['staircase_intensity_active'][new_id]   = probe_screen_intensity
        data_conditions['stimulus_choice_active']               = [stimulus_choice_active]
        data_conditions['terminate_bool']                       = [terminate_bool]
        data_conditions['count_down_terminate']                 = [count_down_terminate]

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
            "nUP": self.nUP,
        }