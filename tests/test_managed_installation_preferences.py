"""Explicit local roots keep managed software trees free of user writes."""
import json

from psychophysics_lab.data import workspace


def test_explicit_configuration_root_preserves_checkout_identity(tmp_path, monkeypatch):
    source = tmp_path / 'protected-source'; source.mkdir()
    legacy = source / '.psycolab_local.json'
    legacy.write_text('{"config_root":"previous identity","last_data_root":"previous data"}')
    before = legacy.read_bytes()
    config = tmp_path / 'student-configuration'
    data = tmp_path / 'student-data'
    monkeypatch.setenv('PSYCOLAB_CONFIG_DIR', str(config))
    monkeypatch.delenv('PSYCOLAB_DATA_DIR', raising=False)
    workspace.remember_data_root(source, data)
    assert legacy.read_bytes() == before
    assert not (source / '.psycolab_preferences.lock').exists()
    assert (config / '.psycolab_preferences.lock').exists()
    assert json.loads((config / '.psycolab_local.json').read_text())['last_data_root'] == str(data.resolve())
    assert workspace.preferred_data_root(source, tmp_path / 'fallback') == data.resolve()


def test_legacy_checkout_keeps_its_existing_preference_location(tmp_path, monkeypatch):
    monkeypatch.delenv('PSYCOLAB_CONFIG_DIR', raising=False)
    monkeypatch.delenv('PSYCOLAB_DATA_DIR', raising=False)
    source = tmp_path / 'source'; source.mkdir()
    data = tmp_path / 'data'
    workspace.remember_data_root(source, data)
    assert workspace.local_preferences_path(source) == source / '.psycolab_local.json'
    assert workspace.preferred_data_root(source, tmp_path / 'fallback') == data.resolve()


def test_explicit_data_root_remains_authoritative(tmp_path, monkeypatch):
    monkeypatch.setenv('PSYCOLAB_CONFIG_DIR', str(tmp_path / 'config'))
    monkeypatch.setenv('PSYCOLAB_DATA_DIR', str(tmp_path / 'selected'))
    source = tmp_path / 'source'; source.mkdir()
    workspace.remember_data_root(source, tmp_path / 'previous')
    assert workspace.preferred_data_root(source, tmp_path / 'selected') == (tmp_path / 'selected').resolve()
