"""Minimal release-metadata consistency checks.

Does not require hardware, run experiment code, write files, or create a tag.
"""
from pathlib import Path
import tomllib

from psychophysics_lab import __version__


ROOT = Path(__file__).resolve().parents[1]


def test_declared_package_version_matches_release_notes_and_changelog():
    package = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert package["tool"]["setuptools"]["dynamic"]["version"]["attr"] == (
        "psychophysics_lab.__version__"
    )
    assert __version__ == "0.3.0"
    assert (ROOT / "docs" / "releases" / f"v{__version__}.md").is_file()
    notes = (ROOT / "docs" / "releases" / f"v{__version__}.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert notes.startswith(f"# PsyCoLab v{__version__}")
    assert f"## {__version__} — " in changelog


def test_release_notes_explain_source_archive_and_recording_boundary():
    notes = (ROOT / "docs" / "releases" / "v0.3.0.md").read_text(encoding="utf-8")
    assert "Source code (zip)" in notes
    assert "20-column" in notes
    assert "load_run(path)" in notes
    assert "pre-release" in notes.lower()
