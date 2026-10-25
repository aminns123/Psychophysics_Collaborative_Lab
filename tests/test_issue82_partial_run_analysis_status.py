"""Issue #82: acquisition failure must remain visible in derived status.

Scientific estimators and eligible partial staircases stay unchanged.
All example trials are synthetic fixtures in disposable directories.
"""
import hashlib
import json

import pytest

from psychophysics_lab.analysis.previews import create_run_figures
from test_pipeline_repairs import saved_run


@pytest.mark.parametrize(
    "run_status, expected_report_status",
    [("completed", "available"), ("aborted_by_user", "partial")],
)
def test_derived_status_preserves_incomplete_acquisition_truth(
    tmp_path, run_status, expected_report_status,
):
    run = saved_run(tmp_path, status=run_status, kind="human", complete=False)
    original_bytes = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in run.iterdir() if p.is_file()
    }

    report = create_run_figures(data_root=tmp_path, run_directory=run)

    assert report["run_status"] == run_status
    assert report["status"] == expected_report_status
    assert report["primary"]["condition_thresholds"]
    assert (run / "analysis" / "staircases.png").is_file()
    assert (run / "analysis" / "threshold_vs_condition.png").is_file()
    assert (run / "analysis" / "sensitivity_vs_condition.png").is_file()
    assert json.loads((run / "analysis" / "analysis_status.json").read_text())["status"] == expected_report_status
    assert {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in run.iterdir() if p.is_file()
    } == original_bytes
