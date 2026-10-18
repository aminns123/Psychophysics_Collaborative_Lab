"""Output provenance, independent precision evidence and non-blocking fallback."""
from dataclasses import replace
import asyncio
import ctypes as ct
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest
from textual.widgets import Button, Input, Select, Static

from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.core import output_precision as output
from psychophysics_lab.core.precision_session import (PrecisionSession, PrecisionSessionRequest,
    precision_commands, measurement_summary, precision_status, record_precision_review, latest_precision)

ROOT=Path(__file__).resolve().parents[1]

def profile():
    return load_monitor_profiles(ROOT)['legacy_reference_display']

def evidence(bits=10):
    return {'windows_report': {'bits_per_color_channel': bits, 'monitor_name': 'TEST DISPLAY'},
            'application_obtained': {'channel_bits': {'red': 16, 'green': 16, 'blue': 16},
                                    'numeric_format': 'floating_point'}, 'physical_precision_verified': False}


def test_halving_samples_are_not_a_claim_of_bit_depth():
    commands=precision_commands('halving')
    assert commands[0]==1 and commands[-1]==0 and len(commands)==18
    assert commands[1:-1]==[commands[n]/2 for n in range(16)]
    rows=[{'screen_intensity':c, 'luminance_cdm2':1+100*c**2.2} for c in commands]
    summary=measurement_summary(rows)
    assert len(summary['levels'])==18
    assert 'no automatic' in summary['conclusion']
    assert all(row['difference_standard_error_cdm2'] is None for row in summary['adjacent_measured_differences'])


@pytest.mark.parametrize('bits',[8,10,12,16,24])
def test_fine_commands_are_adjacent_integer_codes_without_six_decimal_rounding(bits):
    commands=precision_commands('fine',bits,(.5,))
    ordered=sorted(commands)
    scale=2**bits-1
    assert len(commands)==9
    assert [round(c*scale) for c in ordered]==list(range(round(.5*scale)-4,round(.5*scale)+5))
    assert all(b-a==pytest.approx(1/scale,abs=1e-15) for a,b in zip(ordered,ordered[1:]))
    assert commands==precision_commands('fine',bits,(.5,))
    assert commands!=ordered


@pytest.mark.parametrize('mode,bits,anchors',[('bad',10,(.5,)),('fine',True,(.5,)),('fine',0,(.5,)),
    ('fine',25,(.5,)),('fine',10,()),('fine',10,(float('nan'),)),('fine',10,(-.1,))])
def test_invalid_precision_requests_fail_before_display(mode,bits,anchors):
    with pytest.raises(ValueError):precision_commands(mode,bits,anchors)


def test_raw_readings_survive_and_stay_separate_from_luminance_mapping(tmp_path):
    p=profile()
    session=PrecisionSession(tmp_path,p,PrecisionSessionRequest(p.id,'fine',16,(.5,),manufacturer_specification='advertised 10-bit'))
    session.set_output(evidence())
    a,b=sorted(session.plan['commands'])[:2]
    for command,readings in ((a,(10,10.01,9.99)),(b,(10.1,10.11,10.09))):
        for value in readings:session.record(command,str(value))
    payload=json.loads(session.session_file.read_text(encoding='utf-8'))
    assert payload['readings'][0]['screen_intensity']==a
    assert a!=round(a,6)
    assert len(payload['readings'])==6
    assert payload['measurement_summary']['adjacent_measured_differences'][0]['mean_luminance_difference_cdm2']==pytest.approx(.1)
    assert payload['physical_precision_verified'] is False
    assert not list(tmp_path.rglob('pilot_luminance.json'))
    assert not list(tmp_path.glob('profiles/**/active*.json'))
    session.finish()
    record_precision_review(tmp_path,p,assessment='resolved_increments',notes='Two measured levels; meter uncertainty reviewed; no panel-depth claim.')
    assert 'resolved increments' in precision_status(tmp_path,p)
    assert latest_precision(tmp_path,replace(p,viewing_distance_m=p.viewing_distance_m+.1))==(None,None)
    # Editing raw JSON must invalidate the previous assessment fingerprint.
    payload=json.loads(session.session_file.read_text(encoding='utf-8'))
    payload['readings'][0]['luminance_cdm2']=100
    session.session_file.write_text(json.dumps(payload),encoding='utf-8')
    assert 'stale' in precision_status(tmp_path,p)


