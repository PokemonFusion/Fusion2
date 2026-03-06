"""Tests for typed callback registry compatibility resolution."""

from pokemon.battle.registry import CallbackRegistry


class _StubCallbacks:
    class Demo:
        def run(self):
            return "ok"



def test_registry_resolves_string_reference_once():
    registry = CallbackRegistry()
    cb = registry.register("demo", "Demo.run", registry=_StubCallbacks)

    assert cb is not None
    assert callable(cb)
    assert registry.get("demo") is cb
    assert cb() == "ok"


def test_registry_rejects_invalid_string_reference():
    registry = CallbackRegistry()

    cb = registry.register("bad", "NoSeparator", registry=_StubCallbacks)

    assert cb is None
    assert registry.get("bad") is None
