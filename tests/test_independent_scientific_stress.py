"""Independent acquisition/validator audit. Uses disposable synthetic data only."""
import csv
import hashlib
import importlib
import json
from pathlib import Path
import shutil

import numpy as np
import pytest

from psychophysics_lab.experiments._internal.registry import get_experiment, list_experiments
from psychophysics_lab.config.stimulus_parameters import resolve_stimuli
from psychophysics_lab.ui.settings_review import describe_settings
from psychophysics_lab.data.trials import TRIAL_COLUMNS
from simulations.run import simulate
from simulations.registry import TeachingObserver
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = ("contrast_sensitivity", "contrast_sensitivity_windowed", "line_position_baseline",
            "line_position_flanker", "ellipse_centre", "ellipse_major_axis", "orientation_adaptive",
            "orientation_task", "probe_above_below", "example_experiment")
CASES = [(name, method, seed) for name in OFFICIAL
         for method in (("adaptive", "constant_stimuli", "original") if name in
                        {"orientation_task", "probe_above_below", "example_experiment"}
                        else ("adaptive", "constant_stimuli")) for seed in (0, 19, 2**53+1)]


def test_matrix_covers_the_complete_official_registry():
    assert {s.id for s in list_experiments() if not s.origin_namespace} == set(OFFICIAL)


def settings(identity, method, seed=19):
    defaults = get_experiment(identity).field_defaults()
    background = {0:.2, 19:.5, 2**53+1:.9}.get(seed,.5)
    chosen = {"contrast_method":method, "max_trials":64 if method=="constant_stimuli" else 12, "fixed_contrasts":"0,0.01",
              "fixed_repetitions":2, "trial_count":6, "background_intensity":background,
              "starting_probe_intensity":background+.01, "starting_contrast":.02,
              "starting_strength":.1, "staircases_per_condition":2,
              "frequencies_cpd":"2,4", "positions_deg":"-0.2,0.2",
              "aspect_ratios":"0.75,1", "probe_vertical_offset_deg":.4,
              "flanker_cpd":2., "ring_increment":.03, "n_down":2,"n_up":1}
    return {key:value for key,value in chosen.items() if key in defaults}


def records(artifact):
    with artifact.trial_log_file.open(encoding="utf-8",newline="") as stream:
        return list(csv.DictReader(stream,delimiter="\t"))


def run(tmp_path, identity, method, seed=19):
    return simulate(repo_root=ROOT,data_root=tmp_path/"synthetic_data",experiment_id=identity,
                    values=settings(identity,method,seed),seed=seed,analyse=False,
                    observer=TeachingObserver(accuracy=.65))[0]


@pytest.mark.parametrize("identity,method,seed", CASES)
def test_official_method_seed_background_matrix(tmp_path, identity, method, seed):
    artifact = run(tmp_path,identity,method,seed)
    assert artifact.status in {"completed","max_trials_reached"}
    rows = records(artifact)
    assert 0 < len(rows) == artifact.accepted_trials
    assert tuple(rows[0]) == TRIAL_COLUMNS and len(TRIAL_COLUMNS) == 20
    manifest = json.loads((artifact.run_directory/"manifest.json").read_text(encoding="utf-8"))
    assert manifest["data_kind"] == "synthetic" and manifest["experiment_id"] == identity
    assert manifest["simulation"]["seed"] == seed
    assert artifact.run_directory.is_relative_to(tmp_path/"synthetic_data")
    if method == "constant_stimuli":
        assert all(r["staircase_id"] == r["staircase_trial_index"] == r["reversal_count"] == "" for r in rows)
        assert {float(r["presented_display_contrast"]) for r in rows} == {0.,.01}
    failures = [(c.name,c.detail) for c in validate_run(artifact.run_directory) if not c.passed]
    assert not failures, failures


@pytest.mark.parametrize("identity", OFFICIAL)
@pytest.mark.parametrize("method", ["adaptive","constant_stimuli"])
def test_seed_replay_is_exact_through_saved_trial_pipeline(tmp_path,identity,method):
    first,second = run(tmp_path,identity,method),run(tmp_path,identity,method)
    assert first.run_directory != second.run_directory
    assert records(first) == records(second)


