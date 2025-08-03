"""AI helpers for choosing Pokémon moves.

This module implements :class:`AIMoveSelector`, a light–weight move
selection helper used by the battle engine.  The selector exposes a
single public method, :meth:`AIMoveSelector.select_move`, which scores
available moves according to an AI difficulty level and optional
personality profile.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import random
from typing import Dict, List, Sequence

from .damage import stab_multiplier, type_effectiveness

try:  # pragma: no cover - type hints only
    from pokemon.dex.entities import Move  # type: ignore
except Exception:  # pragma: no cover - fallback for tests
    Move = object  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class ScoredMove:
    """Internal container binding a move to its computed score."""

    move: Move
    score: float


class AIMoveSelector:
    """Select moves for AI controlled Pokémon.

    The selector evaluates each candidate move using a tiered system that
    unlocks additional behaviour at higher AI levels.  Personalities can
    further tweak scoring to favour certain move types.
    """

    allowed_sources = {
        0: ["level_up"],
        1: ["level_up", "tm_basic"],
        2: ["level_up", "tm_all"],
        3: ["level_up", "tm_all", "egg"],
        4: ["level_up", "tm_all", "egg", "tutor"],
        5: ["all"],
    }

    personality_weights = {
        "aggressive": (1.2, 0.8),
        "tactician": (0.8, 1.2),
        "balanced": (1.0, 1.0),
        "gimmick": (0.7, 1.3),
    }

    def select_move(self, ai_level: int, ai_personality: str, pokemon, opponent, battle_state) -> Move:
        """Return the best move for the current situation.

        Parameters
        ----------
        ai_level:
            Difficulty tier of the AI, unlocking additional logic.
        ai_personality:
            Optional personality string.  See ``personality_weights``.
        pokemon:
            The active Pokémon controlled by the AI.
        opponent:
            The opposing Pokémon.
        battle_state:
            Arbitrary container with information about the battle.  The
            selector only inspects a handful of optional keys such as
            ``turn`` or ``opponent_likely_to_switch``.
        """

        moves = list(getattr(pokemon, "moves", []))
        moves = [m for m in moves if self._move_allowed(m, ai_level)]
        moves = self._filter_invalid_moves(moves, pokemon, opponent, ai_level)

        if not moves:
            # Fall back to any move; even an invalid one is better than no action
            return random.choice(list(getattr(pokemon, "moves", [])))

        scored: List[ScoredMove] = []
        for move in moves:
            dmg = self._score_move_by_damage(move, pokemon, opponent, ai_level)
            util = self._score_move_by_utility(
                move, pokemon, opponent, battle_state, ai_level
            )
            total = self._apply_personality_weighting(dmg, util, ai_personality)
            scored.append(ScoredMove(move, total))

        scored.sort(key=lambda sm: sm.score, reverse=True)
        best = scored[0]
        logger.debug("AI evaluated moves: %s", scored)
        if best.score <= 0:
            return random.choice([m.move for m in scored])
        return best.move

    # ------------------------------------------------------------------
    # Helper methods
    def _move_allowed(self, move: Move, ai_level: int) -> bool:
        sources = self.allowed_sources.get(ai_level, self.allowed_sources[5])
        src = getattr(move, "source", "level_up")
        if "all" in sources:
            return True
        if isinstance(src, Sequence) and not isinstance(src, (str, bytes)):
            return any(s in sources for s in src)
        return src in sources

    def _filter_invalid_moves(self, moves: List[Move], pokemon, opponent, ai_level: int) -> List[Move]:
        valid: List[Move] = []
        for move in moves:
            pp = getattr(move, "pp", 1)
            if isinstance(pp, int) and pp <= 0:
                continue
            if ai_level >= 2:
                try:
                    eff = type_effectiveness(opponent, move)
                except Exception:
                    eff = 1.0
                if eff == 0:
                    continue
            # very small status move filtering
            if getattr(move, "category", "").lower() == "status":
                tags = set(getattr(move, "tags", []))
                if "status" in tags and getattr(opponent, "status", 0):
                    continue
            valid.append(move)
        return valid

    def _score_move_by_damage(self, move: Move, pokemon, opponent, ai_level: int) -> float:
        category = getattr(move, "category", "")
        if category.lower() == "status":
            return 0.0

        power = getattr(move, "power", 0) or 0
        accuracy = getattr(move, "accuracy", 100)
        score = power * (float(accuracy) / 100.0 if isinstance(accuracy, (int, float)) else 1.0)

        if ai_level >= 2:
            try:
                stab = stab_multiplier(pokemon, move)
            except Exception:
                stab = 1.0
            try:
                eff = type_effectiveness(opponent, move)
            except Exception:
                eff = 1.0
            score *= stab * eff

        priority = getattr(move, "priority", 0)
        if isinstance(priority, (int, float)) and priority:
            score *= 1 + (0.1 * priority)
        return score

    def _score_move_by_utility(
        self, move: Move, pokemon, opponent, battle_state, ai_level: int
    ) -> float:
        if ai_level < 3:
            return 0.0

        tags = set(getattr(move, "tags", []))
        score = 0.0

        hp = getattr(pokemon, "hp", None)
        max_hp = getattr(pokemon, "max_hp", None)
        if "heal" in tags and hp is not None and max_hp:
            if max_hp > 0 and hp / max_hp < 0.5:
                score += 40

        if "setup" in tags:
            boosts = getattr(pokemon, "boosts", {})
            if isinstance(boosts, dict) and not any(boosts.values()):
                score += 30

        if "status" in tags and not getattr(opponent, "status", 0):
            score += 30

        if "hazard" in tags and battle_state and battle_state.get("turn", 0) <= 2:
            score += 20

        if ai_level >= 4 and battle_state:
            if battle_state.get("opponent_likely_to_switch"):
                if "hazard" in tags:
                    score += 40
                if "pivot" in tags:
                    score += 30

        if ai_level >= 5:
            if "combo_setup" in tags:
                score += 25
            if "combo_execute" in tags and battle_state and battle_state.get("combo_ready"):
                score += 35
        return score

    def _apply_personality_weighting(
        self, damage_score: float, utility_score: float, personality: str
    ) -> float:
        weights = self.personality_weights.get(personality, (1.0, 1.0))
        dmg_w, util_w = weights
        return (damage_score * dmg_w) + (utility_score * util_w)


def generate_moveset(pokemon, ai_level: int, ai_personality: str) -> List[Move]:
    """Return up to four synergistic moves for an AI controlled Pokémon.

    The routine filters the Pokémon's move pool according to the AI level and
    then scores the remaining options based on the Pokémon's inferred role and
    optional personality profile.  Higher AI levels (``>= 3``) unlock utility
    considerations such as setup and status moves.

    Parameters
    ----------
    pokemon:
        Pokémon-like object exposing ``types`` and ``move_pool`` or ``moves``.
    ai_level:
        Difficulty tier guiding how many move sources are available.
    ai_personality:
        Personality string influencing damage versus utility preferences.
    """

    sources = AIMoveSelector.allowed_sources.get(
        ai_level, AIMoveSelector.allowed_sources[5]
    )

    def allowed(move: Move) -> bool:
        src = getattr(move, "source", "level_up")
        if "all" in sources:
            return True
        if isinstance(src, Sequence) and not isinstance(src, (str, bytes)):
            return any(s in sources for s in src)
        return src in sources

    move_pool = list(getattr(pokemon, "move_pool", []))
    if not move_pool:
        move_pool = list(getattr(pokemon, "moves", []))
    candidates = [m for m in move_pool if allowed(m)]

    if ai_level < 3:
        return candidates[:4]

    if not candidates:
        return []

    def infer_role() -> str:
        role = getattr(pokemon, "role", None)
        if role:
            return role
        stats = getattr(pokemon, "stats", None)
        if stats:
            atk = getattr(stats, "attack", getattr(stats, "atk", 0))
            spa = getattr(stats, "special_attack", getattr(stats, "spa", 0))
            spe = getattr(stats, "speed", 0)
            hp = getattr(stats, "hp", 0)
            spd = getattr(stats, "special_defense", getattr(stats, "spd", 0))
        else:
            atk = spa = spe = hp = spd = 0
        if atk >= spa and spe >= 80:
            return "physical_sweeper"
        if spd + hp >= atk + spa:
            return "special_tank"
        return "utility_support"

    role = infer_role()
    types = [t.lower() for t in getattr(pokemon, "types", [])]

    def score(move: Move) -> float:
        tags = set(getattr(move, "tags", []))
        category = (getattr(move, "category", "") or "").lower()
        mtype = (getattr(move, "type", "") or "").lower()
        damage = 0.0
        utility = 0.0
        if category != "status":
            if mtype in types:
                damage += 3
            if "coverage" in tags:
                damage += 2
            if "priority" in tags:
                damage += 1
        if "setup" in tags:
            if role in {"setup_attacker", "physical_sweeper"}:
                utility += 2
            else:
                utility += 1
        if ("heal" in tags or "utility" in tags) and ai_level >= 3:
            utility += 2
        if "status" in tags and (
            ai_personality == "tactician" or role == "utility_support"
        ):
            utility += 2
        weights = AIMoveSelector.personality_weights.get(
            ai_personality, (1.0, 1.0)
        )
        return (damage * weights[0]) + (utility * weights[1])

    scored = [(score(mv), mv) for mv in candidates]
    scored.sort(key=lambda x: x[0], reverse=True)

    selected: List[Move] = []
    type_counts: Dict[str, int] = {}
    for _, mv in scored:
        if len(selected) >= 4:
            break
        mtype = getattr(mv, "type", None)
        if mtype:
            count = type_counts.get(mtype, 0)
            if count >= 2:
                continue
        selected.append(mv)
        if mtype:
            type_counts[mtype] = type_counts.get(mtype, 0) + 1

    # Ensure at least one STAB move
    if not any(
        getattr(m, "type", "").lower() in types
        and getattr(m, "category", "").lower() != "status"
        for m in selected
    ):
        for _, mv in scored:
            if mv in selected:
                continue
            if getattr(mv, "type", "").lower() in types and (
                getattr(mv, "category", "").lower() != "status"
            ):
                if selected:
                    selected[-1] = mv
                else:
                    selected.append(mv)
                break

    # Ensure at least one utility/status move for higher AI levels
    if ai_level >= 3 and not any(
        set(getattr(m, "tags", []))
        & {"status", "utility", "setup", "hazard"}
        or getattr(m, "category", "").lower() == "status"
        for m in selected
    ):
        for _, mv in scored:
            if mv in selected:
                continue
            tags = set(getattr(mv, "tags", []))
            category = (getattr(mv, "category", "") or "").lower()
            if tags & {"status", "utility", "setup", "hazard"} or category == "status":
                if selected:
                    selected[-1] = mv
                else:
                    selected.append(mv)
                break

    return selected[:4]


__all__ = ["AIMoveSelector", "generate_moveset"]
