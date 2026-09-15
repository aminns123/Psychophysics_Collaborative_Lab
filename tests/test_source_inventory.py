import hashlib
from pathlib import Path

from psychophysics_lab.core.runner import _runtime_source_fingerprints


def test_source_inventory_includes_new_runtime_helpers_and_excludes_local_files(tmp_path):
    included = ["src/psychophysics_lab/core/new_lifecycle_helper.py", "Events/nested/runtime.py",
                "Experiments/new.py", "Functions/new.py", "Interface/new.py", "libC.py", "packages.zip"]
    excluded = ["tests/test_run.py", "src/psychophysics_lab/tests/helper.py",
                "Events/test_runtime.py", "Events/runtime_test.py", "Events/conftest.py",
                "Events/__pycache__/a.py", "Events/a.pyc", "Events/.venv/a.py",
                "Events/.vscode/a.py", "Events/tmp/a.py", "Events/data/a.py",
                ".git/a.py", ".venv/a.py", "participant/trials.tsv", "configs/local.json"]
    for name in included + excluded:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(name.encode())
    actual = _runtime_source_fingerprints(tmp_path)
    assert list(actual) == sorted(included)
    assert actual == {name: hashlib.sha256(name.encode()).hexdigest() for name in sorted(included)}
    (tmp_path / included[0]).write_bytes(b"changed")
    updated = _runtime_source_fingerprints(tmp_path)
    assert updated[included[0]] != actual[included[0]]
    assert updated == _runtime_source_fingerprints(tmp_path)


def test_actual_inventory_includes_lifecycle_and_all_package_modules():
    root = Path(__file__).resolve().parents[1]
    inventory = _runtime_source_fingerprints(root)
    assert "src/psychophysics_lab/core/lifecycle.py" in inventory
    for path in (root / "src/psychophysics_lab").rglob("*.py"):
        assert path.relative_to(root).as_posix() in inventory
