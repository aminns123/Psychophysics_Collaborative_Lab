from pathlib import Path
import tempfile

from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.data.workspace import (
    create_run_directory,
    load_workspace_state,
    request_from_workspace_state,
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


def test_workspace_remembers_last_setup_and_run_without_reusing_run_directory():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        request = _request(root)
        first = create_run_directory(
            root,
            participant_id=request.participant_id,
            experiment_id=request.experiment_id,
        )
        second = create_run_directory(
            root,
            participant_id=request.participant_id,
            experiment_id=request.experiment_id,
        )
        assert first != second

        manifest = first / "manifest.json"
        manifest.write_text("{}", encoding="utf-8")
        save_workspace_state(
            root,
            request,
            status="completed",
            run_directory=first,
            legacy_setup={"Experiment_Type": "contrast_sensitivity_function"},
            manifest_file=manifest,
        )

        state = load_workspace_state(root)
        restored = request_from_workspace_state(state)
        assert restored is not None
        assert restored.participant_id == "S001"
        assert restored.experiment_id == "contrast_sensitivity"
        assert restored.experiment_values == {"n_down": 2, "n_up": 1}
        assert state["last_status"] == "completed"
        assert state["last_run"]["run_directory"].startswith("S001/")


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
