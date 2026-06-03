"""Tests for battle AI profile, context, and trace scaffolding."""

from __future__ import annotations

import random
import types


def test_resolve_ai_profile_uses_wild_battle_default():
    from pokemon.battle.ai_profiles import build_battle_ai_context
    from pokemon.battle.engine import BattleType

    participant = types.SimpleNamespace(name="Wild Side")
    pokemon = types.SimpleNamespace(name="Oddish", hp=12, max_hp=20)
    opponent = types.SimpleNamespace(name="Player", team="A")
    battle = types.SimpleNamespace(
        type=BattleType.WILD,
        turn=3,
        participants=[participant, opponent],
        opponents_of=lambda part: [opponent],
    )

    context = build_battle_ai_context(participant, pokemon, battle)

    assert context.profile.key == "wild_basic"
    assert context.battle_type == "wild"
    assert context.encounter_kind == "wild"
    assert context.visible_opponents == ("Player",)
    assert context.active_hp == 12
    assert context.active_max_hp == 20


def test_unknown_ai_profile_falls_back_to_trainer_default():
    from pokemon.battle.ai_profiles import build_battle_ai_context
    from pokemon.battle.ai_scoring import score_ai_moves
    from pokemon.battle._shared import _normalize_key
    from pokemon.battle.engine import BattleType

    participant = types.SimpleNamespace(name="AI Trainer", ai_profile="custom_missing_profile")
    pokemon = types.SimpleNamespace(name="Pidgey", hp=15, max_hp=15)
    battle = types.SimpleNamespace(type=BattleType.TRAINER, turn=1, opponents_of=lambda part: [])

    context = build_battle_ai_context(participant, pokemon, battle)

    assert context.requested_profile_key == "custom_missing_profile"
    assert context.profile.key == "trainer_basic"
    move = types.SimpleNamespace(name="Tackle", pp=None, current_pp=None)
    movedex = {
        _normalize_key("Tackle"): types.SimpleNamespace(
            raw={
                "name": "Tackle",
                "type": "Normal",
                "category": "Physical",
                "basePower": 40,
                "accuracy": 100,
                "pp": 35,
            }
        )
    }
    scored = score_ai_moves(
        context,
        [move],
        user=types.SimpleNamespace(name="Pidgey", types=["Normal"], stats={"attack": 50}),
        target=types.SimpleNamespace(name="Target", types=["Normal"], hp=100, max_hp=100, stats={"defense": 50}),
        movedex=movedex,
        raw_getter=lambda entry: dict(getattr(entry, "raw", {}) or {}),
    )
    assert scored and scored[0].score > 0


def test_ai_debug_trace_serializes_scores():
    from pokemon.battle.ai_profiles import AIDebugTrace

    trace = AIDebugTrace(profile_key="trainer_basic")
    trace.add_action("tackle", 1.0, "available")
    trace.add_action("growl", 0.25, "available", "status move")
    trace.choose("tackle", intent="safe_damage")

    data = trace.to_dict()

    assert data["profile_key"] == "trainer_basic"
    assert data["chosen_intent"] == "safe_damage"
    assert data["legal_actions_considered"] == ["tackle", "growl"]
    assert data["scores"][1]["reasons"] == ["available", "status move"]
    assert data["chosen_action"] == "tackle"


def test_select_ai_action_prefers_super_effective_stab_move(monkeypatch):
    from pokemon.battle import engine
    from pokemon.battle._shared import _normalize_key

    participant = types.SimpleNamespace(name="AI Trainer", ai_profile="trainer_skilled")
    moves = [
        types.SimpleNamespace(name="Tackle", pp=None, current_pp=None),
        types.SimpleNamespace(name="Water Gun", pp=None, current_pp=None),
    ]
    active_pokemon = types.SimpleNamespace(
        name="Starmie",
        types=["Water"],
        moves=moves,
        stats={"special_attack": 80, "special_defense": 70, "attack": 50, "defense": 60},
    )
    target = types.SimpleNamespace(
        name="Geodude",
        types=["Rock", "Ground"],
        hp=500,
        max_hp=500,
        stats={"defense": 90, "special_defense": 40},
    )
    opponent = types.SimpleNamespace(name="Player", active=[target])
    monkeypatch.setitem(
        engine.MOVEDEX,
        _normalize_key("Tackle"),
        types.SimpleNamespace(
            raw={
                "name": "Tackle",
                "type": "Normal",
                "category": "Physical",
                "basePower": 40,
                "accuracy": 100,
                "pp": 35,
            }
        ),
    )
    monkeypatch.setitem(
        engine.MOVEDEX,
        _normalize_key("Water Gun"),
        types.SimpleNamespace(
            raw={
                "name": "Water Gun",
                "type": "Water",
                "category": "Special",
                "basePower": 40,
                "accuracy": 100,
                "pp": 25,
            }
        ),
    )

    class StubBattle:
        def __init__(self):
            self.rng = random.Random(0)
            self.type = engine.BattleType.TRAINER

        def opponents_of(self, part):
            return [opponent]

    battle = StubBattle()

    action = engine._select_ai_action(participant, active_pokemon, battle)

    assert action.move.name == "Water Gun"
    trace = participant.last_ai_debug_trace
    assert trace.profile_key == "trainer_skilled"
    assert trace.chosen_intent == "safe_damage"
    assert trace.chosen_action == _normalize_key("Water Gun")
    water_score = next(score for score in trace.scores if score.action == _normalize_key("Water Gun"))
    assert "stab" in water_score.reasons
    assert "super_effective" in water_score.reasons
    assert "profile_weighted" in water_score.reasons
    assert "candidate_band_0.86" in water_score.reasons
    assert battle.last_ai_debug_trace is trace
    assert battle.ai_debug_traces[-1] is trace


