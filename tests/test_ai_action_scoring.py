"""Deterministic action and target valuation using actual battle candidates."""

from __future__ import annotations

import pickle
import random

import pytest

from pokemon.battle.ai_action_scoring import AIActionScorer
from pokemon.battle.ai_profiles import DEFAULT_AI_PROFILES, build_battle_ai_context
from pokemon.battle.battledata import Move, Pokemon
from pokemon.battle.engine import Battle, BattleParticipant, BattleType, _select_ai_action
from pokemon.battle.legal_actions import LegalActions
from pokemon.dex import MOVEDEX
from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats


def mon(species, moves=("Tackle",), *, hp_fraction=1):
    """Use canonical level/IV/EV/nature stats for real battle representations."""
    pokemon = Pokemon(species, level=50, ivs=[0] * 6, evs=[0] * 6, nature="Hardy",
                      moves=[Move(name) for name in moves])
    pokemon.stats = get_stats(pokemon)
    pokemon.max_hp = get_max_hp(pokemon)
    pokemon.hp = max(1, int(pokemon.max_hp * hp_fraction))
    return pokemon


def encounter(own, foes, *, profile="gym_trick_room"):
    """Create actual singles/doubles sides with stable seeded selection."""
    ai = BattleParticipant("Gym", list(own), is_ai=True, max_active=len(own), team="B")
    ai.active = list(own)
    ai.ai_profile = profile
    opponent = BattleParticipant("Player", list(foes), max_active=len(foes), team="A")
    opponent.active = list(foes)
    battle = Battle(BattleType.TRAINER, [opponent, ai], rng=random.Random(5))
    return battle, ai, opponent


def assessments(battle, ai, pokemon, *, planned=()):
    """Score only candidates supplied by the production legality layer."""
    context = build_battle_ai_context(ai, pokemon, battle)
    scorer = AIActionScorer(context, battle, ai, pokemon, movedex=MOVEDEX,
                            raw_getter=lambda entry: getattr(entry, "raw", {}) or {}, planned=planned)
    return scorer.assess(LegalActions(battle, ai, pokemon).moves())


def best(battle, ai, pokemon, *, planned=()):
    """Inspect deterministic utility without probabilistic tie assertions."""
    return max(assessments(battle, ai, pokemon, planned=planned), key=lambda entry: entry.scored.score)


@pytest.mark.parametrize("persistent, duration", [(False, 5), (True, 7)])
def test_trick_room_duration_and_field_references_are_serializable(persistent, duration):
    """Room state uses detached references and expires at its actual duration."""
    from pokemon.battle._shared import restore_battle_value
    from pokemon.battle.battledata import Field

    user = mon("Slowbro", ("Trick Room",))
    if persistent:
        user.ability = "Persistent"
    battle, _, _ = encounter([user], [mon("Jolteon")])
    assert battle.add_pseudo_weather("trickroom", source=user)
    state = battle.field.get_pseudo_weather("trickroom")
    assert state["duration"] == duration
    assert state["target"] is battle.field
    encoded = pickle.loads(pickle.dumps(battle.field.to_dict()))
    restored = Field.from_dict(encoded)
    reference = user.model_id or f"{user.name}|{user.level}|{user.max_hp}"
    restored.pseudo_weather = restore_battle_value(restored.pseudo_weather, {reference: user}, field=restored)
    assert restored.pseudo_weather["trickroom"]["target"] is restored
    assert restored.pseudo_weather["trickroom"]["source"] is user
    battle.field = restored
    for remaining in range(duration - 1, 0, -1):
        battle.residual()
        assert restored.get_pseudo_weather("trickroom")["duration"] == remaining
    battle.residual()
    assert restored.get_pseudo_weather("trickroom") is None


def test_legacy_boolean_trick_room_has_a_bounded_lifetime():
    """Old saved True fields also expire instead of remaining active forever."""
    battle, _, _ = encounter([mon("Slowbro")], [mon("Jolteon")])
    battle.field.pseudo_weather["trickroom"] = True
    for _ in range(5):
        battle.residual()
    assert battle.field.get_pseudo_weather("trickroom") is None


