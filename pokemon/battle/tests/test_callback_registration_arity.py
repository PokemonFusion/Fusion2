"""Tests for callback registration arity compatibility in battle startup hooks."""

from .helpers import build_battle


class _ItemWithSingleArgStart:
    """Item-like object exposing a one-argument ``onStart`` callback."""

    def __init__(self, calls):
        self.raw = {"onStart": self.on_start}
        self._calls = calls

    def on_start(self, pokemon):
        self._calls.append(pokemon)


def test_register_callbacks_supports_single_arg_callback():
    """Battle startup should still run single-argument callbacks."""

    battle, attacker, _ = build_battle()
    calls = []
    attacker.item = _ItemWithSingleArgStart(calls)

    battle.on_enter_battle(attacker)

    assert calls == [attacker]
