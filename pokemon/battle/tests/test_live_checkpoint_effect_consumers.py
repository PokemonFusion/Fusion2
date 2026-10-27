"""Regressions from real commands with named abilities and minimal move references."""

import logging
import random

import pytest

from .helpers import build_battle, load_modules, make_stats
from .test_pending_action_effects import action


@pytest.fixture(autouse=True)
def quiet_log():
    """Keep repeated simulation diagnostics out of the live battle log."""
    logger = logging.getLogger("battle")
    old = logger.disabled
    logger.disabled = True
    yield
    logger.disabled = old


def stage(pokemon, short, long):
    return pokemon.boosts.get(short, pokemon.boosts.get(long, 0))


@pytest.mark.parametrize("species,ability,expected", [("Aron", "Heavy Metal", 120), ("Beldum", "Light Metal", 47.6)])
def test_weight_hooks_resolve_native_species_without_a_handwritten_weight(species, ability, expected):
    from pokemon.battle.effect_context import EffectContext
    battle, user, _ = build_battle(attacker_ability=ability)
    user.species = species
    assert not hasattr(user, "weightkg")
    assert EffectContext.weight(user) == pytest.approx(expected)


@pytest.mark.parametrize("species,ability,item,form", [("Arceus", "Multitype", "Flame Plate", "Arceus-Fire"),
                                                       ("Silvally", "RKS System", "Fire Memory", "Silvally-Fire")])
def test_type_items_update_runtime_form_while_retaining_computed_stats_and_hp(species, ability, item, form):
    battle, user, _ = build_battle(attacker_ability=ability)
    user.species = user.base_species = user.name = species
    user.item = battle._coerce_item(item)
    maximum, hp, attack = user.max_hp, user.hp, user.base_stats.attack
    battle._apply_ability_item_type(user)
    assert str(user.species) == user.name == form and user.types == ["Fire"]
    assert (user.max_hp, user.hp, user.base_stats.attack) == (maximum, hp, attack)


@pytest.mark.parametrize("ability,move,first", [("Gale Wings", "Peck", True), ("Prankster", "Swords Dance", True),
                                                 ("Triage", "Synthesis", True), ("Stall", "Tackle", False),
                                                 ("Mycelium Might", "Swords Dance", False)])
def test_ordering_hydrates_minimal_command_moves_and_named_abilities(ability, move, first):
    battle, user, target = build_battle(attacker_ability=ability)
    user.base_stats.speed, target.base_stats.speed = (100, 200) if first else (200, 100)
    chosen = action(battle, user, target, move)
    chosen.move = load_modules()["BattleMove"](move)
    foe = action(battle, target, user, "Tackle")
    ordered = battle.order_actions([chosen, foe])
    assert (ordered[0].pokemon is user) is first


def test_real_initial_prompt_does_not_spend_mat_blocks_first_playable_turn():
    battle, user, target = build_battle()
    user.base_stats.speed = 400
    battle.start_turn()
    marker = getattr(battle, "mark_initial_prompt", None)
    assert callable(marker), "The live initial prompt must identify its next playable entry turn."
    marker()
    battle.start_turn()
    battle.execute_turn([action(battle, user, user, "Mat Block"), action(battle, target, user, "Tackle")])
    assert user.hp == user.max_hp
    battle.start_turn()
    battle.execute_turn([action(battle, user, user, "Mat Block"), action(battle, target, user, "Tackle")])
    assert user.hp < user.max_hp


def test_incoming_bench_holder_gets_live_battle_context_for_costar():
    battle, user, _ = build_battle()
    Pokemon = load_modules()["Pokemon"]
    ally = Pokemon("Ally", level=50, hp=200, max_hp=200)
    ally.base_stats = make_stats()
    ally.boosts["atk"] = 2
    bench = Pokemon("Flamigo", level=50, hp=200, max_hp=200, ability="Costar")
    part = battle.participants[0]
    part.pokemons.extend([ally, bench])
    part.active[:] = [bench, ally]
    ally.battle = battle
    battle.on_enter_battle(bench)
    assert bench.battle is battle
    assert stage(bench, "atk", "attack") == 2


def test_named_ally_ability_queries_use_current_active_effects():
    battle, user, _ = build_battle(attacker_ability="Minus")
    assert user.hasAbility("minus")
    user.ability_suppressed = True
    assert not user.hasAbility("minus")


def test_telepathy_direct_hit_gate_receives_the_actual_holder_context():
    losses = []
    for ability in ("No Ability", "Telepathy"):
        battle, user, target = build_battle(attacker_ability=ability)
        ally = load_modules()["Pokemon"]("Mew", level=50, hp=200, max_hp=200)
        ally.base_stats = make_stats()
        ally.battle = battle
        part = battle.participants[0]
        part.pokemons.append(ally)
        part.active.append(ally)
        battle.rng = random.Random(1)
        battle.use_move(action(battle, ally, user, "Surf"))
        losses.append(user.max_hp - user.hp)
    assert losses[0] > 0 and losses[1] == 0


def test_embody_aspect_start_and_switch_hooks_boost_once_per_entry():
    battle, user, _ = build_battle(attacker_ability="Defiant")
    user.species = user.base_species = "Ogerpon"
    battle.start_turn()
    from pokemon.battle.terastallization import Terastallization

    typ = Terastallization.reserve(battle, battle.participants[0], user)
    assert Terastallization.activate(battle, battle.participants[0], user, typ)
    assert stage(user, "spe", "speed") == 1


def test_comatose_is_virtual_sleep_without_an_invented_speed_penalty():
    battle, user, target = build_battle(attacker_ability="Comatose")
    battle.start_turn()
    assert stage(user, "spe", "speed") == 0
    assert user.status != "slp"
    battle.use_move(action(battle, target, user, "Thunder Wave"))
    assert user.status != "par"
    battle.use_move(action(battle, user, target, "Tackle"))
    assert target.hp < target.max_hp


@pytest.mark.parametrize("shield,ability,suppressed", [(False, "Intimidate", True),
                                                       (True, "Intimidate", False), (False, "Comatose", False)])
def test_neutralizing_gas_respects_ability_shield_and_unsuppressible_flags(shield, ability, suppressed):
    from pokemon.battle.effect_context import EffectContext
    battle, user, _ = build_battle(attacker_ability=ability, defender_ability="Neutralizing Gas")
    if shield:
        user.item = battle._coerce_item("Ability Shield")
    assert (EffectContext.ability(user) is None) is suppressed


@pytest.mark.parametrize("move", ["Assist", "Nature Power"])
def test_successful_called_attack_does_not_announce_a_failed_parent(move):
    battle, user, target = build_battle()
    messages = []
    battle.log_action = messages.append
    if move == "Assist":
        bench = load_modules()["Pokemon"]("Eevee", moves=[load_modules()["Move"]("Tackle")])
        battle.participants[0].pokemons.append(bench)
    battle.rng = random.Random(1)
    battle.use_move(action(battle, user, target, move))
    assert target.hp < target.max_hp
    assert not any(move in message and "had no effect" in message for message in messages)
    assert any(move in message and "called" in message for message in messages)
