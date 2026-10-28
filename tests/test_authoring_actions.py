"""Settings and normal authoring hub regressions."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from textual.app import App
from textual.widgets import Button, Select, Static
from _manual_authoring_fixture import scaffold_draft
from psychophysics_lab.authoring import inventory, mark_tested, publish, retire, restore, load_authored
from _manual_authoring_fixture import scaffold
from test_beginner_examples import _load
from psychophysics_lab.ui.authoring import AuthoringPanel


def test_experiment_settings_are_validated_and_overrides_resolved(tmp_path):
    source, config = scaffold(tmp_path, "config_task", kind="experiment")
    spec = _load(source, "config_task").SPEC
    document = json.loads(config.read_text())
    document["values"].update(stimulus_ms=17, response_keys="LEFT,RIGHT")
    config.write_text(json.dumps(document))
    assert spec.field_defaults()["stimulus_ms"] == 17
    assert spec.normalise_values({"stimulus_ms": 31})["stimulus_ms"] == 31
    assert spec.normalise_values({})["response_keys"] == "LEFT,RIGHT"
    saved = spec.settings_snapshot()
    document["values"]["stimulus_ms"] = 99
    config.write_text(json.dumps(document))
    assert spec.settings_snapshot()["sha256"] != saved["sha256"]
    assert saved["values"]["stimulus_ms"] == 17
    document["values"]["unknown"] = 1
    config.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="Unknown"):
        spec.field_defaults()
    config.unlink()
    with pytest.raises(FileNotFoundError):
        spec.field_defaults()


@pytest.mark.parametrize("size", [(80, 24), (120, 40)])
def test_normal_authoring_panel_exposes_sources_and_validated_ready_workflow(tmp_path, monkeypatch, size):
    files = scaffold_draft(tmp_path, "panel_line", "stimulus")
    opened, calls = [], []
    class TestApp(App):
        repo_root = tmp_path
        def compose(self):
            yield AuthoringPanel("stimulus")
        def inspect_source(self, path):
            opened.append(path)
    def subprocess_result(args, **kwargs):
        # Exercise actual manifest state transitions; the renderer/simulator is
        # covered separately by the public pipeline tests.
        calls.append((args, kwargs))
        if "--dev-preview" in args:
            mark_tested(tmp_path, "stimulus", "panel_line")
        else:
            publish(tmp_path, "stimulus", "panel_line")
        return SimpleNamespace(returncode=0, stdout="Software check complete", stderr="")
    monkeypatch.setattr("psychophysics_lab.ui.authoring.subprocess.run", subprocess_result)
    monkeypatch.setattr("psychophysics_lab.authoring.load_authored", lambda *a, **kw: {})
    async def scenario():
        app = TestApp()
        async with app.run_test(size=size) as pilot:
            for identity in ("author-python", "author-json"):
                app.query_one("#" + identity, Button).press()
                await pilot.pause()
            assert opened == list(files)
            app.query_one("#author-test", Button).press()
            await pilot.pause()  # deliver button event before waiting for scheduled worker
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert inventory(tmp_path)[0].tested_fingerprint
            app.query_one("#author-ready", Button).press()
            await pilot.pause()  # deliver button event before waiting for scheduled worker
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert inventory(tmp_path)[0].status == "ready"
            assert "--dev-ready" in calls[-1][0]
            assert calls[-1][1]["cwd"] == tmp_path
            assert calls[-1][1]["env"]["PSYCOLAB_REPO_ROOT"] == str(tmp_path)
    asyncio.run(scenario())


def test_researcher_published_retirement_keeps_source_and_requires_explicit_restore(tmp_path):
    source, preset = scaffold_draft(tmp_path, "retirement_example", "experiment")
    untouched_source, untouched_preset = source.read_bytes(), preset.read_bytes()
    tested = mark_tested(tmp_path, "experiment", "retirement_example")
    assert tested.tested_fingerprint
    retired = retire(tmp_path, "experiment", "retirement_example")
    assert retired.status == "retired" and not retired.tested_fingerprint
    assert retire(tmp_path, "experiment", "retirement_example") == retired
    assert source.read_bytes() == untouched_source and preset.read_bytes() == untouched_preset
    assert load_authored(tmp_path, include_drafts=True, tolerate_errors=True) == {}
    with pytest.raises(ValueError, match="retired"):
        mark_tested(tmp_path, "experiment", "retirement_example")
    with pytest.raises(ValueError, match="retired"):
        publish(tmp_path, "experiment", "retirement_example")
    with pytest.raises(ValueError, match="reviewed Git PR"):
        retire(tmp_path, "experiment", "contrast_sensitivity")
    restored = restore(tmp_path, "experiment", "retirement_example")
    assert restored.status == "draft" and restored.tested_fingerprint == ""
    with pytest.raises(ValueError, match="test"):
        publish(tmp_path, "experiment", "retirement_example")
    assert source.read_bytes() == untouched_source and preset.read_bytes() == untouched_preset


def test_researcher_restoration_requires_original_source(tmp_path):
    source, _ = scaffold_draft(tmp_path, "lost_example", "experiment")
    retire(tmp_path, "experiment", "lost_example")
    source.unlink()
    with pytest.raises(ValueError, match="Restore the missing source"):
        restore(tmp_path, "experiment", "lost_example")
    assert inventory(tmp_path)[0].status == "retired"


def test_native_authoring_retire_cancel_confirm_restore(tmp_path):
    source, preset = scaffold_draft(tmp_path, "my_retirement", "experiment")
    old = (source.read_bytes(), preset.read_bytes())
    class TestApp(App):
        repo_root = tmp_path
        def compose(self):
            yield AuthoringPanel("experiment")
        def inspect_source(self, path):
            pass

    async def scenario():
        app = TestApp()
        async with app.run_test(size=(110, 38)) as pilot:
            app.query_one("#author-retire", Button).press()
            await pilot.pause()
            app.screen.query_one("#retire-cancel", Button).press()
            await pilot.pause()
            assert inventory(tmp_path)[0].status == "draft"
            app.query_one("#author-retire", Button).press()
            await pilot.pause()
            app.screen.query_one("#retire-confirm", Button).press()
            await pilot.pause()
            assert inventory(tmp_path)[0].status == "retired"
            assert app.query_one("#author-test", Button).disabled
            assert app.query_one("#author-ready", Button).disabled
            assert not app.query_one("#author-restore", Button).disabled
            app.query_one("#author-restore", Button).press()
            await pilot.pause()
            assert inventory(tmp_path)[0].status == "draft"
            assert inventory(tmp_path)[0].tested_fingerprint == ""

    asyncio.run(scenario())
    assert (source.read_bytes(), preset.read_bytes()) == old
