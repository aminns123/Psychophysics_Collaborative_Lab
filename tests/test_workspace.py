from datetime import datetime
from pathlib import Path
import tempfile

from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.data.workspace import (
    create_run_directory,
    load_workspace_state,
    request_from_workspace_state,
    run_number_from_path,
    save_workspace_state,
)


def _request(root: Path) -> SetupRequest:
    return SetupRequest(
        participant_id="S001",
        session_mode="new",
        experiment_id="contrast_sensitivity",
        monitor_profile_id="legacy_reference_display",
        experiment_values={"n_down": 2, "n_up": 1},
        data_root=str(root),
    )


def test_workspace_uses_human_readable_scientific_hierarchy_and_run_numbers():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        when = datetime(2026, 9, 15, 10, 30)
        kwargs = dict(
            participant_id="S001",
            experiment_id="contrast_sensitivity",
            monitor_profile_id="legacy_reference_display",
            grouping_parts=("max_500cdm2", "background_49cdm2_unverified"),
            now=when,
        )
        first = create_run_directory(root, **kwargs)
        second = create_run_directory(root, **kwargs)

        expected_parent = (
            root
            / "S001"
            / "contrast_sensitivity"
            / "legacy_reference_display"
            / "max_500cdm2"
            / "background_49cdm2_unverified"
            / "2026-09-15"
        )
        assert first == expected_parent / "run_001"
        assert second == expected_parent / "run_002"
        assert run_number_from_path(first) == 1
        assert run_number_from_path(second) == 2


def test_workspace_remembers_last_setup_and_relative_run_path():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        request = _request(root)
        run = create_run_directory(
            root,
            participant_id=request.participant_id,
            experiment_id=request.experiment_id,
            monitor_profile_id=request.monitor_profile_id,
            grouping_parts=("max_500cdm2", "background_49cdm2_unverified"),
            now=datetime(2026, 9, 15),
        )

        manifest = run / "manifest.json"
        manifest.write_text("{}", encoding="utf-8")
        save_workspace_state(
            root,
            request,
            status="completed",
            run_directory=run,
            legacy_setup={"Experiment_Type": "contrast_sensitivity_function"},
            manifest_file=manifest,
        )

        state = load_workspace_state(root)
        restored = request_from_workspace_state(state)
        assert restored is not None
        assert restored.participant_id == "S001"
        assert restored.experiment_id == "contrast_sensitivity"
        assert restored.experiment_values == {"n_down": 2, "n_up": 1}
        assert restored.data_root is None
        assert state["last_status"] == "completed"
        assert state["data_layout_schema_version"] == 1
        assert state["last_run"]["run_directory"].endswith(
            "2026-09-15/run_001"
        )
        assert "\\" not in state["last_run"]["run_directory"]


def test_run_layout_rejects_path_traversal_components():
    import pytest

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        with pytest.raises(ValueError):
            create_run_directory(
                root,
                participant_id="S001",
                experiment_id="contrast_sensitivity",
                monitor_profile_id="display",
                grouping_parts=("../escape",),
            )


def test_data_root_must_be_separate_from_repository():
    import pytest
    from psychophysics_lab.paths import resolve_data_root

    with tempfile.TemporaryDirectory() as temp:
        parent = Path(temp)
        repo = parent / "Psychophysics_Collaborative_Lab"
        repo.mkdir()
        adjacent = parent / "lab_data"

        assert resolve_data_root(adjacent, repo) == adjacent.resolve()
        with pytest.raises(ValueError):
            resolve_data_root(repo / "data", repo)
        with pytest.raises(ValueError):
            resolve_data_root(parent, repo)
