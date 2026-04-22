"""Tests for side and field lifecycle hooks routed through the event core."""

from __future__ import annotations

from pokemon.dex.functions import conditions_funcs as cond_mod

from .helpers import build_battle, load_modules


class _AbilityRecorder:
    def __init__(self):
        self.calls: list[tuple[str, object]] = []

    def call(self, func: str, *args, **kwargs):
        self.calls.append((func, kwargs.get("relayVar", None)))
        return None


def test_side_condition_start_notifies_allied_active_ability():
    modules = load_modules()
    Pokemon = modules["Pokemon"]
    battle, attacker, _ = build_battle()
    ally = Pokemon("Ally", level=50, hp=200, max_hp=200)
    ally.base_stats = attacker.base_stats
    ally.types = ["Normal"]
    ally.boosts = dict(attacker.boosts)
    ally.side = battle.participants[0].side
    ally.battle = battle
    recorder = _AbilityRecorder()
    ally.ability = recorder
    ally.ability_state = battle.init_effect_state(recorder, target=ally)
    battle.participants[0].pokemons.append(ally)
    battle.participants[0].active.append(ally)

    battle.add_side_condition(
        battle.participants[0],
        "tailwind",
        {"onSideStart": None},
        source=attacker,
    )

    assert ("onAllySideConditionStart", "tailwind") in recorder.calls


def test_remove_side_condition_runs_side_end_hook(monkeypatch):
    class DummyBarrier:
        ended = 0

        def onSideEnd(self, side, *args, **kwargs):
            type(self).ended += 1
            return True

    monkeypatch.setattr(cond_mod, "Dummybarrier", DummyBarrier, raising=False)

    battle, attacker, _ = build_battle()
    battle.add_side_condition(
        battle.participants[0],
        "dummybarrier",
        {"onSideStart": None},
        source=attacker,
    )

    removed = battle.remove_side_condition(battle.participants[0], "dummybarrier")

    assert removed is True
    assert DummyBarrier.ended == 1


def test_weather_and_terrain_change_notify_active_abilities():
    battle, attacker, _ = build_battle()
    recorder = _AbilityRecorder()
    attacker.ability = recorder
    attacker.ability_state = battle.init_effect_state(recorder, target=attacker)

    assert battle.setWeather("sandstorm", source=attacker) is True
    assert battle.setTerrain("electricterrain", source=attacker) is True

    hook_names = [name for name, _ in recorder.calls]
    assert "onWeatherChange" in hook_names
    assert "onTerrainChange" in hook_names


def test_pseudo_weather_change_notifies_active_abilities(monkeypatch):
    class DummyRoom:
        def onFieldStart(self, field, *args, **kwargs):
            return True

        def onFieldEnd(self, field, *args, **kwargs):
            return True

    monkeypatch.setattr(cond_mod, "Dummyroom", DummyRoom, raising=False)

    battle, attacker, _ = build_battle()
    recorder = _AbilityRecorder()
    attacker.ability = recorder
    attacker.ability_state = battle.init_effect_state(recorder, target=attacker)

    assert battle.add_pseudo_weather("dummyroom", source=attacker) is True
    assert battle.remove_pseudo_weather("dummyroom") is True

    hook_names = [name for name, _ in recorder.calls]
    assert "onAnyPseudoWeatherChange" in hook_names