def test_select_ai_action_skips_zero_current_pp(monkeypatch):
    from pokemon.battle import engine
    from pokemon.battle._shared import _normalize_key

    participant = types.SimpleNamespace(name="AI Trainer")
    moves = [
        types.SimpleNamespace(name="Hydro Pump", pp=5, current_pp=0),
        types.SimpleNamespace(name="Tackle", pp=35, current_pp=1),
    ]
    active_pokemon = types.SimpleNamespace(name="Squirtle", types=["Water"], moves=moves)
    target = types.SimpleNamespace(name="Target", types=["Normal"], hp=100, max_hp=100)
    opponent = types.SimpleNamespace(name="Player", active=[target])
    monkeypatch.setitem(
        engine.MOVEDEX,
        _normalize_key("Hydro Pump"),
        types.SimpleNamespace(
            raw={
                "name": "Hydro Pump",
                "type": "Water",
                "category": "Special",
                "basePower": 110,
                "accuracy": 80,
                "pp": 5,
            }
        ),
    )
    monkeypatch.setitem(
        engine.MOVEDEX,
        _normalize_key("Tackle"),
        types.SimpleNamespace(
            raw={
                "name": "Tackle",
                "type": "Normal",
                "category": "Physical",
                "basePower": 40,
                "accuracy": 100,
                "pp": 35,
            }
        ),
    )

    class StubBattle:
        def __init__(self):
            self.rng = random.Random(0)
            self.type = engine.BattleType.TRAINER

        def opponents_of(self, part):
            return [opponent]

    action = engine._select_ai_action(participant, active_pokemon, StubBattle())

    assert action.move.name == "Tackle"
    assert participant.last_ai_debug_trace.legal_actions_considered == [_normalize_key("Tackle")]


def test_select_ai_action_uses_emergency_fallback_when_all_pp_empty(monkeypatch):
    from pokemon.battle import engine
    from pokemon.battle._shared import _normalize_key

    participant = types.SimpleNamespace(name="AI Trainer")
    moves = [
        types.SimpleNamespace(name="Hydro Pump", pp=5, current_pp=0),
        types.SimpleNamespace(name="Tackle", pp=35, current_pp=0),
    ]
    active_pokemon = types.SimpleNamespace(name="Squirtle", moves=moves)
    target = types.SimpleNamespace(name="Target", types=["Normal"], hp=100, max_hp=100)
    opponent = types.SimpleNamespace(name="Player", active=[target])
    for name, pp in (("Hydro Pump", 5), ("Tackle", 35)):
        monkeypatch.setitem(
            engine.MOVEDEX,
            _normalize_key(name),
            types.SimpleNamespace(
                raw={
                    "name": name,
                    "type": "Water" if name == "Hydro Pump" else "Normal",
                    "category": "Special" if name == "Hydro Pump" else "Physical",
                    "basePower": 110 if name == "Hydro Pump" else 40,
                    "accuracy": 100,
                    "pp": pp,
                }
            ),
        )

    class StubBattle:
        def __init__(self):
            self.rng = random.Random(0)
            self.type = engine.BattleType.TRAINER

        def opponents_of(self, part):
            return [opponent]

    action = engine._select_ai_action(participant, active_pokemon, StubBattle())

    assert action.move.name == "Flail"
    assert participant.last_ai_debug_trace.scores[0].reasons == ("fallback_no_usable_moves",)


def test_select_ai_action_handles_missing_dex_data():
    from pokemon.battle import engine

    participant = types.SimpleNamespace(name="AI Trainer")
    moves = [types.SimpleNamespace(name="Mystery One", pp=None, current_pp=None)]
    active_pokemon = types.SimpleNamespace(name="Ditto", moves=moves)
    target = types.SimpleNamespace(name="Target", types=["Normal"], hp=100, max_hp=100)
    opponent = types.SimpleNamespace(name="Player", active=[target])

    class StubBattle:
        def __init__(self):
            self.rng = random.Random(0)
            self.type = engine.BattleType.TRAINER

        def opponents_of(self, part):
            return [opponent]

    action = engine._select_ai_action(participant, active_pokemon, StubBattle())

    assert action.move.name == "Mystery One"
    reasons = participant.last_ai_debug_trace.scores[0].reasons
    assert "status_baseline" in reasons
    assert "incomplete_dex" in reasons


