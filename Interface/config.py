import datetime
import json
from pathlib import Path

import Functions.functionsForUse as funcs

from Events.display_contrast import normalized_display_contrast


# ------------------------------ Experiment setup ------------------------------


def run_configure_experiment(NAME, data_save_repository, setupDict, run_directory=None):
    """Configure one experiment and create its runtime state files.

    When ``run_directory`` is supplied (the PsyCoLab public path), every mutable
    runtime file is owned by that unique run. The older directory layout remains
    available when this function is called without ``run_directory``.
    """
    data_root = Path(data_save_repository).expanduser().resolve()

    if setupDict is None:
        legacy_setup = data_root / NAME / "experiment_defined.json"
        with legacy_setup.open("r", encoding="utf-8") as handle:
            setupDict = json.load(handle)
    else:
        setupDict = dict(setupDict)

    current_time = datetime.datetime.now()
    today = f"{current_time.year}_{current_time.month}_{current_time.day}"

    # ------------------------------ Monitor geometry ------------------------------
    monitor_profile = dict(setupDict.get("monitor_profile", {}))
    monitor_refresh_rate = int(
        monitor_profile.get(
            "refresh_rate_hz",
            setupDict.get("monitor_refresh_rate", 60),
        )
    )
    pyglet_wakeup_rate_check = int(
        monitor_profile.get(
            "pyglet_wakeup_rate_hz",
            setupDict.get("pyglet_wakeup_rate_check", 180),
        )
    )
    screen_width_m = float(monitor_profile.get("physical_width_m", 610e-3))
    screen_height_m = float(monitor_profile.get("physical_height_m", 350e-3))
    viewing_distance_m = float(
        monitor_profile.get(
            "viewing_distance_m",
            setupDict.get("viewing_distance_m", 1.0),
        )
    )

    # ------------------------------ Initialize dictionary parameters ------------------------------
    ratio2dw1up = 0.5488

    timeFixate = int(setupDict.get("timeFixate", 250))
    timeInterval = int(setupDict.get("timeInterval", 250))
    timeT = int(setupDict.get("timeT", 0))
    timeAB = int(setupDict.get("timeAB", 200))
    reversal_termination = int(setupDict["reversal_termination"])
    max_trials = int(setupDict.get("max_trials", 10 * 3))

    experiment_params = {
        "background_intensity": float(setupDict["Background_Screen_intensity"]),
        "max_intensity": 1.0,
        "max_monitor_cdm2": float(setupDict["Max_monitor_Luminance"]),
        "background_luminance_cdm2": float(setupDict.get("Background_Luminance", 0.0)),
        "starting_probe_intensity": float(setupDict["starting_probe_intensity"]),
        "timeFixate": timeFixate,
        "timeInterval": timeInterval,
        "timeAB": timeAB,
        "timeT": timeT,
        "viewing_distance_m": viewing_distance_m,
        "number_trials": max_trials,
        "monitor_refresh_rate": monitor_refresh_rate,
        "pyglet_wakeup_rate_check": pyglet_wakeup_rate_check,
        "screen_width_m": screen_width_m,
        "screen_height_m": screen_height_m,
        "monitor_profile_id": monitor_profile.get("id", "legacy_unprofiled"),
        "monitor_calibration_status": monitor_profile.get("calibration_status", "unverified"),
    }

    staircase_params = {
        "trialPOINT": int(setupDict["trialPOINT"]),
        "n_dw": int(setupDict.get("n_down", 2)),
        "n_up": int(setupDict.get("n_up", 1)),
        "number_trials": 10,
        "terminationINDEX": 9,
        "logUNIT_UP": float(setupDict.get("logUNIT_UP", 0.35)),
        "logUNIT_DW": float(setupDict.get("logUNIT_DW", ratio2dw1up * 0.35)),
        "preReversalStepDW": 0.2,
        "Reversal_or_Trial": 1,
        "limit_Trial_Run": 100,
    }

    dict_all_dicts = {
        "experiment_params": experiment_params,
        "staircase_params": staircase_params,
        "monitor_profile": monitor_profile,
    }

    # ------------------------------ Files and timing ------------------------------
    if run_directory is not None:
        run_dir = Path(run_directory).expanduser().resolve()
        state_dir = run_dir / "state"
        run_dir.mkdir(parents=True, exist_ok=True)
        state_dir.mkdir(parents=True, exist_ok=True)

        filename_response_main = run_dir / "legacy_response.txt"
        filename_parameters = state_dir / "parameters.runtime.json"
        filename_Conditions = state_dir / "conditions.runtime.json"
        user_config_path = state_dir / "user_experiment_config.json"
        experiment_defined_path = state_dir / "experiment_defined.json"
    else:
        user_config_path = data_root / "user_experiment_config.json"

        UPDW_Rule = "DW" + str(int(staircase_params["n_dw"])) + "_UP" + str(int(staircase_params["n_up"]))
        experimentNAME = setupDict["Experiment_Type"]
        bkg_intensityFolder = "Background_Intensity_" + str(experiment_params["background_intensity"])

        experiment_type = (
            f"{UPDW_Rule}/{experimentNAME}/"
            f"max_cdm2_{int(experiment_params['max_monitor_cdm2'])}/"
            f"{bkg_intensityFolder}"
        )

        folderName = data_root / NAME / experiment_type / today
        folderParams = folderName / "parameters"
        funcs.check_folder_exist([str(folderName), str(folderParams)])

        filename_everything, _ = funcs.CheckFileName(str(folderName), "_experiment.txt")
        filename_response_main = Path(filename_everything)
        filename_parameters = folderParams / "Records_Parameters.json"
        filename_Conditions = folderParams / "Records_condition.json"
        experiment_defined_path = data_root / NAME / "experiment_defined.json"

    user_config_path.parent.mkdir(parents=True, exist_ok=True)
    with user_config_path.open("w", encoding="utf-8") as handle:
        json.dump(dict_all_dicts, handle, indent=4)

    experiment_defined_path.parent.mkdir(parents=True, exist_ok=True)
    with experiment_defined_path.open("w", encoding="utf-8") as handle:
        json.dump(setupDict, handle, indent=4)

    starting_probe_intensity = experiment_params["starting_probe_intensity"]
    starting_display_contrast = normalized_display_contrast(
        starting_probe_intensity,
        background_intensity=experiment_params["background_intensity"],
        maximum_intensity=experiment_params["max_intensity"],
    )

    background_intensity = experiment_params["background_intensity"]
    background_display_contrast = normalized_display_contrast(
        background_intensity,
        background_intensity=background_intensity,
        maximum_intensity=experiment_params["max_intensity"],
    )
    max_intensity = experiment_params["max_intensity"]
    max_display_contrast = normalized_display_contrast(
        max_intensity,
        background_intensity=background_intensity,
        maximum_intensity=max_intensity,
    )

    flat_dict = {}
    for key in ("experiment_params", "staircase_params"):
        flat_dict.update(dict_all_dicts[key])
    value_params = flat_dict.copy()
    value_params.update(
        {
            # Historical key names retained for analysis compatibility. These
            # values are C_disp, not conventional Weber contrast.
            "background_weber_contrast": background_display_contrast,
            "max_weber_contrast": max_display_contrast,
        }
    )

    # Deferred stimulus review: this legacy value is intentionally NOT
    # reinterpreted as measured pixels/degree here.
    deg1PCD = 31.5
    condition_list = [2 * deg1PCD, 8 * deg1PCD]

    columnsSet = {
        "condition_list": condition_list,
        "staircase_Identities": list(range(len(condition_list))),
        "probe_Alternative_Choice": [0 for _ in range(len(condition_list))],
        "human_Alternative_Choice": [0 for _ in range(len(condition_list))],
        "staircase_Identity_active": [0],
        "stimulus_choice_active": [0],
        "total_Reversals": [0 for _ in range(len(condition_list))],
        "starting_contrast": [starting_display_contrast for _ in range(len(condition_list))],
        "correct_responses": [0 for _ in range(len(condition_list))],
        "weber_contrast_active": [starting_display_contrast for _ in range(len(condition_list))],
        "staircase_intensity_active": [starting_probe_intensity for _ in range(len(condition_list))],
        "reversal_termination": [reversal_termination for _ in range(len(condition_list))],
        "n_dw": [staircase_params["n_dw"]],
        "n_up": [staircase_params["n_up"]],
        "logUNIT_UP": [staircase_params["logUNIT_UP"]],
        "logUNIT_DW": [staircase_params["logUNIT_DW"]],
        "count_down_terminate": [0],
        "terminate_bool": [0],
    }

    column_titles = [
        "stimulus_condition",
        "probe_Alternative_Choice",
        "human_Alternative_Choice",
        "staircase_Identity",
        "probe_weber_contrast",
        "probe_screen_intensity",
    ]

    funcs.create_JSON(str(filename_Conditions), columnsSet)
    funcs.create_JSON(str(filename_parameters), value_params)
    funcs.create_Text_columns(str(filename_response_main), column_titles)

    return str(filename_Conditions), str(filename_parameters), str(filename_response_main)
