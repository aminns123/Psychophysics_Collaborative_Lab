"""Display/input boundary tests with an injected software clock; no hardware claims."""
import sys
from types import SimpleNamespace
import pytest
from psychophysics_lab.core.presentation import Presentation
from psychophysics_lab.researcher import Show, Stimulus, CollectResponse, TrialTimeline, LEFT_RIGHT
from psychophysics_lab.stimuli.registry import get_stimulus


def fake_presentation(monkeypatch, key_time=.005, key="LEFT"):
    clock = {"now": 0.}
    blits = []
    handlers = {}
    class Window:
        has_exit = False
        dispatches = 0
        def dispatch_events(self):
            self.dispatches += 1
            if self.dispatches == 2:
                clock["now"] = key_time
                if key:
                    handlers["on_key_press"](key, 0)
        def push_handlers(self, **callbacks):
            handlers.update(callbacks)
        def remove_handlers(self, **callbacks):
            for name in callbacks:
                handlers.pop(name)
        def clear(self): pass
        def flip(self): pass
    class Image:
        def __init__(self, *args, **kwargs): pass
        def blit(self, x, y): blits.append((x, y))
        def delete(self): pass
    fake = SimpleNamespace(
        gl=SimpleNamespace(glClearColor=lambda *a: None),
        image=SimpleNamespace(ImageData=Image),
        text=SimpleNamespace(Label=lambda *a, **kw: SimpleNamespace(draw=lambda: None)),
        window=SimpleNamespace(key=SimpleNamespace(ESCAPE="ESCAPE", symbol_string=lambda key: key)),
    )
    monkeypatch.setitem(sys.modules, "pyglet", fake)
    monkeypatch.setattr("psychophysics_lab.core.presentation.FloatingTexture", Image)
    monkeypatch.setattr("psychophysics_lab.core.presentation.time.perf_counter", lambda: clock["now"])
    monkeypatch.setattr("psychophysics_lab.core.presentation.time.sleep", lambda *a: None)
    display = object.__new__(Presentation)
    display.window, display.responses, display.held = Window(), LEFT_RIGHT, set()
    display.resolution = (1000, 600)
    display.profile = SimpleNamespace(viewing_distance_m=.6, physical_width_m=.5,
                                      physical_height_m=.3, geometry_status="unverified", expected_resolution_px=(1000,600))
    display._rendered = {"answer": []}
    return display, blits, handlers


@pytest.mark.parametrize("keypress_time", [.005, .020])
def test_only_keys_before_timeout_are_accepted(monkeypatch, keypress_time):
    display, _, handlers = fake_presentation(monkeypatch, keypress_time)
    event = {}
    phase = CollectResponse(actions=("left", "right"), timeout=10)
    if keypress_time < .01:
        response = display.play_phase(phase, event)
        assert response.key == "LEFT" and response.reaction_time_s == keypress_time
    else:
        with pytest.raises(TimeoutError):
            display.play_phase(phase, event)
    assert event["software_onset_s"] == 0.
    assert event["software_offset_s"] == keypress_time
    assert not handlers


def test_prepared_simultaneous_patches_draw_in_written_order(monkeypatch):
    display, blits, _ = fake_presentation(monkeypatch, .02, key=None)
    phase = Show("pair", duration=10, stimuli=(Stimulus("left", -3, 0), Stimulus("right", 3, 0)))
    timeline = TrialTimeline((phase, CollectResponse(actions=("left", "right"))))
    stimulus = get_stimulus("example_stimulus")
    params = {field.key: field.default for field in stimulus.parameters}
    display.prepare(timeline, {"left": (stimulus.id, params), "right": (stimulus.id, params)})
    display.play_phase(phase, {})
    assert len(blits) == 2
    assert blits[0][0] < blits[1][0]
    assert blits[0][1] == blits[1][1]


