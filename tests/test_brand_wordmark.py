"""Keep the original mixed-case terminal wordmark aligned with README."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_original_wordmark_is_shared_by_readme_and_windows_splash():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    launcher = (ROOT / "packaging/windows/GuidedSetup.cs").read_text(encoding="utf-8")

    assert readme.startswith("# PsyCoLab — Psychophysics Collaborative Laboratory\n")
    assert "docs/images/psycolab-logo.png" not in readme
    block = re.search(r"(?m)^\x60\x60\x60text\n([\s\S]*?)\n\x60\x60\x60", readme)
    assert block is not None
    markdown_rows = block.group(1).splitlines()

    source = re.search(r"static readonly string\[\] Logo = \{([\s\S]*?)\n    \};", launcher)
    assert source is not None
    launcher_rows = re.findall(r'^\s*"(.*?)",?$', source.group(1), re.M)
    assert markdown_rows == launcher_rows
    assert len(launcher_rows) == 9
    assert max(map(len, launcher_rows)) == 59
    assert len({len(row) for row in launcher_rows}) > 1
    assert "const int CoStart = 23, LabStart = 39;" in launcher
    assert 'const string Brand = "PsyCoLab"' in launcher
    assert "██╔══██╗" not in launcher
