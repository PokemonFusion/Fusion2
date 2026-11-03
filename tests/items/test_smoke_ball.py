"""Normal run-action and canonical capture separation for a reusable held item."""

import pytest

from pokemon.battle.actions import Action, ActionType
from pokemon.battle.battledata import Pokemon
from pokemon.battle.effect_context import EffectContext
from pokemon.battle.engine import Battle, BattleParticipant, BattleType
from pokemon.items import get_gameplay_item, is_capture_ball
from pokemon.middleware import get_item_by_name


def encounter(*, item="Smoke Ball", ability="Sturdy", trap="Arena Trap"):
    """Build a deliberately slow native holder against a faster trapping foe."""
    runner = Pokemon("Shuckle", level=20, ability=ability, item=item)
    foe = Pokemon("Dugtrio", level=50, ability=trap)
    own, wild = BattleParticipant("Player", [runner]), BattleParticipant("Wild", [foe])
    own.active, wild.active = [runner], [foe]
    battle = Battle(BattleType.WILD, [own, wild])
    return battle, runner, foe, Action(own, ActionType.RUN, pokemon=runner)


@pytest.mark.parametrize("query", ["Smoke Ball", "smokeball", "SMOKE-BALL"])
def test_definition_resolves_completely_and_is_explicitly_not_a_capture_ball(query):
    item = get_gameplay_item(query)
    assert get_item_by_name(query)[1] is item
    assert item.name == "Smoke Ball"
    assert item.price == 4000 and item.category == "Held Items"
    assert item.raw["isPokeball"] is False and item.raw["consumed"] is False
    assert "+flee" in item.desc
    assert not is_capture_ball(query)


@pytest.mark.parametrize("query", ["Smoke", "Smok", "Made Up Ball", "Iron Ball", "Light Ball", "Air Balloon"])
def test_capture_classifier_rejects_non_capture_and_partial_names(query):
    assert not is_capture_ball(query)


@pytest.mark.parametrize("query", ["Poke Ball", "pokeball", "Great Ball", "Master Ball", "Beast Ball", "Cherish Ball"])
def test_existing_real_capture_metadata_still_selects_capture(query):
    assert is_capture_ball(query)


@pytest.mark.parametrize("trap", ["Arena Trap", "Shadow Tag", "Magnet Pull"])
def test_actual_run_action_guarantees_escape_from_trapping_without_consumption(trap):
    battle, holder, _, action = encounter(trap=trap)
    holder.types = ["Steel"]
    battle.execute_actions([action])
    assert battle.battle_over and battle._flee_result["reason"] == "smokeball"
    assert EffectContext.key(holder.item) == "smokeball"
    result = dict(battle._flee_result)
    assert not battle.attempt_flee(action)
    assert battle._flee_result == result


@pytest.mark.parametrize("suppression", ["flag", "klutz", "magicroom", "embargo", "removed"])
def test_suppressed_or_removed_smoke_ball_leaves_normal_trapping_in_force(suppression):
    battle, holder, _, action = encounter()
    if suppression == "flag":
        holder.item_suppressed = True
    elif suppression == "klutz":
        holder.ability = "Klutz"
    elif suppression == "magicroom":
        battle.field.pseudo_weather["magicroom"] = {"duration": 5}
    elif suppression == "embargo":
        holder.volatiles["embargo"] = {"duration": 5}
    else:
        holder.item = ""
    battle.execute_actions([action])
    assert not battle.battle_over
    assert battle._flee_result["reason"] == "trapped"


def test_suppressing_klutz_reactivates_the_held_item_and_both_flags_reload():
    battle, holder, _, action = encounter(ability="Klutz")
    holder.ability_suppressed = True
    restored = Pokemon.from_dict(holder.to_dict())
    assert restored.ability_suppressed
    assert EffectContext.key(EffectContext.item(restored)) == "smokeball"
    holder.item_suppressed = True
    restored = Pokemon.from_dict(holder.to_dict())
    assert restored.item_suppressed and EffectContext.item(restored) is None
    holder.item_suppressed = False
    battle.execute_actions([action])
    assert battle._flee_result["reason"] == "smokeball"


@pytest.mark.parametrize("restricted", [BattleType.TRAINER, BattleType.PVP, BattleType.SCRIPTED,
                                        "trainer", "script", "unknown_policy"])
def test_encounter_restrictions_precede_item_and_run_away(restricted):
    battle, _, _, action = encounter(ability="Run Away")
    if restricted in (BattleType.TRAINER, BattleType.PVP, BattleType.SCRIPTED, "trainer"):
        battle.type = restricted
    else:
        battle.flee_allowed = False if restricted == "script" else None
    battle.execute_actions([action])
    assert not battle.battle_over and battle._flee_result["reason"] == "restricted"


@pytest.mark.parametrize("location", ["bench", "foe", "ally"])
def test_another_holders_item_cannot_supply_the_acting_pokemon(location):
    battle, holder, foe, action = encounter(item="")
    other = Pokemon("Shuckle", item="Smoke Ball")
    if location == "foe":
        foe.item = "Smoke Ball"
    elif location == "bench":
        action.actor.pokemons.append(other)
    else:
        ally = BattleParticipant("Ally", [other])
        ally.active = [other]
        battle.participants.append(ally)
    battle.execute_actions([action])
    assert not battle.battle_over and battle._flee_result["reason"] == "trapped"


@pytest.mark.parametrize("invalid", ["foreign", "bench", "fainted"])
def test_invalid_actor_cannot_run_using_another_or_inactive_item(invalid):
    battle, holder, foe, action = encounter()
    if invalid == "foreign":
        foe.item = "Smoke Ball"
        action.pokemon = foe
    elif invalid == "bench":
        extra = Pokemon("Shuckle", item="Smoke Ball")
        action.actor.pokemons.append(extra)
        action.pokemon = extra
    else:
        holder.hp = 0
    battle.execute_actions([action])
    assert not battle.battle_over and battle._flee_result["reason"] == "invalid"


def test_direct_item_dispatch_cannot_turn_smoke_ball_into_a_capture():
    battle, holder, _, run = encounter()
    run.actor.has_item = lambda *args: True
    debits = []
    run.actor.remove_item = lambda name: debits.append(name) or True
    action = Action(run.actor, ActionType.ITEM, battle.participants[1], item="Smoke Ball", pokemon=holder)
    battle.execute_item(action)
    assert not debits and not getattr(battle, "capture_succeeded", False)
    assert not getattr(action, "item_executed", False)
