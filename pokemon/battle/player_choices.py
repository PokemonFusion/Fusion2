"""Validate and persist an ordinary player's independent field-slot choices."""

from __future__ import annotations

from pokemon.helpers.party_helpers import get_battle_switch_choices, resolve_battle_switch_choice
from pokemon.items import is_capture_ball
from pokemon.names import normalize_name

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

    def tera(self, *, actor=None, cancel=False):
        """Persist a Tera reservation before this actor chooses its move."""
        from .terastallization import Terastallization

        position, pokemon = self.actor(actor)
        self._check(position, pokemon)
        side = Terastallization.side(self.battle, self.participant)
        previous = dict(getattr(self.battle, "tera_pending", {}))
        if cancel:
            declaration = previous.get(side, {})
            if declaration.get("pokemon") != Terastallization.identifier(pokemon):
                raise ValueError("That Pokemon has no Terastallization reserved.")
            self.battle.tera_pending.pop(side)
            message = f"{position}: Terastallization cancelled."
        else:
            tera_type = Terastallization.reserve(self.battle, self.participant, pokemon)
            message = f"{position} ({pokemon.name}) will Terastallize into {tera_type} when its move is locked. Choose a move with +attack."
        try:
            self.session.logic.sync_runtime_state()
            self.session.storage.set("state", self.session._compact_state_for_persist(self.session.state.to_dict()))
        except Exception:
            self.battle.tera_pending = previous
            self.session.logic.sync_runtime_state()
            raise
        self.caller.msg(message)

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

    def switch_choices(self):
        """Expose stable party slots and the reserved Fusion choice to prompts."""
        return get_battle_switch_choices(self.caller, self.participant.pokemons)

    def switch(self, party_slot, *, actor=None):
        """Reserve one conscious bench member for the specified active slot."""
        position, pokemon = self.actor(actor)
        self._check(position, pokemon)
        try:
            index, incoming = resolve_battle_switch_choice(self.caller, self.switch_choices(), party_slot)
        except (ValueError, TypeError, KeyError):
            raise ValueError("Invalid Pokémon slot. Use +party or +switch to see available slots.") from None
        pending = self.participant.pending_action
        pending = pending if isinstance(pending, list) else [pending] if pending else []
        reserved = [action.pokemon for action in pending if action.action_type is ActionType.SWITCH]
        action = next((action for action in LegalActions(self.battle, self.participant, pokemon).switches(reserved=reserved)
                       if action.pokemon is incoming), None)
        if action is None:
            raise ValueError(f"{position} cannot switch to that Pokémon (active, fainted, reserved or trapped).")
        self._store(position, pokemon, action, {"switch": index}, lambda pos: pos.declareSwitch(index),
                    f"{position} ({pokemon.name}) prepares to switch to {incoming.name}.")

    def item(self, item_name, target=None, *, actor=None):
        """Queue medicine for this actor or a ball against the wild opponent."""
        if normalize_name(item_name) == "smokeball":
            raise ValueError("Smoke Ball is a held item. Equip it with +hold before battle and use +flee.")
        position, pokemon = self.actor(actor)
        self._check(position, pokemon)
        if not self.participant.has_item(item_name):
            raise ValueError(f"You do not have any {item_name}.")
        is_ball = is_capture_ball(item_name)
        if is_ball and self.battle.type.name != "WILD":
            raise ValueError("Poké Balls can only be used against wild Pokémon.")
        owner = self.battle.opponent_of(self.participant) if is_ball else self.participant
        target_pokemon = owner.active[0] if is_ball and owner.active else pokemon
        item_move = None
        if target is not None and not is_ball:
            selector, _, item_move = str(target).partition("/")
            try:
                _, target_pokemon = resolve_battle_switch_choice(self.caller, self.switch_choices(), selector.strip())
            except (ValueError, TypeError, KeyError):
                raise ValueError("Choose an owned party slot, including a fainted reserve.") from None
            item_move = item_move.strip() or None
        action = Action(self.participant, ActionType.ITEM, owner, item=item_name, priority=6,
                        pokemon=pokemon, target_pokemon=target_pokemon, target_slot=slot_for(owner, target_pokemon), item_move=item_move)
        target = next((name for name, mon in self.target_labels([target_pokemon]).items()), target_pokemon.name)
        declaration = {"item": item_name, "target": target, "item_target_ref": getattr(target_pokemon, "model_id", None), "item_move": item_move}
        self._store(position, pokemon, action, declaration,
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