@pytest.mark.parametrize("method", ["adaptive","constant_stimuli"])
def test_csf_variants_share_actual_trial_response_and_adaptation_sequences(tmp_path,method):
    gaussian = run(tmp_path,"contrast_sensitivity",method)
    circular = run(tmp_path,"contrast_sensitivity_windowed",method)
    assert records(gaussian) == records(circular)
    def read(a,name):
        return json.loads((a.run_directory/name).read_text(encoding="utf-8"))
    original,new = read(gaussian,"resolved_experiment.json"),read(circular,"resolved_experiment.json")
    assert original["experiment_id"] != new["experiment_id"]
    assert new["grating_stimulus_id"] == "circular_windowed_sinusoidal_grating"
    assert not any("sigma" in key for key in new)
    for a in (gaussian,circular):
        presentations = read(a,"trial_presentations.json")
        assert presentations


def test_one_degree_circle_uses_real_preparation_and_independent_radial_oracle():
    from psychophysics_lab.stimuli.registry import get_stimulus
    spec=get_experiment("contrast_sensitivity_windowed")
    chosen=spec.normalise_values({"aperture_diameter_deg":1.,"fade_width_deg":.1,
        "frequencies_cpd":"2","starting_contrast":.2,"background_intensity":.37})
    selected=resolve_stimuli(spec,chosen,repo_root=ROOT)
    description=describe_settings(spec,chosen,selected)
    params=description["stimuli"]["grating"]
    assert params["size_deg"] == 1. and params["fade_width_deg"] == .1
    radii=np.asarray([.125,.3,.4,.45,.5,.6])
    x=np.full_like(radii,.125);y=np.sqrt(radii**2-x**2)
    actual=get_stimulus("circular_windowed_sinusoidal_grating").render(params,x,y)
    np.testing.assert_allclose(actual,.37+.1*np.asarray([1,1,1,.5,0,0]),atol=1e-14)
    assert np.all(actual[-2:] == .37)


def test_gaussian_selected_sigma_cutoff_and_tail_against_independent_oracle():
    from psychophysics_lab.stimuli.registry import get_stimulus
    spec=get_experiment("contrast_sensitivity")
    values=spec.normalise_values({"frequencies_cpd":"2","starting_contrast":.2,
                                "background_intensity":.37})
    description=describe_settings(spec,values,resolve_stimuli(spec,values,repo_root=ROOT))
    p=description["stimuli"]["grating"]
    assert p["sigma_deg"]==.5 and p["cutoff_sigmas"]==3. and p["contrast"]==.2
    radii=np.asarray([.125,.5,1.,1.25,1.5,1.6])
    x=np.full_like(radii,.125);y=np.sqrt(radii**2-x**2)
    envelope=np.exp(-radii**2/(2*.5**2))*np.asarray([1,1,1,.5,0,0])
    actual=get_stimulus("contrast_sensitivity_grating").render(p,x,y)
    np.testing.assert_allclose(actual,.37+.1*envelope,atol=1e-14)
    assert np.all(actual[-2:]==.37)


@pytest.mark.parametrize("method", ["adaptive","constant_stimuli"])
def test_scientific_constraints_and_schedule_ceiling_remain_strict(method):
    circular=get_experiment("contrast_sensitivity_windowed")
    with pytest.raises(ValueError,match="cannot exceed"):
        circular.normalise_values({"contrast_method":method,"aperture_diameter_deg":1.,"fade_width_deg":.6})
    for identity in OFFICIAL:
        spec=get_experiment(identity)
        with pytest.raises(ValueError):
            spec.normalise_values(settings(identity,"constant_stimuli")|{"max_trials":1})
    for identity in ("contrast_sensitivity","contrast_sensitivity_windowed"):
        with pytest.raises(ValueError):
            get_experiment(identity).normalise_values({"contrast_method":method,"background_intensity":.99,
                "starting_contrast":.2,"fixed_contrasts":".2"})


