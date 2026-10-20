"""Native Terapagos transition, ability timing and reversible live state."""

import random

import pytest

from pokemon.battle.battledata import Move, Pokemon
from pokemon.battle.damage import stab_multiplier, type_effectiveness
from pokemon.battle.engine import Action, ActionType, Battle, BattleMove, BattleParticipant, BattleType
from pokemon.battle.native_forms import NativeBattleForm
from pokemon.battle.terastallization import Terastallization
from pokemon.dex.entities import Stats
from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats


def battler(species, ability, moves=("Splash", "Tera Starstorm"), **kwargs):
    """Build a calculated battler with the real species and move definitions."""
    mon = Pokemon(species, level=50, ability=ability, moves=[Move(name) for name in moves], **kwargs)
    mon.max_hp = get_max_hp(mon)
    mon.hp = mon.max_hp
    mon.base_stats = Stats(**get_stats(mon))
    return mon


def encounter(species="Terapagos", ability="Tera Shift", **kwargs):
    """Start native entry hooks in a real, isolated PvP engine."""
    user = battler(species, ability, **kwargs)
    foe = battler("Mew", "Synchronize", moves=("Splash",))
    a = BattleParticipant("Player", [user], team="A")
    b = BattleParticipant("Foe", [foe], team="B")
    a.active, b.active = [user], [foe]
    battle = Battle(BattleType.PVP, [a, b], rng=random.Random(19))
    battle.tera_used, battle.tera_pending = set(), {}
    battle.start_turn()
    return battle, user, foe


def commit(battle, user):
    """Reserve and commit the next real move, consuming the side once."""
    owner = battle.participants[0]
    tera = Terastallization.reserve(battle, owner, user)
    assert Terastallization.activate(battle, owner, user, tera)


@pytest.mark.parametrize("weather,terrain", [
    ("RainDance", "ElectricTerrain"), ("SunnyDay", "GrassyTerrain"),
    ("Sandstorm", "MistyTerrain"), ("Snow", "PsychicTerrain"),
    ("PrimordialSea", None), (None, "ElectricTerrain"), (None, None),
])
def test_native_stellar_commits_then_clears_only_weather_and_terrain(weather, terrain):
    """Teraform Zero runs at successful Tera, after the new ability is installed."""
    battle, user, _ = encounter(tera_type="Fire")
    assert user.species == "Terapagos-Terastal"
    assert battle.setWeather(weather, source=user) if weather else True
    assert battle.setTerrain(terrain, source=user) if terrain else True
    battle.field.pseudo_weather["trickroom"] = {"duration": 3}
    field = (battle.field.weather, battle.field.terrain)
    maximum = user.max_hp
    user.hp -= 23
    tera = Terastallization.reserve(battle, battle.participants[0], user)
    assert tera == "Stellar" and user.species == "Terapagos-Terastal"
    assert (battle.field.weather, battle.field.terrain) == field
    assert not battle.tera_used
    assert Terastallization.activate(battle, battle.participants[0], user, tera)
    assert user.species == "Terapagos-Stellar" and user.terastallized == "Stellar"
    assert str(getattr(user.ability, "name", user.ability)).replace(" ", "").lower() == "teraformzero"
    assert user.max_hp == get_max_hp(user) > maximum
    assert user.max_hp - user.hp == 23
    assert user.base_stats.special_attack == get_stats(user)["special_attack"]
    assert user.types == ["Normal"]
    assert not battle.field.weather and not battle.field.terrain
    assert list(battle.field.pseudo_weather) == ["trickroom"]
    assert battle.tera_used == {"A"} and not battle.tera_pending
    with pytest.raises(ValueError, match="already Terastallized"):
        Terastallization.reserve(battle, battle.participants[0], user)
    assert battle.setWeather("RainDance", source=user)
    assert battle.setTerrain("ElectricTerrain", source=user)
    battle.start_turn()
    battle.on_switch_out(user)
    battle.on_enter_battle(user)
    assert battle.field.weather == "raindance" and battle.field.terrain == "electricterrain"
    assert user.species == "Terapagos-Stellar"


@pytest.mark.parametrize("species,ability", [
    ("Terapagos", "No Ability"), ("Terapagos-Stellar", "Teraform Zero"),
    ("Ogerpon-Teal-Tera", "Embody Aspect (Teal)"), ("Ogerpon-Wellspring", "Water Absorb"),
])
def test_unsupported_forms_still_reject_without_side_effects(species, ability):
    """Opening the native Terastal transition does not open other form gates."""
    battle, user, _ = encounter(species, ability)
    battle.setWeather("RainDance", source=user)
    with pytest.raises(ValueError):
        Terastallization.reserve(battle, battle.participants[0], user)
    assert not battle.tera_used and not battle.tera_pending
    assert not user.terastallized and battle.field.weather == "raindance"


@pytest.mark.parametrize("invalid", ["fainted", "transformed", "spent", "wrong_type", "switched"])
def test_invalid_commit_does_not_transform_or_clear(invalid):
    """A failed/cancelled declaration cannot pay HP, change form or clear fields."""
    battle, user, foe = encounter()
    battle.setWeather("RainDance", source=foe)
    battle.setTerrain("ElectricTerrain", source=foe)
    tera = Terastallization.reserve(battle, battle.participants[0], user)
    if invalid == "fainted":
        user.hp = 0
    elif invalid == "transformed":
        user.transformed = True
    elif invalid == "spent":
        battle.tera_used.add("A")
    elif invalid == "wrong_type":
        tera = "Fire"
    else:
        battle.participants[0].active = []
    maximum = user.max_hp
    assert not Terastallization.activate(battle, battle.participants[0], user, tera)
    assert user.species == "Terapagos-Terastal" and not user.terastallized
    assert user.max_hp == maximum
    assert battle.field.weather == "raindance" and battle.field.terrain == "electricterrain"


