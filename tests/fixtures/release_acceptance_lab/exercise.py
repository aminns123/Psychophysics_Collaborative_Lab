"""Fresh-process acceptance driver, never loaded as an official experiment."""
import asyncio
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from textual.widgets import Button, Input, Select, Static

from psychophysics_lab import extensions as ext
from psychophysics_lab import app as launcher
from psychophysics_lab.config.preflight import validate_setup
from psychophysics_lab.data.reader import load_run
from psychophysics_lab.experiments._internal.registry import get_experiment, list_experiments
from psychophysics_lab.stimuli.registry import get_stimulus
from psychophysics_lab.ui import setup
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ReviewScreen, ExperimentParametersScreen, CodeViewScreen
from scripts.validate_run import validate_run

root, lab, data = map(Path, sys.argv[1:4])
identity = "releaseaudit__diamond_axis"


def mark(message):
    with (data.parent / "acceptance_progress.log").open("a", encoding="utf-8") as stream:
        stream.write(message + "\n")


protected = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (root / "src").rglob("*.py")}
ext.configure(root, lab, trusted=True)
mark("Trusted disposable source configured")


async def settle(app, pilot):
    for _ in range(150):
        await pilot.pause(.03)
        screen = app.screen
        if screen.is_mounted and all(w.is_mounted for w in screen.query("*")):
            await pilot.pause(.03)
            if app.screen is screen:
                return
    raise AssertionError("TUI did not settle")


async def software_test():
    app = PsyCoLabSetupApp(repo_root=root, data_root=data)
    async with app.run_test(size=(150, 50)) as pilot:
        for page, name in (("stimuli", "releaseaudit__diamond"), ("experiments", identity)):
            mark("Opening " + page)
            app.open_hub_page(page)
            await settle(app, pilot)
            app.screen.query_one("#author-component", Select).value = name
            await settle(app, pilot)
            app.screen.query_one("#author-test", Button).press()
            await pilot.pause(.1)
            mark("Waiting for Test: " + name)
            await app.workers.wait_for_complete()
            mark("Test worker finished: " + name)
            await settle(app, pilot)
            message = str(app.screen.query_one("#author-result", Static).render())
            assert "Validation failed" not in message and "Could not finish" not in message, message
            assert ext.status(root, "stimulus" if page == "stimuli" else "experiment", name) == "tested", message
            app.screen.query_one("#author-ready", Button).press()
            await pilot.pause(.1)
            await app.workers.wait_for_complete()
            mark("Ready worker finished: " + name)
            await settle(app, pilot)
            assert ext.status(root, "stimulus" if page == "stimuli" else "experiment", name) == "ready"
        # Ready's message requests Refresh (F5). Check the real fresh-process
        # refresh validation, then start the continuing acquisition session.
        from psychophysics_lab.ui import refresh
        refresh.check_refresh(refresh.capture_state(app), root)


asyncio.run(software_test())
assert not ext.load(root)
diamond = get_stimulus("releaseaudit__diamond")
p = {f.key: f.default for f in diamond.parameters}
np.testing.assert_array_equal(diamond.render(p, np.array([0., .2, .3, .31]), np.zeros(4)), [.7, .7, .7, .5])
p["axis"] = "vertical"
np.testing.assert_array_equal(diamond.render(p, np.array([0., .16]), np.zeros(2)), [.7, .5])

mounts = []


