"""Validate and persist an ordinary player's independent field-slot choices."""

from __future__ import annotations

from ._shared import _normalize_key
from .active_slots import slot_for
from .engine import Action, ActionType
from .legal_actions import LegalActions


class PlayerChoices:
    """One turn's view of a caller's controlled, living field positions."""

    def __init__(self, session, caller):
        self.session = session
        self.caller = caller
        self.battle = session.battle
        if self.battle is None or self.battle.battle_over:
            raise ValueError("This battle has ended.")
        self.turn = self.battle.turn_count
        self.participant = next((part for part in self.battle.participants
                                 if part.player is caller or (part.player is not None
                                 and getattr(part.player, "id", None) == getattr(caller, "id", object()))), None)
        if self.participant is None or self.participant.is_ai:
            raise ValueError("You do not control a side in this battle.")

    def positions(self):
        """Return currently controlled positions, with stable A1/A2/B1/B2 labels."""
        if self.session.data is None or self.session.battle is not self.battle:
            raise ValueError("That battle has changed. Choose an action again.")
        return {name: pos for name, pos in self.session.data.turndata.positions.items()
                if any(mon is getattr(pos, "pokemon", None) for mon in self.participant.active)
                and LegalActions.conscious(pos.pokemon)}

    def actor(self, position=None):
        """Require an explicit actor when more than one battler can act."""
        positions = self.positions()
        position = position.upper() if position else None
        if position is None and len(positions) == 1:
            position = next(iter(positions))
        if position not in positions:
            labels = ", ".join(f"{name} ({pos.pokemon.name})" for name, pos in positions.items())
            raise ValueError("Choose your acting slot: " + (labels or "no active Pokémon"))
        return position, positions[position].pokemon

    def _check(self, position, pokemon):
        """Reject stale callbacks, replacements and duplicate input before mutation."""
        if self.session.battle is not self.battle or self.battle.turn_count != self.turn or self.battle.battle_over:
            raise ValueError("That choice is from an earlier turn. Choose an action again.")
        current = self.positions().get(position)
        if current is None or current.pokemon is not pokemon:
            raise ValueError("That active Pokémon has changed. Choose an action again.")
        if position in self.session.state.declare or current.getAction():
            raise ValueError(f"{position} ({pokemon.name}) already has an action queued this turn.")

    def legal_moves(self, pokemon):
        """Expose the same executable candidates used by NPCs."""
        return LegalActions(self.battle, self.participant, pokemon).moves()

    def target_labels(self, targets):
        """Label legal target identities using the current field positions."""
        return {name: pos.pokemon for name, pos in self.session.data.turndata.positions.items()
                if any(mon is getattr(pos, "pokemon", None) for mon in targets)}

    def move(self, move_key, target=None, *, actor=None):
        """Queue a legal move; automatic and spread targets need no target token."""
        position, pokemon = self.actor(actor)
        self._check(position, pokemon)
        key = _normalize_key(move_key)
        actions = [action for action in self.legal_moves(pokemon) if _normalize_key(action.move.key) == key]
        if not actions:
            raise ValueError(f"{position} cannot use that move now (check PP, Disable and move locks).")
        move = actions[0].move
        legality = LegalActions(self.battle, self.participant, pokemon)
        labels = self.target_labels(legality.targets(move))
        automatic = move.raw.get("target") in legality.automatic_targets or move.raw.get("target") == "self"
        if automatic:
            if target and target.upper() not in labels:
                raise ValueError("Valid targets: " + ", ".join(labels))
            action = actions[0]
            target = next(name for name, mon in labels.items() if mon is action.target_pokemon)
        else:
            if target is None and len(labels) == 1:
                target = next(iter(labels))
            target = target.upper() if target else None
            action = next((action for action in actions if action.target_pokemon is labels.get(target)), None)
            if action is None:
                raise ValueError("Choose a legal target: " + ", ".join(f"{name} ({mon.name})" for name, mon in labels.items()))
        declaration = {"move": key, "target": target, "target_ref": getattr(action.target_pokemon, "model_id", None)}
        affected = ", ".join(labels) if automatic else target
        if move.raw.get("target") == "randomNormal":
            affected = "one opponent from " + ", ".join(labels)
        self._store(position, pokemon, action, declaration,
                    lambda pos: pos.declareAttack(target, key), f"{position} ({pokemon.name}) prepares {move.name} → {affected}.")

    def switch(self, party_slot, *, actor=None):
        """Reserve one conscious bench member for the specified active slot."""
        position, pokemon = self.actor(actor)
        self._check(position, pokemon)
        try:
            index = int(party_slot) - 1
            if index < 0:
                raise ValueError
            incoming = self.participant.pokemons[index]
        except (ValueError, TypeError, IndexError):
            raise ValueError("Choose a valid party slot to switch in.") from None
        pending = self.participant.pending_action
        pending = pending if isinstance(pending, list) else [pending] if pending else []
        reserved = [action.pokemon for action in pending if action.action_type is ActionType.SWITCH]
        action = next((action for action in LegalActions(self.battle, self.participant, pokemon).switches(reserved=reserved)
                       if action.pokemon is incoming), None)
        if action is None:
            raise ValueError(f"{position} cannot switch to that Pokémon (active, fainted, reserved or trapped).")
        self._store(position, pokemon, action, {"switch": index + 1}, lambda pos: pos.declareSwitch(index + 1),
                    f"{position} ({pokemon.name}) prepares to switch to {incoming.name}.")

    def item(self, item_name, target=None, *, actor=None):
        """Queue medicine for this actor or a ball against the wild opponent."""
        position, pokemon = self.actor(actor)
        self._check(position, pokemon)
        if not self.participant.has_item(item_name):
            raise ValueError(f"You do not have any {item_name}.")
        is_ball = _normalize_key(item_name).lower().endswith("ball")
        if is_ball and self.battle.type.name != "WILD":
            raise ValueError("Poké Balls can only be used against wild Pokémon.")
        owner = self.battle.opponent_of(self.participant) if is_ball else self.participant
        target_pokemon = owner.active[0] if is_ball and owner.active else pokemon
        action = Action(self.participant, ActionType.ITEM, owner, item=item_name, priority=6,
                        pokemon=pokemon, target_pokemon=target_pokemon, target_slot=slot_for(owner, target_pokemon))
        target = next(name for name, mon in self.target_labels([target_pokemon]).items())
        self._store(position, pokemon, action, {"item": item_name, "target": target},
                    lambda pos: pos.declareItem(item_name), f"{position} ({pokemon.name}) prepares {item_name} → {target}.")

    def _store(self, position, pokemon, action, declaration, declare, message):
        """Save one choice atomically in memory before allowing turn advancement."""
        session = self.session
        pos = session.data.turndata.positions[position]
        previous = self.participant.pending_action
        previous_position = pos.turninit
        actions = list(previous) if isinstance(previous, list) else [previous] if previous else []
        # Legacy single commands may have supplied this same actor's action.
        actions = [old for old in actions if (old.switch_from or old.pokemon) is not pokemon]
        actions.append(action)
        declaration = {**declaration, "trainer": str(self.caller.id), "pokemon": getattr(pokemon, "model_id", None)}
        action.player_selected = True
        try:
            declare(pos)
            session.state.declare[position] = declaration
            self.participant.pending_action = actions if len(actions) > 1 else action
            session.storage.set("state", session._compact_state_for_persist(session.logic.state.to_dict()))
        except Exception:
            pos.turninit = previous_position
            session.state.declare.pop(position, None)
            self.participant.pending_action = previous
            raise
        self.caller.msg(message)
        session.maybe_run_turn(actor=self.caller)
