"""All tests keep machine preferences/calibration outside the real workspace."""
import pytest

@pytest.fixture(autouse=True)
def isolated_local_configuration(tmp_path_factory, monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path_factory.mktemp("local_configuration")))
