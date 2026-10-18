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
