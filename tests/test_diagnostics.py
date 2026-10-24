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


def test_ui_logging_keeps_local_crash_report_when_windows_console_handle_fails(
    tmp_path, monkeypatch,
):
    """A deliberate runtime failure must not be replaced by Textual WinError 6."""
    from psychophysics_lab.ui import setup as ui_setup

    class AppStub:
        repo_root = tmp_path / "framework"
        data_root = tmp_path

    def invalid_output_handle(*args, **kwargs):
        raise OSError(6, "The handle is invalid")

    try:
        raise RuntimeError("Display driver changed")
    except RuntimeError as exc:
        # Simulate *both* Textual's captured stderr and stdout being broken.
        # The original failure has already been handled by the override dialog.
        with monkeypatch.context() as patched:
            patched.setattr(ui_setup.traceback, "print_exception", invalid_output_handle)
            patched.setattr("builtins.print", invalid_output_handle)
            ui_setup._report_ui_exception(
                AppStub(), exc, phase="tui_researcher_override"
            )

    reports = sorted((tmp_path / ".psycolab_logs").glob("psycolab_error_*.log"))
    assert len(reports) == 1
    saved = reports[0].read_text(encoding="utf-8")
    assert "phase: tui_researcher_override" in saved
    assert "RuntimeError: Display driver changed" in saved
