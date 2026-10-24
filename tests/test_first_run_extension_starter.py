"""Non-destructive first-run laboratory source provisioner, Windows-first.

Only temp path fixtures are written. No participant, monitor, or real lab files.
"""
import asyncio
import hashlib
from pathlib import Path
import shutil

import pytest

from psychophysics_lab import extensions as ext
from psychophysics_lab.config.local import config_root, preferences, save_preferences

TEMPLATE = Path(__file__).resolve().parents[1] / "examples" / "laboratory_extensions"


@pytest.fixture
def empty_checkout(tmp_path):
    repo = tmp_path / "Laboratory" / "Psychophysics_Collaborative_Lab"
    repo.mkdir(parents=True)
    source = repo / "examples" / "laboratory_extensions"
    shutil.copytree(TEMPLATE, source)
    return repo


def _bytes(root):
    return {
        p.relative_to(root).as_posix(): (
            hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns
        )
        for p in root.rglob("*") if p.is_file()
    }


def test_first_run_creates_ready_to_edit_sibling_but_never_trusts_python(empty_checkout):
    repo = empty_checkout
    target, created = ext.initialise_default(repo, data_root=repo.parent / "data")
    assert created is True
    assert target == repo.parent / "PsyCoLab_Extensions"
    assert (target / "psycolab_extensions.json").is_file()
    assert (target / "stimulus_library.py").is_file()
    assert (target / "experiments" / "demolab__left_right.py").is_file()
    assert (target / "presets" / "left_right.json").is_file()
    assert ext.configured(repo) is None
    assert not (config_root(repo) / "preferences.json").exists()

    # There is no automatic execution/approval, Ready marking or rewrite.
    before = _bytes(target)
    same, created_again = ext.initialise_default(repo, data_root=repo.parent / "data")
    assert (same, created_again) == (target, False)
    assert _bytes(target) == before


def test_existing_scientific_source_is_never_overwritten(empty_checkout):
    repo = empty_checkout
    target, _ = ext.initialise_default(repo, data_root=repo.parent / "data")
    scientist = target / "experiments" / "demolab__left_right.py"
    scientist.write_bytes(scientist.read_bytes() + b"\n# scientist notes\n")
    before = _bytes(target)
    root, created = ext.initialise_starter(repo, data_root=repo.parent / "data")
    assert root == target and created is False
    assert _bytes(target) == before
    assert scientist.read_bytes().endswith(b"# scientist notes\n")


def test_existing_nested_manual_folder_is_not_restructured(empty_checkout):
    repo = empty_checkout
    target = ext.suggested_root(repo)
    nested = target / "laboratory_extensions"
    shutil.copytree(TEMPLATE, nested)
    before = _bytes(target)
    with pytest.raises(ValueError, match="Existing folder was left unchanged"):
        ext.initialise_default(repo, data_root=repo.parent / "data")
    assert _bytes(target) == before
    assert not (target / "psycolab_extensions.json").exists()
    assert ext.validate_root(nested, repo, repo.parent / "data")[0] == nested


def test_user_can_choose_new_or_empty_custom_folder(empty_checkout):
    repo = empty_checkout
    custom = repo.parent / "MyLab_Projects" / "custom_studies"
    custom.mkdir(parents=True)
    path, created = ext.initialise_starter(repo, custom, data_root=repo.parent / "data")
    assert created and path == custom
    assert (custom / "stimulus_library.py").is_file()
    assert not ext.suggested_root(repo).exists()
    # Changing location requires deliberate trust; no implicit enabling.
    assert ext.configured(repo) is None
    ext.configure(repo, custom, trusted=True, data_root=repo.parent / "data")
    assert ext.configured(repo, repo.parent / "data")[0] == custom
    ext.configure(repo)
    assert ext.configured(repo) is None
    assert preferences(config_root(repo))["extensions"]["root"] == str(custom)
    assert ext.initialise_default(repo, data_root=repo.parent / "data") is None
    assert not ext.suggested_root(repo).exists()


def test_deliberately_disabled_starter_is_not_recreated(empty_checkout):
    repo = empty_checkout
    save_preferences(config_root(repo), extensions={"enabled": False})
    assert ext.initialise_default(repo, data_root=repo.parent / "data") is None
    assert not ext.suggested_root(repo).exists()


def test_starter_refuses_overlapping_data_or_checkout(empty_checkout):
    repo = empty_checkout
    with pytest.raises(ValueError, match="separate folders"):
        ext.initialise_starter(repo, repo / "local", data_root=repo.parent / "data")
    with pytest.raises(ValueError, match="separate folders"):
        ext.initialise_starter(repo, repo.parent / "data", data_root=repo.parent / "data")
    assert not (repo / "local").exists()
    assert not (repo.parent / "data").exists()


def test_build_experiments_create_starter_button_uses_selected_location(tmp_path, monkeypatch):
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp
    from textual.widgets import Button, Input, Static

    real_repo = Path(__file__).resolve().parents[1]
    requested = tmp_path / "custom_laboratory_science"
    called = []

    def fake_initialise(repo, root, *, data_root):
        called.append((repo, root, data_root))
        return requested, True

    monkeypatch.setattr(ext, "initialise_starter", fake_initialise)

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=real_repo, data_root=tmp_path / "data")
        async with app.run_test(size=(120, 48)) as pilot:
            app.open_hub_page("experiments")
            await pilot.pause()
            app.screen.query_one("#extensions-root", Input).value = str(requested)
            app.screen.query_one("#extensions-starter", Button).press()
            await pilot.pause()
            text = str(app.screen.query_one("#extensions-status", Static).render())
            assert "Starter files created" in text
            assert "NOT trusted/enabled" in text

    asyncio.run(scenario())
    assert called == [(real_repo, str(requested), tmp_path / "data")]
