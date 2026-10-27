"""A pause must observe the current mounted screen after queued navigation."""
import asyncio
from types import SimpleNamespace

from textual.pilot import Pilot
from conftest import wait_for_textual_mounts


def test_pause_does_not_return_for_the_previous_screen(monkeypatch):
    child=SimpleNamespace(is_mounted=True)
    old=SimpleNamespace(is_mounted=True,query=lambda _: [child])
    new=SimpleNamespace(is_mounted=False,query=lambda _: [child])
    class App:
        screen_stack=[old]
        @property
        def screen(self):
            return self.screen_stack[-1]
    app=App();calls=[]
    async def queued_pause(pilot,delay=None):
        calls.append(delay)
        if len(calls)==2:
            app.screen_stack=[new]  # navigation during the settling await
        elif len(calls)==3:
            new.is_mounted=True
    monkeypatch.setattr(Pilot,"pause",queued_pause)
    wait_for_textual_mounts.__wrapped__(monkeypatch)
    asyncio.run(Pilot.pause(SimpleNamespace(app=app)))
    assert app.screen is new and new.is_mounted


def test_pause_rechecks_children_added_during_settling(monkeypatch):
    children=[SimpleNamespace(is_mounted=True)]
    screen=SimpleNamespace(is_mounted=True,query=lambda _: list(children))
    app=SimpleNamespace(screen=screen,screen_stack=[screen]);calls=[]
    async def queued_pause(pilot,delay=None):
        calls.append(delay)
        if len(calls)==2:
            children.append(SimpleNamespace(is_mounted=False))
        elif len(calls)==3:
            children[-1].is_mounted=True
    monkeypatch.setattr(Pilot,"pause",queued_pause)
    wait_for_textual_mounts.__wrapped__(monkeypatch)
    asyncio.run(Pilot.pause(SimpleNamespace(app=app)))
    assert len(children)==2 and all(child.is_mounted for child in children)
