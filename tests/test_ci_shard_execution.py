"""The real shard child keeps crash capture and propagates failing assertions."""
import json

import pytest

from scripts import ci_test_shard


@pytest.mark.parametrize("fail", [False, True])
def test_real_pytest_child_retains_diagnostics_and_failure_status(tmp_path, monkeypatch, fail):
    case = tmp_path / "test_child.py"
    case.write_text(
        "import faulthandler, json\nfrom pathlib import Path\n"
        "def test_child(pytestconfig):\n"
        "    Path('evidence.json').write_text(json.dumps({\n"
        "        'fatal_capture': faulthandler.is_enabled(),\n"
        "        'timeout_dump': float(pytestconfig.getini('faulthandler_timeout'))}))\n"
        f"    assert {not fail!r}, 'deliberate child failure must reach the shard'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ci_test_shard, "partition", lambda: (tmp_path, [[case], [], [], []], [8, 0, 0, 0]))
    result = ci_test_shard.main(["ci_test_shard.py", "0"])
    assert result == (1 if fail else 0)
    assert json.loads((tmp_path / "evidence.json").read_text()) == {
        "fatal_capture": True, "timeout_dump": 0.0,
    }


def test_shards_still_cover_every_test_module_once():
    root, buckets, _ = ci_test_shard.partition()
    selected = [path for bucket in buckets for path in bucket]
    assert len(selected) == len(set(selected))
    assert set(selected) == set((root / "tests").rglob("test_*.py"))