def test_offensive_setup_needs_an_available_attack():
    """Exhausted physical attacks do not justify spending a turn on Swords Dance."""
    user = mon("Mew", ("Swords Dance", "Tackle", "Water Gun"))
    user.moves[1].pp = 0
    battle, ai, _ = encounter([user], [mon("Snorlax")])
    setup = next(entry for entry in assessments(battle, ai, user) if entry.action.move.name == "Swords Dance")
    assert setup.scored.score == 0


def test_protect_does_not_value_damaging_black_sludge_as_healing():
    """Black Sludge only supplies a recovery reason for a Poison-type holder."""
    user = mon("Eevee", ("Protect", "Tackle"))
    user.item = "Black Sludge"
    battle, ai, _ = encounter([user], [mon("Eevee")])
    def protect():
        """Inspect the current Protect choice without sampling the selector."""
        return next(entry for entry in assessments(battle, ai, user) if entry.action.move.name == "Protect")
    assert protect().scored.score == 0
    user.types = ["Poison"]
    assert protect().scored.score > 0
    user.volatiles["healblock"] = {"duration": 5}
    assert protect().scored.score == 0


def test_two_foe_targets_are_scored_individually():
    """Water Gun chooses the vulnerable second foe, not the first slot."""
    user = mon("Squirtle", ("Water Gun",))
    battle, ai, _ = encounter([user, mon("Eevee")], [mon("Squirtle"), mon("Geodude")])
    action = _select_ai_action(ai, user, battle)
    assert action.target_slot == 1
    assert action.target_pokemon.name == "Geodude"
    trace = ai.last_ai_debug_trace.to_dict()
    water_targets = {entry["target"] for entry in trace["scores"] if entry["action"].lower() == "watergun"}
    assert water_targets == {"A1 Squirtle", "A2 Geodude"}


def test_spread_values_both_foes_and_friendly_fire():
    """Earthquake gains two-foe value when its own ally is visibly immune."""
    user = mon("Golem", ("Earthquake", "Bulldoze", "Rock Slide"))
    ally = mon("Pidgeot")
    battle, ai, _ = encounter([user, ally], [mon("Pikachu"), mon("Jolteon")])
    immune = best(battle, ai, user)
    assert immune.action.move.name == "Earthquake"
    assert "spread_target_set" in immune.scored.reasons
    ally.types = ["Electric"]
    ally.hp = 1
    unsafe = next(entry for entry in assessments(battle, ai, user) if entry.action.move.name == "Earthquake")
    assert unsafe.scored.score == 0
    assert "ally_lethal_risk" in unsafe.scored.reasons
    assert best(battle, ai, user).action.move.name == "Rock Slide"


def test_spread_gains_and_loses_the_second_foe():
    """A fainted second foe contributes neither damage value nor a target."""
    user = mon("Blastoise", ("Surf",))
    battle, ai, opponent = encounter([user, mon("Vaporeon")], [mon("Charmander"), mon("Vulpix")])
    two = best(battle, ai, user)
    opponent.active[1].hp = 0
    one = best(battle, ai, user)
    assert two.scored.score > one.scored.score
    assert all(mon.hp > 0 for mon in one.targets)


def test_ally_pollen_puff_is_healing_and_plain_attacks_never_target_ally():
    """A permitted normal-target heal can support an injured same-side actor."""
    user = mon("Butterfree", ("Pollen Puff", "Tackle"))
    ally = mon("Snorlax", hp_fraction=0.1)
    battle, ai, _ = encounter([user, ally], [mon("Blissey"), mon("Blissey")])
    choice = best(battle, ai, user)
    assert choice.action.move.name == "Pollen Puff"
    assert choice.action.target_pokemon is ally
    assert choice.intent == "support_ally"
    assert all(entry.action.target_pokemon is not ally for entry in assessments(battle, ai, user)
               if entry.action.move.name == "Tackle")
    ally.hp = ally.max_hp
    healed = next(entry for entry in assessments(battle, ai, user)
                  if entry.action.move.name == "Pollen Puff" and entry.action.target_pokemon is ally)
    assert healed.scored.score == 0