@pytest.mark.parametrize('key', ['SPACE', 'ENTER', '1'])
def test_readiness_key_has_no_response_and_own_instructions(monkeypatch, key):
    from psychophysics_lab.researcher import WaitForKey
    display, _, handlers = fake_presentation(monkeypatch, key=key)
    display._rendered = {'ready': []}
    display.show_response_instructions = False
    labels = []
    monkeypatch.setattr(sys.modules['pyglet'].text, 'Label', lambda text, **kw: labels.append(text) or SimpleNamespace(draw=lambda: None))
    event = {}
    assert display.play_phase(WaitForKey('ready', key=key, instructions='Researcher instruction'), event) is None
    assert event['readiness']['key'] == key
    assert 'response' not in event
    assert labels == ['Researcher instruction'] and not handlers


def test_escape_at_readiness_and_handler_cleanup(monkeypatch):
    from psychophysics_lab.researcher import WaitForKey, ParticipantAbort
    display, _, handlers = fake_presentation(monkeypatch, key='ESCAPE')
    display._rendered = {'ready': []}
    event = {}
    with pytest.raises(ParticipantAbort):
        display.play_phase(WaitForKey('ready', key='SPACE'), event)
    assert 'readiness' not in event and 'software_offset_s' in event and not handlers


def test_readiness_held_key_cannot_become_first_trial_answer(monkeypatch):
    from psychophysics_lab.researcher import WaitForKey, ResponseParadigm
    display, _, handlers = fake_presentation(monkeypatch)
    display._rendered = {'ready': [], 'answer': []}
    display.responses = ResponseParadigm('shared-key-test', ('left','right'), ('ENTER','RIGHT'))
    clock = {'dispatch': 0, 'now': 0.}
    monkeypatch.setattr('psychophysics_lab.core.presentation.time.perf_counter', lambda: clock['now'])
    def dispatch():
        clock['dispatch'] += 1
        clock['now'] = clock['dispatch'] / 100
        if clock['dispatch'] in {2, 3, 4, 6}:
            handlers['on_key_press']('ENTER', 0)
        if clock['dispatch'] == 5:
            display.held.discard('ENTER')  # the existing on_key_release handler
    display.window.dispatch_events = dispatch
    ready = {}
    assert display.play_phase(WaitForKey('ready', key='ENTER'), ready) is None
    assert display.held == {'ENTER'} and clock['dispatch'] == 2
    answer = display.play_phase(CollectResponse(actions=('left','right')), {})
    assert answer.key == 'ENTER' and clock['dispatch'] == 6
    assert answer.reaction_time_s == pytest.approx(.03)


def test_human_readiness_beep_is_a_distinct_request(monkeypatch):
    from psychophysics_lab.researcher import WaitForKey, Beep
    display, _, _ = fake_presentation(monkeypatch, key='SPACE')
    display._rendered = {'ready': []}
    commands = []
    def request(beep, *, trigger):
        commands.append((beep, trigger))
        return {'trigger': trigger, 'output': 'injected command only'}
    monkeypatch.setattr('psychophysics_lab.core.tone.request_beep', request)
    event = {}
    assert display.play_phase(WaitForKey('ready', key='SPACE', beep=Beep()), event) is None
    assert [trigger for _, trigger in commands] == ['accepted_readiness']
    assert event['audio']['trigger'] == 'accepted_readiness'


