"""Shared console layout and real input routing at representative terminal sizes."""
import asyncio
from pathlib import Path

import pytest
from textual.widgets import Button, Input, Static

from psychophysics_lab.ui.console import PAGES
from psychophysics_lab.ui.setup import (
    PsyCoLabSetupApp, ExperimentConfigScreen, ReviewScreen, ChangeDisplayScreen,
    CodeViewScreen,
)
from psychophysics_lab.ui.calibration_review import (
    PhysicalVerificationScreen, ExperimentQualificationScreen,
)
from psychophysics_lab.ui.luminance_data import LuminanceDataScreen
from psychophysics_lab.ui.profiles import ProfileScreen
from psychophysics_lab.ui.source_view import SourceView
from psychophysics_lab.ui.stimulus_parameters import StimulusParametersPanel, JsonPresetEditor
from psychophysics_lab.ui.stimulus_editor import StimulusValueEditor
from psychophysics_lab.ui.unified_run import VirtualObserverOptionsScreen

ROOT = Path(__file__).resolve().parents[1]


def check_shell(app, section):
    screen = app.screen
    assert screen.console_section == section
    assert len(screen.query('#hub-nav')) == len(screen.query('#console-heading')) == 1
    header = screen.query_one('#console-heading')
    sidebar = screen.query_one('#hub-nav')
    # Catch dock-corner occlusion: the application title must actually be visible.
    assert app.get_widget_at(1, 0)[0] is header
    assert sidebar.region.width == (17 if app.size.width < 100 else 23)
    assert screen.query_one('#nav-' + section).has_class('nav-selected')
    from textual.geometry import Region
    w, h = app.size
    side = 17 if w < 100 else 23
    workspace = screen.query_one('#console-workspace')
    assert header.region == Region(0, 0, w, 2)
    assert sidebar.region == Region(0, 2, side, h - 3)
    assert workspace.region == Region(side, 2, w - side, h - 3)
    assert screen.query_one('Footer').region == Region(0, h - 1, w, 1)
    assert workspace.scrollable_content_region == Region(side + 2, 3, w - side - 5, h - 5)
    assert workspace.styles.scrollbar_size_vertical == 1
    assert workspace.styles.scrollbar_gutter == 'stable'
    # Expanding the active path must not move the major navigation rows.
    y = 3
    for key, _, _ in PAGES:
        control = screen.query_one('#nav-' + key)
        if not control.display:
            continue
        assert control.region.y == y
        assert control.region.height == 2
        y += 4 if key == 'setup' else 2

    if workspace.show_vertical_scrollbar:
        assert workspace.vertical_scrollbar.region == Region(w - 3, 3, 1, h - 5)
    for group in workspace.query('VerticalScroll'):
        assert group.styles.overflow_y == 'hidden'


@pytest.mark.parametrize('size', [(60, 24), (80, 24), (120, 40), (160, 55)])
def test_all_main_routes_have_visible_shell_and_scrollable_workspace(tmp_path, monkeypatch, size):
    monkeypatch.setenv('PSYCOLAB_CONFIG_DIR', str(tmp_path / 'config'))

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / 'data', include_historical=True)
        async with app.run_test(size=size) as pilot:
            app.query_one('#participant', Input).value = 'CONSOLE_DRAFT'
            for section, _, _ in PAGES:
                button = app.screen.query_one('#nav-' + section, Button)
                button.focus()
                await pilot.pause()
                await pilot.press('enter')
                await pilot.pause()
                check_shell(app, section)
                await pilot.press('f6')
                assert app.focused is app.screen.query_one('#nav-' + section)
            app.open_hub_page('setup')
            await pilot.pause()
            assert app.query_one('#participant', Input).value == 'CONSOLE_DRAFT'
            # Resize the same mounted screen, not just a fresh app.
            await pilot.resize_terminal(140, 48)
            await pilot.pause()
            check_shell(app, 'setup')
            await pilot.click(app.screen.query_one('#nav-experiments', Button))
            await pilot.pause()
            check_shell(app, 'experiments')

    asyncio.run(scenario())


def test_sidebar_preserves_default_routes_and_keyboard_focus_order(tmp_path, monkeypatch):
    monkeypatch.setenv('PSYCOLAB_CONFIG_DIR', str(tmp_path / 'config'))

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / 'data')
        async with app.run_test(size=(100, 35)) as pilot:
            assert not app.screen.query_one('#nav-simulations').display
            await pilot.press('f6', 'tab')
            assert app.focused.id == 'path-configure'
            await pilot.press('tab')
            assert app.focused.id == 'nav-stimuli'
            await pilot.press('enter')
            await pilot.pause()
            check_shell(app, 'stimuli')
            await pilot.press('f6', 'shift+tab', 'shift+tab', 'enter')
            await pilot.pause()
            check_shell(app, 'setup')

    asyncio.run(scenario())


@pytest.mark.parametrize('size', [(60, 24), (80, 24), (120, 40), (160, 55)])
def test_nested_pages_keep_sidebar_back_actions_and_configuration(tmp_path, monkeypatch, size):
    monkeypatch.setenv('PSYCOLAB_CONFIG_DIR', str(tmp_path / 'config'))

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / 'data')
        async with app.run_test(size=size) as pilot:
            app.query_one('#participant', Input).value = 'CONSOLE_DRAFT'
            app.query_one('#configure', Button).press()
            await pilot.pause()
            configuration = app.screen
            assert isinstance(configuration, ExperimentConfigScreen)
            check_shell(app, 'setup')
            configuration.query_one('#field-trial-count', Input).value = '3'
            panel = configuration.query(StimulusParametersPanel).first()
            source = ROOT / 'src/psychophysics_lab/stimulus_library.py'
            profile = app.monitor_profiles['legacy_reference_display']
            pages = [
                (ChangeDisplayScreen(configuration), 'setup', 'display-cancel'),
                (StimulusValueEditor(panel), 'setup', 'stimulus-values-back'),
                (JsonPresetEditor(panel), 'setup', 'json-cancel'),
                (SourceView(source), 'setup', 'source-close'),
                (CodeViewScreen(title='Stimulus source', path=source), 'setup', 'back'),
                (ProfileScreen(profile=profile), 'display', 'profile-back'),
                (PhysicalVerificationScreen(profile), 'display', 'verification-back'),
                (ExperimentQualificationScreen(profile), 'display', 'qualification-back'),
                (LuminanceDataScreen(profile), 'display', 'dataset-back'),
            ]
            for page, section, back in pages:
                app.push_screen(page)
                await pilot.pause()
                check_shell(app, section)
                button = page.query_one('#' + back, Button)
                button.focus()
                await pilot.pause()
                await pilot.press('enter')
                await pilot.pause()
                assert app.screen is configuration
                assert configuration.query_one('#field-trial-count', Input).value == '3'
            configuration.query_one('#review', Button).press()
            await pilot.pause()
            assert isinstance(app.screen, ReviewScreen)
            check_shell(app, 'setup')
            review = app.screen
            app.push_screen(VirtualObserverOptionsScreen(review.request))
            await pilot.pause()
            check_shell(app, 'setup')
            app.screen.query_one('#virtual-back', Button).press()
            await pilot.pause()
            assert app.screen is review

    asyncio.run(scenario())
