"""Tests for event dispatcher error reporting and callback fallback behavior."""

from pokemon.battle import events
from pokemon.battle.events import EventDispatcher


def test_dispatcher_reports_event_and_handler_identity_on_failure(monkeypatch):
    monkeypatch.setattr(events, "handle_battle_exception", lambda **kwargs: kwargs)

    dispatcher = EventDispatcher()

    def broken_handler(*, pokemon):
        raise RuntimeError("boom")

    dispatcher.register("start", broken_handler)
    failures = dispatcher.dispatch("start", pokemon=object(), battle=None)

    assert len(failures) == 1
    failure = failures[0]
    assert failure["event"] == "start"
    assert failure["extra"]["event_name"] == "start"
    assert failure["extra"]["handler"].endswith("broken_handler")


def test_dispatcher_does_not_fallback_call_without_opt_in(monkeypatch):
    monkeypatch.setattr(events, "handle_battle_exception", lambda **kwargs: kwargs)

    dispatcher = EventDispatcher(allow_arity_fallback=False)
    calls = {"count": 0}

    def kwargs_handler(**kwargs):
        if kwargs:
            raise TypeError("reject kwargs")
        calls["count"] += 1

    dispatcher.register("update", kwargs_handler)
    failures = dispatcher.dispatch("update", pokemon=object(), battle=None)

    assert calls["count"] == 0
    assert len(failures) == 1


def test_dispatcher_can_fallback_call_when_enabled(monkeypatch):
    monkeypatch.setattr(events, "handle_battle_exception", lambda **kwargs: kwargs)

    dispatcher = EventDispatcher(allow_arity_fallback=True)
    calls = {"count": 0}

    def kwargs_handler(**kwargs):
        if kwargs:
            raise TypeError("reject kwargs")
        calls["count"] += 1

    dispatcher.register("update", kwargs_handler)
    failures = dispatcher.dispatch("update", pokemon=object(), battle=None)

    assert calls["count"] == 1
    assert failures == []
