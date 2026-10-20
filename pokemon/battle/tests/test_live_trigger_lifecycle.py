"""Fresh live trigger failures and their relevant mechanics negatives."""

import logging
import random

import pytest

from .helpers import build_battle, load_modules


@pytest.fixture(autouse=True)
def quiet_offline_battle_log():
    """Keep isolated diagnostics out of the running game's battle log."""
    logger = logging.getLogger("battle")
    disabled = logger.disabled
    logger.disabled = True
    yield
    logger.disabled = disabled


def use(battle, user, target, name):
    """Execute a real move and retain swallowed callback failures as failures."""
    from pokemon.battle.actions import Action, ActionType

    battle.rng = random.Random(0)
    move = load_modules()["BattleMove"](name)
    battle.use_move(Action(battle.participant_for(user), ActionType.MOVE,
                           battle.participant_for(target), move, pokemon=user))
    assert not getattr(battle, "_callback_failures", [])
    return move


def carrier(ability, species):
    """Give a synthetic, fully isolated carrier the actual form family."""
    battle, pokemon, foe = build_battle(attacker_ability=ability)
    pokemon.name = pokemon.species = pokemon.base_species = species
    pokemon.types = pokemon._lookup_species_types() or pokemon.types
    return battle, pokemon, foe


def opponent_reserve(battle):
    """Keep a knockout fixture in battle so AfterFaint bonuses can activate."""
    participant = battle.participants[1]
    reserve = load_modules()["Pokemon"]("Magikarp")
    reserve.battle = battle
    reserve.side = participant.side
    participant.pokemons.append(reserve)
    return reserve


@pytest.mark.parametrize("ability,stat", [("Moxie", "attack"), ("Chilling Neigh", "attack"),
                                         ("Grim Neigh", "special_attack"),
                                         ("As One (Glastrier)", "attack"),
                                         ("As One (Spectrier)", "special_attack")])
def test_actual_direct_knockout_dispatches_the_source_faint_trigger_once(ability, stat):
    battle, user, target = build_battle(attacker_ability=ability)
    opponent_reserve(battle)
    target.hp = 1
    use(battle, user, target, "Tackle")
    battle.run_faint()
    assert user.boosts[stat] == 1
    battle.run_faint()
    assert user.boosts[stat] == 1


def test_an_earlier_nonfatal_attack_does_not_get_credit_for_later_indirect_fainting():
    battle, user, target = build_battle(attacker_ability="Moxie")
    opponent_reserve(battle)
    use(battle, user, target, "Tackle")
    assert target.hp > 0
    target.hp = 0
    battle.run_faint()
    assert user.boosts["attack"] == 0


def test_a_source_that_fainted_from_recoil_does_not_get_the_knockout_bonus():
    battle, user, target = build_battle(attacker_ability="Moxie")
    opponent_reserve(battle)
    target.hp = 1
    use(battle, user, target, "Tackle")
    user.hp = 0
    battle.run_faint()
    assert user.boosts["attack"] == 0


def test_beast_boost_selects_a_real_non_hp_stat_with_canonical_tie_order():
    battle, user, target = build_battle(attacker_ability="Beast Boost")
    opponent_reserve(battle)
    user.base_stats.hp = 999
    user.base_stats.special_defense = 200
    target.hp = 1
    use(battle, user, target, "Tackle")
    battle.run_faint()
    assert user.boosts["special_defense"] == 1
    user.base_stats.attack = 200
    assert user.getBestStat(True, True) == "atk"


@pytest.mark.parametrize("ability", ["Moxie", "Beast Boost", "Chilling Neigh", "Grim Neigh",
                                   "As One (Glastrier)", "As One (Spectrier)"])
def test_final_knockout_does_not_dispatch_a_post_battle_source_bonus(ability):
    battle, user, target = build_battle(attacker_ability=ability)
    target.hp = 1
    use(battle, user, target, "Tackle")
    battle.run_faint()
    assert target.hp == 0 and battle.participants[1].has_lost
    assert all(value == 0 for value in user.boosts.values())


@pytest.mark.parametrize("ability", ["Dazzling", "Queenly Majesty", "Armor Tail"])
def test_priority_immunity_still_spends_the_attacking_moves_pp(ability):
    battle, user, target = build_battle(defender_ability=ability)
    move = load_modules()["Move"]("Quick Attack")
    move.pp = 30
    user.moves = [move]
    use(battle, user, target, "Quick Attack")
    assert target.hp == target.max_hp
    assert move.pp == 29


