"""Bounded, visible-state valuation of executable move and target choices."""

from __future__ import annotations

from dataclasses import dataclass, replace

from ._shared import _normalize_key
from .active_slots import slot_for
from .ai_scoring import (
    ScoredAIMove,
    _accuracy_factor,
    _safe_stab,
    _safe_type_effectiveness,
    _stat_value,
    fallback_scored_move,
    score_ai_moves,
)
from .legal_actions import LegalActions


@dataclass(frozen=True)
class AIActionAssessment:
    """Keep a legal action bound to its score, intent and affected targets."""

    action: object
    scored: ScoredAIMove
    intent: str = "safe_damage"
    targets: tuple = ()


class AIActionScorer:
    """Rank legal actions without reading opponents' moves or queued choices."""

    def __init__(self, context, battle, participant, pokemon, *, movedex, raw_getter, planned=()):
        """Capture current battlers and the AI side's already selected actions."""
        self.context = context
        self.battle = battle
        self.participant = participant
        self.user = pokemon
        self.movedex = movedex
        self.raw_getter = raw_getter
        self.planned = tuple(planned)
        self.legality = LegalActions(battle, participant, pokemon)
        self.foes = tuple(mon for part in battle.opponents_of(participant)
                          for mon in part.active if LegalActions.conscious(mon))
        self.allies = tuple(mon for part in getattr(battle, "participants", [participant])
                            if part is participant or (getattr(part, "team", None) is not None
                            and part.team == getattr(participant, "team", None))
                            for mon in getattr(part, "active", []) if LegalActions.conscious(mon))
        if not self.allies:
            self.allies = (pokemon,)

    def assess(self, actions):
        """Return scored legal choices, retaining a harmless zero-utility fallback."""
        assessed = []
        for action in actions:
            base = self._base(action.move, action.target_pokemon)
            targets = tuple(self.legality.targets(action.move))
            key = _normalize_key(action.move.key).lower()
            raw = action.move.raw
            intent = "safe_damage"
            reasons = list(base.reasons)
            if key == "struggle":
                assessed.append(AIActionAssessment(action, base, targets=targets))
                continue
            friendly = self._friendly(action.target_pokemon)
            healing = raw.get("heal") or key in {"healpulse", "floralhealing", "pollenpuff", "junglehealing", "lunarblessing"}
            if friendly and raw.get("target", "normal") in {"normal", "any"} and not healing:
                continue
            if healing and friendly:
                relevant = targets if raw.get("target") in self.legality.automatic_targets else (action.target_pokemon,)
                value = sum(self._recovery(mon, action.move) for mon in relevant)
                intent = "preserve_self" if action.target_pokemon is self.user else "support_ally"
                reasons.append("recover_missing_hp" if value else "no_recovery_benefit")
            elif healing and key != "pollenpuff":
                value = 0.0
                intent = "support_ally"
                reasons.append("enemy_recovery")
            elif key == "helpinghand" and friendly and action.target_pokemon is not self.user:
                value = self._helping_hand(action.target_pokemon)
                intent = "support_ally"
                reasons.append("ally_damage_support" if value else "no_ally_attack")
            elif raw.get("stallingMove"):
                value = self._protect()
                intent = "stall_turn"
                reasons.append("protect_visible_benefit" if value else "no_protect_benefit")
            elif key == "trickroom":
                value = self._trick_room()
                intent = "control_field"
                reasons.append("trick_room_speed_advantage" if value else "room_not_beneficial")
            elif base.power > 0 and base.category.lower() != "status":
                if friendly:
                    # Ordinary attacks on allies are legal player choices, but
                    # are not a useful AI policy without a supported benefit.
                    continue
                value, damage_reasons = self._damage(action, targets)
                reasons.extend(damage_reasons)
            elif raw.get("status") and not friendly:
                relevant = targets if raw.get("target") in self.legality.automatic_targets else (action.target_pokemon,)
                value = sum(self._status(mon, action.move) for mon in relevant if not self._friendly(mon))
                intent = "status_target"
                reasons.append("status_visible_benefit" if value else "status_inapplicable")
            elif raw.get("boosts"):
                relevant = targets if raw.get("target") in self.legality.automatic_targets else (action.target_pokemon,)
                value = sum(self._boosts(mon, raw["boosts"]) for mon in relevant)
                intent = "setup" if friendly else "status_target"
                reasons.append("available_stat_stages" if value else "no_useful_stat_stages")
            else:
                value = base.score
                reasons.append("unmodeled_utility_baseline")
            if intent != "safe_damage" and intent not in self.context.profile.allowed_intents:
                value = min(value, base.score)
                reasons.append("profile_intent_limited")
            if base.category.lower() == "status":
                value *= _accuracy_factor(base.accuracy)
            assessed.append(AIActionAssessment(action, replace(base, score=max(0.0, value),
                                                               reasons=tuple(reasons)), intent, targets))
        # When every choice has zero utility, prefer avoiding lethal ally damage.
        return sorted(assessed, key=lambda entry: ("ally_lethal_risk" in entry.scored.reasons,
                                                  "enemy_recovery" in entry.scored.reasons))

    def _base(self, move, target):
        """Reuse existing profile damage weights and preserve emergency traces."""
        if str(move.key).lower() == "struggle":
            reason = "fallback_no_usable_moves" if getattr(self.user, "moves", []) else "fallback_no_moves"
            return fallback_scored_move(move, movedex=self.movedex, raw_getter=self.raw_getter, reason=reason)
        scored = score_ai_moves(self.context, [move], user=self.user, target=target,
                                movedex=self.movedex, raw_getter=self.raw_getter)
        return scored[0] if scored else fallback_scored_move(move, movedex=self.movedex, raw_getter=self.raw_getter)

    def _friendly(self, pokemon):
        """Test identity against conscious actors on this AI's side."""
        return any(mon is pokemon for mon in self.allies)

    def _damage(self, action, targets):
        """Value the complete spread set and penalize actual friendly-fire exposure."""
        spread = action.move.raw.get("target") in {"allAdjacent", "allAdjacentFoes"}
        targets = targets if spread else (action.target_pokemon,)
        reduction = 0.75 if spread and len(targets) > 1 else 1.0
        value = 0.0
        reasons = ["spread_target_set"] if spread else []
        for mon in targets:
            if self._friendly(mon):
                damage = self.estimate_damage(action.move, mon) * reduction
                if self._ally_immune(mon, action.move):
                    reasons.append("ally_immune")
                    continue
                if damage >= getattr(mon, "hp", 1):
                    reasons.append("ally_lethal_risk")
                    return 0.0, reasons
                cost = self._base(action.move, mon).score * reduction * 1.5
                value -= cost
                if cost:
                    reasons.append("friendly_fire_penalty")
                continue
            candidate = self._base(action.move, mon)
            damage = self.estimate_damage(action.move, mon) * reduction
            contribution = candidate.score * reduction
            if damage > 0 and damage >= getattr(mon, "hp", float("inf")):
                contribution += 45.0 * self.context.profile.scoring.ko_bonus_weight
                reasons.append("visible_ko")
            if self._room_active() and self._speed(self.user) < self._speed(mon) and action.move.priority == 0:
                contribution *= 1.08
                reasons.append("room_attack_order")
            value += contribution
        return value, reasons

    def estimate_damage(self, move, target):
        """Use a pure rough damage estimate; never execute callbacks or consume RNG."""
        raw = move.raw
        category, move_type = raw.get("category", "Physical"), move.type
        power = max(0, raw.get("basePower", move.power) or 0)
        if _normalize_key(move.key).lower() == "terablast":
            from .terastallization import tera_blast_parameters

            move_type, category, power = tera_blast_parameters(self.user)
        physical = str(category).lower() == "physical"
        attack = self._stat(self.user, "atk" if physical else "spa")
        defense = self._stat(target, "def" if physical else "spd")
        level = max(1, getattr(self.user, "level", 50))
        if not power:
            return 0.0
        effectiveness = _safe_type_effectiveness(target, move_type)
        burn = 0.5 if physical and getattr(self.user, "status", None) == "brn" else 1.0
        return (((2 * level / 5 + 2) * power * attack / max(1, defense) / 50) + 2) * _safe_stab(self.user, move_type) * effectiveness * burn

    def _recovery(self, target, move):
        """Value recoverable missing HP with a deficit threshold and urgency cap."""
        if getattr(target, "volatiles", {}).get("healblock"):
            return 0.0
        maximum = max(1, getattr(target, "max_hp", 1))
        missing = max(0, maximum - getattr(target, "hp", maximum))
        if missing / maximum < 0.2 or not self._friendly(target):
            return 0.0
        if any(getattr(action, "target_pokemon", None) is target and
               (getattr(action.move, "raw", {}) or {}).get("heal") for action in self.planned if getattr(action, "move", None)):
            return 0.0
        fraction = move.raw.get("heal") or (1, 2)
        recoverable = min(missing, maximum * fraction[0] / max(1, fraction[1])) / maximum
        urgency = missing / maximum
        return min(230.0, 160 * recoverable + 170 * urgency)

    def _helping_hand(self, ally):
        """Value support only when the ally can still execute a legal attack."""
        if getattr(ally, "tempvals", {}).get("moved"):
            return 0.0
        planned = [action for action in self.planned if
                   (getattr(action, "switch_from", None) or getattr(action, "pokemon", None)) is ally]
        available = LegalActions(self.battle, self.participant, ally).moves(fallback=False)
        moves = [action.move for action in available if not planned or any(
            getattr(chosen, "move", None) and chosen.move.key == action.move.key
            and not self._friendly(getattr(chosen, "target_pokemon", None)) for chosen in planned)]
        attacks = [move for move in moves if move.power > 0 and move.raw.get("category") != "Status"
                   and (move.pp is None or move.pp > 0) and move.priority <= 3]
        if not attacks:
            return 0.0
        return min(150.0, max(self._base(move, foe).score for move in attacks for foe in self.foes) * 0.6)

    def _status(self, target, move):
        """Apply bounded major-status utility and visible core immunities."""
        if getattr(target, "status", None):
            return 0.0
        status = move.raw["status"]
        types = {str(kind).lower() for kind in getattr(target, "types", [])}
        immunities = {"psn": {"poison", "steel"}, "tox": {"poison", "steel"},
                      "brn": {"fire"}, "par": {"electric"}, "frz": {"ice"}}
        if types & immunities.get(status, set()):
            return 0.0
        if str(move.key).lower() == "thunderwave" and _safe_type_effectiveness(target, move.type) == 0:
            return 0.0
        score = 85.0
        if status == "brn":
            score *= 1.35 if self._stat(target, "atk") >= self._stat(target, "spa") else 0.6
        if status == "par" and self._room_active():
            score *= 0.3
        if getattr(target, "hp", 1) <= getattr(target, "max_hp", 1) / 4:
            score *= 0.4
        return score

    def _boosts(self, target, boosts):
        """Value useful available stages without repeating completed setup."""
        friendly = self._friendly(target)
        if friendly and getattr(target, "hp", 1) < getattr(target, "max_hp", 1) * 0.5:
            return 0.0
        useful = 0.0
        for stat, change in boosts.items():
            stage = self._stage(target, stat)
            if friendly and change > 0:
                if stat in {"atk", "spa"}:
                    category = "Physical" if stat == "atk" else "Special"
                    available = LegalActions(self.battle, self.participant, target).moves(fallback=False)
                    if not any(action.move.raw.get("category") == category for action in available):
                        continue
                if stat == "spe" and self._room_active():
                    continue
                useful += max(0, min(change, 6 - stage)) / (1 + max(0, stage))
            elif not friendly and change < 0:
                if stat == "spe" and self._room_active():
                    continue
                useful += max(0, min(-change, stage + 6)) / (1 + max(0, -stage))
        return min(140.0, useful * 55.0)

    def _protect(self):
        """Value visible residual, recovery or ally cover with a stall penalty."""
        residual = any(getattr(foe, "status", None) in {"brn", "psn", "tox"} for foe in self.foes)
        partners = [mon for mon in self.allies if mon is not self.user]
        ally_attack = any(self._helping_hand(mon) > 0 for mon in partners)
        item = getattr(self.user, "item", None) or getattr(self.user, "held_item", None)
        item_key = _normalize_key(getattr(item, "name", item) or "").lower()
        poison_type = any(str(kind).lower() == "poison" for kind in getattr(self.user, "types", []))
        healing = (item_key == "leftovers" or (item_key == "blacksludge" and poison_type))
        healing = healing and not getattr(self.user, "volatiles", {}).get("healblock")
        low_hp = getattr(self.user, "hp", 1) <= getattr(self.user, "max_hp", 1) / 3
        if not residual and not healing and not (low_hp and ally_attack):
            return 0.0
        stall = getattr(self.user, "volatiles", {}).get("stall", {})
        denominator = stall.get("counter", 1) if isinstance(stall, dict) else 2
        return (160.0 if low_hp else 95.0) / max(1, denominator)

    def _trick_room(self):
        """Compare current team speeds for the explicitly selected room strategy."""
        if self.context.profile.strategy_key != "trick_room" or not self.foes:
            return 0.0
        if any(_normalize_key(getattr(getattr(action, "move", None), "key", "")).lower() == "trickroom" for action in self.planned):
            return 0.0
        pairs = [(ally, foe) for ally in self.allies for foe in self.foes]
        advantage = sum((self._speed(foe) > self._speed(ally)) - (self._speed(foe) < self._speed(ally))
                        for ally, foe in pairs) / len(pairs)
        benefit = -advantage if self._room_active() else advantage
        healthy = getattr(self.user, "hp", 1) >= getattr(self.user, "max_hp", 1) * 0.5
        return 210.0 * benefit if benefit >= 0.5 and healthy else 0.0

    def _room_active(self):
        """Read the live field without mutating its effect state."""
        field = getattr(self.battle, "field", None)
        getter = getattr(field, "get_pseudo_weather", None)
        return bool(getter("trickroom")) if callable(getter) else False

    @staticmethod
    def _stage(pokemon, stat):
        """Resolve existing short/long stat-stage names within the legal bounds."""
        aliases = {"atk": "attack", "def": "defense", "spa": "special_attack", "spd": "special_defense", "spe": "speed"}
        boosts = getattr(pokemon, "boosts", {})
        return max(-6, min(6, boosts.get(stat, boosts.get(aliases.get(stat, stat), 0))))

    def _stat(self, pokemon, stat):
        """Apply the current boost stage to a canonical battle stat."""
        aliases = {"atk": "attack", "def": "defense", "spa": "special_attack", "spd": "special_defense", "spe": "speed"}
        value = _stat_value(pokemon, aliases.get(stat, stat), stat) or 50
        stage = self._stage(pokemon, stat)
        return value * ((2 + stage) / 2 if stage >= 0 else 2 / (2 - stage))

    def _speed(self, pokemon):
        """Include paralysis in the current speed estimate."""
        return self._stat(pokemon, "spe") * (0.5 if getattr(pokemon, "status", None) == "par" else 1.0)

    @staticmethod
    def _ally_immune(pokemon, move):
        """Recognize the AI's own ally's known elemental immunity abilities."""
        ability = getattr(pokemon, "ability", None)
        key = _normalize_key(getattr(ability, "name", ability) or "").lower()
        return key in {"Ground": {"levitate"}, "Water": {"waterabsorb", "stormdrain", "dryskin"},
                       "Electric": {"voltabsorb", "lightningrod", "motordrive"}, "Fire": {"flashfire"}}.get(move.type, set())

    def target_label(self, pokemon):
        """Describe a candidate target without conflating two same-species slots."""
        owner = getattr(self.battle, "participant_for", lambda mon: None)(pokemon)
        if owner is None:
            return getattr(pokemon, "name", "Pokemon")
        slot = slot_for(owner, pokemon)
        team = getattr(owner, "team", None)
        prefix = f"{team}{slot + 1} " if team and slot is not None else ""
        return prefix + getattr(pokemon, "name", "Pokemon")
