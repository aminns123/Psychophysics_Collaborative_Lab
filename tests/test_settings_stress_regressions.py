"""Regressions discovered by endpoint, combination and failure stress testing."""
import asyncio
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest
from textual.widgets import Button, DataTable
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.config.stimulus_parameters import resolve_stimuli
from psychophysics_lab.ui.settings_review import describe_settings, review_rows
from psychophysics_lab.core import presentation
from psychophysics_lab.core.timeline import TrialTimeline, Show, CollectResponse
from psychophysics_lab.stimuli.registry import get_stimulus

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('identity', ['example_experiment','probe_above_below'])
def test_review_keeps_nonvisual_markers_without_inventing_durations(identity):
    spec=get_experiment(identity)
    values=spec.normalise_values({'trial_count':2})
    snapshots=resolve_stimuli(spec,values,repo_root=ROOT)
    description=describe_settings(spec,values,snapshots)
    rows=review_rows(spec,values,snapshots,description,refresh_hz=60)
    markers=[phase['name'] for phase in description['phases'] if phase['kind']=='record_state']
    assert markers
    for marker in markers:
        assert any(group=='Trial action' and name==marker and value=='Record state' for group,name,value,_ in rows)
        assert not any(name==marker+' duration' for _,name,_,_ in rows)
    assert any(name.endswith(' planned display') for _,name,_,_ in rows)


def test_flanker_reports_its_dark_band_limit_before_preparing_stimuli():
    spec=get_experiment('line_position_flanker')
    base={'probe_vertical_offset_deg':.2,'flanker_cpd':2.}
    with pytest.raises(ValueError,match='Background intensity'):
        spec.normalise_values(base|{'background_intensity':0.})
    values=spec.normalise_values(base|{'background_intensity':.009})
    snapshots=resolve_stimuli(spec,values,repo_root=ROOT)
    description=describe_settings(spec,values,snapshots)
    stimulus=get_stimulus(snapshots['first']['document']['stimulus_id'])
    array=presentation.render_values(stimulus,description['stimuli']['first'],pixels=(128,96))
    assert array.min()>=0 and array.max()<=1


def test_failed_second_patch_releases_partial_allocations_and_allows_retry(monkeypatch):
    live=set()
    class Texture:
        allocations = 0
        def __init__(self,array):
            type(self).allocations += 1
            if type(self).allocations == 4:
                raise ValueError("injected second-phase texture creation failure")
            live.add(self)
        def delete(self):
            assert self in live,'Texture deleted twice after failed prepare'
            live.remove(self)
    monkeypatch.setitem(sys.modules,'pyglet',SimpleNamespace())
    monkeypatch.setattr(presentation,'FloatingTexture',Texture)
    display=object.__new__(presentation.Presentation)
    display.profile=SimpleNamespace(viewing_distance_m=.5,physical_width_m=.6,
        physical_height_m=.34,geometry_status='unverified')
    display.resolution=(400,300)
    stimulus=get_stimulus('detection_scene')
    params={field.key:field.default for field in stimulus.parameters}
    plan=TrialTimeline((Show('one',slot='one',duration=10),Show('two',slot='two',duration=10),
        CollectResponse(actions=('left','right'))))
    valid={'one':(stimulus.id,params),'two':(stimulus.id,params)}
    display.prepare(plan,valid)
    assert len(live)==2
    # Inject an allocation failure after the first replacement texture was
    # created. Legal researcher-chosen contrasts must not be used as a fake error.
    with pytest.raises(ValueError,match='injected second-phase'):
        display.prepare(plan,valid)
    assert not live
    assert display._rendered=={} and display._phase_geometry=={}
    display.prepare(plan,valid)
    assert len(live)==2


@pytest.mark.parametrize('identity',['example_experiment','probe_above_below'])
def test_real_tui_review_can_display_the_entire_example_trial(tmp_path,identity):
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp,ExperimentParametersScreen,ReviewScreen
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path)
        spec=get_experiment(identity)
        async with app.run_test(size=(120,45)) as pilot:
            screen=ExperimentParametersScreen(data_root=tmp_path,participant_id='STRESS_REVIEW',session_mode='new',
                experiment=spec,monitor_profile_id='legacy_reference_display',defaults=spec.field_defaults())
            app.push_screen(screen)
            await pilot.pause()
            screen.query_one('#review',Button).press()
            await pilot.pause()
            assert isinstance(app.screen,ReviewScreen)
            table=app.screen.query_one('#resolved-settings-table',DataTable)
            rendered=str([table.get_row_at(index) for index in range(table.row_count)])
            assert 'Record state' in rendered and 'planned display' in rendered
    asyncio.run(scenario())


@pytest.mark.parametrize('seed',[2**53+1,2**63-1,2**128+1])
@pytest.mark.parametrize('representation',['integer','text','decimal_text'])
def test_unbounded_integer_settings_preserve_exact_values(seed,representation):
    from psychophysics_lab.experiments._internal.spec import ConfigField
    field=ConfigField('seed','Seed','int',1,minimum=0)
    raw=seed if representation=='integer' else str(seed)+('.0' if representation=='decimal_text' else '')
    assert field.coerce(raw)==seed


@pytest.mark.parametrize('raw',[True,'NaN','Infinity','3.5','-1'])
def test_exact_integer_parser_still_rejects_invalid_values(raw):
    from psychophysics_lab.experiments._internal.spec import ConfigField
    with pytest.raises(ValueError):
        ConfigField('count','Count','int',1,minimum=0).coerce(raw)


@pytest.mark.parametrize('raw,expected',[(2.,2),('2.0',2),('1e3',1000)])
def test_exact_integer_parser_preserves_supported_whole_number_inputs(raw,expected):
    from psychophysics_lab.experiments._internal.spec import ConfigField
    assert ConfigField('count','Count','int',1,minimum=0).coerce(raw)==expected


def test_large_seed_survives_json_tui_trial_order_and_saved_manifest(tmp_path):
    import csv
    import json
    import random
    from textual.widgets import Input
    from psychophysics_lab.ui.parameter_files import load_experiment_json
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp,ExperimentParametersScreen
    from simulations.run import simulate
    seed=2**63-1
    spec=get_experiment('orientation_task')
    values=spec.field_defaults()|{'random_seed':seed,'trial_count':8}
    path=tmp_path/'settings.json'
    path.write_text(json.dumps({'schema_version':1,'experiment_id':spec.id,'values':values}),encoding='utf-8')
    loaded=load_experiment_json(path,spec)
    assert loaded['random_seed']==seed
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=(120,45)) as pilot:
            screen=ExperimentParametersScreen(data_root=tmp_path/'data',participant_id='LARGE_SEED',session_mode='new',
                experiment=spec,monitor_profile_id='legacy_reference_display',defaults=loaded)
            app.push_screen(screen)
            await pilot.pause()
            screen.query_one('#field-random-seed',Input).value=str(seed)+'.0'
            await pilot.pause()
            return screen._collect()
    actual=asyncio.run(scenario())
    assert actual['random_seed']==seed
    result,_=simulate(repo_root=ROOT,data_root=tmp_path/'data',experiment_id=spec.id,values=actual,analyse=False)
    manifest=json.loads(result.manifest_file.read_text(encoding='utf-8'))
    assert manifest['experiment_values']['random_seed']==seed
    with result.trial_log_file.open(encoding='utf-8',newline='') as stream:
        rows=list(csv.DictReader(stream,delimiter='\t'))
    expected=[i%2 for i in range(8)]
    random.Random(seed).shuffle(expected)
    assert [int(row['target_alternative']) for row in rows]==expected
