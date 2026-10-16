"""Shared move, target and reserve legality for battle action selection."""

from __future__ import annotations

from ._shared import _normalize_key, get_pp, get_raw


def pokemon_key(pokemon):
    """Identify a roster member without conflating same-species Pokemon."""
    reference = getattr(pokemon, "model_id", None) or getattr(pokemon, "unique_id", None)
    return ("model", str(reference)) if reference else ("runtime", id(pokemon))


class LegalActions:
    """Enumerate legal choices using current engine state and control hooks."""

    automatic_targets = frozenset({"all", "allAdjacent", "allAdjacentFoes", "allies", "allySide", "foeSide", "allyTeam", "randomNormal"})

    def __init__(self, battle, participant, pokemon):
        self.battle = battle
        self.participant = participant
        self.pokemon = pokemon

    @classmethod
    def for_action(cls, battle, action):
        """Recover a choice's original actor, including switches from a second slot."""
        from .engine import ActionType

        active = list(getattr(action.actor, "active", []))
        if action.action_type is ActionType.SWITCH:
            slot = getattr(action, "switch_slot", None) or 0
            source = getattr(action, "switch_from", None)
            if source is None:
                source = active[slot] if 0 <= slot < len(active) else None
        else:
            source = action.pokemon or (active[0] if active else None)
        return cls(battle, action.actor, source)

    @staticmethod
    def conscious(pokemon) -> bool:
        """Accept living battlers, including minimal offline test battlers."""
        return pokemon is not None and getattr(pokemon, "hp", 1) > 0 and not getattr(pokemon, "is_fainted", False)

    def is_active(self) -> bool:
        """Reject foreign, replaced, fainted or terminal actors."""
        if not self.conscious(self.pokemon) or getattr(self.participant, "has_lost", False):
            return False
        if getattr(self.battle, "battle_over", False):
            return False
        roster = getattr(self.participant, "pokemons", None)
        if roster is not None and not any(pokemon is self.pokemon for pokemon in roster):
            return False
        active = getattr(self.participant, "active", None)
        return active is None or any(pokemon is self.pokemon for pokemon in active)

    def targets(self, move) -> list:
        """Return living targets permitted by the move's declared target class."""
        foes = [mon for part in self.battle.opponents_of(self.participant)
                if not getattr(part, "has_lost", False)
                for mon in getattr(part, "active", []) if self.conscious(mon)]
        allies = [mon for part in getattr(self.battle, "participants", [self.participant])
                  if part is self.participant or (
                      getattr(self.participant, "team", None) is not None
                      and getattr(part, "team", None) == self.participant.team)
                  for mon in getattr(part, "active", []) if self.conscious(mon)]
        others = [mon for mon in allies if mon is not self.pokemon]
        target = (getattr(move, "raw", {}) or {}).get("target", "normal")
        if target == "self":
            return [self.pokemon] if self.conscious(self.pokemon) else []
        if target in {"adjacentAlly", "ally"}:
            return others
        if target in {"adjacentAllyOrSelf", "allies", "allySide", "allyTeam"}:
            return allies or [self.pokemon]
        if target == "all":
            return foes + allies
        if target in {"normal", "any", "allAdjacent"}:
            return foes + others
        if target in {"adjacentFoe", "allAdjacentFoes", "foeSide", "randomNormal"}:
            return foes
        # Unknown target classes must not silently become arbitrary attacks.
        return []

    def _move(self, source):
        """Build an executable move while retaining authoritative remaining PP."""
        from .engine import MOVEDEX, BattleMove

        name = getattr(source, "name", source)
        key = _normalize_key(getattr(source, "key", None) or str(name))
        entry = MOVEDEX.get(key)
        raw = {**get_raw(entry), **(getattr(source, "raw", {}) or {})}
        pp = next((value for value in (getattr(source, "current_pp", None), getattr(source, "pp", None), get_pp(entry))
                   if value is not None), None)
        return BattleMove(str(raw.get("name") or name), key=key, pp=pp,
                          power=raw.get("basePower", getattr(source, "power", 0)) or 0,
                          accuracy=raw.get("accuracy", getattr(source, "accuracy", 100)),
                          priority=raw.get("priority", getattr(source, "priority", 0)) or 0,
                          type=raw.get("type", getattr(source, "type", None)), raw=raw)

    def _move_allowed(self, source, move) -> bool:
        """Use the engine's existing Disable, Encore, choice and move-lock rules."""
        if getattr(source, "disabled", False) or (move.pp is not None and move.pp <= 0):
            return False
        key = _normalize_key(move.key).lower()
        for hook in ("_locked_move_override", "_override_action_move"):
            resolver = getattr(self.battle, hook, None)
            if callable(resolver):
                enforced = resolver(self.pokemon, move)
                if _normalize_key(getattr(enforced, "key", None) or getattr(enforced, "name", "")).lower() != key:
                    return False
        locked = getattr(self.pokemon, "choice_locked_move", None)
        choice_item = getattr(self.battle, "_choice_item_key", None)
        if locked and callable(choice_item) and choice_item(self.pokemon) and _normalize_key(locked).lower() != key:
            return False
        disabled = getattr(self.battle, "_is_move_disabled", None)
        return not (callable(disabled) and disabled(self.pokemon, move))

    def moves(self, *, fallback: bool = True) -> list:
        """Enumerate executable move/target pairs, with Struggle as the emergency move."""
        from .engine import Action, ActionType

        if not self.is_active() or not self.battle.opponents_of(self.participant):
            return []
        actions = []
        for source in getattr(self.pokemon, "moves", []) or []:
            move = self._move(source)
            if not self._move_allowed(source, move):
                continue
            targets = self.targets(move)
            if move.raw.get("target") in self.automatic_targets:
                targets = targets[:1]
            for target in targets:
                owner = getattr(self.battle, "participant_for", lambda mon: None)(target)
                if owner is None:
                    owner = next((part for part in self.battle.opponents_of(self.participant)
                                  if any(mon is target for mon in part.active)), self.participant)
                actions.append(Action(self.participant, ActionType.MOVE, owner, move,
                                      priority=move.priority, pokemon=self.pokemon, target_pokemon=target,
                                      target_slot=next((index for index, mon in enumerate(owner.active) if mon is target), 0)))
        if not actions and fallback:
            # Struggle is not a learned move and is exempt from choice/Disable locks.
            struggle = self._move("Struggle")
            struggle.pp = None
            targets = self.targets(struggle)
            if targets:
                target = targets[0]
                owner = next(part for part in self.battle.opponents_of(self.participant)
                             if any(mon is target for mon in part.active))
                actions.append(Action(self.participant, ActionType.MOVE, owner, struggle,
                                      pokemon=self.pokemon, target_pokemon=target,
                                      target_slot=next(index for index, mon in enumerate(owner.active) if mon is target)))
        return actions

    def reserves(self, *, slot: int = 0, forced: bool = False, reserved=()) -> list:
        """Return distinct legal reserves in stable party order for one active slot."""
        part = self.participant
        if getattr(part, "has_lost", False) or not 0 <= slot < getattr(part, "max_active", 1):
            return []
        active = list(getattr(part, "active", []))
        current = active[slot] if slot < len(active) else None
        if forced and self.conscious(current):
            return []
        if not forced:
            if current is not self.pokemon or not self.is_active():
                return []
            trapped = getattr(self.battle, "_is_trapped", None)
            if (callable(trapped) and trapped(current)) or getattr(current, "trapped", False):
                return []
        excluded = {pokemon_key(mon) for mon in [*active, *reserved] if mon is not None}
        result = []
        for mon in getattr(part, "pokemons", []):
            key = pokemon_key(mon)
            if self.conscious(mon) and key not in excluded:
                result.append(mon)
                excluded.add(key)
        return result

    def switches(self, *, reserved=()) -> list:
        """Enumerate voluntary replacements for this actor's exact active slot."""
        from .engine import Action, ActionType

        active = list(getattr(self.participant, "active", []))
        slot = next((index for index, mon in enumerate(active) if mon is self.pokemon), None)
        if slot is None:
            return []
        return [Action(self.participant, ActionType.SWITCH, priority=6, pokemon=mon,
                       switch_slot=slot, switch_from=self.pokemon)
                for mon in self.reserves(slot=slot, reserved=reserved)]

    def refresh(self, action, *, fallback: bool = False, reserved=()):
        """Revalidate a queued choice; only choose a replacement before turn ordering."""
        from .engine import ActionType

        if not self.is_active():
            return None
        legal = self.moves() + self.switches(reserved=reserved)
        for candidate in legal:
            if candidate.action_type is not action.action_type:
                continue
            if candidate.action_type is ActionType.SWITCH:
                if candidate.pokemon is action.pokemon and candidate.switch_slot == (action.switch_slot or 0):
                    return candidate
            elif _normalize_key(candidate.move.key) == _normalize_key(action.move.key):
                selected_slot = getattr(action, "target_slot", None)
                if selected_slot is not None:
                    if candidate.target is action.target and candidate.target_slot == selected_slot:
                        return candidate
                    continue
                target = getattr(action, "target_pokemon", None)
                if target is candidate.target_pokemon or (target is None and candidate.target is action.target):
                    return candidate
        return legal[0] if fallback and legal else None
