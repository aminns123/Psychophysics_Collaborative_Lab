"""Physical units and editor/TUI values must reach the real scientific path."""
import asyncio
from dataclasses import replace
import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from textual.widgets import Button, DataTable, Input, Static

from psychophysics_lab.config.stimulus_parameters import document_for, snapshot, resolve_stimuli, digest
from psychophysics_lab.core.presentation import (display_degree_coordinates, render_values,
    validate_geometry, placement_pixels)
from psychophysics_lab.core.timeline import Stimulus
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.stimuli.registry import get_stimulus
from psychophysics_lab.ui.parameter_files import (file_hash, ensure_json, ensure_unchanged,
    replace_reviewed_json)
from psychophysics_lab.ui.settings_review import describe_settings, parameter_sources

ROOT = Path(__file__).resolve().parents[1]


def profile(**updates):
    return SimpleNamespace(physical_width_m=.6, physical_height_m=.34, viewing_distance_m=.5,
                           geometry_status='verified', **updates)


@pytest.mark.parametrize('centre', [0., 15.])
@pytest.mark.parametrize('length', [.133, 1.2])
def test_probe_length_matches_physical_monitor_geometry_at_centre_and_eccentricity(centre, length):
    p = profile()
    stimulus = get_stimulus('detection_scene')
    values = document_for(stimulus)['parameters'] | {'size_deg':4.,'probe_length_deg':length,
        'probe_width_deg':1., 'probe_x_deg':0., 'probe_y_deg':0., 'contrast':.1}
    size = validate_geometry(p,(2560,1440),stimulus,values)
    placement = Stimulus('first',0.,centre)
    origin = placement_pixels(p,(2560,1440),size,placement)
    coordinates = display_degree_coordinates(p,(2560,1440),size,origin,placement)
    present = render_values(stimulus,values,pixels=size,coordinates=coordinates)
    absent = render_values(stimulus,values | {'probe_present':False},pixels=size,coordinates=coordinates)
    rows = np.flatnonzero(np.max(present-absent,axis=1)>1e-10)
    # An area-covered boundary can include one partially filled pixel per edge.
    pitch = p.physical_height_m/1440
    lower = math.degrees(math.atan((origin[1]+rows[0]-720)*pitch/.5))
    upper = math.degrees(math.atan((origin[1]+rows[-1]+1-720)*pitch/.5))
    pixel_deg = math.degrees(math.atan(pitch/.5))
    assert abs((upper-lower)-length) < 2*pixel_deg
    expected_metres = .5*(math.tan(math.radians(centre+length/2))-math.tan(math.radians(centre-length/2)))
    assert abs((rows[-1]-rows[0]+1)*pitch-expected_metres) < 2*pitch


def test_each_axis_and_frequency_use_real_pixel_pitch_and_distance():
    p = profile()
    pixels = (101,81)
    placement = Stimulus('g',10.,3.)
    origin = (1500,800)
    x,y = display_degree_coordinates(p,(2560,1440),pixels,origin,placement)
    expected_x = np.degrees(np.arctan((origin[0]+np.arange(101)+.5-1280)*(.6/2560)/.5))-10.
    expected_y = np.degrees(np.arctan((origin[1]+np.arange(81)+.5-720)*(.34/1440)/.5))-3.
    np.testing.assert_array_equal(x[0], expected_x)
    np.testing.assert_array_equal(y[:,0], expected_y)
    # The actual production grating must use these coordinates in its carrier.
    stimulus = get_stimulus('thesis_csf_grating')
    params = document_for(stimulus)['parameters'] | {'spatial_frequency_cpd':3.,'contrast':.2}
    image = render_values(stimulus,params,pixels=pixels,coordinates=(x,y))
    expected = .5+.1*np.exp(-(x*x+y*y)/2)*np.sin(2*np.pi*3*x)
    np.testing.assert_allclose(image, expected, rtol=0, atol=1e-15)
    # Uniform texture degrees are detectably different at eccentricity.
    assert not np.allclose(np.diff(x[0]),np.diff(x[0])[0],rtol=1e-5,atol=0)


def test_old_detection_snapshots_fill_only_the_previously_hardcoded_dimensions():
    spec = get_experiment('line_position_baseline')
    stimulus = get_stimulus('detection_scene')
    document = document_for(stimulus)
    document['parameters'].pop('probe_length_deg')
    document['parameters'].pop('probe_width_deg')
    old = snapshot(document,file_identity='old.json')
    result = resolve_stimuli(spec,spec.field_defaults() | {'probe_vertical_offset_deg':.2},
                            {'first':old},repo_root=ROOT)['first']
    assert result['document']['parameters']['probe_length_deg'] == .133
    assert result['document']['parameters']['probe_width_deg'] == .013
    assert result['source_resolved_sha256'] == old['resolved_sha256']
    assert result['resolved_sha256'] == digest(result['document'])
    assert 'probe_length_deg' not in old['document']['parameters']
    missing_original = dict(result['document']['parameters'])
    missing_original.pop('background')
    with pytest.raises(ValueError,match='missing parameters'):
        stimulus.validate_parameters(missing_original)


def test_review_uses_actual_trial_overrides_and_keeps_base_inputs_editable():
    baseline = get_experiment('line_position_baseline')
    values = baseline.normalise_values(baseline.field_defaults() | {'probe_vertical_offset_deg':.2})
    snapshots = resolve_stimuli(baseline,values,repo_root=ROOT)
    snapshots['first'] = snapshot(document_for(get_stimulus('detection_scene'),
        snapshots['first']['document']['parameters'] | {'probe_length_deg':1.2}),file_identity='long.json')
    description = describe_settings(baseline,values,snapshots)
    assert description['stimuli']['first']['probe_length_deg'] == 1.2
    controlled = parameter_sources(description,'first')
    assert {'background','contrast','probe_x_deg','probe_y_deg','ring_present','flanker_present'} <= controlled
    assert 'probe_length_deg' not in controlled
    # Orientation is read as an input before its sign is set per trial.
    orientation = get_experiment('orientation_task')
    values = orientation.field_defaults()
    description = describe_settings(orientation,values,resolve_stimuli(orientation,values,repo_root=ROOT))
    assert 'orientation_deg' not in parameter_sources(description,'target')