@pytest.mark.parametrize("identity", OFFICIAL)
@pytest.mark.parametrize("bad", [float("nan"),float("inf"),-float("inf")])
def test_nonfinite_scientific_and_method_values_rejected(identity,bad):
    spec=get_experiment(identity)
    for key in ("starting_contrast","starting_probe_intensity","starting_strength","background_intensity"):
        if key in spec.field_defaults():
            with pytest.raises((ValueError,TypeError)):
                spec.normalise_values(settings(identity,"adaptive") | {key:bad})


@pytest.mark.parametrize("mode", ["abort","setup_failure","bad_key","negative_rt"])
def test_interruption_preserves_accepted_prefix_and_allows_next_run(tmp_path,monkeypatch,mode):
    from psychophysics_lab.researcher import RunContext,ParticipantAbort
    from psychophysics_lab.core.trial_execution import VirtualPresentation
    from psychophysics_lab.core.presentation import Response
    original=RunContext.trial
    def disrupted(self,*args,**kwargs):
        if self.accepted_trials == 2:
            if mode == "abort":
                self.abort("Independent audit: cancelled after two accepted responses")
            elif mode == "setup_failure":
                raise OSError("Independent audit: presentation setup failure")
            else:
                self.virtual_presentation=VirtualPresentation(Response(0,"WRONG" if mode=="bad_key" else self.responses.keys[0],-.1 if mode=="negative_rt" else .3))
        return original(self,*args,**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(RunContext,"trial",disrupted)
        if mode == "abort":
            aborted=run(tmp_path,"example_experiment","constant_stimuli")
            assert aborted.status == "aborted_by_user"
        else:
            with pytest.raises((OSError,ValueError)):
                run(tmp_path,"example_experiment","constant_stimuli")
    runs=list((tmp_path/"synthetic_data").rglob("manifest.json"))
    assert len(runs)==1
    manifest=json.loads(runs[0].read_text(encoding="utf-8"))
    assert manifest["accepted_trials"]==2
    assert manifest["status"] == ("aborted_by_user" if mode=="abort" else "error")
    failures=[(c.name,c.detail) for c in validate_run(runs[0].parent) if not c.passed]
    assert not failures,failures
    assert run(tmp_path,"example_experiment","constant_stimuli").status=="completed"


@pytest.mark.parametrize("corruption", ["count","response","schema","metadata"])
def test_validator_rejects_semantic_tampering_even_with_resealed_output_hashes(tmp_path,corruption):
    artifact=run(tmp_path,"contrast_sensitivity_windowed","constant_stimuli")
    copy=tmp_path/"tampered";shutil.copytree(artifact.run_directory,copy)
    manifest_path=copy/"manifest.json"
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    if corruption=="count":
        manifest["accepted_trials"]+=1
    elif corruption=="metadata":
        resolution=json.loads((copy/"resolved_experiment.json").read_text(encoding="utf-8"))
        resolution["experiment_id"]="wrong_experiment"
        (copy/"resolved_experiment.json").write_text(json.dumps(resolution),encoding="utf-8")
    else:
        rows=records(artifact)
        if corruption=="response":rows[0]["participant_response"]="999"
        columns=list(TRIAL_COLUMNS)
        if corruption=="schema":columns[0]="wrong_index"
        with (copy/"trials.tsv").open("w",encoding="utf-8",newline="") as stream:
            writer=csv.writer(stream,delimiter="\t");writer.writerow(columns)
            writer.writerows([[row[key] for key in TRIAL_COLUMNS] for row in rows])
    for name in manifest["output_sha256"]:
        manifest["output_sha256"][name]=hashlib.sha256((copy/name).read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest),encoding="utf-8")
    checks=validate_run(copy)
    assert any(not c.passed and "hash" not in c.name.lower() for c in checks),[(c.name,c.detail) for c in checks]


def test_repeated_runs_close_plot_resources(tmp_path):
    import matplotlib.pyplot as plt
    before=set(plt.get_fignums())
    for seed in range(8):
        run(tmp_path,"orientation_task","adaptive",seed)
        assert set(plt.get_fignums()) == before
