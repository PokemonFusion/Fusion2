"""Legal AI candidates, bounded switches and late invalidation regressions."""

from __future__ import annotations

import pickle
import random
from dataclasses import replace

import pytest

from pokemon.battle.ai_profiles import DEFAULT_AI_PROFILES
from pokemon.battle.battledata import Move, Pokemon
from pokemon.battle.engine import ActionType, Battle, BattleMove, BattleParticipant, BattleType, _select_ai_action
from pokemon.battle.legal_actions import LegalActions


def mon(name="Squirtle", moves=("Tackle", "Water Gun"), *, hp=100):
    """Build a real engine roster member with deterministic remaining PP."""
    pokemon = Pokemon(name, level=20, hp=hp, max_hp=100, types=["Water"], moves=[Move(move) for move in moves])
    for move in pokemon.moves:
        move.pp = 20
    return pokemon


def encounter(*, doubles=False):
    """Create real participant objects and optional second active positions."""
    team = [mon(), mon("Bulbasaur", ("Tackle",)), mon("Pikachu", ("Thunderbolt",))]
    ai = BattleParticipant("NPC", team, is_ai=True, team="B", max_active=2 if doubles else 1)
    ai.active = team[:ai.max_active]
    foe = BattleParticipant("Player", [mon("Eevee"), mon("Geodude")], team="A", max_active=ai.max_active)
    foe.active = foe.pokemons[:foe.max_active]
    battle = Battle(BattleType.TRAINER, [foe, ai], rng=random.Random(0))
    return battle, ai, foe


@pytest.mark.parametrize("control", ("disabled", "pp", "disable", "taunt", "encore", "choice"))
def test_move_controls_filter_before_scoring(control):
    """The scorer cannot resurrect a move rejected by PP or effect controls."""
    battle, ai, _ = encounter()
    user = ai.active[0]
    user.moves = [Move("Tackle"), Move("Growl")]
    for move in user.moves:
        move.pp = 20
    expected = {"Tackle"}
    if control == "disabled":
        user.moves[1].disabled = True
    elif control == "pp":
        user.moves[1].current_pp = 0
    elif control == "disable":
        user.volatiles["disable"] = BattleMove("Growl")
    elif control == "taunt":
        user.volatiles["taunt"] = True
    elif control == "encore":
        user.volatiles["encore"] = BattleMove("Tackle")
    else:
        user.item = "Choice Band"
        user.choice_locked_move = "tackle"
    assert {action.move.name for action in LegalActions(battle, ai, user).moves()} == expected
    assert _select_ai_action(ai, user, battle).move.name == "Tackle"


@pytest.mark.parametrize("invalid", ("fainted", "foreign", "terminal", "replaced"))
def test_invalid_actor_cannot_choose_a_move(invalid):
    """Invalid actors never generate attacks for another active Pokemon."""
    battle, ai, _ = encounter()
    actor = ai.active[0]
    if invalid == "fainted":
        actor.hp = 0
    elif invalid == "foreign":
        actor = mon("Foreign")
    elif invalid == "terminal":
        ai.has_lost = True
    else:
        ai.active = [ai.pokemons[1]]
    assert _select_ai_action(ai, actor, battle) is None


def test_struggle_is_usable_with_empty_pp_and_choice_lock():
    """The emergency move is not an unlearned Flail or blocked by the old choice."""
    battle, ai, foe = encounter()
    user = ai.active[0]
    user.item = "Choice Band"
    user.choice_locked_move = "tackle"
    for move in user.moves:
        move.pp = 0
    chosen = _select_ai_action(ai, user, battle)
    assert chosen.move.name == "Struggle"
    before = foe.active[0].hp
    battle.use_move(chosen)
    assert foe.active[0].hp < before
    assert all(move.pp == 0 for move in user.moves)


def test_targets_are_specific_living_legal_roster_members():
    """Fainted targets are excluded and self/ally/foe classes stay distinct."""
    battle, ai, foe = encounter(doubles=True)
    legal = LegalActions(battle, ai, ai.active[0])
    foe.active[0].hp = 0
    assert legal.targets(BattleMove("Attack", raw={"target": "adjacentFoe"})) == [foe.active[1]]
    assert legal.targets(BattleMove("Support", raw={"target": "adjacentAlly"})) == [ai.active[1]]
    assert legal.targets(BattleMove("Recover", raw={"target": "self"})) == [ai.active[0]]
    assert legal.targets(BattleMove("Invalid", raw={"target": "unsupported"})) == []


