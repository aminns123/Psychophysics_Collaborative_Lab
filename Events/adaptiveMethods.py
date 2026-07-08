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


# -----------------------------------------------------------------------------
# Legacy data layout
# -----------------------------------------------------------------------------
# These maps translate list indices into readable names. When rebuilding the
# project, replace the underlying lists with dicts or dataclasses and drop
# these constants.

DATA_PARAM_INDEX = {
    "probe_lr": 1,
    "probe_pos_x": 3,
    "probe_start": 4,
    # Legacy note: index 5 is written as ``self.nUP`` before a stimulus trial
    # and as ``reversal_tick`` after a response. Keep the storage behavior for
    # now, but split this field when moving to a dict/dataclass config.
    "reversal_tick": 5,
    "rate_down": 6,
    "total_reversals": 9,
    "rate_up": 10,
    "probe_pos_y": 11,
    "background_contrast": 12,
    "max_contrast": 13,
    "reversal_point": 14,
    "n_up": 15,
    "distance_to_monitor": 17,
    "pixel_metre_ratio": 18,
    "terminate_criteria": 19,
    "terminate_bool": 20,
    "step_down_up": 21,
    "condition_rule": 22,
    "log_unit_up": 23,
    "log_unit_down": 24,
    "trial_limit": 25,
    "wait_count": 26,
    "pre_reversal_step": 28,
    "condition_mode": 29,
    "trial_point": 30,
}

STORE_DATA_INDEX = {
    "probe_positions": 0,
    "probe_lr": 1,
    "human_lr": 2,
    "reversals": 3,
    "adm_ids": 4,
    "rate_down": 5,
    "contrast": 6,
    "rate_up": 7,
    "reversal_count": 8,
    "param_start": 9,
    "correct_tick": 10,
    "next_contrast": 11,
    "probe_y_positions": 12,
    "n_up_values": 13,
    "weber_contrast": 14,
    "spatial_frequency": 15,
}

CONDITION_MODE = {
    "reversal": 0,
    "trial_count": 1,
}

# Rules passed to ``conditionRateUPDW`` via dataParams[22].
CONDITION_RULE = {
    "weighted_average": 0,
    "additive_step": 1,
    "log_step": 2,
    "log_step_offset": 3,
}

DEFAULT_PRE_REVERSAL_RATE = 0.3
LEFT_RESPONSE = 0
RIGHT_RESPONSE = 1


# -----------------------------------------------------------------------------
# Contrast conversion
# -----------------------------------------------------------------------------

