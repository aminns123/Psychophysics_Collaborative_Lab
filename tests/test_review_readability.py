"""Presentation improvements retain full scientific values and source authority."""
import asyncio
from pathlib import Path

import pytest
from textual.widgets import Button, DataTable, Static
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.ui.review_authority import authority_for_row
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentParametersScreen, ReviewScreen

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('size', [(60, 24), (150, 50)])
def test_long_values_and_authority_remain_readable_in_both_review_views(tmp_path, size):
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'data')
        async with app.run_test(size=size) as pilot:
            spec = get_experiment('contrast_sensitivity')
            app.push_screen(ExperimentParametersScreen(data_root=app.data_root,
                participant_id='READABILITY', session_mode='new', experiment=spec,
                monitor_profile_id='legacy_reference_display', defaults=spec.normalise_values({})))
            await pilot.pause()
            app.screen.query_one('#review', Button).press()
            await pilot.pause()
            review = app.screen
            assert isinstance(review, ReviewScreen) and not review.configuration_error
            table = review.query_one('#resolved-settings-table', DataTable)
            records = [tuple(str(v) for v in table.get_row_at(i)) for i in range(table.row_count)]
            assert [r[:3] for r in records] == [tuple(map(str, r[:3])) for r in review._review_rows]
            row = next(i for i, r in enumerate(review._review_rows) if len(str(r[2])) > 24)
            table.move_cursor(row=row)
            await pilot.pause()
            assert str(review._review_rows[row][2]) in str(review.query_one('#review-file-location', Static).renderable)
            assert str(review._file_targets[row]['path']) in records[row][4] if review._file_targets[row]['path'] else True
            assert any(r.height > 1 for r in table.rows.values())
            review.query_one('#review-expand-table', Button).press()
            await pilot.pause()
            expanded = app.screen
            wide = expanded.query_one('#expanded-settings-table', DataTable)
            assert records == [tuple(str(v) for v in wide.get_row_at(i)) for i in range(wide.row_count)]
            wide.move_cursor(row=row)
            await pilot.pause()
            assert str(review._review_rows[row][2]) in str(expanded.query_one('#expanded-review-location', Static).renderable)
            expanded.query_one('#expanded-review-back', Button).press()
            await pilot.pause()
            assert app.screen is review and table.cursor_row == row
            for button in review.query('#review-table-actions Button'):
                button.focus()
                await pilot.pause()
                assert button.region.width > 0 and button.region.height == 3
    asyncio.run(scenario())


@pytest.mark.parametrize('value,status', [(None, 'Missing required input'), ('nonsense', 'Invalid selected input')])
def test_invalid_draft_rows_identify_the_generic_correction_route(value, status):
    spec = get_experiment('line_position_baseline')
    field = next(f for f in spec.fields if f.key == 'probe_vertical_offset_deg')
    result = authority_for_row(spec, {field.key: value}, {}, {},
        ('Experiment', field.display_label, str(value), 'Requested vertical offset'),
        {'kind': 'experiment_json', 'key': field.key}, {'experiment': None})
    assert result['status'] == status
    assert result['edit_kind'] == 'experiment' and result['field'] == field.key
    assert 'Review → Edit inputs / stimuli' in result['route']
