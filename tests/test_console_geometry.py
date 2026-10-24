"""Geometry, hierarchy and scroll behavior are the shared application contract."""
import asyncio
from pathlib import Path
import pytest
from textual.widgets import Button, Input, Select
from psychophysics_lab.ui.setup import PsyCoLabSetupApp
from test_laboratory_console import check_shell
ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('size', [(60,24),(80,24),(120,40),(160,55)])
def test_geometry_survives_scrolling_dropdowns_and_every_calibration_stage(tmp_path,monkeypatch,size):
    monkeypatch.setenv('PSYCOLAB_CONFIG_DIR',str(tmp_path/'config'))
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            check_shell(app,'setup')
            workspace=app.screen.query_one('#console-workspace')
            assert workspace.max_scroll_y > 0
            workspace.focus()
            await pilot.press('pagedown')
            await pilot.pause()
            assert workspace.scroll_y > 0
            check_shell(app,'setup')
            select=app.screen.query_one('#experiment',Select)
            select.focus()
            await pilot.pause()
            await pilot.press('enter')
            await pilot.pause()
            assert select.expanded
            check_shell(app,'setup')
            await pilot.press('escape')
            app.open_hub_page('help')
            await pilot.pause()
            check_shell(app,'help')
            if size[1]>=40:
                assert app.screen.query_one('#console-workspace').max_scroll_y == 0
            app.open_hub_page('display')
            await pilot.pause()
            for stage in ('bind','geometry','spatial','luminance','precision','timing','review'):
                control=app.screen.query_one('#cal-stage-'+stage,Button)
                control.focus()
                await pilot.pause()
                await pilot.press('enter')
                await pilot.pause()
                assert app.screen.active_calibration_stage==stage
                check_shell(app,'display')
                workspace=app.screen.query_one('#console-workspace')
                workspace.scroll_end(animate=False)
                await pilot.pause()
                check_shell(app,'display')
    asyncio.run(asyncio.wait_for(scenario(), 45))


def test_navigation_markers_and_subpage_routes_preserve_drafts(tmp_path,monkeypatch):
    monkeypatch.setenv('PSYCOLAB_CONFIG_DIR',str(tmp_path/'config'))
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=(120,40)) as pilot:
            await pilot.pause()
            app.query_one('#participant',Input).value='GEOMETRY_TEST'
            active=app.screen.query_one('#nav-setup',Button)
            inactive=app.screen.query_one('#nav-data',Button)
            assert str(active.label).startswith('-> ')
            assert str(inactive.label).startswith('- ')
            await pilot.hover(inactive)
            assert str(inactive.label).startswith('> ')
            await pilot.press('f6')
            await pilot.pause()
            assert app.focused is active
            assert str(active.label).startswith('> ')
            await pilot.press('tab','enter')
            await pilot.pause()
            assert type(app.screen).__name__=='ExperimentConfigScreen'
            configuration=app.screen
            configuration.query_one('#field-trial-count',Input).value='3'
            await pilot.click(app.screen.query_one('#path-review',Button))
            await pilot.pause()
            assert type(app.screen).__name__=='ReviewScreen'
            assert app.screen.query_one('#resolved-settings-table').row_count > 0
            await pilot.click(app.screen.query_one('#path-configure',Button))
            await pilot.pause()
            assert app.screen is configuration
            assert configuration.query_one('#field-trial-count',Input).value=='3'
            from psychophysics_lab.ui.source_view import SourceView
            app.push_screen(SourceView(ROOT/'src/psychophysics_lab/stimulus_library.py'))
            await pilot.pause()
            await pilot.click(app.screen.query_one('#path-review',Button))
            await pilot.pause()
            assert type(app.screen).__name__=='ReviewScreen'

            check_shell(app,'setup')
    asyncio.run(asyncio.wait_for(scenario(), 45))