def test_inspection_is_not_measurement_and_cannot_be_reviewed_as_resolved(tmp_path):
    p=profile();session=PrecisionSession(tmp_path,p,PrecisionSessionRequest(p.id))
    session.set_output(evidence());session.finish()
    assert 'Windows reports: 10-bit' in precision_status(tmp_path,p)
    assert 'Application obtained: RGB 16/16/16, floating_point' in precision_status(tmp_path,p)
    assert '0 measured command levels' in precision_status(tmp_path,p)
    with pytest.raises(ValueError,match='repeated'):
        record_precision_review(tmp_path,p,assessment='resolved_increments',notes='Reported 10-bit')
    record_precision_review(tmp_path,p,assessment='inconclusive',notes='No meter available yet.')
    assert 'inconclusive' in precision_status(tmp_path,p)
    assert session.session['physical_precision_verified'] is False


def test_failed_measurement_save_does_not_accept_or_erase_readings(tmp_path,monkeypatch):
    import psychophysics_lab.core.precision_session as module
    p=profile();session=PrecisionSession(tmp_path,p,PrecisionSessionRequest(p.id,'halving'))
    session.record(1,'100')
    before=session.session_file.read_bytes()
    def fail(*args,**kwargs):raise OSError('disk fault')
    monkeypatch.setattr(module,'atomic_write_json',fail)
    with pytest.raises(OSError):session.record(.5,'20')
    assert len(session.session['readings'])==1
    assert session.session_file.read_bytes()==before


def test_windows_report_matches_selected_display_and_clones_are_unknown(monkeypatch):
    class API:
        clone=False
        def GetDisplayConfigBufferSizes(self,flags,npaths,nmodes):
            npaths._obj.value=2;nmodes._obj.value=2;return 0
        def QueryDisplayConfig(self,flags,npaths,paths,nmodes,modes,topology):
            for i,path in enumerate(paths):
                path.source.id=0 if self.clone else i
                path.target.id=100+i
                path.target.refresh.numerator=60;path.target.refresh.denominator=1
            return 0
        def DisplayConfigGetDeviceInfo(self,pointer):
            value=pointer._obj
            if value.header.type==1:value.name=f'DISPLAY{value.header.id}'
            if value.header.type==2:value.friendly=f'MONITOR{value.header.id}'
            if value.header.type==9:value.bits=10 if value.header.id==100 else 8
            return 0
    api=API()
    monkeypatch.setattr(output.sys,'platform','win32')
    monkeypatch.setattr(output.ct,'windll',SimpleNamespace(user32=api),raising=False)
    assert output.windows_output('DISPLAY0')['bits_per_color_channel']==10
    assert output.windows_output('display1')['bits_per_color_channel']==8
    assert output.windows_output('MISSING')['bits_per_color_channel'] is None
    api.clone=True
    assert output.windows_output('DISPLAY0')['status']=='unknown'


@pytest.mark.parametrize('floating,bits,expected',[(False,8,8),(False,10,10),(True,16,11),(True,32,24)])
def test_buffer_storage_and_usable_spacing_are_not_confused(floating,bits,expected):
    values={1:bits,2:bits,3:bits,4:bits,0x8820:int(floating)}
    gl=SimpleNamespace(GLint=ct.c_int,GL_RED_BITS=1,GL_GREEN_BITS=2,GL_BLUE_BITS=3,GL_ALPHA_BITS=4,
        glGetIntegerv=lambda enum,pointer:setattr(pointer._obj,'value',values[enum]),
        gl_info=SimpleNamespace(have_extension=lambda name:True,get_renderer=lambda:'mock',get_version=lambda:'mock'))
    actual=output.framebuffer_info(gl)
    assert actual['channel_bits']['red']==bits
    assert actual['buffer_precision_bits_in_0_1']==expected