@pytest.mark.parametrize("ability", ["Dazzling", "Queenly Majesty", "Armor Tail"])
def test_priority_immunity_does_not_block_an_ordinary_attack(ability):
    battle, user, target = build_battle(defender_ability=ability)
    use(battle, user, target, "Tackle")
    assert target.hp < target.max_hp


@pytest.mark.parametrize("ability,species,weather,form", [
    ("Forecast", "Castform", "sunnyday", "Castform-Sunny"),
    ("Forecast", "Castform", "raindance", "Castform-Rainy"),
    ("Forecast", "Castform", "snow", "Castform-Snowy"),
    ("Flower Gift", "Cherrim", "sunnyday", "Cherrim-Sunshine"),
])
def test_real_weather_change_dispatch_reaches_the_form_holder(ability, species, weather, form):
    battle, user, target = carrier(ability, species)
    assert battle.setWeather(weather, target)
    assert str(user.species) == form
    assert not getattr(battle, "_callback_failures", [])
    battle.clearWeather()
    assert str(user.species) == species


def test_zero_to_hero_changes_the_departing_palafin_and_keeps_the_form_on_return():
    battle, user, target = carrier("Zero to Hero", "Palafin")
    battle.on_switch_out(user)
    assert str(user.species) == "Palafin-Hero"
    battle.on_enter_battle(user)
    assert str(user.species) == "Palafin-Hero"


@pytest.mark.parametrize("ability,species", [("Protean", "Greninja"), ("Libero", "Cinderace")])
def test_prepare_hit_type_change_is_once_per_entry_and_persists_in_checkpoint_state(ability, species):
    battle, user, target = carrier(ability, species)
    use(battle, user, target, "Tackle")
    assert user.types == ["Normal"]
    restored = load_modules()["Pokemon"].from_dict(user.to_dict())
    assert restored.ability_state.get("type_change_used") is True
    modules = load_modules()
    restored_target = modules["Pokemon"]("Restored Foe", hp=200, max_hp=200)
    first, second = modules["BattleParticipant"]("A", [restored]), modules["BattleParticipant"]("B", [restored_target])
    first.active, second.active = [restored], [restored_target]
    resumed = modules["Battle"](modules["BattleType"].WILD, [first, second])
    assert restored.ability_state["target"] is restored
    use(resumed, restored, restored_target, "Water Gun")
    assert restored.types == ["Normal"]
    use(battle, user, target, "Water Gun")
    assert user.types == ["Normal"]
    battle.on_switch_out(user)
    battle.on_enter_battle(user)
    use(battle, user, target, "Water Gun")
    assert user.types == ["Water"]


@pytest.mark.parametrize("ability", ["Protean", "Libero"])
def test_type_change_abilities_preserve_tera_typing(ability):
    battle, user, target = build_battle(attacker_ability=ability, attacker_types=["Water"])
    user.terastallized = "Water"
    use(battle, user, target, "Tackle")
    assert user.types == ["Water"]


@pytest.mark.parametrize("ability", ["Protean", "Libero"])
def test_matching_type_does_not_spend_the_later_type_change_activation(ability):
    battle, user, target = build_battle(attacker_ability=ability, attacker_types=["Normal"])
    use(battle, user, target, "Tackle")
    assert not user.ability_state.get("type_change_used")
    use(battle, user, target, "Water Gun")
    assert user.types == ["Water"]


def flee(battle, user):
    """Issue the actual engine run action; chance remains a legal outcome."""
    from pokemon.battle.actions import Action, ActionType

    battle.rng = random.Random(0)
    battle.attempt_flee(Action(battle.participant_for(user), ActionType.RUN, pokemon=user))
    return battle._flee_result


@pytest.mark.parametrize("types,ability", [(["Flying"], "No Ability"), (["Steel"], "Levitate")])
def test_arena_trap_cannot_trap_an_airborne_escape(types, ability):
    battle, user, target = build_battle(attacker_types=types, attacker_ability=ability, defender_ability="Arena Trap")
    assert flee(battle, user)["reason"] != "trapped"


