"""Ordinary launch cannot provision, repair, or bless an altered environment."""
import json
import sys

import pytest
from scripts import launcher_setup as setup
from test_locked_windows_environment import qualified


@pytest.mark.parametrize('change', [None, 'root', 'project', 'profile', 'artifact',
                                   'inventory', 'core_fingerprint', 'interpreter', 'identity'])
def test_check_preserves_state_and_never_installs(tmp_path, monkeypatch, change):
    root, project, python, calls = qualified(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, 'prefix', str(setup.VENV))
    if change == 'project':
        project.write_text(project.read_text() + '\n# changed\n')
    elif change == 'identity':
        def stale(_):
            raise setup.InstallationIdentityError('stale editable metadata')
        monkeypatch.setattr(setup, '_validate_environment', stale)
    elif change:
        state = json.loads(setup.STATE.read_text())
        if change == 'root': state['source_root'] = str(tmp_path / 'other')
        elif change == 'profile': state['qualification']['profile_sha256'] = 'changed'
        elif change == 'artifact': next(iter(state['qualification']['artifacts'].values()))['sha256'] = 'changed'
        else: state['qualification'][change] = 'changed'
        setup.STATE.write_text(json.dumps(state))
    before = setup.STATE.read_bytes()
    assert setup.check_only() == (0 if change is None else 1)
    assert setup.STATE.read_bytes() == before
    assert not any('install' in command or 'venv' in command for command in calls)


def test_check_rejects_another_interpreter_before_commands(tmp_path, monkeypatch):
    qualified(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, 'prefix', str(tmp_path / 'unrelated'))
    monkeypatch.setattr(setup, '_environment_evidence', lambda _: pytest.fail('wrong interpreter used'))
    assert setup.check_only() == 1


def test_check_never_adopts_an_unqualified_environment(tmp_path, monkeypatch):
    root, project, python, calls = qualified(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, 'prefix', str(setup.VENV))
    setup.STATE.unlink()
    assert setup.check_only() == 1
    assert not setup.STATE.exists() and not calls


@pytest.mark.parametrize('value', [None, 'unreadable', []])
def test_malformed_evidence_is_refused_without_repair(tmp_path, monkeypatch, value):
    qualified(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, 'prefix', str(setup.VENV))
    state = json.loads(setup.STATE.read_text()); state['qualification'] = value
    setup.STATE.write_text(json.dumps(state)); before = setup.STATE.read_bytes()
    assert setup.check_only() == 1 and setup.STATE.read_bytes() == before