def test_heal_pulse_does_not_prefer_healing_an_injured_enemy():
    """Pure healing supplies no enemy utility even when the ally is full HP."""
    user, ally = mon("Slowbro", ("Heal Pulse",)), mon("Snorlax")
    battle, ai, _ = encounter([user, ally], [mon("Eevee", hp_fraction=0.1)])
    entries = assessments(battle, ai, user)
    assert all(entry.scored.score == 0 for entry in entries)
    assert _select_ai_action(ai, user, battle).target_pokemon is ally


@pytest.mark.parametrize("name", ("Poison Gas", "Growl"))
def test_spread_status_and_debuffs_value_each_affected_foe(name):
    """A second eligible foe adds utility; fainted targets add none."""
    user = mon("Mew", (name,))
    battle, ai, foe = encounter([user, mon("Snorlax")], [mon("Eevee"), mon("Eevee")])
    two = best(battle, ai, user).scored.score
    foe.active[1].hp = 0
    one = best(battle, ai, user).scored.score
    assert two > one > 0


def test_helping_hand_requires_an_ally_attack_and_rejects_planned_switch():
    """Support must benefit a legal attack, not a switching or already-moved ally."""
    user, ally = mon("Eevee", ("Helping Hand", "Tackle")), mon("Golem", ("Earthquake",))
    reserve = mon("Pidgeot")
    battle, ai, _ = encounter([user, ally], [mon("Pikachu"), mon("Jolteon")])
    ai.pokemons.append(reserve)
    useful = next(entry for entry in assessments(battle, ai, user) if entry.action.move.name == "Helping Hand")
    assert useful.scored.score > 0
    switch = LegalActions(battle, ai, ally).switches()[0]
    useless = next(entry for entry in assessments(battle, ai, user, planned=[switch]) if entry.action.move.name == "Helping Hand")
    assert useless.scored.score == 0


def test_helping_hand_does_not_boost_a_planned_ally_pollen_puff_heal():
    """The same hybrid move can be either an attack or an unsupported heal."""
    user = mon("Eevee", ("Helping Hand",), hp_fraction=0.1)
    ally = mon("Butterfree", ("Pollen Puff",))
    battle, ai, _ = encounter([user, ally], [mon("Eevee")])
    choices = LegalActions(battle, ai, ally).moves()
    healing = next(action for action in choices if action.target_pokemon is user)
    attacking = next(action for action in choices if action.target_pokemon is not user)
    assert best(battle, ai, user, planned=[healing]).scored.score == 0
    assert best(battle, ai, user, planned=[attacking]).scored.score > 0


@pytest.mark.parametrize("blocked", ("healthy", "already_statused", "type_immune"))
def test_status_and_recovery_use_current_state(blocked):
    """Full health, an existing status, or a type immunity removes utility."""
    user = mon("Mew", ("Recover", "Will-O-Wisp", "Tackle"))
    foe = mon("Snorlax")
    battle, ai, _ = encounter([user], [foe])
    entries = assessments(battle, ai, user)
    assert next(entry for entry in entries if entry.action.move.name == "Recover").scored.score == 0
    if blocked == "already_statused":
        foe.status = "psn"
    elif blocked == "type_immune":
        foe.types = ["Fire"]
    else:
        user.hp = user.max_hp // 5
        assert best(battle, ai, user).action.move.name == "Recover"
        return
    assert next(entry for entry in assessments(battle, ai, user)
                if entry.action.move.name == "Will-O-Wisp").scored.score == 0


