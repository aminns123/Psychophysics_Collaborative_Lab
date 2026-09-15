import csv
from pathlib import Path
import tempfile

import pytest

from psychophysics_lab.data.trials import (
    TRIAL_COLUMNS,
    TRIAL_COLUMN_DEFINITIONS,
    TRIAL_SCHEMA_VERSION,
    write_trial_data_dictionary,
)
from psychophysics_lab.experiments.contrast_sensitivity import CSF_SPEC


def test_every_trial_column_has_exactly_one_definition():
    assert TRIAL_COLUMNS == tuple(TRIAL_COLUMN_DEFINITIONS)
    assert len(TRIAL_COLUMNS) == len(set(TRIAL_COLUMNS))


def test_per_run_dictionary_preserves_order_and_csf_specific_encodings():
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "trial_data_dictionary.tsv"
        write_trial_data_dictionary(
            path,
            experiment_id=CSF_SPEC.id,
            overrides=CSF_SPEC.trial_column_overrides,
        )

        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))

        assert [row["column_name"] for row in rows] == list(TRIAL_COLUMNS)
        assert all(int(row["trial_schema_version"]) == TRIAL_SCHEMA_VERSION for row in rows)
        assert all(row["experiment_id"] == "contrast_sensitivity" for row in rows)

        by_name = {row["column_name"]: row for row in rows}
        assert by_name["participant_response"]["units_or_encoding"] == "0 = left; 1 = right"
        assert by_name["target_alternative"]["units_or_encoding"] == "0 = left; 1 = right"
        assert "31.5" in by_name["stimulus_condition"]["notes"]
        assert "actually presented" in by_name["presented_screen_intensity"]["meaning"]
        assert "not what was shown" in by_name["next_screen_intensity"]["notes"]


def test_unknown_experiment_override_column_is_rejected():
    with tempfile.TemporaryDirectory() as temp:
        with pytest.raises(ValueError):
            write_trial_data_dictionary(
                Path(temp) / "dictionary.tsv",
                experiment_id="example",
                overrides={"not_a_trial_column": {"meaning": "bad"}},
            )
