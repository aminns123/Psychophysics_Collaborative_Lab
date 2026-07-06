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
    "probe_start": 4,
    "rate_down": 6,
    "rate_up": 10,
    "background_contrast": 12,
    "max_contrast": 13,
    "reversal_point": 14,
    "n_up": 15,
    "step_down_up": 21,
    "condition_rule": 22,
    "log_unit_up": 23,
    "log_unit_down": 24,
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
    "reversal_count": 8,
    "param_start": 9,
    "correct_tick": 10,
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


# -----------------------------------------------------------------------------
# Contrast conversion
# -----------------------------------------------------------------------------

def weberContrast(contrast_cpu, background_crt, max_crt, log_function=math.log10,
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
    weber_values = []
    for value in contrast_cpu:
        weber = (value - background_crt) / span
        if apply_log:
            weber = log_function(weber)
        weber_values.append(weber)
    return weber_values


def findCPU_fromWeberContrast(max_cpu, background_cpu, weber_contrast):
    """Convert Weber contrast back to CPU luminance."""
    return ((max_cpu - background_cpu) * weber_contrast) + background_cpu


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


def admID_staircase(adm_list, contrast_list, adm_id_now):
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


def _to_weber(value, background_cpu, max_cpu):
    """Convert a single CPU contrast value to Weber contrast."""
    return weberContrast([value], background_cpu, max_cpu)[0]


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


def _count_adm_reversals(adm_ids, contrast_values, current_adm_id, background, maximum):
    """Count staircase reversals for trials belonging to the current ADM."""
    adm_contrasts = admID_staircase(adm_ids, contrast_values, current_adm_id)
    weber_contrasts = weberContrast(adm_contrasts, background, maximum)
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


def _weber_to_cpu_luminance(weber_contrast, params):
    """Convert Weber contrast back to CPU luminance, clamped to background."""
    background = params["background_contrast"]
    cpu_luminance = findCPU_fromWeberContrast(
        params["max_contrast"], background, weber_contrast
    )
    return max(cpu_luminance, background)


def conditions(storeData, dataParams, conditionS):
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
    total_reversals = _count_adm_reversals(
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

    contrast_weber = _to_weber(
        response["base_contrast"],
        params["background_contrast"],
        params["max_contrast"],
    )

    if conditionS:
        references = _reference_contrasts_weber(storeData, params, previous_state)
        updated = _update_staircase_weber(
            response,
            references,
            params,
            previous_state,
            counts_by_id[adm_index][1],
        )
        contrast_weber = updated["contrast_weber"]
        correct_tick = updated["correct_tick"]
        param_start = updated["param_start"]
        reversal_n = updated["reversal_n"]
        rate_down = updated["rate_down"]
        count_reversals_total = updated["count_reversals_total"]
        response_count = updated["response_count"]
    else:
        correct_tick = previous_state["correct_tick"]
        param_start = previous_state["param_start"]
        reversal_n = previous_state["reversal_n"]
        rate_down = previous_state["rate_down"]
        count_reversals_total = previous_state["count_reversals_total"]
        response_count = response["response_count"]

    contrast_cpu = _weber_to_cpu_luminance(contrast_weber, params)

    return (
        contrast_cpu,
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
    if trial.name == "stimuli":
        trial.print_Value()
    elif event != "MOUSE" and trial.name == "responses":
        subject_response(trial, args)


def _key_to_response(key):
    """Map keyboard input to a binary 2AFC response (0 = left/down, 1 = right/up)."""
    key = str(key)
    if key in ("LSHIFT", "LEFT", "DOWN"):
        return 0
    if key in ("RSHIFT", "RIGHT", "UP"):
        return 1
    raise ValueError(f"Unrecognised response key: {key}")


def _find_baseline_contrast(store_data, adm_id, probe_start):
    """Find the contrast baseline for the current ADM before recording a response."""
    contrast_history = store_data[11]
    adm_ids = store_data[4]
    param_starts = store_data[9]
    min_trials = 1
    start_index = 1

    unique_ids = check_values(adm_ids)
    counts_by_id, _ = count_values_type(adm_ids, unique_ids, start_index)
    adm_id_list = appendTrials(counts_by_id)
    adm_index = findIndex(adm_id_list, adm_id)

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
    """
    if not args:
        return

    import winsound

    duration = 500
    data_params_main = funcs.from_Text(trial.fileParamsMain)
    store_data = funcs.readText_toList(trial.filesDataMain)
    data_params = funcs.from_Text(trial.fileParams1)
    condition_dictionary = funcs.readText_toList_keyValue(trial.fileADM_cond)
    spatial_frequency = condition_dictionary[1][0]

    adm_id = data_params_main[0]
    distance_to_monitor = data_params[17]
    pixel_metre_ratio = data_params[18]
    probe_pos_y = data_params[11]
    n_up = data_params[15]
    probe_start = data_params[4]
    probe_pos_x = data_params[3]
    probe_lr = int(data_params[1])
    rate_up = data_params[10]
    background_cpu = data_params[12]
    max_cpu = data_params[13]

    probe_pos_deg = funcs.Meter_convertToArcangle(
        probe_pos_x, distance_to_monitor, pixel_metre_ratio
    )
    probe_pos_y_deg = funcs.Meter_convertToArcangle(
        probe_pos_y, distance_to_monitor, pixel_metre_ratio
    )

    cL_param = _find_baseline_contrast(store_data, adm_id, probe_start)
    value_response = _key_to_response(args[0])

    if probe_lr == value_response:
        winsound.Beep(1000, duration)
    else:
        winsound.Beep(300, duration)

    store_data[0].append(round(probe_pos_deg, 4))
    store_data[1].append(round(probe_lr, 4))
    store_data[2].append(round(value_response, 4))
    store_data[4].append(round(adm_id, 4))
    store_data[6].append(round(cL_param, 8))
    store_data[7].append(round(rate_up, 4))
    store_data[12].append(round(probe_pos_y_deg, 4))
    store_data[13].append(round(n_up + 1, 4))

    (
        new_contrast,
        reversal_tick,
        correct_tick,
        param_start,
        rate_down,
        response_count,
        total_reversals,
        rate_up,
    ) = conditions(store_data, data_params, True)

    store_data[5].append(round(rate_down, 4))
    store_data[3].append(round(total_reversals, 4))
    store_data[8].append(round(reversal_tick, 4))
    store_data[9].append(param_start)
    store_data[10].append(correct_tick)
    store_data[11].append(round(new_contrast, 8))

    weber_value = weberContrast([cL_param], background_cpu, max_cpu)[0]
    store_data[14].append(round(weber_value, 8))
    store_data[15].append(spatial_frequency)

    funcs.write_toText(trial.filesDataMain, store_data)
    data_params[5] = reversal_tick
    data_params[9] = total_reversals
    data_params[10] = rate_up
    funcs.to_Text(trial.fileParams1, data_params)


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


class Trial_ADMs:
    """Adaptive trial that assigns ADM conditions and logs probe parameters."""

    def __init__(
        self,
        name,
        stimuli,
        duration_ms,
        pos,
        contrast,
        number_trials,
        n_up,
        file_array_position,
        file_params_main,
        file_params,
        file_params_position,
        files_adm_index,
        file_adm_condition,
        file_adm_ab,
        files_data_main,
        text,
        keys=None,
        mouse=False,
    ):
        self.stimuli = stimuli
        self.T = duration_ms
        self.name = name
        self.keys = keys or []
        self.mouse = mouse
        self.pos = pos
        self.contrast = contrast
        self.numberTrials = number_trials
        self.nUP = n_up
        self.fileParamsMain = file_params_main
        self.fileParams1 = file_params
        self.filesDataMain = files_data_main
        self.text = text
        self.filesADM_INDEX = files_adm_index
        self.fileArrayPos = file_array_position
        self.filePosition = file_params_position
        self.fileADM_cond = file_adm_condition
        self.fileADM_AB = file_adm_ab

    def print_Value(self):
        """Select the next ADM condition and persist probe parameters to disk."""
        if self.name != "flanker_selectivity_LR":
            print("No trial handler found for:", self.name)
            return

        import random
        import winsound

        data_position = funcs.from_Text(self.filePosition)
        data_params_main = funcs.from_Text(self.fileParamsMain)
        data_params = funcs.from_Text(self.fileParams1)
        data_main = funcs.readText_toList(self.filesDataMain)
        condition_list = funcs.from_Text(self.fileArrayPos)
        condition_dictionary = funcs.readText_toList_keyValue(self.fileADM_cond)
        data_adm_index = funcs.readText_toList(self.filesADM_INDEX)

        contrast_list = data_main[6]
        adm_id_list = data_main[4]
        distance_to_monitor = data_params[17]
        pixel_metre_ratio = data_params[18]
        terminate_criteria = data_params[19]
        terminate_bool = int(data_params[20])
        trial_limit = int(data_params[25])
        wait_count = int(data_params[26])
        background_contrast = data_params[12]
        max_contrast = data_params[13]

        px, py = self.pos[0], self.pos[1]
        condition_value = condition_list[random.randrange(len(condition_list))]
        adm_cond, adm_index, out_text = condition_ADM(data_adm_index, condition_value)

        kwargs = {"position": px, "frequency": 40}
        condition_dictionary, kwargs = condition_Dictionary(
            condition_value, out_text, condition_dictionary, **kwargs
        )
        px = kwargs["position"]
        spatial_frequency = kwargs["frequency"]

        probe_pos_deg = funcs.Meter_convertToArcangle(
            round(px * pixel_metre_ratio, 4),
            distance_to_monitor,
            pixel_metre_ratio,
        )
        current_adm_id = int(adm_id_list[-1])
        adm_contrasts = admID_staircase(adm_id_list, contrast_list, current_adm_id)
        weber_list = weberContrast(adm_contrasts, background_contrast, max_contrast)
        reversal_count, _, _ = count_reversals_HighLow(weber_list)

        if reversal_count > terminate_criteria or len(weber_list) > trial_limit:
            for index, adm_j in enumerate(adm_index):
                if int(adm_j) != current_adm_id:
                    continue
                if len(condition_list) > 1:
                    remove_value = adm_cond[index]
                    if remove_value in condition_list:
                        condition_list.remove(remove_value)
                elif len(condition_list) == 1:
                    wait_count += 1
                    if wait_count > 3:
                        terminate_bool = 1
                break

        px_metres = round(px * pixel_metre_ratio, 4)
        if px_metres >= 0:
            value_response = 1
        else:
            value_response = 0

        winsound.Beep(550, self.T)

        data_params[26] = wait_count
        data_params[5] = self.nUP
        data_params[11] = round(py * pixel_metre_ratio, 4)
        data_params[3] = px_metres
        data_params[1] = value_response
        data_params_main[0] = out_text
        data_params[20] = terminate_bool

        data_adm_index[0] = adm_cond
        data_adm_index[1] = adm_index
        data_position[0] = px
        data_position[1] = py

        funcs.write_toText(self.filesADM_INDEX, data_adm_index)
        funcs.write_toText(self.fileADM_cond, condition_dictionary)
        funcs.write_toText(self.fileADM_AB, funcs.from_Text(self.fileADM_AB))
        funcs.write_toText(self.fileParams1, [float(x) for x in data_params])
        funcs.write_toText(self.fileParamsMain, [float(x) for x in data_params_main])
        funcs.write_toText(self.filePosition, [float(x) for x in data_position])
        funcs.write_toText(self.fileArrayPos, condition_list)

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
            "contrast": self.contrast,
            "text": self.text,
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
