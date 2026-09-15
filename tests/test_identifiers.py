from types import SimpleNamespace

import pytest

from psychophysics_lab.data.identifiers import validate_path_component
from psychophysics_lab.data.participants import list_participants, validate_participant_id
from psychophysics_lab.data.workspace import create_run_directory


UNSAFE = [".", "..", "a/b", "a\\b", "a<", "a>", "a:", 'a"', "a|", "a?", "a*",
          "a\x00", "a\n", "a\t", "a\x7f", "a\x85", "a ", "a.", "a..", " "]
UNSAFE += [name for base in ["CON", "PRN", "AUX", "NUL"] +
           [f"{prefix}{n}" for prefix in ("COM", "LPT") for n in range(1, 10)]
           for name in (base, base.lower(), base + ".txt", base.lower() + ".data.json")]


@pytest.mark.parametrize("name", UNSAFE)
def test_unsafe_identifiers_rejected_for_participants_and_grouping(name):
    with pytest.raises(ValueError):
        validate_participant_id(name)
    with pytest.raises(ValueError):
        validate_path_component(name, label="group")


@pytest.mark.parametrize("name", ["S001", "pilot-A", "subject_1", "a.b", "conifer", "COM10", "a" * 64])
def test_existing_participant_code_formats_remain_usable(name):
    assert validate_participant_id(name) == name


def test_leading_spaces_remain_convenient_but_cannot_hide_reserved_name():
    assert validate_participant_id(" S001") == "S001"
    with pytest.raises(ValueError):
        validate_participant_id(" CON")


@pytest.mark.parametrize("field", ["participant_id", "experiment_id", "monitor_profile_id", "grouping_parts"])
def test_every_run_component_validated_before_creating_directories(tmp_path, field):
    values = dict(participant_id="S001", experiment_id="example", monitor_profile_id="display", grouping_parts=())
    values[field] = ("NUL.txt",) if field == "grouping_parts" else "NUL.txt"
    with pytest.raises(ValueError):
        create_run_directory(tmp_path, **values)
    assert list(tmp_path.iterdir()) == []


def test_participant_listing_filters_names_without_normalizing_actual_directories():
    # Fake entries allow checking Windows-invalid names on Windows itself.
    entries = [SimpleNamespace(name=name, is_dir=lambda: True, is_symlink=lambda: False)
               for name in ["S002", "S001", ".psycolab_logs", "CON", "S003.", " S004", "S005 ", "a/b"]]
    entries.append(SimpleNamespace(name="file", is_dir=lambda: False))
    entries.append(SimpleNamespace(name="linked", is_dir=lambda: True, is_symlink=lambda: True))
    root = SimpleNamespace(exists=lambda: True, iterdir=lambda: entries)
    assert list_participants(root) == ("S001", "S002")


def test_missing_participant_root(tmp_path):
    assert list_participants(tmp_path / "missing") == ()