def test_setup_stops_at_capped_stages_or_low_health():
    """Setup has bounded value and does not repeat at a completed boost."""
    user = mon("Scyther", ("Swords Dance", "Tackle"))
    battle, ai, _ = encounter([user], [mon("Snorlax")])
    assert best(battle, ai, user).action.move.name == "Swords Dance"
    user.boosts = {"attack": 6}
    assert best(battle, ai, user).action.move.name == "Tackle"
    user.boosts = {}
    user.hp = 1
    assert best(battle, ai, user).action.move.name == "Tackle"


def test_protect_values_residual_or_ally_cover_and_penalizes_repetition():
    """Protect needs a visible benefit; its stall counter bounds repetition."""
    user = mon("Eevee", ("Protect", "Tackle"), hp_fraction=0.2)
    battle, ai, foe = encounter([user], [mon("Snorlax")])
    assert best(battle, ai, user).action.move.name == "Tackle"
    foe.active[0].status = "tox"
    assert best(battle, ai, user).action.move.name == "Protect"
    user.volatiles["stall"] = {"counter": 8}
    assert best(battle, ai, user).action.move.name == "Tackle"


def test_trick_room_set_preserve_and_reverse_harmful_room():
    """The preset changes the field only when the team's visible speeds benefit."""
    user = mon("Slowbro", ("Trick Room", "Water Gun"))
    battle, ai, _ = encounter([user, mon("Snorlax")], [mon("Jolteon"), mon("Crobat")])
    room = best(battle, ai, user)
    assert room.action.move.name == "Trick Room"
    assert room.intent == "control_field"
    battle.field.add_pseudo_weather("trickroom", {"duration": 5})
    assert best(battle, ai, user).action.move.name == "Water Gun"
    for own in ai.active:
        own.stats["speed"] = 200
    assert best(battle, ai, user).action.move.name == "Trick Room"


def test_trick_room_is_not_duplicated_by_second_actor():
    """Two slow AI actors cannot cancel their own newly declared room."""
    users = [mon("Slowbro", ("Trick Room", "Water Gun")), mon("Slowking", ("Trick Room", "Water Gun"))]
    battle, ai, _ = encounter(users, [mon("Jolteon"), mon("Crobat")])
    actions = ai.choose_actions(battle)
    assert len(actions) == 2
    assert [action.move.name for action in actions].count("Trick Room") == 1


def test_scorer_is_read_only_and_does_not_use_opponent_moves_or_rng():
    """Scoring leaves resources, callbacks, planned foe actions and RNG untouched."""
    user = mon("Slowbro", ("Trick Room", "Water Gun"))
    battle, ai, foe = encounter([user, mon("Snorlax")], [mon("Jolteon"), mon("Aerodactyl")])
    before = pickle.dumps([mon.to_dict() for part in battle.participants for mon in part.pokemons])
    rng_state = battle.rng.getstate()
    scores = [entry.scored.score for entry in assessments(battle, ai, user)]
    for pokemon in foe.active:
        pokemon.moves = [Move("Protect"), Move("Explosion")]
    foe.pending_action = object()
    assert scores == [entry.scored.score for entry in assessments(battle, ai, user)]
    assert battle.rng.getstate() == rng_state
    # Reset only the deliberately altered opponent test inputs before comparison.
    for pokemon in foe.active:
        pokemon.moves = [Move("Tackle")]
    assert pickle.dumps([mon.to_dict() for part in battle.participants for mon in part.pokemons]) == before


def test_explicit_profile_controls_only_the_selected_gym_primitive(monkeypatch):
    """Generic gym AI does not gain unspecified field-strategy preferences."""
    user = mon("Slowbro", ("Trick Room", "Water Gun"))
    battle, ai, _ = encounter([user], [mon("Jolteon")], profile="gym_leader")
    room = next(entry for entry in assessments(battle, ai, user) if entry.action.move.name == "Trick Room")
    assert room.scored.score == 0
    profile = DEFAULT_AI_PROFILES["gym_trick_room"]
    assert profile.strategy_key == "trick_room"
    assert profile.knowledge_policy == "visible_only"
