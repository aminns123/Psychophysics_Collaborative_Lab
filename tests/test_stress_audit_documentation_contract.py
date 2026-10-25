"""Current active documentation and saved CSF descriptions must match the Python API.

Historical audit files are intentionally not rewritten. No physical display,
participant data or scientific formulas are exercised by these checks.
"""
from pathlib import Path

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
