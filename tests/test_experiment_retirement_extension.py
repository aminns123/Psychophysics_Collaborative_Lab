"""Non-destructive retirement of trusted laboratory experiments."""
import pytest
from test_laboratory_extensions import lab, enable, ROOT, EXPERIMENT, STIMULUS
from psychophysics_lab import extensions as ext
from psychophysics_lab.development import execute_user_action
from psychophysics_lab.experiments._internal.registry import list_experiments


def test_retire_restore_preserves_other_loaded_experiments_and_stimuli(lab):
    from psychophysics_lab.experiments._internal import registry as experiments
    from psychophysics_lab.stimuli import registry as stimuli
    enable(lab)
    assert not ext.load(ROOT, development=True)
    before_experiments = dict(experiments._REGISTRY)
    before_stimuli = dict(stimuli._REGISTRY)
    before_loaded = dict(ext._loaded)
    ext.retire(ROOT, "experiment", EXPERIMENT)
    assert experiments._REGISTRY == {k: v for k, v in before_experiments.items() if k != EXPERIMENT}
    assert stimuli._REGISTRY == before_stimuli
    assert ext._loaded == {k: v for k, v in before_loaded.items() if k != ("experiment", EXPERIMENT)}
    ext.restore(ROOT, "experiment", EXPERIMENT)
    assert experiments._REGISTRY == {k: v for k, v in before_experiments.items() if k != EXPERIMENT}
    assert stimuli._REGISTRY == before_stimuli


def test_retired_broken_source_is_not_rediscovered(lab):
    enable(lab)
    ext.retire(ROOT, "experiment", EXPERIMENT)
    source = lab / "experiments" / (EXPERIMENT + ".py")
    source.write_text("syntax error [", encoding="utf-8")
    ext.unload()  # Editing any local science still requires a restart/retest.
    assert not ext.load(ROOT, development=True)
    assert ext.status(ROOT, "experiment", EXPERIMENT) == "retired"


def test_missing_previously_tested_source_can_be_explicitly_retired_but_not_restored(lab):
    enable(lab)
    assert execute_user_action(ROOT, "test", EXPERIMENT, {"trial_count": 2}) == 0
    source = lab / "experiments" / (EXPERIMENT + ".py")
    source.unlink()
    assert ext.status(ROOT, "experiment", EXPERIMENT) == "draft"
    ext.retire(ROOT, "experiment", EXPERIMENT)
    assert ext.status(ROOT, "experiment", EXPERIMENT) == "retired"
    with pytest.raises(ValueError, match="Missing|missing"):
        ext.restore(ROOT, "experiment", EXPERIMENT)
    assert not source.exists()


def test_retired_run_remains_readable_and_restoration_requires_fresh_test(lab, tmp_path, monkeypatch):
    from simulations.run import simulate
    from scripts.validate_run import validate_run
    from psychophysics_lab.data.reader import load_run
    monkeypatch.setattr("psychophysics_lab.analysis.previews.create_run_figures", lambda **kw: None)
    enable(lab)
    assert execute_user_action(ROOT, "preview", STIMULUS, {}) == 0
    ext.publish(ROOT, "stimulus", STIMULUS)
    assert execute_user_action(ROOT, "test", EXPERIMENT, {"trial_count": 2}) == 0
    ext.publish(ROOT, "experiment", EXPERIMENT)
    run, _ = simulate(repo_root=ROOT, data_root=tmp_path / "archives", experiment_id=EXPERIMENT,
                      values={"trial_count": 2}, analyse=False)
    saved = {p.relative_to(run.run_directory): p.read_bytes() for p in run.run_directory.rglob("*") if p.is_file()}
    ext.retire(ROOT, "experiment", EXPERIMENT)
    assert len(load_run(run.run_directory)["trials"]["trial_index"]) == 2
    assert all(check.passed for check in validate_run(run.run_directory))
    ext.restore(ROOT, "experiment", EXPERIMENT)
    with pytest.raises(ValueError, match="successful"):
        ext.publish(ROOT, "experiment", EXPERIMENT)
    assert execute_user_action(ROOT, "test", EXPERIMENT, {"trial_count": 2}) == 0
    ext.publish(ROOT, "experiment", EXPERIMENT)
    assert ext.status(ROOT, "experiment", EXPERIMENT) == "ready"
    assert saved == {p.relative_to(run.run_directory): p.read_bytes() for p in run.run_directory.rglob("*") if p.is_file()}


def test_explicit_retire_and_restore_require_new_test(lab, tmp_path):
    enable(lab)
    assert execute_user_action(ROOT, "test", EXPERIMENT, {"trial_count": 4}) == 0
    ext.publish(ROOT, "experiment", EXPERIMENT)
    source = lab / "experiments" / (EXPERIMENT + ".py")
    original = source.read_bytes()
    archived = tmp_path / "archived_result.json"
    archived.write_text('{"status": "completed"}')
    original_archive = archived.read_bytes()
    ext.retire(ROOT, "experiment", EXPERIMENT)
    assert ext.status(ROOT, "experiment", EXPERIMENT) == "retired"
    assert not ext.load(ROOT)
    assert EXPERIMENT not in {spec.id for spec in list_experiments()}
    with pytest.raises(ValueError, match="retired"):
        ext.publish(ROOT, "experiment", EXPERIMENT)
    ext.restore(ROOT, "experiment", EXPERIMENT)
    assert ext.status(ROOT, "experiment", EXPERIMENT) == "draft"
    with pytest.raises(ValueError, match="successful"):
        ext.publish(ROOT, "experiment", EXPERIMENT)
    assert source.read_bytes() == original
    assert archived.read_bytes() == original_archive


def test_retirement_scope_excludes_stimulus_and_officials(lab):
    enable(lab)
    previous = ext.records(ROOT)
    with pytest.raises(ValueError, match="Only laboratory experiments"):
        ext.retire(ROOT, "stimulus", STIMULUS)
    with pytest.raises(ValueError, match="current laboratory namespace"):
        ext.retire(ROOT, "experiment", "contrast_sensitivity")
    assert ext.records(ROOT) == previous