def test_first_trial_flip_finishes_session_dwell_in_final_provenance(monkeypatch, tmp_path):
    import json
    from psychophysics_lab.researcher import RunContext, WaitForKey
    from psychophysics_lab.experiments._internal.registry import get_experiment
    from psychophysics_lab.config.stimulus_parameters import resolve_stimuli
    from dataclasses import replace
    from pathlib import Path
    display, _, handlers = fake_presentation(monkeypatch)
    display.metadata = {'physical_display_used': False, 'test_backend': 'injected software window'}
    clock = {'now': 0.}
    monkeypatch.setattr('psychophysics_lab.core.presentation.time.perf_counter', lambda: clock['now'])
    def dispatch():
        clock['now'] += .01
        kind = getattr(display, '_last_visual_event', {}).get('kind')
        if kind in {'key_wait','response'}:
            handlers['on_key_press']('SPACE' if kind == 'key_wait' else 'LEFT', 0)
    display.window.dispatch_events = dispatch
    monkeypatch.setattr('psychophysics_lab.core.presentation.Presentation', lambda *a, **kw: display)
    display.window.close = lambda: None
    spec = replace(get_experiment('contrast_sensitivity'), session_start=[
        WaitForKey('ready', key='SPACE', slot='fixation'), Show('settle', slot='fixation', duration=1)])
    values = spec.normalise_values({'fixation_ms':1, 'grating_ms':1})
    root = Path(__file__).resolve().parents[1]
    context = RunContext(values, display.profile, spec, tmp_path, data_kind='uncalibrated_presentation_test',
                         stimulus_snapshots=resolve_stimuli(spec, values, repo_root=root))
    try:
        context.initialise(expected_trials=1, resolution={'task':'software timing boundary regression'})
        path = tmp_path/'session_events.json'
        assert 'next_flip_s' not in json.loads(path.read_text())['events'][-1]
        context.play_trial([Show('fixation', slot='fixation', duration=1),
                            CollectResponse(actions=('left','right'), slot='fixation')], target=0, condition=2)
        assert context._session_trace['events'][-1]['actual_display_duration_s'] > 0
    finally:
        context.close()
    last = json.loads(path.read_text())['events'][-1]
    assert last['next_flip_s'] == last['software_onset_s'] + last['actual_display_duration_s']


@pytest.mark.parametrize('abort_next_trial', [False, True])
def test_native_trial_summaries_match_durable_boundary(monkeypatch, tmp_path, abort_next_trial):
    """Real phase player may finish a previous screen's dwell on the next trial."""
    import json
    from pathlib import Path
    from dataclasses import replace
    from psychophysics_lab.researcher import RunContext, ParticipantAbort
    from psychophysics_lab.config.stimulus_parameters import resolve_stimuli
    from psychophysics_lab.experiments._internal.registry import get_experiment
    display, _, handlers = fake_presentation(monkeypatch)
    display.metadata = {'physical_display_used': False, 'test_backend': 'injected native phase player'}
    clock = {'now': 0.}
    monkeypatch.setattr('psychophysics_lab.core.presentation.time.perf_counter', lambda: clock['now'])
    def dispatch():
        clock['now'] += .01
        if getattr(display, '_last_visual_event', {}).get('kind') == 'response':
            display.held.discard('LEFT')  # injected key release before a fresh answer
            handlers['on_key_press']('LEFT', 0)
    display.window.dispatch_events = dispatch
    display.window.close = lambda: None
    monkeypatch.setattr('psychophysics_lab.core.presentation.Presentation', lambda *a, **kw: display)
    spec = replace(get_experiment('contrast_sensitivity'), session_start=[])
    values = spec.normalise_values({'fixation_ms': 1, 'grating_ms': 1})
    context = RunContext(values, display.profile, spec, tmp_path,
        data_kind='uncalibrated_presentation_test',
        stimulus_snapshots=resolve_stimuli(spec, values, repo_root=Path(__file__).resolve().parents[1]))
    try:
        context.initialise(expected_trials=3 if abort_next_trial else 2, resolution={'task': 'native journal ownership regression'})
        for _ in range(2):
            context.play_trial([Show('fixation', slot='fixation', duration=1),
                CollectResponse(actions=('left', 'right'), slot='fixation')], target=0, condition=2)
        if abort_next_trial:
            display.window.has_exit = True
            with pytest.raises(ParticipantAbort):
                context.play_trial([Show('fixation', slot='fixation', duration=1),
                    CollectResponse(actions=('left', 'right'), slot='fixation')], target=0, condition=2)
        else:
            context.complete()
    finally:
        context.close()
    records = [json.loads(line) for line in (tmp_path/'trial_events.jsonl').read_text().splitlines()]
    assert json.loads((tmp_path/'trial_actions.json').read_text())['trials'] == [r['trial'] for r in records]
    assert json.loads((tmp_path/'trial_presentations.json').read_text())['trials'] == [r['presentation'] for r in records if r['presentation'] is not None]
    assert context.accepted_trials == 2
    assert all(r['presentation']['phase_events'][0]['actual_display_duration_s'] > 0
               for r in records if r['presentation'] is not None)
