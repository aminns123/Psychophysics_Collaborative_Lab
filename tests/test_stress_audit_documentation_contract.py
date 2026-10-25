"""Current active documentation and saved CSF descriptions must match the Python API.

Historical audit files are intentionally not rewritten. No physical display,
participant data or scientific formulas are exercised by these checks.
"""
from pathlib import Path

import pytest

from psychophysics_lab.experiments.contrast_sensitivity import SCIENTIFIC_SPEC


ROOT = Path(__file__).resolve().parents[1]


def test_active_guides_do_not_require_retired_csf_archive_or_future_extensions():
    architecture = (ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
    installation = (ROOT / "docs" / "INSTALLATION.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Independent laboratory ownership — implemented" in architecture
    assert "still-active physical CSF reference implementation" not in architecture
    assert "independently loadable" not in architecture or "future change" not in architecture
    assert "libC.py prepends" not in installation
    assert "do not install" in architecture.lower()
    assert "now use the **current public**" in readme


def test_saved_csf_boundary_description_agrees_with_saturating_step_logic():
    boundary = SCIENTIFIC_SPEC["boundary_policy"].lower()
    exclusions = SCIENTIFIC_SPEC["exclusions"].lower()
    assert "saturate" in boundary
    assert "saturates" in exclusions
    assert "renderer" in exclusions and "rejected" in exclusions
    assert "without clipping" not in exclusions


def test_simulation_documented_scenario_listing_is_runnable(capsys):
    from simulations.__main__ import main

    assert main(["--list-scenarios", "--experiment", "all"]) == 0
    listing = capsys.readouterr()
    assert "contrast_sensitivity\tteaching_demo\t" in listing.out
    assert not listing.err

    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])
    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert not captured.err
    # argparse wraps help to the terminal width; test wording independently
    # of line breaks through the same entry point researchers actually use.
    help_text = " ".join(captured.out.lower().split())
    assert "threshold probability" in help_text
    assert "midpoint" not in help_text
    assert "csf_baseline" not in help_text
    assert "csf_short_censored" not in help_text