@pytest.mark.parametrize('reported_bits',[8,10])
@pytest.mark.parametrize('obtained_bits',[8,11])
def test_negotiation_inspects_actual_format_and_warns_on_fallback(monkeypatch,obtained_bits,reported_bits):
    windows=[]
    config=SimpleNamespace(red_size=10,green_size=10,blue_size=10,_pf=1)
    screen=SimpleNamespace(get_matching_configs=lambda template:[config])
    class Error(Exception):pass
    class Window:
        def __init__(self,**kwargs):self.kwargs=kwargs;self.closed=False;self.visible=False;windows.append(self)
        def close(self):self.closed=True
        def set_caption(self,title):self.caption=title
        def set_visible(self,value):self.visible=value
    monkeypatch.setitem(sys.modules,'pyglet',SimpleNamespace(
        window=SimpleNamespace(Window=Window,NoSuchConfigException=Error),
        gl=SimpleNamespace(Config=lambda **kwargs:kwargs,ConfigException=Error)))
    monkeypatch.setattr('psychophysics_lab.core.display.screen_info',lambda screen,index:SimpleNamespace(device_id='SELECTED'))
    monkeypatch.setattr(output,'windows_output',lambda identity:{'bits_per_color_channel':reported_bits})
    def inspect(window,identity,**kwargs):
        assert identity=='SELECTED'
        assert kwargs['requested_bits']==10  # even when Windows says 8-bit
        return {'fallback':obtained_bits<10,'message':'OUTPUT FALLBACK','application_obtained':{'buffer_precision_bits_in_0_1':obtained_bits}}
    monkeypatch.setattr(output,'inspect_output',inspect)
    if obtained_bits<10:
        with pytest.warns(RuntimeWarning,match='FALLBACK'):window,report=output.create_output_window(screen,fullscreen=True)
        assert windows[0].closed and report['fallback'] and 'FALLBACK' in window.caption
    else:
        window,report=output.create_output_window(screen,fullscreen=True)
        assert len(windows)==1 and not report['fallback']
    assert window.visible and window.kwargs['visible'] is False


def test_precision_stage_launches_request_and_remains_navigable_without_measurements(tmp_path,monkeypatch):
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp
    from psychophysics_lab.core.display import DisplayInfo
    monkeypatch.setenv('PSYCOLAB_CONFIG_DIR',str(tmp_path/'config'))
    monkeypatch.setattr('psychophysics_lab.core.display.enumerate_displays',lambda:[DisplayInfo(0,0,0,2560,1440,60)])
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'data',include_historical=True)
        async with app.run_test(size=(140,45)) as pilot:
            app.query_one('#nav-display',Button).press();await pilot.pause()
            screen=app.screen
            screen.query_one('#cal-stage-precision',Button).press();await pilot.pause()
            assert 'Not checked' in str(screen.query_one('#precision-summary',Static).render())
            screen.query_one('#calibration-next',Button).press();await pilot.pause()
            assert screen.active_calibration_stage=='timing'
            screen.query_one('#cal-stage-precision',Button).press();await pilot.pause()
            screen.query_one('#precision-mode',Select).value='fine'
            screen.query_one('#precision-bits',Input).value='12'
            screen.query_one('#precision-centres',Input).value='0.4,0.6'
            screen.query_one('#precision-measure',Button).press();await pilot.pause()
        request=app.return_value
        assert isinstance(request,PrecisionSessionRequest)
        assert request.mode=='fine' and request.reference_bits==12 and request.anchors==(.4,.6)
    asyncio.run(scenario())


def test_inspection_after_photometry_preserves_measurement_review(tmp_path):
    import os
    p = profile()
    measured = PrecisionSession(tmp_path, p, PrecisionSessionRequest(p.id, 'fine', 10, (.5,)))
    measured.set_output(evidence(10))
    for command in sorted(measured.plan['commands'])[:2]:
        measured.record(command, '15.0')
        measured.record(command, '15.1')
    measured.finish()
    record_precision_review(tmp_path, p, assessment='resolved_increments',
                            notes='Tested adjacent fine commands with repeated meter readings.')
    # A later inspection must show CURRENT format while retaining older raw data.
    checked = PrecisionSession(tmp_path, p, PrecisionSessionRequest(p.id))
    checked.set_output(evidence(8))
    checked.finish()
    os.utime(measured.session_file, ns=(1_000_000_000, 1_000_000_000))
    os.utime(checked.session_file, ns=(2_000_000_000, 2_000_000_000))
    assert latest_precision(tmp_path, p)[0] == checked.session_file
    assert latest_precision(tmp_path, p, measurement_only=True)[0] == measured.session_file
    report = precision_status(tmp_path, p)
    assert 'Windows reports: 8-bit' in report
    assert '2 measured command levels' in report
    assert 'resolved increments' in report
    assert 'output configuration changed since measurement' in report


