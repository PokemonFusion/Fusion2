"""Field effects and highest-stat abilities must use persisted battle context."""

import logging

import pytest

from .helpers import build_battle, load_modules


@pytest.fixture(autouse=True)
def quiet_log():
    logger = logging.getLogger("battle")
    old = logger.disabled
    logger.disabled = True
    yield
    logger.disabled = old


@pytest.mark.parametrize("ability,kind,value", [("Protosynthesis", "weather", "sunnyday"), ("Quark Drive", "terrain", "electricterrain")])
def test_highest_stat_boost_uses_long_stat_names_and_survives_checkpoint(ability, kind, value):
    battle, user, target = build_battle(attacker_ability=ability)
    user.base_stats.attack = 200
    getattr(battle, "setWeather" if kind == "weather" else "setTerrain")(value, source=user)
    from pokemon.battle.effect_context import EffectContext
    effect = EffectContext.ability(user)
    assert effect.call("onModifyAtk", 100, pokemon=user) == 130
    restored = load_modules()["Pokemon"].from_dict(user.to_dict())
    restored.battle = battle
    assert effect.call("onModifyAtk", 100, pokemon=restored) == 130
    getattr(battle, "clearWeather" if kind == "weather" else "clearTerrain")()
    assert battle.runEvent("ModifyAtk", user, None, None, 100) == 100


@pytest.mark.parametrize("ability,field", [("Protosynthesis", "sunnyday"), ("Quark Drive", "electricterrain")])
def test_highest_speed_uses_the_speed_multiplier(ability, field):
    battle, user, target = build_battle(attacker_ability=ability)
    user.base_stats.speed = 240
    (battle.setWeather if ability == "Protosynthesis" else battle.setTerrain)(field, source=user)
    assert battle.runEvent("ModifySpe", user, None, None, 100) == 150


@pytest.mark.parametrize("ability", ["Protosynthesis", "Quark Drive"])
def test_booster_is_consumed_once_and_ends_when_the_holder_leaves(ability):
    from pokemon.battle.effect_context import EffectContext
    battle, user, target = build_battle(attacker_ability=ability)
    user.base_stats.attack = 200
    user.item = battle._coerce_item("boosterenergy")
    effect = EffectContext.ability(user)
    effect.call("onStart", pokemon=user)
    assert not user.item
    assert effect.call("onModifyAtk", 100, pokemon=user) == 130
    effect.call("onStart", pokemon=user)
    assert effect.call("onModifyAtk", 100, pokemon=user) == 130
    effect.call("onEnd", pokemon=user)
    assert battle.runEvent("ModifyAtk", user, None, None, 100) == 100


def test_mimicry_changes_and_restores_the_actual_field_type():
    battle, user, target = build_battle(attacker_ability="Mimicry", attacker_types=["Ground", "Steel"])
    assert battle.setTerrain("electricterrain", source=target)
    assert user.types == ["Electric"]
    battle.clearTerrain()
    assert user.types == ["Ground", "Steel"]


def test_surge_surfer_reads_field_terrain_and_stops_after_clear():
    battle, user, target = build_battle(attacker_ability="Surge Surfer")
    battle.setTerrain("electricterrain", source=target)
    assert battle.runEvent("ModifySpe", user, None, None, 100) == 200
    battle.clearTerrain()
    assert battle.runEvent("ModifySpe", user, None, None, 100) == 100


def test_hadron_engine_reads_field_terrain_for_special_attack():
    from pokemon.battle.effect_context import EffectContext
    battle, user, target = build_battle(attacker_ability="Hadron Engine")
    battle.setTerrain("electricterrain", source=target)
    assert EffectContext.ability(user).call("onModifySpA", 120, pokemon=user) == 160
    battle.clearTerrain()
    assert EffectContext.ability(user).call("onModifySpA", 120, pokemon=user) == 120


@pytest.mark.parametrize("ability,item", [("Multitype", "flameplate"), ("RKS System", "firememory")])
def test_initial_preassigned_active_gets_its_item_type(ability, item):
    battle, user, target = build_battle(attacker_ability=ability)
    user.item = battle._coerce_item(item)
    battle.start_turn()
    assert user.types == ["Fire"]
