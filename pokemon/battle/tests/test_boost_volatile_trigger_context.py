"""Live stat/volatile triggers must retain the actual move and opposing source."""

import random

import pytest

from .helpers import build_battle, load_modules


def move_action(battle, user, target, name):
    """Build an ordinary action from a named local dex move."""
    from pokemon.battle.actions import Action, ActionType

    return Action(battle.participant_for(user), ActionType.MOVE,
                  battle.participant_for(target), load_modules()["BattleMove"](name), pokemon=user)


def use(battle, user, target, name):
    """Use the real engine entry without forcing the callback outcome."""
    battle.rng = random.Random(0)
    action = move_action(battle, user, target, name)
    battle.use_move(action)
    assert not getattr(battle, "_callback_failures", [])
    return action.move


def stage(pokemon, short, long):
    """Read either supported stage spelling from independent battle state."""
    return pokemon.boosts.get(short, pokemon.boosts.get(long, 0))


def test_competitive_reacts_to_the_real_opponents_growl():
    battle, user, holder = build_battle(defender_ability="Competitive")
    use(battle, user, holder, "Growl")
    assert stage(holder, "atk", "attack") == -1
    assert stage(holder, "spa", "special_attack") == 2


def test_mirror_armor_reflects_the_drop_to_its_real_source():
    battle, user, holder = build_battle(defender_ability="Mirror Armor")
    use(battle, user, holder, "Growl")
    assert stage(holder, "atk", "attack") == 0
    assert stage(user, "atk", "attack") == -1


def test_defiant_does_not_react_to_its_own_shell_smash_drops():
    battle, user, target = build_battle(attacker_ability="Defiant")
    use(battle, user, user, "Shell Smash")
    assert stage(user, "atk", "attack") == 2
    assert stage(user, "def", "defense") == -1


def test_showdown_move_id_is_lowercase_while_the_legacy_dex_key_stays_usable():
    battle, user, holder = build_battle()
    selected = use(battle, user, holder, "Taunt")
    assert selected.id == "taunt"
    assert "taunt" in holder.volatiles


def test_oblivious_blocks_taunt_before_its_start_callback_runs():
    battle, user, holder = build_battle(defender_ability="Oblivious")
    use(battle, user, holder, "Taunt")
    assert "taunt" not in holder.volatiles


def test_aroma_veil_protects_its_own_holder_from_taunt():
    battle, user, holder = build_battle(defender_ability="Aroma Veil")
    use(battle, user, holder, "Taunt")
    assert "taunt" not in holder.volatiles


def test_inner_focus_prevents_the_real_fake_out_flinch():
    battle, user, holder = build_battle(defender_ability="Inner Focus")
    use(battle, user, holder, "Fake Out")
    assert holder.hp < holder.max_hp
    assert "flinch" not in holder.volatiles


def test_steadfast_reacts_once_when_flinch_actually_prevents_a_move():
    battle, holder, foe = build_battle(attacker_ability="Steadfast")
    battle.rng = random.Random(0)
    battle.execute_actions([move_action(battle, foe, holder, "Fake Out"), move_action(battle, holder, holder, "Splash")])
    assert stage(holder, "spe", "speed") == 1
    battle.start_turn()
    use(battle, holder, holder, "Splash")
    assert stage(holder, "spe", "speed") == 1


def test_cotton_down_lowers_other_active_pokemon_without_lowering_its_holder():
    battle, user, holder = build_battle(defender_ability="Cotton Down")
    use(battle, user, holder, "Tackle")
    assert stage(holder, "spe", "speed") == 0
    assert stage(user, "spe", "speed") == -1


def test_electromorphosis_uses_the_real_charge_volatile():
    battle, user, holder = build_battle(defender_ability="Electromorphosis")
    use(battle, user, holder, "Tackle")
    assert "charge" in holder.volatiles
    assert "charged" not in holder.volatiles


@pytest.mark.parametrize("ability", ["Insomnia", "Vital Spirit", "Sweet Veil", "Purifying Salt"])
def test_sleep_guard_abilities_prevent_yawn_before_starting_its_counter(ability):
    battle, user, holder = build_battle(defender_ability=ability)
    use(battle, user, holder, "Yawn")
    assert "yawn" not in holder.volatiles


def test_own_tempo_blocks_confusion_and_inner_focus_allows_it():
    for ability, blocked in (("Own Tempo", True), ("Inner Focus", False)):
        battle, user, holder = build_battle(defender_ability=ability)
        use(battle, user, holder, "Confuse Ray")
        assert ("confusion" not in holder.volatiles) == blocked


def test_aroma_veil_protects_an_ally_but_does_not_protect_an_enemy():
    battle, user, holder = build_battle()
    ally = load_modules()["Pokemon"]("Ally", hp=200, max_hp=200, ability="Aroma Veil")
    ally.side, ally.battle = holder.side, battle
    part = battle.participant_for(holder)
    part.pokemons.append(ally)
    part.active.append(ally)
    use(battle, user, holder, "Taunt")
    assert "taunt" not in holder.volatiles
    other, source, target = build_battle(attacker_ability="Aroma Veil")
    use(other, source, target, "Taunt")
    assert "taunt" in target.volatiles


def test_an_ordinary_taunt_starts_once_and_does_not_taunt_its_source():
    battle, user, holder = build_battle()
    calls = []
    original = battle.runEvent

    def observe(event, *args, **kwargs):
        if event == "TryAddVolatile":
            calls.append(event)
        return original(event, *args, **kwargs)

    battle.runEvent = observe
    use(battle, user, holder, "Taunt")
    assert "taunt" in holder.volatiles and "taunt" not in user.volatiles
    assert calls == ["TryAddVolatile"]


def test_a_reflected_drop_keeps_the_opponent_as_source_for_competitive():
    battle, user, holder = build_battle(attacker_ability="Competitive", defender_ability="Mirror Armor")
    use(battle, user, holder, "Growl")
    assert stage(holder, "atk", "attack") == 0
    assert stage(user, "atk", "attack") == -1
    assert stage(user, "spa", "special_attack") == 2


def test_mirror_armor_reflection_does_not_bounce_between_two_holders():
    battle, user, holder = build_battle(attacker_ability="Mirror Armor", defender_ability="Mirror Armor")
    use(battle, user, holder, "Growl")
    assert stage(holder, "atk", "attack") == 0
    assert stage(user, "atk", "attack") == -1


def test_mirror_armor_does_not_reflect_a_drop_already_prevented_by_the_stage_floor():
    battle, user, holder = build_battle(defender_ability="Mirror Armor")
    holder.boosts["attack"] = -6
    use(battle, user, holder, "Growl")
    assert stage(holder, "atk", "attack") == -6
    assert stage(user, "atk", "attack") == 0
