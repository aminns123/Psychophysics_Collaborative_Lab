import json
from pathlib import Path
import random

import numpy as np
import pyglet

import Functions.functionsForUse as funcs
from Events.adaptive_session import LegacyStaircaseSession
from Events.stimuliC import Dot_stairCase_centre, Grating_ADM
from libC import ExpWindow, Params, key, run
from Events.adaptiveMethods import Trials_read_write_staircase_conditions, Trial_small


# ------------------------------ Experiment setup ------------------------------

def run_experiment(filename_Conditions, file_params_Stimulus, file_response_record, data_save_repository):
    """Run the reference contrast-sensitivity experiment.

    ``data_save_repository`` is the run-owned state directory when launched from
    PsyCoLab. The legacy four-argument interface is preserved.
    """
    state_directory = Path(data_save_repository)
    run_directory = Path(file_response_record).parent
    with (state_directory / "user_experiment_config.json").open("r", encoding="utf-8") as f:
        dict_all_dicts = json.load(f)

    experiment_params = dict_all_dicts["experiment_params"]
    monitor_profile = dict(dict_all_dicts.get("monitor_profile", {}))
    adaptive_session = LegacyStaircaseSession(
        filename_Conditions,
        file_params_Stimulus,
        file_response_record,
        max_trials=experiment_params["number_trials"],
        metadata_path=run_directory / "adaptive_session.json",
        trial_log_path=run_directory / "trials.tsv",
    )

    # ------------------------------ Window setup ------------------------------
    pyglet.options["vsync"] = True
    pyglet.options["double_buffer"] = True
    win = ExpWindow(fullscreen=True)

    pixel_width = win.width
    pixel_height = win.height
    screen_width_pixel = pixel_width
    screen_height_pixel = pixel_height
    aspect_ratio = screen_width_pixel / screen_height_pixel

    monitor_refresh_rate = int(experiment_params.get("monitor_refresh_rate", 60))
    screen_width_m = float(experiment_params.get("screen_width_m", 610e-3))
    screen_height_m = float(experiment_params.get("screen_height_m", 350e-3))
    viewing_distance_m = float(experiment_params["viewing_distance_m"])
    pyglet_wakeup_rate_check = int(experiment_params.get("pyglet_wakeup_rate_check", 60))

    expected_resolution = monitor_profile.get("expected_resolution_px")
    if expected_resolution is not None:
        expected = tuple(int(value) for value in expected_resolution)
        actual = (int(win.width), int(win.height))
        if expected != actual:
            try:
                win.close()
            finally:
                raise RuntimeError(
                    "Actual fullscreen resolution does not match the selected monitor profile: "
                    f"expected {expected[0]}x{expected[1]}, got {actual[0]}x{actual[1]}."
                )

    cx, cy = win.width // 2, win.height // 2
    pixel_metre_ratio = funcs.ratio_PIXEL_Meter(win.width, screen_width_m)

    fov_x_deg = 2 * np.degrees(np.arctan((screen_width_m / 2) / viewing_distance_m))
    fov_y_deg = 2 * np.degrees(np.arctan((screen_height_m / 2) / viewing_distance_m))
    ppd_x = screen_width_pixel / fov_x_deg
    ppd_y = screen_height_pixel / fov_y_deg

    monitor_screen_params = {
        "monitor_profile_id": experiment_params.get("monitor_profile_id", "legacy_unprofiled"),
        "monitor_calibration_status": experiment_params.get("monitor_calibration_status", "unverified"),
        "monitor_refresh_rate": monitor_refresh_rate,
        "screen_width_pixel": screen_width_pixel,
        "screen_height_pixel": screen_height_pixel,
        "screen_width_m": screen_width_m,
        "screen_height_m": screen_height_m,
        "viewing_distance_m": viewing_distance_m,
        "aspect_ratio": aspect_ratio,
        "pixel_metre_ratio": pixel_metre_ratio,
        "fov_x_deg": float(fov_x_deg),
        "fov_y_deg": float(fov_y_deg),
        "ppd_x": float(ppd_x),
        "ppd_y": float(ppd_y),
        "center_x_pixel": cx,
        "center_y_pixel": cy,
        "window_width_pixel": win.width,
        "window_height_pixel": win.height,
        "pyglet_wakeup_rate_check": pyglet_wakeup_rate_check,
    }

    runtime_display_path = run_directory / "runtime_display.json"
    temporary_display = runtime_display_path.with_name(runtime_display_path.name + ".tmp")
    temporary_display.write_text(json.dumps(monitor_screen_params, indent=2), encoding="utf-8")
    temporary_display.replace(runtime_display_path)

    timeFixate = experiment_params["timeFixate"]
    timeInterval = experiment_params["timeInterval"]
    timeAB = experiment_params["timeAB"]
    timeT = experiment_params["timeT"]

    # ------------------------------ Stimulus parameters ------------------------------
    kwargs_fixate = {
        "c": experiment_params["background_intensity"] + 0.09,
        "sigma": 0.035,
        "fs": 0.0,
        "phi": 0.0,
        "edge": 2.0,
        "res": 64,
        "msg": "Experiment over! ----- Press: Esc",
    }

    kwargs_fake_Fixate = {
        "c": experiment_params["background_intensity"],
        "sigma": 0.00001,
        "fs": 0.0,
        "phi": 0.0,
        "edge": 2.0,
        "res": 64,
        "msg": "-- Experiment over! -- Press: Esc --",
    }

    kwargs_grating = {
        "width": 100,
        "fs": 40,
        "ph": 0.0,
        "speed": 0.0,
        "contr": 0.018,
        "theta": 0.0,
        "bg": experiment_params["background_intensity"],
        "box": False,
        "Lbg": 25,
        "Lmin": 0.0,
        "Lmax": 25,
        "gamma": 0.0,
        "BRTRR": 1.2,
        "flanker_width_deg": 5.0,
        "grating_displacement_deg": 5.0,
        "probe_displacement_dx": 0.4,
        "probe_displacement_dy": 0.3,
    }

    # ------------------------------ Experiment setup ------------------------------
    win.set_background(
        [
            experiment_params["background_intensity"],
            experiment_params["background_intensity"],
            experiment_params["background_intensity"],
        ]
    )

    def _make_text_label(message, position, font_size=24):
        return pyglet.text.Label(
            message,
            x=position[0],
            y=position[1],
            anchor_x="center",
            anchor_y="center",
            font_size=font_size,
        )

    def _make_adm_trial(name, stimuli, duration_ms, position, keys_for_trial=None):
        return adaptive_session.attach(
            Trials_read_write_staircase_conditions(
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
        )

    # ------------------------------ Trial sequence ------------------------------
    grating_width = int(
        funcs.convertArcangleTOPixel(
            kwargs_grating["flanker_width_deg"],
            viewing_distance_m,
            pixel_metre_ratio,
        )
    )
    grating_displacement = int(
        funcs.convertArcangleTOPixel(
            kwargs_grating["grating_displacement_deg"],
            viewing_distance_m,
            pixel_metre_ratio,
        )
    )

    alternative_forced_choice = {
        "2AFC_choice": [cx - grating_displacement, cx + grating_displacement],
    }
    kwargs_grating.update({"width": grating_width})

    data_conditions = funcs.read_JSON(filename_Conditions)
    data_conditions.update({"2AFC_choice": alternative_forced_choice["2AFC_choice"]})
    funcs.create_JSON(filename_Conditions, data_conditions)

    resolved_experiment = {
        "schema_version": 2,
        "experiment_id": "contrast_sensitivity",
        "timings_ms": {
            "fixation": int(timeFixate),
            "interval": int(timeInterval),
            "stimulus": int(timeAB),
            "response_timeout": int(timeT),
        },
        "fixation_stimulus": dict(kwargs_fixate),
        "blank_fixation_stimulus": dict(kwargs_fake_Fixate),
        "grating_stimulus": dict(kwargs_grating),
        "resolved_geometry": {
            "grating_width_px": int(grating_width),
            "grating_displacement_px": int(grating_displacement),
            "alternative_positions_px": list(alternative_forced_choice["2AFC_choice"]),
            "center_px": [int(cx), int(cy)],
        },
        "conditions": {
            "condition_list": list(data_conditions.get("condition_list", [])),
            "staircase_identities": list(data_conditions.get("staircase_Identities", [])),
        },
        "response_mapping": {
            "left": 0,
            "right": 1,
            "accepted_keys": ["LEFT", "RIGHT"],
        },
        "adaptive_parameters": {
            "n_down": int(adaptive_session.parameters["n_dw"]),
            "n_up": int(adaptive_session.parameters["n_up"]),
            "log_step_up": float(adaptive_session.parameters["logUNIT_UP"]),
            "log_step_down": float(adaptive_session.parameters["logUNIT_DW"]),
            "reversal_limit_per_staircase": list(
                data_conditions.get("reversal_termination", [])
            ),
            "max_accepted_responses": int(experiment_params["number_trials"]),
        },
    }
    resolved_path = run_directory / "resolved_experiment.json"
    resolved_tmp = resolved_path.with_name(resolved_path.name + ".tmp")
    resolved_tmp.write_text(json.dumps(resolved_experiment, indent=2), encoding="utf-8")
    resolved_tmp.replace(resolved_path)

    response_keys = [key.RIGHT, key.LEFT]
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

    win.set_logger(adaptive_session.logger(win))

    # ------------------------------ Stimuli ------------------------------
    experiment_title = [_make_text_label("Contrast Sensitivity Function\n", (cx, cy))]
    welcome_line = [_make_text_label("Press SPACE when ready.", (cx, cy - 50))]
    farewell_line = [_make_text_label("Experiment over!", (cx, cy - 50))]

    trials = [
        Trial_small("Start", experiment_title, 5 * 1000, keys_default, mouse=False),
        Trial_small("Start", welcome_line, 0, keys_default, mouse=False),
    ]

    fakeProbe = Dot_stairCase_centre(
        (cx, cy),
        experiment_params["background_intensity"],
        filename_Conditions,
        Params(**kwargs_fake_Fixate),
    )
    centreDOT = Dot_stairCase_centre(
        (cx, cy),
        experiment_params["background_intensity"],
        filename_Conditions,
        Params(**kwargs_fixate),
    )
    probeStimulus = Grating_ADM(
        (cx, cy),
        filename_Conditions,
        Params(**kwargs_grating),
    )

    fake_probe_trial = [fakeProbe]
    probe_trial = [probeStimulus]
    fixation_trial = [centreDOT]

    # ------------------------------ Trial loop ------------------------------
    fixateDOT = _make_adm_trial(
        "fixation",
        fixation_trial,
        timeFixate,
        [cx, cy],
    )
    fixateInterval = _make_adm_trial(
        "fixation",
        fake_probe_trial,
        timeInterval,
        [cx, cy],
    )
    fixateRESPONSE = _make_adm_trial(
        "response",
        fixation_trial,
        timeT,
        [cx, cy],
        response_keys,
    )

    trial_exps = [fixateDOT]
    for _ in range(experiment_params["number_trials"]):
        posX = random.choice(alternative_forced_choice["2AFC_choice"])

        fixate_state_new_condition = _make_adm_trial(
            "new_condition",
            fake_probe_trial,
            timeInterval,
            [posX, cy],
        )
        stimulusPROBE = _make_adm_trial(
            "stimuli",
            probe_trial,
            timeAB,
            [posX, cy],
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
    trials += [Trial_small("End", farewell_line, 0, keys_none, mouse=False)]

    pyglet.clock.schedule_interval(lambda dt: None, 1 / pyglet_wakeup_rate_check)

    win.set_trials(trials)
    try:
        run(refresh_rate=monitor_refresh_rate)
    except Exception as exc:
        adaptive_session.save(status="error", error=exc)
        raise
    finally:
        adaptive_session.finish()
        funcs.removeZeroRow(file_response_record)
        funcs.correctFileSpacings(file_response_record)
