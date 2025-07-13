from __future__ import annotations

from evennia import Command

from pokemon.battle import Action, ActionType, BattleMove


class CmdBattleAttack(Command):
    """Queue a move to use in the current battle."""

    key = "+battleattack"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def parse(self):
        parts = self.args.split()
        self.move_name = parts[0] if parts else ""
        self.target_name = parts[1] if len(parts) > 1 else ""

    def func(self):
        if not self.move_name:
            self.caller.msg("Usage: +battleattack <move> [target]")
            return
        inst = self.caller.ndb.get("battle_instance")
        if not inst or not inst.battle:
            self.caller.msg("You are not currently in battle.")
            return
        participant = inst.battle.participants[0]
        target = inst.battle.opponent_of(participant)
        if self.target_name:
            for part in inst.battle.participants:
                if part is participant:
                    continue
                if part.name.lower().startswith(self.target_name.lower()):
                    target = part
                    break
        move = BattleMove(name=self.move_name)
        action = Action(participant, ActionType.MOVE, target, move, getattr(move, "priority", 0))
        participant.pending_action = action
        self.caller.msg(f"You prepare to use {self.move_name}.")


class CmdBattleSwitch(Command):
    """Switch your active Pokémon in battle."""

    key = "+battleswitch"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        slot = self.args.strip()
        if not slot:
            self.caller.msg("Usage: +battleswitch <slot>")
            return
        inst = self.caller.ndb.get("battle_instance")
        if not inst or not inst.battle:
            self.caller.msg("You are not currently in battle.")
            return
        participant = inst.battle.participants[0]
        try:
            index = int(slot) - 1
            pokemon = participant.pokemons[index]
        except (ValueError, IndexError):
            self.caller.msg("Invalid Pokémon slot.")
            return
        action = Action(participant, ActionType.SWITCH)
        action.target = pokemon
        participant.pending_action = action
        self.caller.msg(f"You prepare to switch to {pokemon.name}.")


class CmdBattleItem(Command):
    """Use an item during battle."""

    key = "+battleitem"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        item_name = self.args.strip()
        if not item_name:
            self.caller.msg("Usage: +battleitem <item>")
            return
        if not self.caller.has_item(item_name):
            self.caller.msg(f"You do not have any {item_name}.")
            return
        inst = self.caller.ndb.get("battle_instance")
        if not inst or not inst.battle:
            self.caller.msg("You are not currently in battle.")
            return
        participant = inst.battle.participants[0]
        target = inst.battle.opponent_of(participant)
        action = Action(
            participant,
            ActionType.ITEM,
            target,
            item=item_name,
            priority=6,
        )
        participant.pending_action = action
        if hasattr(self.caller, "trainer"):
            self.caller.trainer.remove_item(item_name)
        self.caller.msg(f"You prepare to use {item_name}.")

