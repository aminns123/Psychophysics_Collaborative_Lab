from pathlib import Path

from psychophysics_lab.diagnostics import write_crash_report


def test_crash_report_is_written_locally(tmp_path):
    try:
        raise RuntimeError("synthetic launch failure")
    except RuntimeError as exc:
        report = write_crash_report(exc, data_root=tmp_path, phase="test")

    assert report is not None
    assert report.parent == tmp_path / ".psycolab_logs"
    text = report.read_text(encoding="utf-8")
    assert "synthetic launch failure" in text
    assert "phase: test" in text
