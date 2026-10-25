"""Issue #82: review planning must initialise state on direct construction."""
from pathlib import Path

from psychophysics_lab.ui.settings_review import _PlanningContext


def test_direct_planning_context_initialises_read_tracking_without_describe_settings():
    # These construction arguments deliberately contain no real acquisition
    # state: only constructor semantics are under test.
    run = _PlanningContext({}, None, None, Path(), synthetic=True, stimulus_snapshots={})
    assert run.overrides == {}
    assert run.parameter_reads == {}
    run.overrides.setdefault("probe", {})["contrast"] = 0.1
    run.parameter_reads.setdefault("probe", set()).add("contrast")
    assert run.overrides["probe"]["contrast"] == 0.1
    assert "contrast" in run.parameter_reads["probe"]