def test_trainer_skilled_scores_super_effective_move_higher_than_wild_basic():
    from pokemon.battle._shared import _normalize_key
    from pokemon.battle.ai_profiles import DEFAULT_AI_PROFILES
    from pokemon.battle.ai_scoring import score_ai_moves

    move = types.SimpleNamespace(name="Water Gun", pp=None, current_pp=None)
    movedex = {
        _normalize_key("Water Gun"): types.SimpleNamespace(
            raw={
                "name": "Water Gun",
                "type": "Water",
                "category": "Special",
                "basePower": 40,
                "accuracy": 100,
                "pp": 25,
            }
        )
    }
    user = types.SimpleNamespace(name="Starmie", types=["Water"], stats={"special_attack": 80})
    target = types.SimpleNamespace(
        name="Geodude",
        types=["Rock", "Ground"],
        hp=500,
        max_hp=500,
        stats={"special_defense": 40},
    )

    wild_score = score_ai_moves(
        types.SimpleNamespace(profile=DEFAULT_AI_PROFILES["wild_basic"]),
        [move],
        user=user,
        target=target,
        movedex=movedex,
        raw_getter=lambda entry: dict(getattr(entry, "raw", {}) or {}),
    )[0]
    skilled_score = score_ai_moves(
        types.SimpleNamespace(profile=DEFAULT_AI_PROFILES["trainer_skilled"]),
        [move],
        user=user,
        target=target,
        movedex=movedex,
        raw_getter=lambda entry: dict(getattr(entry, "raw", {}) or {}),
    )[0]

    assert skilled_score.score > wild_score.score
    assert "weighted_type_effectiveness" in skilled_score.reasons


def test_gym_leader_candidate_band_is_narrower_than_wild_basic():
    from pokemon.battle.ai_profiles import DEFAULT_AI_PROFILES
    from pokemon.battle.ai_scoring import top_ai_move_candidates

    candidates = [
        _scored_move("best", 100.0),
        _scored_move("near", 70.0),
        _scored_move("far", 50.0),
    ]
    wild_top = top_ai_move_candidates(
        candidates,
        context=types.SimpleNamespace(profile=DEFAULT_AI_PROFILES["wild_basic"]),
    )
    gym_top = top_ai_move_candidates(
        candidates,
        context=types.SimpleNamespace(profile=DEFAULT_AI_PROFILES["gym_leader"]),
    )

    assert [candidate.key for candidate in wild_top] == ["best", "near"]
    assert [candidate.key for candidate in gym_top] == ["best"]


def test_feature_boss_tolerates_strong_inaccurate_move_more_than_gym_leader():
    from pokemon.battle._shared import _normalize_key
    from pokemon.battle.ai_profiles import DEFAULT_AI_PROFILES
    from pokemon.battle.ai_scoring import score_ai_moves

    move = types.SimpleNamespace(name="Mega Punch", pp=None, current_pp=None)
    movedex = {
        _normalize_key("Mega Punch"): types.SimpleNamespace(
            raw={
                "name": "Mega Punch",
                "type": "Normal",
                "category": "Physical",
                "basePower": 120,
                "accuracy": 60,
                "pp": 5,
            }
        )
    }
    user = types.SimpleNamespace(name="Boss Mon", types=["Normal"], stats={"attack": 90})
    target = types.SimpleNamespace(
        name="Target",
        types=["Water"],
        hp=500,
        max_hp=500,
        stats={"defense": 90},
    )

    gym_score = score_ai_moves(
        types.SimpleNamespace(profile=DEFAULT_AI_PROFILES["gym_leader"]),
        [move],
        user=user,
        target=target,
        movedex=movedex,
        raw_getter=lambda entry: dict(getattr(entry, "raw", {}) or {}),
    )[0]
    boss_score = score_ai_moves(
        types.SimpleNamespace(profile=DEFAULT_AI_PROFILES["feature_boss"]),
        [move],
        user=user,
        target=target,
        movedex=movedex,
        raw_getter=lambda entry: dict(getattr(entry, "raw", {}) or {}),
    )[0]

    assert boss_score.score > gym_score.score
    assert "weighted_accuracy" in boss_score.reasons
    assert "risk_tolerance_0.7" in boss_score.reasons


def _scored_move(key: str, score: float):
    from pokemon.battle.ai_scoring import ScoredAIMove

    return ScoredAIMove(
        source_move=None,
        key=key,
        display_name=key,
        pp=None,
        priority=0,
        power=0,
        accuracy=100,
        move_type=None,
        category="",
        raw={},
        score=score,
        reasons=(),
    )
