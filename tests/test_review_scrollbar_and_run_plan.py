"""Post-merge checks for the interrupted Review/scrollbar/side-nav changes.

Verifies the rendered TUI layout as well as table values; no scientific
calculator, participant display, or saved run is invoked.
"""

import asyncio
from pathlib import Path

import pytest
from textual.widgets import Button, DataTable
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.ui.setup import (
    PsyCoLabSetupApp, ExperimentConfigScreen, ReviewScreen,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("size", [(60, 24), (80, 24), (120, 40), (160, 55)])
def test_review_table_and_page_scrollbar_have_distinct_rails(tmp_path, monkeypatch, size):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "config"))

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=size) as pilot:
            spec = get_experiment("line_position_baseline")
            values = spec.normalise_values({
                "n_down": 3,
                "n_up": 2,
                "logUNIT_UP": 0.21,
                "logUNIT_DW": 0.07,
                "reversal_termination": 6,
                "initial_one_down_limit": 2,
                "probe_vertical_offset_deg": 0.2,
                "positions_deg": "0",
                "staircases_per_condition": 1,
                "max_trials": 30,
            })
            configuration = ExperimentConfigScreen(
                data_root=app.data_root, participant_id="TEST_ONLY",
                session_mode="new", experiment=spec,
                monitor_profile_id="legacy_reference_display", defaults=values,
            )
            app.push_screen(configuration)
            await pilot.pause()
            configuration.query_one("#review", Button).press()
            await pilot.pause()

            assert isinstance(app.screen, ReviewScreen)
            screen = app.screen
            table = screen.query_one("#resolved-settings-table", DataTable)
            workspace = screen.query_one("#console-workspace")
            outer_edge = screen.query_one("#console-edge-right")

            # The table is entirely within the framed content region.
            # The frame is separate from a one-column outer scrollbar rail.
            assert table.region.width > 0
            assert table.region.right <= outer_edge.region.x - 1
            assert outer_edge.region.right < workspace.region.right
            if workspace.show_vertical_scrollbar:
                rail = workspace.vertical_scrollbar.region
                assert rail.x >= outer_edge.region.right + 1
                assert rail.width == 1

            rows = [tuple(str(value) for value in table.get_row_at(n))
                    for n in range(table.row_count)]
            assert rows
            resolved = {(row[0], row[1]): row[2] for row in rows}
            # Only the selected, editable setting should appear when the
            # experiment's resolved run plan agrees with that value.
            for key in (
                "adaptive_rule / n_down", "adaptive_rule / n_up",
                "adaptive_rule / log_up", "adaptive_rule / log_down",
                "adaptive_rule / reversal_limit",
                "adaptive_rule / initial_one_down_limit",
                "adaptive_rule / max_trials",
            ):
                assert ("Run plan", key) not in resolved
            # This is a post-acquisition estimator for human and synthetic
            # responses, not the removed "threshold_rule" planning key.
            from psychophysics_lab.experiments.line_position_baseline import primary_rule, make_conditions
            expected = primary_rule(values, make_conditions(values))
            assert resolved[("Threshold estimation", "Within-staircase method")] == expected["within_staircase"]
            assert resolved[("Threshold estimation", "Across-staircase method")] == expected["across_staircases"]
            assert resolved[("Threshold estimation", "Retained reversals")] == str(values["threshold_reversals"])

            editable = {label: value for group, label, value, *_ in rows
                        if group == "Adaptive"}
            for field in spec.fields:
                if field.key in spec.adaptive.controls:
                    assert editable[field.display_label] == str(values[field.key])

            # Keep both the selected sidebar text and focus treatment plain,
            # left-aligned, and non-underlined after navigation.
            selected = screen.query_one("#nav-setup", Button)
            assert selected.styles.text_align == "left"
            assert not selected.styles.text_style.underline
            assert str(selected.label).startswith("-> ")

    asyncio.run(asyncio.wait_for(scenario(), 40))