@pytest.mark.parametrize("trapper", ["Arena Trap", "Shadow Tag", "Magnet Pull"])
def test_ghosts_can_escape_trapping_abilities_even_when_also_steel(trapper):
    battle, user, target = build_battle(attacker_types=["Ghost", "Steel"], defender_ability=trapper)
    assert flee(battle, user)["reason"] != "trapped"


def test_shadow_tag_does_not_trap_another_shadow_tag_holder():
    battle, user, target = build_battle(attacker_ability="Shadow Tag", defender_ability="Shadow Tag")
    assert flee(battle, user)["reason"] != "trapped"


@pytest.mark.parametrize("trapper,types", [("Arena Trap", ["Normal"]), ("Shadow Tag", ["Normal"]), ("Magnet Pull", ["Steel"])])
def test_qualifying_grounded_or_steel_escape_remains_trapped(trapper, types):
    battle, user, target = build_battle(attacker_types=types, defender_ability=trapper)
    result = flee(battle, user)
    assert result["success"] is False and result["reason"] == "trapped"


def test_gravity_makes_a_flying_escape_qualify_for_arena_trap():
    battle, user, target = build_battle(attacker_types=["Flying"], defender_ability="Arena Trap")
    battle.field.pseudo_weather["gravity"] = {}
    assert flee(battle, user)["reason"] == "trapped"


@pytest.mark.parametrize("types,item,trapped", [(["Flying"], "Iron Ball", True),
                                               (["Normal"], "Air Balloon", False)])
def test_escape_grounding_observes_held_item_exceptions(types, item, trapped):
    battle, user, target = build_battle(attacker_types=types, defender_ability="Arena Trap")
    battle.set_item(user, item)
    assert (flee(battle, user)["reason"] == "trapped") is trapped


def test_a_suppressed_trapping_ability_does_not_block_escape():
    battle, user, target = build_battle(defender_ability="Arena Trap")
    target.ability_suppressed = True
    assert flee(battle, user)["reason"] != "trapped"


def test_run_away_remains_guaranteed_but_a_suppressed_run_away_does_not_bypass_trapping():
    battle, user, target = build_battle(attacker_ability="Run Away", defender_ability="Arena Trap")
    assert flee(battle, user)["reason"] == "runaway"
    battle.battle_over = False
    user.ability_suppressed = True
    assert flee(battle, user)["reason"] == "trapped"


def test_hospitality_heals_one_quarter_of_its_allys_max_hp():
    from pokemon.battle.engine import _resolve_ability

    battle, user, target = build_battle(attacker_ability="Hospitality")
    ally = load_modules()["Pokemon"]("Ally", hp=80, max_hp=200)
    part = battle.participant_for(user)
    part.pokemons.append(ally)
    part.active.append(ally)
    ally.battle, ally.side = battle, part.side
    battle.singleEvent("Start", _resolve_ability(user.ability), user.ability_state, user)
    assert ally.hp == 130


@pytest.mark.parametrize("hp,form,state", [(101, "Cramorant-Gulping", "gulping"), (100, "Cramorant-Gorging", "gorging")])
def test_gulp_missile_arms_its_own_holder_and_releases_the_correct_effect_once(hp, form, state):
    battle, user, target = carrier("Gulp Missile", "Cramorant")
    user.hp = hp
    use(battle, user, target, "Surf")
    assert str(user.species) == form
    assert "gulpmissile" not in target.volatiles
    previous = target.hp
    use(battle, target, user, "Tackle")
    assert target.hp == previous - target.max_hp // 4
    assert str(user.species) == "Cramorant"
    if state == "gulping":
        assert target.boosts["defense"] == -1
    else:
        assert target.status == "par"
    previous = target.hp
    use(battle, target, user, "Tackle")
    assert target.hp == previous


def test_gulp_missiles_indirect_damage_is_prevented_by_magic_guard():
    battle, user, target = carrier("Gulp Missile", "Cramorant")
    target.ability = "Magic Guard"
    use(battle, user, target, "Surf")
    previous = target.hp
    use(battle, target, user, "Tackle")
    assert target.hp == previous
    assert target.boosts["defense"] == -1


def test_gorging_paralysis_preserves_electric_type_immunity():
    battle, user, target = carrier("Gulp Missile", "Cramorant")
    user.hp = 100
    target.types = ["Electric"]
    use(battle, user, target, "Surf")
    use(battle, target, user, "Tackle")
    assert target.status != "par"
