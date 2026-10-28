"""Checks for explicit laboratory experiment retirement."""
from pathlib import Path
import pytest
from psychophysics_lab import extensions


def test_retire_requires_experiment_kind(tmp_path):
    with pytest.raises(ValueError):
        extensions.retire(tmp_path, "stimulus", "test__stimulus")