def test_external_file_replacement_keeps_history_and_refuses_unloaded_edits(tmp_path):
    path = ensure_json(tmp_path/'parameters.json',{'value':1})
    expected = file_hash(path)
    ensure_json(path,{'value':99})
    assert json.loads(path.read_text()) == {'value':1}
    replace_reviewed_json(path,{'value':2},expected)
    assert json.loads(next((tmp_path/'.history').glob('*.json')).read_text()) == {'value':1}
    with pytest.raises(ValueError,match='not overwritten'):
        replace_reviewed_json(path,{'value':3},expected)
    assert json.loads(path.read_text()) == {'value':2}


def test_literal_json_and_tui_routes_feed_same_review_and_actual_run(tmp_path,monkeypatch):
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentConfigScreen, ReviewScreen
    from psychophysics_lab.ui.stimulus_parameters import StimulusParametersPanel
    from psychophysics_lab.researcher import RunContext
    from simulations.run import simulate
    opened = []
    monkeypatch.setattr('psychophysics_lab.ui.editor.open_parameter_file',lambda root,path,*a,**k: opened.append(path))
    launch = {}
    async def scenario():
        spec = get_experiment('line_position_baseline')
        app = PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=(120,45)) as pilot:
            screen = ExperimentConfigScreen(data_root=tmp_path/'data', participant_id='JSON_TEST',session_mode='new',
                experiment=spec,monitor_profile_id='legacy_reference_display',defaults=spec.field_defaults())
            app.push_screen(screen)
            await pilot.pause()
            screen.query_one('#experiment-json-edit',Button).press()
            await pilot.pause()
            assert app.screen is screen and opened[-1].is_file()
            path = opened[-1]
            document = json.loads(path.read_text())
            document['values'].update(probe_vertical_offset_deg=.2,positions_deg='0.0',
                max_trials=3,staircases_per_condition=1,fixation_ms=750,starting_contrast=.04)
            path.write_text(json.dumps(document),encoding='utf-8')
            with pytest.raises(ValueError,match='Reload'):
                screen._collect()
            screen.query_one('#experiment-json-reload',Button).press()
            await pilot.pause()
            assert screen.query_one('#field-fixation-ms',Input).value == '750'
            # Also edit through the TUI: the same reviewed file must be updated.
            screen.query_one('#field-stimulus-ms',Input).value = '450'
            panel = next(p for p in screen.query(StimulusParametersPanel) if p.slot=='first')
            panel.query_one('#stimulus-file-first',Button).press()
            await pilot.pause()
            target_path = opened[-1]
            target = json.loads(target_path.read_text())
            target['parameters']['probe_length_deg'] = 1.2
            target_path.write_text(json.dumps(target),encoding='utf-8')
            panel.query_one('#stimulus-file-reload-first',Button).press()
            await pilot.pause()
            assert panel.current()['document']['parameters']['probe_length_deg'] == 1.2
            screen.query_one('#review',Button).press()
            await pilot.pause()
            assert isinstance(app.screen,ReviewScreen)
            table = app.screen.query_one('#resolved-settings-table',DataTable)
            displayed = str([table.get_row_at(i) for i in range(table.row_count)])
            assert 'Probe length' in displayed and '1.2' in displayed and 'detection_scene' in displayed
            assert '450' in displayed and '750' in displayed and 'consecutive_up_down' in displayed
            assert json.loads(path.read_text())['values']['stimulus_ms'] == 450
            launch['request'] = app.screen.request
            # Editing after Review must never silently launch the old settings.
            target_path.write_text(json.dumps(target | {'parameter_info':{}}),encoding='utf-8')
            with pytest.raises(ValueError,match='Review again'):
                app.verify_settings_current(app.screen.request)
    asyncio.run(scenario())
    request = launch['request']
    seen = []
    original = RunContext.trial
    def capture(run,*args,**kwargs):
        seen.append(kwargs['parameters_by_slot']['first'])
        return original(run,*args,**kwargs)
    monkeypatch.setattr(RunContext,'trial',capture)
    artifacts,_ = simulate(repo_root=ROOT,data_root=tmp_path/'simulation',experiment_id=request.experiment_id,
        values=request.experiment_values,stimulus_snapshots=request.stimulus_snapshots,analyse=False)
    assert len(seen)==3 and all(p['probe_length_deg']==1.2 for p in seen)
    traces=json.loads((artifacts.run_directory/'trial_actions.json').read_text())['trials']
    for trace in traces:
        phases=trace['plan']['phases']
        assert phases[0]['duration_ms']==750 and phases[1]['duration_ms']==450


def test_source_change_requires_restart_instead_of_running_stale_loaded_python(tmp_path,monkeypatch):
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp
    app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'data')
    spec=get_experiment('line_position_baseline')
    values=spec.field_defaults() | {'probe_vertical_offset_deg':.2}
    snapshots=resolve_stimuli(spec,values,repo_root=ROOT)
    source=str((ROOT/spec.source_paths[0]).resolve())
    monkeypatch.setitem(app.loaded_source_hashes,source,'older loaded code')
    with pytest.raises(ValueError,match='Restart PsyCoLab'):
        app.verify_loaded_sources(spec,snapshots)