def drive(**options):
    mounts.append(options)
    number = len(mounts)

    async def scenario():
        app = PsyCoLabSetupApp(**options)
        async with app.run_test(size=(150, 50)) as pilot:
            await settle(app, pilot)
            if number > 1:
                assert "PASSED" in options.get("simulation_summary", ""), options
                app.open_hub_page("data")
                await settle(app, pilot)
                assert identity in str(app.screen.query_one("#data-details", Static).render())
                for action, filename in (("inspect-trials", "trials.tsv"), ("inspect-adaptive", "adaptive_session.json")):
                    app.screen.query_one("#" + action, Button).press()
                    await settle(app, pilot)
                    assert isinstance(app.screen, CodeViewScreen)
                    assert app.screen.path.name == filename
                    app.pop_screen()
                    await settle(app, pilot)
                app.screen.query_one("#preview-figures", Button).press()
                await settle(app, pilot)
                assert "plotted" in str(app.screen.query_one("#data-status", Static).render()).lower() or "created" in str(app.screen.query_one("#data-status", Static).render()).lower()
                if number == 3:
                    app.open_hub_page("experiments")
                    await settle(app, pilot)
                    app.screen.query_one("#author-component", Select).value = identity
                    await settle(app, pilot)
                    app.screen.query_one("#author-contribute", Button).press()
                    await settle(app, pilot)
                    message = str(app.screen.query_one("#author-result", Static).render())
                    assert "PACKAGE PREPARED" in message, message
                    app.exit(None)
                    return None
                app.open_hub_page("setup")
                await settle(app, pilot)
            app.query_one("#run-intent", Select).value = "simulation"
            app.query_one("#participant", Input).value = "acceptance"
            app.query_one("#experiment", Select).value = identity
            await settle(app, pilot)
            app.query_one("#configure", Button).press()
            await settle(app, pilot)
            app.screen.query_one("#review", Button).press()
            await settle(app, pilot)
            review = app.screen
            assert isinstance(review, ReviewScreen) and not review.configuration_error, (
                type(review).__name__, getattr(review, "configuration_error", None),
                [(w.id, str(w.render())) for w in review.query(Static) if w.id])
            assert {"Conditions", "Responses", "Trial", "diamond"} <= {row[0] for row in review._review_rows}
            review._edit_review_parameter(next(i for i, row in enumerate(review._review_rows) if row[1] == "Diamond exposure (ms)"))
            await settle(app, pilot)
            assert isinstance(app.screen, ExperimentParametersScreen)
            field = app.screen.query_one("#field-exposure-ms", Input)
            field.value = "-1"
            app.screen.query_one("#review", Button).press()
            await settle(app, pilot)
            assert isinstance(app.screen, ExperimentParametersScreen) and field.value == "-1"
            field.value = "55"
            app.screen.query_one("#review", Button).press()
            await settle(app, pilot)
            assert app.screen is review and review.request.experiment_values["exposure_ms"] == 55
            try:
                validate_setup(review.request, get_experiment(identity), app.monitor_profiles[review.request.monitor_profile_id])
            except ValueError as error:
                assert "Human acquisition blocked" in str(error)
            else:
                raise AssertionError("Unqualified display was allowed for human acquisition")
            app.screen.query_one("#run-simulation", Button).press()
            await settle(app, pilot)
            app.screen.query_one("#virtual-seeds-0", Input).value = "1729"
            app.screen.query_one("#virtual-run", Button).press()
            await pilot.pause(.1)
            return app.return_value

    return asyncio.run(scenario())


# Replace only the terminal driver with Pilot; execute the actual application
# coordinator, scenario runner, recorder and saved-data inspectors unchanged.
original = setup.run_setup_tui
setup.run_setup_tui = drive
try:
    assert launcher._main([]) == 0
finally:
    setup.run_setup_tui = original
assert len(mounts) == 3
runs = sorted(p.parent for p in data.rglob("manifest.json"))
assert len(runs) == 2 and runs[0] != runs[1]
for run in runs:
    manifest = json.loads((run / "manifest.json").read_text())
    assert manifest["data_kind"] == "synthetic" and manifest["status"] == "completed"
    assert manifest["experiment_values"]["exposure_ms"] == 55
    assert len(load_run(run)["trials"]["trial_index"]) == 16
    assert all(check.passed for check in validate_run(run)), validate_run(run)
    trials = [json.loads(line) for line in (run / "trial_events.jsonl").read_text().splitlines()]
    assert {t["presentation"]["measurements"]["ratio"] for t in trials} == {.4, .7}
    assert {t["presentation"]["measurements"]["major_axis"] for t in trials} == {0, 1}
    assert all(t["presentation"]["measurements"]["requested_exposure_ms"] == 55 for t in trials)
assert (runs[0] / "trials.tsv").read_bytes() == (runs[1] / "trials.tsv").read_bytes()
assert all(hashlib.sha256(p.read_bytes()).hexdigest() == digest for p, digest in protected.items())
proposals = list((lab / "contribution_proposals").glob("*"))
assert len(proposals) == 1
assert (proposals[0] / "stimulus_library.py").read_bytes() == (lab / "stimulus_library.py").read_bytes()
ext.configure(root)
assert identity not in {spec.id for spec in list_experiments()}
print(json.dumps({"status": "PASS", "new_stimulus": "diamond", "new_experiment": identity,
                  "application_mounts": len(mounts), "saved_runs": [str(p) for p in runs],
                  "contribution_proposal": str(proposals[0]), "physical_display_used": False}))