def test_forced_reserves_are_stable_distinct_and_ignore_trapping():
    """An empty/fainted slot can use a live reserve without duplicating an active."""
    battle, ai, _ = encounter(doubles=True)
    lead = ai.active[0]
    lead.volatiles["ingrain"] = True
    assert not LegalActions(battle, ai, lead).switches()
    lead.hp = 0
    ai.pokemons.append(ai.pokemons[2])
    assert LegalActions(battle, ai, lead).reserves(slot=0, forced=True) == [ai.pokemons[2]]
    assert not LegalActions(battle, ai, lead).reserves(slot=2, forced=True)
    assert not LegalActions(battle, ai, lead).reserves(slot=1, forced=True)


def test_a_reserved_incoming_pokemon_cannot_fill_two_slots():
    """Two active slots cannot independently reserve the same party member."""
    battle, ai, _ = encounter(doubles=True)
    first = LegalActions(battle, ai, ai.active[0]).switches()[0]
    assert first.switch_slot == 0
    assert not LegalActions(battle, ai, ai.active[1]).switches(reserved=[first.pokemon])


def test_basic_ai_does_not_attack_an_ally_for_a_higher_score():
    """Central legal ally targets do not turn the old damage policy into friendly fire."""
    battle, ai, foe = encounter(doubles=True)
    ai.active[0].moves = [Move("Water Gun")]
    ai.active[1].types = ["Fire", "Rock"]
    for pokemon in foe.active:
        pokemon.types = ["Water"]
    chosen = _select_ai_action(ai, ai.active[0], battle)
    assert chosen.target is foe


def test_bounded_voluntary_switch_and_cooldown(monkeypatch):
    """A threatened actor can preserve itself without switching every turn."""
    battle, ai, _ = encounter()
    ai.active[0].hp = 20
    monkeypatch.setitem(DEFAULT_AI_PROFILES, "qa_switch", replace(DEFAULT_AI_PROFILES["trainer_skilled"], key="qa_switch", switch_likelihood=1))
    ai.ai_profile = "qa_switch"
    chosen = _select_ai_action(ai, ai.active[0], battle)
    assert chosen.action_type is ActionType.SWITCH
    battle.execute_actions([chosen])
    assert ai.active == [chosen.pokemon]
    assert ai.last_ai_switch_turn == battle.turn_count
    ai.active[0].hp = 20
    assert _select_ai_action(ai, ai.active[0], battle).action_type is ActionType.MOVE


def test_stale_preferred_action_falls_back_before_ordering():
    """An invalid queued move is replaced before action priority is calculated."""
    battle, ai, _ = encounter()
    user = ai.active[0]
    preferred = next(action for action in LegalActions(battle, ai, user).moves() if action.move.name == "Water Gun")
    user.volatiles["disable"] = BattleMove("Water Gun")
    ai.pending_action = preferred
    actions = battle.select_actions()
    assert len(actions) == 1
    assert actions[0].move.name == "Tackle"


def test_invalidated_action_does_not_gain_switch_priority():
    """Late invalidation skips safely rather than executing a fallback attack at +6."""
    battle, ai, foe = encounter()
    chosen = LegalActions(battle, ai, ai.active[0]).switches()[0]
    chosen.pokemon.hp = 0
    before = foe.active[0].hp
    battle.execute_actions([chosen])
    assert foe.active[0].hp == before
    assert ai.active[0] is chosen.switch_from


def test_switch_replaces_the_selected_active_slot():
    """A2 switching must not eject its A1 sibling."""
    battle, ai, _ = encounter(doubles=True)
    first = ai.active[0]
    chosen = LegalActions(battle, ai, ai.active[1]).switches()[0]
    battle.execute_actions([chosen])
    assert ai.active == [first, chosen.pokemon]


def test_attack_hits_the_incoming_pokemon_in_its_selected_slot():
    """An ordinary switch changes the occupant without making the slot untargetable."""
    battle, ai, foe = encounter()
    chosen = LegalActions(battle, ai, ai.active[0]).moves()[0]
    outgoing = foe.active[0]
    incoming = foe.pokemons[1]
    battle.switch_pokemon(foe, incoming)
    before = incoming.hp
    battle.execute_actions([chosen])
    assert incoming.hp < before
    assert outgoing.hp == 100


def test_move_control_snapshot_does_not_pickle_callbacks():
    """Disable/Encore controls save move references without live function graphs."""
    from pokemon.battle._shared import restore_battle_value

    pokemon = mon()
    locked = BattleMove("Tackle", onHit=lambda *args: True)
    pokemon.volatiles["disable"] = locked
    encoded = pokemon.to_dict()
    pickle.dumps(encoded)
    restored = Pokemon.from_dict(encoded)
    restored.volatiles = restore_battle_value(restored.volatiles, {})
    assert restored.volatiles["disable"].name == "Tackle"
