"""Small battle AI profile, context, and debug-trace scaffolding."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


DEFAULT_INTENT = "safe_damage"


@dataclass(frozen=True)
class AIScoringWeights:
    """Profile-tunable weights for the current move-only AI scorer."""

    damage_weight: float = 1.0
    accuracy_weight: float = 1.4
    stab_weight: float = 1.0
    type_effectiveness_weight: float = 1.0
    ko_bonus_weight: float = 1.0
    overkill_penalty_weight: float = 1.0
    priority_weight: float = 1.0
    status_baseline: float = 8.0
    risk_tolerance: float = 0.5
    top_candidate_band: float = 0.8
    randomness: float = 0.55


@dataclass(frozen=True)
class AIProfile:
    """Resolved AI behavior profile for an AI-controlled battler."""

    key: str
    level: int = 1
    risk_tolerance: float = 0.5
    switch_likelihood: float = 0.0
    item_policy: str = "none"
    knowledge_policy: str = "visible_only"
    allowed_intents: tuple[str, ...] = (DEFAULT_INTENT,)
    strategy_key: str | None = None
    scoring: AIScoringWeights = field(default_factory=AIScoringWeights)


@dataclass(frozen=True)
class BattleAIContext:
    """Lightweight battle view used by future AI selectors."""

    profile: AIProfile
    requested_profile_key: str | None
    participant_name: str
    pokemon_name: str
    battle_type: str
    encounter_kind: str
    visible_opponents: tuple[str, ...] = ()
    visible_allies: tuple[str, ...] = ()
    active_hp: int | None = None
    active_max_hp: int | None = None
    turn: int | None = None


@dataclass(frozen=True)
class AIScoreReason:
    """A single scored candidate captured for AI debugging."""

    action: str
    score: float
    reasons: tuple[str, ...] = ()


@dataclass
class AIDebugTrace:
    """Non-player-facing record of one AI decision."""

    profile_key: str
    requested_profile_key: str | None = None
    resolved_profile_key: str | None = None
    actor_name: str | None = None
    target_name: str | None = None
    chosen_intent: str | None = None
    legal_actions_considered: list[str] = field(default_factory=list)
    scores: list[AIScoreReason] = field(default_factory=list)
    chosen_action: str | None = None

    def __post_init__(self) -> None:
        if self.resolved_profile_key is None:
            self.resolved_profile_key = self.profile_key

    def add_action(self, action: str, score: float = 0.0, *reasons: str) -> None:
        """Record one legal action candidate."""

        key = str(action)
        self.legal_actions_considered.append(key)
        self.scores.append(AIScoreReason(key, float(score), tuple(reasons)))

    def choose(self, action: str, *, intent: str | None = None) -> None:
        """Record the final chosen action and optional intent."""

        self.chosen_action = str(action)
        if intent is not None:
            self.chosen_intent = intent

    def to_dict(self) -> dict[str, Any]:
        """Return a compact serializable representation."""

        return {
            "profile_key": self.profile_key,
            "requested_profile_key": self.requested_profile_key,
            "resolved_profile_key": self.resolved_profile_key,
            "actor_name": self.actor_name,
            "target_name": self.target_name,
            "chosen_intent": self.chosen_intent,
            "legal_actions_considered": list(self.legal_actions_considered),
            "scores": [
                {
                    "action": score.action,
                    "score": score.score,
                    "reasons": list(score.reasons),
                }
                for score in self.scores
            ],
            "chosen_action": self.chosen_action,
        }


DEFAULT_AI_PROFILES: dict[str, AIProfile] = {
    "wild_basic": AIProfile(
        key="wild_basic",
        level=0,
        risk_tolerance=0.65,
        switch_likelihood=0.0,
        item_policy="none",
        allowed_intents=(DEFAULT_INTENT,),
        scoring=AIScoringWeights(
            damage_weight=1.0,
            accuracy_weight=0.9,
            stab_weight=0.85,
            type_effectiveness_weight=0.6,
            ko_bonus_weight=0.55,
            overkill_penalty_weight=0.5,
            priority_weight=0.6,
            status_baseline=7.0,
            risk_tolerance=0.65,
            top_candidate_band=0.65,
            randomness=0.85,
        ),
    ),
    "trainer_basic": AIProfile(
        key="trainer_basic",
        level=1,
        risk_tolerance=0.5,
        switch_likelihood=0.02,
        item_policy="none",
        allowed_intents=(DEFAULT_INTENT, "status_target"),
        scoring=AIScoringWeights(
            top_candidate_band=0.78,
            randomness=0.55,
        ),
    ),
    "trainer_skilled": AIProfile(
        key="trainer_skilled",
        level=3,
        risk_tolerance=0.35,
        switch_likelihood=0.18,
        item_policy="conservative",
        allowed_intents=(
            "finish_target",
            DEFAULT_INTENT,
            "setup",
            "status_target",
            "preserve_self",
        ),
        scoring=AIScoringWeights(
            damage_weight=1.05,
            accuracy_weight=1.7,
            stab_weight=1.05,
            type_effectiveness_weight=1.25,
            ko_bonus_weight=1.25,
            overkill_penalty_weight=1.1,
            priority_weight=1.1,
            status_baseline=7.0,
            risk_tolerance=0.35,
            top_candidate_band=0.86,
            randomness=0.35,
        ),
    ),
    "gym_leader": AIProfile(
        key="gym_leader",
        level=5,
        risk_tolerance=0.25,
        switch_likelihood=0.28,
        item_policy="budgeted",
        allowed_intents=(
            "finish_target",
            DEFAULT_INTENT,
            "setup",
            "status_target",
            "control_field",
            "preserve_self",
            "pivot",
        ),
        strategy_key="gym",
        scoring=AIScoringWeights(
            damage_weight=1.05,
            accuracy_weight=2.3,
            stab_weight=1.1,
            type_effectiveness_weight=1.4,
            ko_bonus_weight=1.5,
            overkill_penalty_weight=1.4,
            priority_weight=1.2,
            status_baseline=5.5,
            risk_tolerance=0.25,
            top_candidate_band=0.9,
            randomness=0.15,
        ),
    ),
    "feature_boss": AIProfile(
        key="feature_boss",
        level=5,
        risk_tolerance=0.7,
        switch_likelihood=0.25,
        item_policy="scripted",
        allowed_intents=(
            "finish_target",
            DEFAULT_INTENT,
            "setup",
            "status_target",
            "control_field",
            "preserve_self",
            "pivot",
            "stall_turn",
            "support_ally",
        ),
        strategy_key="feature",
        scoring=AIScoringWeights(
            damage_weight=1.15,
            accuracy_weight=1.1,
            stab_weight=1.15,
            type_effectiveness_weight=1.35,
            ko_bonus_weight=1.5,
            overkill_penalty_weight=1.0,
            priority_weight=1.25,
            status_baseline=6.5,
            risk_tolerance=0.7,
            top_candidate_band=0.85,
            randomness=0.25,
        ),
    ),
}

AI_PROFILE_ALIASES: dict[str, str] = {
    "basic": "trainer_basic",
    "trainer": "trainer_basic",
    "npc": "trainer_basic",
    "minor_trainer": "trainer_basic",
    "skilled": "trainer_skilled",
    "wild": "wild_basic",
    "gym": "gym_leader",
    "leader": "gym_leader",
    "boss": "feature_boss",
}


def resolve_ai_profile(
    profile_key: str | None = None,
    *,
    participant: Any | None = None,
    battle: Any | None = None,
    fallback_key: str | None = None,
) -> AIProfile:
    """Resolve an AI profile from explicit, participant, or battle metadata."""

    key = _requested_profile_key(profile_key, participant)
    if not key:
        key = fallback_key or _default_profile_key(participant=participant, battle=battle)

    normalized = _normalize_profile_key(key)
    profile = DEFAULT_AI_PROFILES.get(normalized)
    if profile is not None:
        return profile

    fallback = _normalize_profile_key(
        fallback_key or _default_profile_key(participant=participant, battle=battle)
    )
    return DEFAULT_AI_PROFILES.get(fallback, DEFAULT_AI_PROFILES["trainer_basic"])


def build_battle_ai_context(
    participant: Any,
    active_pokemon: Any,
    battle: Any,
    *,
    profile_key: str | None = None,
) -> BattleAIContext:
    """Build a compact battle context for the current AI decision."""

    requested_key = _requested_profile_key(profile_key, participant)
    profile = resolve_ai_profile(
        requested_key,
        participant=participant,
        battle=battle,
    )
    battle_type = _battle_type_key(battle)
    opponents = _participants_to_names(_safe_opponents_of(battle, participant))
    allies = _participants_to_names(_safe_allies_of(battle, participant))
    return BattleAIContext(
        profile=profile,
        requested_profile_key=requested_key,
        participant_name=_name(participant, "AI"),
        pokemon_name=_name(active_pokemon, "Pokemon"),
        battle_type=battle_type,
        encounter_kind=_encounter_kind(battle, battle_type),
        visible_opponents=opponents,
        visible_allies=allies,
        active_hp=_int_or_none(
            getattr(active_pokemon, "hp", getattr(active_pokemon, "current_hp", None))
        ),
        active_max_hp=_int_or_none(getattr(active_pokemon, "max_hp", None)),
        turn=_int_or_none(getattr(battle, "turn", getattr(battle, "turn_count", None))),
    )


def attach_ai_debug_trace(
    participant: Any,
    battle: Any,
    trace: AIDebugTrace,
    *,
    limit: int = 20,
) -> None:
    """Attach a trace for future admin inspection without emitting output."""

    try:
        setattr(participant, "last_ai_debug_trace", trace)
    except Exception:
        pass
    try:
        setattr(battle, "last_ai_debug_trace", trace)
    except Exception:
        pass
    try:
        traces = getattr(battle, "ai_debug_traces", None)
        if not isinstance(traces, list):
            traces = []
            setattr(battle, "ai_debug_traces", traces)
        traces.append(trace)
        if limit > 0 and len(traces) > limit:
            del traces[:-limit]
    except Exception:
        pass


def _normalize_profile_key(key: Any) -> str:
    text = str(key or "").strip().lower().replace("-", "_").replace(" ", "_")
    return AI_PROFILE_ALIASES.get(text, text or "trainer_basic")


def _requested_profile_key(explicit_key: str | None, participant: Any | None) -> str | None:
    return _first_text(
        explicit_key,
        getattr(participant, "ai_profile", None),
        getattr(participant, "ai_profile_key", None),
        getattr(participant, "profile_key", None),
        _db_attr(participant, "ai_profile"),
        _db_attr(getattr(participant, "player", None), "ai_profile"),
        _db_attr(getattr(participant, "trainer", None), "ai_profile"),
    )


def _default_profile_key(*, participant: Any | None, battle: Any | None) -> str:
    if bool(getattr(participant, "is_wild", False)):
        return "wild_basic"
    if bool(getattr(participant, "is_npc", False)):
        return "trainer_basic"
    battle_type = _battle_type_key(battle).lower()
    if battle_type == "wild":
        return "wild_basic"
    if battle_type == "trainer":
        return "trainer_basic"
    return "trainer_basic"


def _battle_type_key(battle: Any) -> str:
    battle_type = getattr(battle, "type", None)
    name = getattr(battle_type, "name", None)
    if name:
        return str(name).lower()
    if battle_type is not None:
        return str(battle_type).lower()
    return "unknown"


def _encounter_kind(battle: Any, battle_type: str) -> str:
    state = getattr(battle, "state", None)
    kind = getattr(state, "encounter_kind", None)
    if kind:
        return str(kind).lower()
    return battle_type


def _participants_to_names(participants: tuple[Any, ...]) -> tuple[str, ...]:
    return tuple(_name(participant, "Unknown") for participant in participants)


def _safe_opponents_of(battle: Any, participant: Any) -> tuple[Any, ...]:
    try:
        return tuple(battle.opponents_of(participant))
    except Exception:
        return ()


def _safe_allies_of(battle: Any, participant: Any) -> tuple[Any, ...]:
    team = getattr(participant, "team", None)
    members = getattr(battle, "participants", None)
    if team is None or not members:
        return ()
    return tuple(
        member
        for member in members
        if member is not participant and getattr(member, "team", None) == team
    )


def _name(value: Any, fallback: str) -> str:
    return str(
        getattr(value, "name", None)
        or getattr(value, "key", None)
        or getattr(value, "species", None)
        or fallback
    )


def _first_text(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _db_attr(obj: Any, attr: str) -> Any:
    db = getattr(obj, "db", None)
    if db is None:
        return None
    try:
        if isinstance(db, dict):
            return db.get(attr)
        return getattr(db, attr, None)
    except Exception:
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "AIDebugTrace",
    "AIScoringWeights",
    "AIProfile",
    "AIScoreReason",
    "BattleAIContext",
    "DEFAULT_AI_PROFILES",
    "attach_ai_debug_trace",
    "build_battle_ai_context",
    "resolve_ai_profile",
]