def test_halving_diagnostic_does_not_certify_fine_increments(tmp_path):
    p = profile()
    session = PrecisionSession(tmp_path, p, PrecisionSessionRequest(p.id, 'halving'))
    session.set_output(evidence())
    for command in (1., .5):
        session.record(command, '10')
        session.record(command, '10.1')
    session.finish()
    with pytest.raises(ValueError, match='fine-step'):
        record_precision_review(tmp_path, p, assessment='resolved_increments',
                                notes='Only a halving sequence has been run.')
    record_precision_review(tmp_path, p, assessment='inconclusive',
                            notes='Near-black examination only; no fine code spacing measured.')


def test_float_texture_supports_scaled_photometer_square(monkeypatch):
    from psychophysics_lab.core.presentation import FloatingTexture
    vertices = []
    gl = SimpleNamespace(
        GL_TEXTURE_2D=1, GL_QUADS=7,
        glEnable=lambda *args: None, glDisable=lambda *args: None,
        glBindTexture=lambda *args: None, glColor4f=lambda *args: None,
        glBegin=lambda *args: None, glEnd=lambda *args: None,
        glTexCoord2f=lambda *args: None,
        glVertex2f=lambda x, y: vertices.append((x, y)))
    monkeypatch.setitem(sys.modules, 'pyglet', SimpleNamespace(gl=gl))
    texture = object.__new__(FloatingTexture)
    texture.identifier = 123
    texture.width, texture.height = 1, 1
    texture.blit(10, 20, width=64, height=48)
    assert vertices == [(10, 20), (74, 20), (74, 68), (10, 68)]


def test_photometer_uses_scientific_float_texture_upload(monkeypatch, tmp_path):
    import numpy as np
    from psychophysics_lab.core import geometry_check
    from psychophysics_lab.core import presentation
    p = profile()
    session = PrecisionSession(tmp_path, p, PrecisionSessionRequest(p.id, 'fine', 10, (.5,)))
    windows, captured = [], []
    class Window:
        # Historical reference profile deliberately has no bound resolution.
        width, height = 1920, 1080
        def __init__(self):
            self.events = {}
            self.closed = False
        def event(self, fn):
            self.events[fn.__name__] = fn
            return fn
        def clear(self):
            pass
        def close(self):
            self.closed = True
    class Texture:
        def __init__(self, array):
            assert array.dtype == np.float32 and array.shape == (1, 1)
            self.value = float(array[0, 0])
            captured.append(['created', self.value])
        def blit(self, x, y, *, width=None, height=None):
            captured.append(['drawn', self.value, width, height])
        def delete(self):
            captured.append(['deleted', self.value])
    monkeypatch.setattr(presentation, 'FloatingTexture', Texture)
    def create_window(*args, **kwargs):
        window = Window()
        windows.append(window)
        return window, evidence()
    monkeypatch.setattr('psychophysics_lab.core.output_precision.create_output_window',
                        create_window)
    monkeypatch.setattr(geometry_check, 'select_screen', lambda p: (object(), {}))
    label = lambda *args, **kwargs: SimpleNamespace(text='', draw=lambda: None)
    fake = SimpleNamespace(
        gl=SimpleNamespace(glClearColor=lambda *args: None),
        text=SimpleNamespace(Label=label),
        app=SimpleNamespace(run=lambda: windows[-1].events['on_draw']()),
        window=SimpleNamespace(key=SimpleNamespace()))
    monkeypatch.setitem(sys.modules, 'pyglet', fake)
    geometry_check._draw_luminance_session(p, session.request, session)
    assert [kind for kind, *rest in captured] == ['created', 'drawn', 'deleted']
    assert captured[0][1] == pytest.approx(float(np.float32(session.plan['starting_command'])))
    assert captured[1][2] > 1 and captured[1][3] > 1
    assert windows[-1].closed
    assert 'floating texture' in session.session['output_precision']['photometer_patch_path']