@pytest.mark.parametrize("suppressed", [False, True])
def test_only_the_active_native_stellar_holder_clears(suppressed):
    """Copied abilities and suppressed Teraform Zero do not erase the field."""
    battle, user, foe = encounter("Mew", "Teraform Zero", tera_type="Stellar")
    battle.setWeather("RainDance", source=foe)
    commit(battle, user)
    assert battle.field.weather == "raindance"
    battle, user, foe = encounter()
    user.ability_suppressed = suppressed
    battle.setWeather("RainDance", source=foe)
    commit(battle, user)
    assert bool(battle.field.weather) is suppressed


def test_stellar_checkpoint_and_cleanup_preserve_identity_damage_and_budget():
    """A checkpoint retains the form; final cleanup restores only runtime state."""
    battle, user, _ = encounter()
    commit(battle, user)
    user.hp -= 17
    state = user.to_dict()
    restored = Pokemon.from_dict(state)
    assert restored.species == "Terapagos-Stellar" and restored.terastallized == "Stellar"
    assert restored.max_hp == user.max_hp and restored.hp == user.hp
    assert restored.base_species == "Terapagos"
    battle.participants[0].pokemons = battle.participants[0].active = [restored]
    battle.restore_transforms()
    assert restored.species == "Terapagos" and restored.types == ["Normal"]
    assert not restored.terastallized and not restored.stellar_boosted_types
    assert restored.max_hp == get_max_hp(restored)
    assert restored.max_hp - restored.hp == 17
    assert battle.tera_used == {"A"}


def test_real_roster_checkpoint_retains_native_form_stats_and_single_side_budget():
    """Reconstruct the production roster/position state after the new transition."""
    from pokemon.battle.battledata import BattleData, Team, TurnData
    from pokemon.battle.logic import BattleLogic
    from pokemon.battle.state import BattleState

    battle, user, foe = encounter()
    data = BattleData(Team("Player", [user]), Team("Foe", [foe]))
    data.turndata = TurnData(data.teams, teamslots=1)
    state = BattleState.from_battle_data(data, ai_type="PVP")
    logic = BattleLogic(battle, data, state)
    commit(battle, user)
    user.hp -= 11
    battle.setWeather("RainDance", source=foe)
    restored = BattleLogic.from_dict(logic.to_dict())
    mon = restored.battle.participants[0].active[0]
    assert mon.species == "Terapagos-Stellar" and mon.terastallized == "Stellar"
    assert mon.max_hp == get_max_hp(mon) and mon.hp == user.hp
    assert mon.base_stats.special_attack == get_stats(mon)["special_attack"]
    assert restored.battle.tera_used == {"A"} and restored.battle.field.weather == "raindance"
    restored.battle.on_enter_battle(mon)
    assert restored.battle.field.weather == "raindance"
    with pytest.raises(ValueError):
        Terastallization.reserve(restored.battle, restored.battle.participants[0], mon)
    restored.battle.restore_transforms()
    assert mon.species == "Terapagos" and mon.max_hp - mon.hp == 11


def test_repeated_stellar_boosts_and_terastal_starstorm_rules():
    """Terapagos keeps Stellar boosts; Terastal Starstorm remains Normal."""
    battle, user, foe = encounter()
    move = BattleMove("Tera Starstorm")
    battle.use_move(Action(battle.participants[0], ActionType.MOVE, battle.participants[1],
                           move=move, pokemon=user, target_pokemon=foe))
    assert move.type == "Normal" and move.raw["target"] == "normal"
    commit(battle, user)
    for name, move_type, multiplier in (("Tackle", "Normal", 2), ("Water Gun", "Water", 4915 / 4096)):
        for _ in range(3):
            assert stab_multiplier(user, BattleMove(name, type=move_type), consume=True) == multiplier
        assert not user.stellar_boosted_types
    assert type_effectiveness(user, BattleMove("Karate Chop", type="Fighting")) == 2
    assert type_effectiveness(user, BattleMove("Lick", type="Ghost")) == 0


@pytest.mark.parametrize("physical", [False, True])
def test_stellar_starstorm_hits_both_foes_and_preserves_dex(physical):
    """The native signature becomes Stellar spread and uses the stronger offense."""
    battle, user, foe = encounter()
    other = battler("Blissey", "Natural Cure", moves=("Splash",))
    ally = battler("Blissey", "Natural Cure", moves=("Splash",))
    battle.participants[0].pokemons.append(ally)
    battle.participants[0].active.append(ally)
    battle.participants[1].pokemons.append(other)
    battle.participants[1].active.append(other)
    for mon in (other, ally):
        mon.battle = battle
    commit(battle, user)
    if physical:
        user.boosts["attack"] = 6
    before = [mon.hp for mon in (foe, other, ally)]
    move = BattleMove("Tera Starstorm")
    battle.use_move(Action(battle.participants[0], ActionType.MOVE, battle.participants[1],
                           move=move, pokemon=user, target_pokemon=foe))
    assert move.type == "Stellar" and move.raw["target"] == "allAdjacentFoes"
    assert move.category == ("Physical" if physical else "Special")
    assert foe.hp < before[0] and other.hp < before[1] and ally.hp == before[2]
    assert not user.stellar_boosted_types
    from pokemon.dex import MOVEDEX
    from pokemon.battle._shared import get_raw

    raw = get_raw(MOVEDEX["Terastarstorm"])
    assert raw["type"] == "Normal" and raw["target"] == "normal"
