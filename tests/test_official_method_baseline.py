"""Exercise Configuration -> Review -> canonical saved run for nine studies."""
import asyncio
import csv
from pathlib import Path
import pytest
from textual.widgets import Button, DataTable

from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentConfigScreen, ReviewScreen
from simulations.run import simulate
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = ("contrast_sensitivity", "line_position_baseline", "line_position_flanker",
            "ellipse_centre", "ellipse_major_axis", "orientation_adaptive",
            "orientation_task", "probe_above_below", "example_experiment")


@pytest.mark.parametrize("identity", OFFICIAL)
@pytest.mark.parametrize("method", ["adaptive", "constant_stimuli"])
def test_official_selected_method_reaches_review_execution_and_validated_data(tmp_path, identity, method):
    spec = get_experiment(identity)
    chosen = spec.field_defaults()
    for key, value in {"probe_vertical_offset_deg": .5, "flanker_cpd": 2., "ring_increment": .05,
                       "frequencies_cpd": "2", "positions_deg": "0", "aspect_ratios": "1",
                       "trial_count": 4, "max_trials": 4, "staircases_per_condition": 1}.items():
        if key in chosen:
            chosen[key] = value
    chosen.update(contrast_method=method, fixed_contrasts="0,0.01", fixed_repetitions=2)
    if identity == "ellipse_major_axis":
        chosen["ring_conditions"] = "base_only"
    chosen = spec.normalise_values(chosen)
    reviewed = []
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=(130, 50)) as pilot:
            screen = ExperimentConfigScreen(data_root=app.data_root, participant_id="METHOD_MATRIX",
                session_mode="new", experiment=spec, monitor_profile_id="legacy_reference_display", defaults=chosen)
            app.push_screen(screen)
            await pilot.pause()
            screen.query_one("#review", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, ReviewScreen)
            table = app.screen.query_one("#resolved-settings-table", DataTable)
            assert any(str(table.get_row_at(i)[2]) == method for i in range(table.row_count)), (
                identity, method, app.screen.request.experiment_values.get("contrast_method"),
                table.row_count, [table.get_row_at(i) for i in range(table.row_count)],
            )
            if method == "constant_stimuli":
                assert not any(str(table.get_row_at(i)[0]) == "Adaptive" for i in range(table.row_count))
            reviewed.append(dict(app.screen.request.experiment_values))
    asyncio.run(scenario())
    artifact, _ = simulate(repo_root=ROOT, data_root=tmp_path / "data", experiment_id=identity,
                           values=reviewed[0], seed=53, analyse=False)
    assert artifact.accepted_trials == 4
    assert artifact.status in {"completed", "max_trials_reached"}
    assert not [c for c in validate_run(artifact.run_directory) if not c.passed]
    with artifact.trial_log_file.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    assert len(rows[0]) == 20
    if method == "constant_stimuli":
        assert all(row["staircase_id"] == row["reversal_count"] == "" for row in rows)
        assert {float(row["presented_display_contrast"]) for row in rows} == {0, .01}
