from pathlib import Path

from psychophysics_lab.diagnostics import (
    start_fatal_fault_capture,
    write_crash_report,
)


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


def test_fatal_fault_capture_is_removed_after_clean_exit(tmp_path):
    capture = start_fatal_fault_capture(data_root=tmp_path)
    assert capture is not None
    path = capture.path
    assert path.exists()
    capture.close(clean_exit=True)
    assert not path.exists()


def test_fatal_fault_capture_is_retained_after_error_exit(tmp_path):
    capture = start_fatal_fault_capture(data_root=tmp_path)
    assert capture is not None
    path = capture.path
    capture.close(clean_exit=False)
    assert path.exists()
    assert "PsyCoLab fatal-fault capture" in path.read_text(encoding="utf-8")
