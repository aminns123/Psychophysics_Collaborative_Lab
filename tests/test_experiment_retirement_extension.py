"""Non-destructive retirement of trusted laboratory experiments."""
import pytest
from test_laboratory_extensions import lab, enable, ROOT, EXPERIMENT, STIMULUS
from psychophysics_lab import extensions as ext
from psychophysics_lab.development import execute_user_action
from psychophysics_lab.experiments._internal.registry import list_experiments


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