def convert_screen_intensity_history_to_weber_contrast_list(contrast_cpu, background_crt, max_crt, log_function=math.log10,
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


#def convert_screenIntensity_to_weber_contrast(max_Intensity, background_Intensity, screen_Intensity):
#    """Convert Weber contrast back to CPU luminance."""
#    return ((max_Intensity - background_Intensity) * screen_Intensity) + background_Intensity


def convert_weber_contrast_to_screenIntensity(max_Intensity, background_Intensity, weber_contrast):
    """Convert Weber contrast back to CPU luminance."""
    return ((max_Intensity - background_Intensity) * weber_contrast) + background_Intensity

# -----------------------------------------------------------------------------
# Staircase step rules
# -----------------------------------------------------------------------------

def rate_dw(rate_down, reversals, reversal_point):
    """
    Down-step rate before vs after the reversal threshold.

    Uses a fixed rate (0.3) until ``reversal_point`` reversals, then switches
    to the configured ``rate_down``.
    """
    if reversals < reversal_point:
        return DEFAULT_PRE_REVERSAL_RATE
    return rate_down


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


def findIndexFloat(array_list, target):
    """Return the index of ``target`` in ``array_list`` (exact match)."""
    for index, value in enumerate(array_list):
        if value == target:
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


def returnOnce(values):
    """Return absolute values, keeping first occurrence of each."""
    seen = []
    for value in values:
        absolute = abs(value)
        if absolute not in seen:
            seen.append(absolute)
    return seen


def count_Abs_type(count_rows):
    """Merge counts for values that differ only by sign."""
    merged_values = []
    merged_counts = []

    for value, count in count_rows:
        key = abs(value)
        if key not in merged_values:
            merged_values.append(key)
            merged_counts.append(count)
        else:
            index = findIndexFloat(merged_values, key)
            merged_counts[index] += count

    return [[merged_values[i], merged_counts[i]] for i in range(len(merged_values))]


# -----------------------------------------------------------------------------
# Staircase orchestration (``conditions`` and helpers)
# -----------------------------------------------------------------------------

def _parse_data_params(data_params):
    """Map legacy parameter list indices to named values."""
    return {name: data_params[index] for name, index in DATA_PARAM_INDEX.items()}


def _parse_store_data(store_data):
    """Map legacy trial-store list indices to named trial arrays."""
    return {name: store_data[index] for name, index in STORE_DATA_INDEX.items()}


def _append_store_value(store_data, field_name, value):
    """Append ``value`` to a named field in the legacy trial store."""
    store_data[STORE_DATA_INDEX[field_name]].append(value)


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


def _adm_trial_counts(store_data, start_index=1):
    """Return per-ADM-ID trial counts and the index for the current ADM."""
    trials = _parse_store_data(store_data)
    adm_ids = trials["adm_ids"]
    current_adm_id = int(adm_ids[-1])

    unique_ids = check_values(adm_ids)
    counts_by_id, _ = count_values_type(adm_ids, unique_ids, start_index)
    adm_id_list = appendTrials(counts_by_id)
    adm_index = findIndex(adm_id_list, current_adm_id)

    return counts_by_id, adm_index, current_adm_id


def _count_staircase_reversals(adm_ids, contrast_values, current_adm_id, background, maximum):
    """Count staircase reversals for trials belonging to the current ADM."""
    adm_contrasts   = retrieve_staircase_weber_contrasts(adm_ids, contrast_values, current_adm_id)
    weber_contrasts = convert_screen_intensity_history_to_weber_contrast_list(adm_contrasts, background, maximum)
    return count_reversals_HighLow(weber_contrasts)[0]


def _load_previous_trial_state(store_data, adm_index, counts_by_id):
    """
    Recover staircase state from the previous trial for the current ADM.

    Returns a dict with keys: param_start, correct_tick, reversal_n,
    count_reversals_total.
    """
    trials = _parse_store_data(store_data)
    adm_ids = trials["adm_ids"]
    current_adm_id = int(adm_ids[-1])

    if counts_by_id[adm_index][1] < 1:
        return {
            "param_start": 0,
            "correct_tick": trials["correct_tick"][0],
            "reversal_n": trials["reversal_count"][-1],
            "count_reversals_total": 0,
        }

    for trial_index in range(len(trials["correct_tick"]) - 1, -1, -1):
        if int(adm_ids[trial_index]) != current_adm_id:
            continue
        return {
            "param_start": trials["param_start"][trial_index],
            "correct_tick": trials["correct_tick"][trial_index],
            "reversal_n": trials["reversal_count"][trial_index],
            "count_reversals_total": trials["reversals"][trial_index],
        }

    return {
        "param_start": 0,
        "correct_tick": trials["correct_tick"][0],
        "reversal_n": trials["reversal_count"][-1],
        "count_reversals_total": 0,
    }


def _evaluate_current_response(store_data, adm_index, counts_by_id, params):
    """
    Assess the latest trial: wrong/correct, contrast used, recent response tally.
    """
    trials = _parse_store_data(store_data)
    adm_ids = trials["adm_ids"]
    current_adm_id = int(adm_ids[-1])
    last_index = len(trials["probe_lr"]) - 1
    n_up = params["n_up"]
    adm_trial_count = counts_by_id[adm_index][1]

    wrong = trials["probe_lr"][last_index] != trials["human_lr"][last_index]
    base_contrast = trials["contrast"][last_index]
    response_count = 0

    if adm_trial_count >= n_up:
        responses_seen = 0
        for trial_index in range(last_index, 0, -1):
            if responses_seen >= n_up + 1:
                break
            if int(adm_ids[trial_index]) != current_adm_id:
                continue

            if trials["probe_lr"][trial_index] == trials["human_lr"][trial_index]:
                response_count -= 1
            else:
                response_count += 1
            responses_seen += 1

        if int(adm_ids[last_index]) == current_adm_id:
            wrong = trials["probe_lr"][last_index] != trials["human_lr"][last_index]

    return {
        "wrong": wrong,
        "base_contrast": base_contrast,
        "response_count": response_count,
    }


def _resolve_condition_threshold(params, total_reversals, adm_trial_count):
    """Pick the active stopping rule based on experiment configuration."""
    if params["condition_mode"] == CONDITION_MODE["trial_count"]:
        return adm_trial_count, params["trial_point"]
    return total_reversals, params["reversal_point"]


def _reference_contrasts_weber(store_data, params, previous_state):
    """Build Weber-space reference contrasts for up/down staircase steps."""
    trials = _parse_store_data(store_data)
    background = params["background_contrast"]
    maximum = params["max_contrast"]
    param_start = previous_state["param_start"]

    if param_start == 0:
        previous_up = params["probe_start"]
        param_start += 1
        previous_wrong = None
    else:
        correct_index, wrong_index = defineReversal_Multi(
            store_data, previous_state["reversal_n"]
        )
        previous_up = trials["contrast"][correct_index]
        previous_wrong = _to_weber(trials["contrast"][wrong_index], background, maximum)

    return {
        "param_start": param_start,
        "previous_up": _to_weber(previous_up, background, maximum),
        "previous_wrong": previous_wrong,
        "background_weber": _to_weber(background, background, maximum),
    }


def _update_staircase_weber(response, references, params, previous_state, adm_trial_count):
    """Apply staircase update rules in Weber contrast space."""
    total_reversals = response["total_reversals"]
    base_contrast = _to_weber(
        response["base_contrast"],
        params["background_contrast"],
        params["max_contrast"],
    )

    state = {
        "contrast_weber": base_contrast,
        "correct_tick": previous_state["correct_tick"],
        "param_start": references["param_start"],
        "reversal_n": previous_state["reversal_n"],
        "rate_down": previous_state.get("rate_down"),
        "count_reversals_total": previous_state["count_reversals_total"],
        "response_count": response["response_count"],
    }

    if response["wrong"]:
        state["count_reversals_total"] = total_reversals
        state["correct_tick"] = 0
        state["contrast_weber"] = conditionRateUPDW(
            base_contrast,
            references["previous_up"],
            params["rate_up"],
            params["step_down_up"],
            params["log_unit_up"],
            params["condition_rule"],
        )
        state["reversal_n"] += 1
        return state

    state["count_reversals_total"] = total_reversals
    condition_now, condition_point = _resolve_condition_threshold(
        params, total_reversals, adm_trial_count
    )
    past_threshold = (
        condition_now >= condition_point
        or total_reversals >= params["reversal_point"]
    )

    if past_threshold:
        if state["correct_tick"] >= params["n_up"]:
            state["correct_tick"] = 0
            state["reversal_n"] = 1
            state["rate_down"] = rate_dw(
                params["rate_down"], total_reversals, params["reversal_point"]
            )
            state["contrast_weber"] = conditionRateUPDW(
                base_contrast,
                references["previous_wrong"],
                state["rate_down"],
                -params["step_down_up"],
                -params["log_unit_down"],
                params["condition_rule"],
            )
        else:
            state["contrast_weber"] = base_contrast
            state["correct_tick"] += 1
    else:
        state["rate_down"] = rate_dw(
            params["rate_down"], total_reversals, params["reversal_point"]
        )
        state["contrast_weber"] = conditionRateUPDW(
            base_contrast,
            references["background_weber"],
            state["rate_down"],
            -params["step_down_up"],
            -params["pre_reversal_step"],
            params["condition_rule"],
        )
        state["correct_tick"] = 0

    return state


def _weber_contrast_to_cpu_intensity(probe_weber_contrast, params):
    """Convert Weber contrast back to CPU luminance, clamped to background."""
    background      = params["background_contrast"]
    probe_intensity = convert_weber_contrast_to_screenIntensity(
        params["max_contrast"], background, probe_weber_contrast
    )
    return max(probe_intensity, background)


def update_staircase_probe_screen_intensity(storeData, dataParams, conditionS):
    """
    Update adaptive staircase contrast for the current ADM condition.

    Parameters
    ----------
    storeData : list
        Trial history in legacy list format (see ``STORE_DATA_INDEX``).
    dataParams : list
        Experiment parameters in legacy list format (see ``DATA_PARAM_INDEX``).
    conditionS : bool
        When True, apply Weber-space staircase updates before converting back
        to CPU luminance. When False, re-use the previous contrast state.

    Returns
    -------
    tuple
        (contrast_cpu, reversal_tick, correct_tick, param_start, rate_down,
         response_count, count_reversals_total, rate_up)
    """
    params = _parse_data_params(dataParams)
    trials = _parse_store_data(storeData)

    counts_by_id, adm_index, current_adm_id = _adm_trial_counts(storeData)
    total_reversals = _count_staircase_reversals(
        trials["adm_ids"],
        trials["contrast"],
        current_adm_id,
        params["background_contrast"],
        params["max_contrast"],
    )

    previous_state = _load_previous_trial_state(storeData, adm_index, counts_by_id)
    previous_state["rate_down"] = trials["rate_down"][-1]

    response = _evaluate_current_response(storeData, adm_index, counts_by_id, params)
    response["total_reversals"] = total_reversals

    # tick #
    contrast_weber = _to_weber(
        response["base_contrast"],
        params["background_contrast"],
        params["max_contrast"],
    )

    if conditionS:
        references  = _reference_contrasts_weber(storeData, params, previous_state)
        updated     = _update_staircase_weber(
            response,
            references,
            params,
            previous_state,
            counts_by_id[adm_index][1],
        )
        contrast_weber          = updated["contrast_weber"]
        correct_tick            = updated["correct_tick"]
        param_start             = updated["param_start"]
        reversal_n              = updated["reversal_n"]
        rate_down               = updated["rate_down"]
        count_reversals_total   = updated["count_reversals_total"]
        response_count          = updated["response_count"]
    else:
        correct_tick            = previous_state["correct_tick"]
        param_start             = previous_state["param_start"]
        reversal_n              = previous_state["reversal_n"]
        rate_down               = previous_state["rate_down"]
        count_reversals_total   = previous_state["count_reversals_total"]
        response_count          = response["response_count"]

    probe_screen_intensity = _weber_contrast_to_cpu_intensity(contrast_weber, params)

    return (
        probe_screen_intensity,
        reversal_n,
        correct_tick,
        param_start,
        rate_down,
        response_count,
        count_reversals_total,
        params["rate_up"],
    )


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
    if key in ("LSHIFT", "LEFT", "DOWN"):
        return LEFT_RESPONSE
    if key in ("RSHIFT", "RIGHT", "UP"):
        return RIGHT_RESPONSE
    raise ValueError(f"Unrecognised response key: {key}")


def _find_baseline_contrast(store_data, adm_id, probe_start):
    """Find the contrast baseline for the current ADM before recording a response."""
    trials              = _parse_store_data(store_data)
    contrast_history    = trials["next_contrast"]
    adm_ids             = trials["adm_ids"]
    param_starts        = trials["param_start"]
    min_trials          = 1
    start_index         = 1

    unique_ids      = check_values(adm_ids)
    counts_by_id, _ = count_values_type(adm_ids, unique_ids, start_index)
    adm_id_list     = appendTrials(counts_by_id)
    adm_index       = findIndex(adm_id_list, adm_id)

    if counts_by_id[adm_index][1] < min_trials:
        return probe_start

    for trial_index in range(len(contrast_history) - 1, -1, -1):
        if int(adm_ids[trial_index]) != adm_id:
            continue
        base_contrast = contrast_history[trial_index]
        if int(param_starts[trial_index]) == 0:
            return probe_start
        return base_contrast

    return probe_start


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
    """
    if not args:
        return

    data_responses      = funcs.readText_toList(trial.file_response_record)

    stimulus_condition_history       = data_responses[0]
    probe_Alternative_Choice_history = data_responses[1]
    human_Alternative_Choice_history = data_responses[2]
    staircase_Identity_history       = data_responses[3]
    probe_weber_contrast_history     = data_responses[4]
    probe_screen_intensity_history   = data_responses[5]

    duration            = 500

    conditions_data     = funcs.read_JSON(trial.fileParamsfilename_Conditionsain)
    staircase_id        = conditions_data['staircase_Identity_now'][0]  
    stimulus_condition  = conditions_data['stimulus_condition'][staircase_id]
    probe_weber_contrast= conditions_data['now_weber_contrast'][staircase_id]  
    probe_choice        = conditions_data['probe_Alternative_Choice'][staircase_id]

    params              = funcs.read_JSON(trial.file_params_Stimulus)


    distance_to_monitor = params["distance_to_monitor"]
    pixel_metre_ratio   = params["pixel_metre_ratio"]
    probe_pos_y         = params["probe_pos_y"]
    n_up                = params["n_up"]
    n_dw                = params["n_dw"] 
    probe_start         = params["probe_start"]
    probe_pos_x         = params["probe_pos_x"]
    probe_lr            = int(params["probe_lr"])
    rate_up             = params["rate_up"]
    background_cpu      = params["background_contrast"]
    max_cpu             = params["max_contrast"]

    subject_response    = _key_to_response(args[0])

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
        probe_screen_intensity_history   = data_responses[5]

        list_find  = [1, 2, 3, 1, 2, 3]

        value_find = staircase_id
        indices = [i for i, x in enumerate(staircase_Identity_history) if x == value_find]

        return probe_Alternative_Choice_history[indices], human_Alternative_Choice_history[indices]
    
    def _check_responses_history(staircase_stimulus_choice, staircase_subject_choice):
        """
        Check if last stimulus and subjects choices are equal and are as long as n_dw. 
        """
        last_4_stimulus = staircase_stimulus_choice[:-n_dw]
        last_4_subject  = staircase_subject_choice[:-n_dw]

        if probe_choice == subject_response:
            count_correct_responses = 0
            for i in range(n_dw):
                if last_4_stimulus[-i] == last_4_subject[-i]:
                    count_correct_responses+=1
                elif last_4_stimulus[-i] != last_4_subject[-i]:
                    pass

            if count_correct_responses == n_dw:
                # contrast needs to be decreased
                dw_bool = 0 
                return dw_bool
            else:
                # contrast remains the same
                pass_bool = 2
                return pass_bool
        elif probe_choice != subject_response:
            # contrast needs to be increased
            up_bool = 1
            return up_bool
        else:
            return 0

    def _update_probe_contrast(integer):
        def _increase_contrast():
            return 0
    
        def _decrease_contrast():
            return 0
        
        if integer == 0:
            return _decrease_contrast()
        elif integer == 1:
            return _increase_contrast()
        else:
            pass

    
    # isolate staircase
    (
    staircase_stimulus_choice, 
    staircase_subject_choice
    ) = _get_single_staircase_history(data_responses, staircase_id)
    # check last responses (do we change contrast of probe?)
    contrast_update_bool        = _check_responses_history(staircase_stimulus_choice, staircase_subject_choice)
    # update probes: contrast and cpu_intensity
    new_probe_weber_contrast    = _update_probe_contrast(contrast_update_bool)
    new_probe_screen_intensity  = _weber_contrast_to_cpu_intensity(new_probe_weber_contrast, params)

    data_responses[0] = stimulus_condition_history.append(stimulus_condition)
    data_responses[1] = probe_Alternative_Choice_history.append(probe_choice)
    data_responses[2] = human_Alternative_Choice_history.append(subject_response)
    data_responses[3] = staircase_Identity_history.append(staircase_id)
    data_responses[4] = probe_weber_contrast_history.append(new_probe_weber_contrast)
    data_responses[5] = probe_screen_intensity_history.append(new_probe_screen_intensity)

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
        n_up,
        filename_Conditions,
        file_paramsStimulus,
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
        self.nUP            = n_up
        self.fileCondition      = filename_Conditions
        self.fileParamsStimulus = file_paramsStimulus
        self.fileResponseRecord = file_response_record

    def state_new_condition_for_stimulus(self):
        """states new condition for stimulus, to be passed over to stimulus.py file"""
        import random

        data_params         = funcs.read_JSON(self.fileParamsStimulus)
        background_intensity= data_params["background_intensity"]
        max_intensity       = data_params["max_intensity"]


        data_responses      = funcs.readText_toList(self.fileResponseRecord)
        staircase_Identity_history          = data_responses[3]
        probe_screen_intensity_history      = data_responses[5]


        data_conditions      = funcs.read_JSON(self.fileCondition)
        condition_list       = data_conditions['condition_list']
        staircase_Identities = data_conditions['staircase_Identities']
        current_staircase_id = data_conditions['staircase_Identity']   
        now_screen_intensity = data_conditions['now_screen_intensity']

        new_id                  = random.choice(staircase_Identities)
        condition_value         = condition_list[new_id]
        probe_screen_intensity  = now_screen_intensity[new_id]
        terminate_criteria      = data_conditions["terminate_criteria"][new_id]
        last_responses          = data_conditions["last_responses"]

        # ---------------------------------------- # 

        probe_weber_contrast_history = convert_screen_intensity_history_to_weber_contrast_list(
                                        probe_screen_intensity_history, 
                                        background_intensity, 
                                        max_intensity)

        reversal_count               = _count_staircase_reversals(
                                        staircase_Identity_history, 
                                        probe_weber_contrast_history, 
                                        current_staircase_id, 
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
                    last_responses += 1
                    if last_responses >= 2:
                        terminate_bool = 1
            else:
                pass
        
        
        _terminate_staircase_bool()

        px = self.pos  
        if px >= 0:
            value_response = RIGHT_RESPONSE
        else:
            value_response = LEFT_RESPONSE

        _beep(550, self.T)

        """save updated conditions"""

        probe_weber_contrast = convert_screen_intensity_history_to_weber_contrast_list(
                                        [probe_screen_intensity], 
                                        background_intensity, 
                                        max_intensity)[0]

        data_conditions['stimulus_condition']               = condition_list
        data_conditions['probe_Alternative_Choice'][new_id] = value_response
        data_conditions['staircase_Identity_now']           = [new_id]
        data_conditions['now_weber_contrast'][new_id]       = probe_weber_contrast
        data_conditions['now_screen_intensity'][new_id]     = probe_screen_intensity
        
        funcs.create_JSON(self.fileCondition, data_conditions)

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


# -----------------------------------------------------------------------------
# ADM condition assignment
# -----------------------------------------------------------------------------

def condition_ADM(data_adm_index, condition_value):
    """
    Look up or create an ADM ID for a stimulus condition (e.g. position or SF).

    Returns
    -------
    tuple
        (condition_values, adm_ids, active_adm_id)
    """
    adm_cond, adm_index = data_adm_index[0], data_adm_index[1]

    for index, cond_j in enumerate(adm_cond):
        if cond_j == condition_value:
            return adm_cond, adm_index, int(adm_index[index])

    next_id = len(adm_cond)
    if next_id not in adm_index:
        adm_cond.append(condition_value)
        adm_index.append(next_id)
        return adm_cond, adm_index, next_id

    for index, adm_j in enumerate(adm_index):
        if adm_j == next_id:
            return adm_cond, adm_index, int(adm_index[index])

    return adm_cond, adm_index, next_id


def condition_INDEX(data_adm_index, adm_value):
    """Return the condition value associated with an ADM ID."""
    adm_cond, adm_index = data_adm_index[0], data_adm_index[1]
    for index, adm_j in enumerate(adm_index):
        if adm_j == adm_value:
            return int(adm_cond[index])
    return None


def condition_KEY_VALUE(condition_value, condition_statement, **kwargs):
    """Assign a condition parameter into ``kwargs`` by name."""
    if condition_statement == "position":
        kwargs["px"] = condition_value
    elif condition_statement == "frequency":
        kwargs["fs"] = condition_value
    else:
        print("No condition handler for:", condition_statement)
    return kwargs


def condition_Dictionary(condition_value, adm_id, condition_dict, **kwargs):
    """
    Bind the next free condition slot to ``condition_value`` and ``adm_id``.

    ``condition_dict`` layout: [names, values, active_flags, adm_ids].
    """
    names, values, active_flags, adm_ids = condition_dict

    for index, is_active in enumerate(active_flags):
        if int(is_active) != 1:
            continue
        kwargs[names[index]] = condition_value
        values[index] = condition_value
        adm_ids[index] = adm_id
        break

    condition_dict[1] = values
    condition_dict[3] = adm_ids
    return condition_dict, kwargs


def associationAB(condition_list, values_list):
    """
    Group threshold values by condition and return lists per unique condition.

    Conditions are sorted in ascending order.
    """
    unique_conditions = check_values(condition_list)
    counts, _ = count_values_type(condition_list, unique_conditions, 0)
    condition_keys = sorted(appendTrials(counts))
    grouped = [[] for _ in range(len(condition_keys))]

    for index, condition in enumerate(condition_list):
        key_index = condition_keys.index(condition)
        grouped[key_index].append(values_list[index])

    return grouped
