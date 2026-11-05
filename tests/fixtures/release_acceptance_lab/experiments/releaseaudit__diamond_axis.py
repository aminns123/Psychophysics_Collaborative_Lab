"""Disposable axis judgment; software acceptance, no threshold claim.

Two aspect ratios are conditions. H/V target alternatives rotate an independent
diamond. Strength is a digital increment above .5. The finite adaptive method
stops at the response goal, irrespective of reversals. Requested ms are not
photon timing. No framework source or official experiment is imported.
"""
from psychophysics_lab.researcher import (
    ConfigField, ResponseParadigm, AdaptiveSelection, WaitForKey, Show,
    Stimulus, CollectResponse, experiment,
)
from psychophysics_lab.methods.teaching import (
    TeachingAdaptiveMethod, teaching_method_fields, teaching_adaptive_fields,
    review_teaching_adaptive,
)

# A1 — what, where and when
STIMULI = {"diamond": "releaseaudit__diamond", "fixation": "fixation_cross"}
FIELDS = (
    ConfigField("trial_count", "Accepted responses", "int", 16, minimum=4, maximum=100),
    ConfigField("exposure_ms", "Diamond exposure", "int", 45, minimum=1, maximum=500, units="ms"),
    ConfigField("eccentricity_deg", "Diamond horizontal position", "float", .6, minimum=-2., maximum=2., units="degrees"),
    ConfigField("contrast_method", "Selection method", "choice", "adaptive", choices=("adaptive",)),
) + tuple(f for f in teaching_method_fields() if f.key in {"starting_strength", "max_trials"}) + teaching_adaptive_fields()
RESPONSES = ResponseParadigm("diamond_axis", ("horizontal", "vertical"), ("H", "V"))
SESSION_START = [WaitForKey("ready", key="SPACE", slot="fixation"), Show("settle", slot="fixation", duration=20)]
MEASUREMENT_UNITS = {"ratio": "minor/major semiaxes", "major_axis": "0=horizontal,1=vertical",
                     "requested_exposure_ms": "ms", "presented_display_contrast": "digital increment above .5"}


def trial_events(settings, condition):
    return [Show("fixation", slot="fixation", duration=25),
            Show("diamond", stimuli=(Stimulus("diamond", x_deg=settings["eccentricity_deg"]),), duration="exposure_ms"),
            CollectResponse(actions=RESPONSES.alternatives, slot="fixation")]


# A2 — scientific conditions, appearance, response interpretation and stopping
def make_conditions(settings):
    return [{"value": (.4, .7)[i % 2], "target": (i // 2) % 2} for i in range(settings["trial_count"])]


def choose_condition(run, conditions, state):
    return conditions[run.accepted_trials]


def prepare_stimuli(run, condition, state):
    return {"diamond": run.stimulus_parameters("diamond", ratio=condition["value"],
                axis=RESPONSES.alternatives[condition["target"]], intensity=.5 + condition["contrast"]),
            "fixation": run.stimulus_parameters("fixation")}


def validate_settings(settings):
    if settings["contrast_method"] != "adaptive":
        yield "This disposable acceptance study declares only finite adaptive selection."
    if settings["starting_strength"] > .5:
        yield "Digital increment cannot exceed .5."
    if settings["trial_count"] > settings["max_trials"]:
        yield "Response goal exceeds the safety ceiling."


# B — installed public execution and recorder
def procedure(run):
    method = TeachingAdaptiveMethod(run, make_conditions=make_conditions, choose=choose_condition, maximum=.5)
    while not method.is_finished:
        condition = method.next_trial()
        record = method.trial_record(condition)
        record["measurements"] = {"ratio": condition["value"], "major_axis": condition["target"],
                                  "requested_exposure_ms": run.values["exposure_ms"]}
        with run.trial(trial_events(run.values, condition), target=condition["target"], condition=condition["value"],
                       parameters_by_slot=prepare_stimuli(run, condition, method.state), **record) as trial:
            assert trial.response["correct"] == (trial.response["alternative"] == condition["target"])
            method.accept_response(condition, trial.response, trial)
    method.complete()


SPEC = experiment(id="releaseaudit__diamond_axis", name="Disposable diamond axis",
    description=__doc__, stimuli=STIMULI, fields=FIELDS, responses=RESPONSES,
    session_start=SESSION_START, procedure=procedure, validator=validate_settings,
    adaptive=AdaptiveSelection("consecutive_up_down", controls=("n_down", "n_up", "down_factor", "up_factor", "max_trials")),
    method_reviewer={"adaptive": lambda run: review_teaching_adaptive(run, make_conditions, choose_condition)},
    supports_simulation=True, calibration_requirements=("geometry", "timing"),
    monitor_capabilities=("display_binding", "resolution"),
    source_paths=("experiments/releaseaudit__diamond_axis.py",))
