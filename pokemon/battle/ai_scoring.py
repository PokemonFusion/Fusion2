"""Move-only AI scoring helpers for runtime battle action selection."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from ._shared import _normalize_key
from .ai_profiles import AIScoringWeights
from .damage import stab_multiplier, type_effectiveness


DEFAULT_SCORING_WEIGHTS = AIScoringWeights()


@dataclass(frozen=True)
class ScoredAIMove:
    """A move candidate with enough data for engine action creation."""

    source_move: Any
    key: str
    display_name: str
    pp: int | None
    priority: int
    power: int
    accuracy: int | float | bool
    move_type: str | None
    category: str
    raw: dict[str, Any]
    score: float
    reasons: tuple[str, ...]


def score_ai_moves(
    context,
    moves: Sequence[Any],
    *,
    user: Any,
    target: Any,
    movedex: Mapping[str, Any],
    raw_getter: Callable[[Any], dict[str, Any]],
) -> list[ScoredAIMove]:
    """Return legal, scored move candidates for the current AI decision.

    This is intentionally a cheap heuristic, not the real damage calculator.
    It scores only move actions and leaves switching, items, doubles strategy,
    and full setup/status intelligence for later phases.
    """

    scored: list[ScoredAIMove] = []
    for move in moves:
        candidate = _score_one_move(
            context,
            move,
            user=user,
            target=target,
            movedex=movedex,
            raw_getter=raw_getter,
        )
        if candidate is not None:
            scored.append(candidate)
    return scored


def choose_weighted_ai_move(
    scored_moves: Sequence[ScoredAIMove],
    *,
    rng: random.Random | None = None,
    context: Any | None = None,
    candidate_band: float | None = None,
    randomness: float | None = None,
) -> ScoredAIMove | None:
    """Choose a move from top candidates using weighted random selection."""

    if not scored_moves:
        return None
    best_score = max(candidate.score for candidate in scored_moves)
    if best_score <= 0:
        return scored_moves[0]

    top = top_ai_move_candidates(
        scored_moves,
        context=context,
        candidate_band=candidate_band,
    )
    if len(top) == 1:
        return top[0]

    weights_config = _weights_for_context(context)
    profile_randomness = _clamp(
        randomness if randomness is not None else weights_config.randomness,
        0.0,
        1.0,
    )
    weight_power = max(0.25, 1.5 - profile_randomness)
    picker = rng or random
    weights = [max(candidate.score, 0.01) ** weight_power for candidate in top]
    try:
        return picker.choices(list(top), weights=weights, k=1)[0]
    except AttributeError:  # pragma: no cover - available on supported Python
        if not hasattr(picker, "random"):
            return top[0]
        total = sum(weights)
        roll = picker.random() * total
        running = 0.0
        for candidate, weight in zip(top, weights):
            running += weight
            if roll <= running:
                return candidate
        return top[-1]


def top_ai_move_candidates(
    scored_moves: Sequence[ScoredAIMove],
    *,
    context: Any | None = None,
    candidate_band: float | None = None,
) -> list[ScoredAIMove]:
    """Return candidates close enough to the best score for weighted choice."""

    if not scored_moves:
        return []
    best_score = max(candidate.score for candidate in scored_moves)
    if best_score <= 0:
        return [scored_moves[0]]
    band = candidate_band_for_context(context, candidate_band=candidate_band)
    threshold = best_score * band
    return [candidate for candidate in scored_moves if candidate.score >= threshold]


def candidate_band_for_context(
    context: Any | None,
    *,
    candidate_band: float | None = None,
) -> float:
    """Return the clamped top-candidate band for an AI profile context."""

    weights = _weights_for_context(context)
    return _clamp(
        candidate_band if candidate_band is not None else weights.top_candidate_band,
        0.0,
        1.0,
    )


def fallback_scored_move(
    move: Any,
    *,
    movedex: Mapping[str, Any],
    raw_getter: Callable[[Any], dict[str, Any]],
    reason: str = "fallback_first_legal",
) -> ScoredAIMove:
    """Build a safe candidate when scoring cannot find a better move."""

    key, dex_entry, raw = _move_lookup(move, movedex, raw_getter)
    return _candidate_from_parts(
        move,
        key=key,
        dex_entry=dex_entry,
        raw=raw,
        score=0.0,
        reasons=(reason,),
    )


def _score_one_move(
    context,
    move: Any,
    *,
    user: Any,
    target: Any,
    movedex: Mapping[str, Any],
    raw_getter: Callable[[Any], dict[str, Any]],
) -> ScoredAIMove | None:
    key, dex_entry, raw = _move_lookup(move, movedex, raw_getter)
    weights = _weights_for_context(context)
    pp = _move_pp(move, dex_entry, raw)
    if pp is not None and pp <= 0:
        return None

    power = _move_power(move, dex_entry, raw)
    accuracy = _move_accuracy(move, dex_entry, raw)
    raw_accuracy_factor = _accuracy_factor(accuracy)
    accuracy_factor = _weighted_accuracy_factor(raw_accuracy_factor, weights)
    category = str(raw.get("category") or getattr(dex_entry, "category", "") or getattr(move, "category", "") or "")
    move_type = _move_type(move, dex_entry, raw)
    priority = _move_priority(move, raw)
    reasons: list[str] = ["profile_weighted"]

    if raw_accuracy_factor < 1.0:
        reasons.append(f"accuracy_{int(round(raw_accuracy_factor * 100))}")
        reasons.append("weighted_accuracy")
        reasons.append(f"risk_tolerance_{_fmt_weight(weights.risk_tolerance)}")

    if power <= 0 or category.lower() == "status":
        # Status/support intelligence is deliberately shallow in this slice.
        score = weights.status_baseline * accuracy_factor
        reasons.append("status_baseline")
        if not raw:
            reasons.append("incomplete_dex")
        return _candidate_from_parts(
            move,
            key=key,
            dex_entry=dex_entry,
            raw=raw,
            score=score,
            reasons=tuple(reasons),
        )

    score = float(power) * weights.damage_weight * accuracy_factor
    if power < 40:
        reasons.append("low_power")

    stab = _safe_stab(user, move_type)
    if stab > 1.0:
        score *= _weighted_multiplier(stab, weights.stab_weight)
        reasons.append("stab")
        if weights.stab_weight != 1.0:
            reasons.append("weighted_stab")

    effectiveness = _safe_type_effectiveness(target, move_type)
    if effectiveness == 0:
        score = 0.0
        reasons.append("immune")
    elif effectiveness > 1.0:
        score *= _weighted_multiplier(effectiveness, weights.type_effectiveness_weight)
        reasons.append("super_effective")
        reasons.append("weighted_type_effectiveness")
    elif 0 < effectiveness < 1.0:
        score *= _weighted_multiplier(effectiveness, weights.type_effectiveness_weight)
        reasons.append("resisted")
        reasons.append("weighted_type_effectiveness")

    stat_ratio = _stat_ratio(user, target, category)
    if stat_ratio != 1.0:
        score *= stat_ratio
        reasons.append("stat_preference")

    estimated_damage = float(power) * max(stab, 1.0) * max(effectiveness, 0.0) * stat_ratio
    target_hp = _number_attr(target, "hp", "current_hp")
    if target_hp is not None and estimated_damage >= target_hp and effectiveness > 0:
        score += 30.0 * weights.ko_bonus_weight
        reasons.append("ko_candidate")
        reasons.append("weighted_ko_bonus")
        if target_hp > 0:
            score -= (
                min(15.0, max(0.0, estimated_damage - target_hp) / target_hp * 3.0)
                * weights.overkill_penalty_weight
            )
            reasons.append("overkill_checked")
            if weights.overkill_penalty_weight != 1.0:
                reasons.append("weighted_overkill_penalty")

    if priority > 0:
        bonus = 0.0
        target_max_hp = _number_attr(target, "max_hp")
        if target_hp is not None and target_max_hp and target_hp / target_max_hp <= 0.25:
            bonus += 5.0
        user_speed = _stat_value(user, "speed", "spe")
        target_speed = _stat_value(target, "speed", "spe")
        if user_speed is not None and target_speed is not None and user_speed < target_speed:
            bonus += 2.0 * priority
        if bonus:
            score += bonus * weights.priority_weight
            reasons.append("priority")
            if weights.priority_weight != 1.0:
                reasons.append("weighted_priority")

    if not raw:
        reasons.append("incomplete_dex")

    return _candidate_from_parts(
        move,
        key=key,
        dex_entry=dex_entry,
        raw=raw,
        score=max(0.0, score),
        reasons=tuple(reasons or ("damage",)),
    )


def _candidate_from_parts(
    move: Any,
    *,
    key: str,
    dex_entry: Any,
    raw: dict[str, Any],
    score: float,
    reasons: tuple[str, ...],
) -> ScoredAIMove:
    return ScoredAIMove(
        source_move=move,
        key=key,
        display_name=str(raw.get("name") or getattr(move, "name", None) or key),
        pp=_move_pp(move, dex_entry, raw),
        priority=_move_priority(move, raw),
        power=_move_power(move, dex_entry, raw),
        accuracy=_move_accuracy(move, dex_entry, raw),
        move_type=_move_type(move, dex_entry, raw),
        category=str(raw.get("category") or getattr(dex_entry, "category", "") or getattr(move, "category", "") or ""),
        raw=raw,
        score=float(score),
        reasons=reasons,
    )


def _move_lookup(
    move: Any,
    movedex: Mapping[str, Any],
    raw_getter: Callable[[Any], dict[str, Any]],
) -> tuple[str, Any, dict[str, Any]]:
    key = _normalize_key(getattr(move, "key", None) or getattr(move, "name", ""))
    dex_entry = movedex.get(key)
    raw = dict(raw_getter(dex_entry) or {})
    return key, dex_entry, raw


def _move_pp(move: Any, dex_entry: Any, raw: Mapping[str, Any]) -> int | None:
    for value in (
        getattr(move, "current_pp", None),
        getattr(move, "pp", None),
        raw.get("pp"),
        getattr(dex_entry, "pp", None),
    ):
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _move_power(move: Any, dex_entry: Any, raw: Mapping[str, Any]) -> int:
    for value in (
        raw.get("basePower"),
        raw.get("power"),
        getattr(dex_entry, "power", None),
        getattr(move, "power", None),
    ):
        if isinstance(value, (int, float)) and value > 0:
            return int(value)
    return 0


def _move_accuracy(move: Any, dex_entry: Any, raw: Mapping[str, Any]) -> int | float | bool:
    for value in (
        raw.get("accuracy"),
        getattr(dex_entry, "accuracy", None),
        getattr(move, "accuracy", None),
    ):
        if value is not None:
            return value
    return 100


def _accuracy_factor(accuracy: Any) -> float:
    if accuracy is True or accuracy is None:
        return 1.0
    if accuracy is False:
        return 0.0
    if isinstance(accuracy, (int, float)):
        if accuracy <= 1:
            return max(0.0, float(accuracy))
        return max(0.0, min(1.0, float(accuracy) / 100.0))
    return 1.0


def _weighted_accuracy_factor(accuracy_factor: float, weights: AIScoringWeights) -> float:
    if accuracy_factor >= 1.0:
        return 1.0
    if accuracy_factor <= 0.0:
        return 0.0
    risk = _clamp(weights.risk_tolerance, 0.0, 1.0)
    accuracy_weight = max(0.05, float(weights.accuracy_weight))
    exponent = max(0.2, accuracy_weight * (1.0 - (0.65 * risk)))
    adjusted = accuracy_factor ** exponent
    risk_cap = accuracy_factor + ((1.0 - accuracy_factor) * risk * 0.5)
    return _clamp(min(adjusted, risk_cap), 0.0, 1.0)


def _weighted_multiplier(multiplier: float, weight: float) -> float:
    if multiplier <= 0:
        return 0.0
    return max(0.0, 1.0 + ((multiplier - 1.0) * float(weight)))


def _move_type(move: Any, dex_entry: Any, raw: Mapping[str, Any]) -> str | None:
    value = raw.get("type") or getattr(dex_entry, "type", None) or getattr(move, "type", None)
    return str(value) if value else None


def _move_priority(move: Any, raw: Mapping[str, Any]) -> int:
    for value in (getattr(move, "priority", None), raw.get("priority")):
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            continue
    return 0


def _safe_stab(user: Any, move_type: str | None) -> float:
    if not move_type:
        return 1.0
    try:
        return float(stab_multiplier(user, _MoveLike(move_type)))
    except Exception:
        types = [str(t).lower() for t in getattr(user, "types", []) or []]
        return 1.5 if str(move_type).lower() in types else 1.0


def _safe_type_effectiveness(target: Any, move_type: str | None) -> float:
    if not move_type:
        return 1.0
    try:
        return float(type_effectiveness(target, _MoveLike(move_type)))
    except Exception:
        return 1.0


def _stat_ratio(user: Any, target: Any, category: str) -> float:
    lower = category.lower()
    if lower == "physical":
        attack = _stat_value(user, "attack", "atk")
        defense = _stat_value(target, "defense", "def")
    elif lower == "special":
        attack = _stat_value(user, "special_attack", "spa")
        defense = _stat_value(target, "special_defense", "spd")
    else:
        return 1.0

    if attack is None or defense is None or defense <= 0:
        return 1.0
    return max(0.5, min(1.5, attack / defense))


def _stat_value(pokemon: Any, *names: str) -> float | None:
    stats = getattr(pokemon, "stats", None) or getattr(pokemon, "base_stats", None)
    for name in names:
        for source in (stats, pokemon):
            if source is None:
                continue
            value = getattr(source, name, None)
            if value is None and isinstance(source, Mapping):
                value = source.get(name)
            number = _to_float(value)
            if number is not None:
                return number
    return None


def _number_attr(obj: Any, *names: str) -> float | None:
    for name in names:
        number = _to_float(getattr(obj, name, None))
        if number is not None:
            return number
    return None


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _weights_for_context(context: Any | None) -> AIScoringWeights:
    profile = getattr(context, "profile", None)
    weights = getattr(profile, "scoring", None)
    if isinstance(weights, AIScoringWeights):
        return weights
    risk = getattr(profile, "risk_tolerance", DEFAULT_SCORING_WEIGHTS.risk_tolerance)
    risk_number = _to_float(risk)
    if risk_number is None:
        risk_number = DEFAULT_SCORING_WEIGHTS.risk_tolerance
    return AIScoringWeights(risk_tolerance=_clamp(risk_number, 0.0, 1.0))


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _fmt_weight(value: float) -> str:
    return f"{float(value):.2f}".rstrip("0").rstrip(".")


@dataclass(frozen=True)
class _MoveLike:
    type: str


__all__ = [
    "ScoredAIMove",
    "candidate_band_for_context",
    "choose_weighted_ai_move",
    "fallback_scored_move",
    "score_ai_moves",
    "top_ai_move_candidates",
]
