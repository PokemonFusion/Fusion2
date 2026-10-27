"""Native ally, delayed-item, and display lifecycles from qualified live fixtures."""
import random

import pytest

from .helpers import build_battle, load_modules
from .test_live_ability_reactions import ally
from .test_live_checkpoint_effect_consumers import quiet_log, stage
from .test_pending_action_effects import action


def test_commander_native_doubles_boosts_dondozo_once_and_hides_tatsugiri():
    from pokemon.battle.legal_actions import LegalActions
    battle, user, foe = build_battle(attacker_ability="Commander")
    user.species = user.base_species = "Tatsugiri"
    partner = ally(battle, name="Dondozo")
    battle.start_turn()
    assert "commanding" in user.volatiles and "commanded" in partner.volatiles
    assert all(stage(partner, short, long) == 2 for short, long in
               (("atk", "attack"), ("def", "defense"), ("spa", "special_attack"), ("spd", "special_defense"), ("spe", "speed")))
    battle.dispatcher.dispatch("update", pokemon=user, battle=battle)
    assert stage(partner, "atk", "attack") == 2
    targets = LegalActions(battle, battle.participants[1], foe).targets(action(battle, foe, user, "Tackle").move)
    assert user not in targets and partner in targets


def test_commander_does_not_activate_without_its_native_partner():
    battle, user, _ = build_battle(attacker_ability="Commander")
    user.species = user.base_species = "Tatsugiri"
    friend = ally(battle, name="Eevee")
    battle.start_turn()
    assert not user.volatiles.get("commanding") and not friend.volatiles.get("commanded")


def test_cud_chew_repeats_the_consumed_berry_without_consuming_a_new_held_item():
    battle, user, _ = build_battle(attacker_ability="Cud Chew")
    user.hp = 140
    user.item = battle._coerce_item("Oran Berry")
    battle.start_turn()
    assert battle.eat_item(user, force=True)
    assert user.hp == 150
    assert battle.set_item(user, "Choice Band")
    for _ in range(2):
        battle.residual()
        battle.end_turn()
    assert user.hp == 160
    assert user.item.raw["name"] == "Choice Band"
    assert "cudchew" not in user.volatiles
    for _ in range(2):
        battle.residual()
        battle.end_turn()
    assert user.hp == 160


def test_symbiosis_transfers_only_after_an_ally_uses_its_item():
    battle, user, _ = build_battle(attacker_ability="Symbiosis")
    user.item = battle._coerce_item("Choice Band")
    friend = ally(battle)
    friend.hp = 140
    friend.item = battle._coerce_item("Oran Berry")
    assert battle.eat_item(friend, force=True)
    assert user.item is None and friend.item.raw["name"] == "Choice Band"


def test_symbiosis_does_not_transfer_after_an_ally_item_is_removed():
    battle, user, _ = build_battle(attacker_ability="Symbiosis")
    user.item = battle._coerce_item("Choice Band")
    friend = ally(battle)
    friend.item = battle._coerce_item("Oran Berry")
    assert battle.take_item(friend, source=user)
    assert user.item.raw["name"] == "Choice Band" and friend.item is None


def test_early_bird_wakes_one_action_after_rest_through_normal_turn_resets():
    losses = []
    for ability in ("No Ability", "Early Bird"):
        battle, user, target = build_battle(attacker_ability=ability)
        user.hp = 100
        battle.rng = random.Random(1)
        battle.start_turn()
        battle.use_move(action(battle, user, user, "Rest"))
        assert user.status == "slp"
        battle.start_turn()
        battle.run_switch()
        battle.run_after_switch()
        battle.use_move(action(battle, user, target, "Tackle"))
        losses.append(target.max_hp - target.hp)
    assert losses[0] == 0 and losses[1] > 0


def test_illusion_uses_a_serializable_bench_disguise_and_breaks_on_direct_damage():
    battle, user, foe = build_battle(attacker_ability="Illusion")
    user.species = user.base_species = user.name = "Zoroark"
    user.types = ["Dark"]
    bench = load_modules()["Pokemon"]("Eevee", hp=200, max_hp=200)
    battle.participants[0].pokemons.append(bench)
    hp, maximum = user.hp, user.max_hp
    battle.start_turn()
    assert user.name == "Eevee" and str(user.species) == "Zoroark" and user.types == ["Dark"]
    assert (user.hp, user.max_hp) == (hp, maximum)
    restored = load_modules()["Pokemon"].from_dict(user.to_dict())
    assert restored.name == "Eevee" and isinstance(restored.ability_state["illusion"], dict)
    battle.rng = random.Random(1)
    battle.use_move(action(battle, foe, user, "Tackle"))
    assert user.name == "Zoroark" and "illusion" not in user.ability_state
