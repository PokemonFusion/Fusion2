from __future__ import annotations

from evennia import Command

from pokemon.battle import Action, ActionType, BattleMove


class CmdBattleAttack(Command):
    """Queue a move to use in the current battle.

    Usage:
      +battleattack <move> [target]
    """

    key = "+battleattack"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def parse(self):
        parts = self.args.split()
        self.move_name = parts[0] if parts else ""
        self.target_name = parts[1] if len(parts) > 1 else ""

    def func(self):
        inst = getattr(self.caller.ndb, "battle_instance", None)
        if not inst or not inst.battle:
            self.caller.msg("You are not currently in battle.")
            return
        participant = inst.battle.participants[0]
        active = participant.active[0] if participant.active else None
        if not active:
            self.caller.msg("You have no active Pokémon.")
            return

        slots = getattr(active, "activemoveslot_set", None)
        if slots:
            try:
                qs = slots.all().order_by("slot")
            except Exception:
                qs = list(slots)
        else:
            qs = []
        moves = [s.move.name for s in qs]

        move_name = self.move_name
        if not move_name or move_name.lower() not in [m.lower() for m in moves]:
            lines = ["Available moves:"]
            lines += [f"  {m}" for m in moves]
            targets = [p.name for p in inst.battle.participants if p is not participant]
            if targets:
                lines.append("Valid targets:")
                lines += [f"  {t}" for t in targets]
            self.caller.msg("\n".join(lines))
            return

        targets = [p for p in inst.battle.participants if p is not participant]
        target = None
        if len(targets) == 1:
            target = targets[0]
        elif self.target_name:
            for part in targets:
                if part.name.lower().startswith(self.target_name.lower()):
                    target = part
                    break
        if target is None:
            names = ", ".join(p.name for p in targets)
            self.caller.msg(f"Valid targets: {names}")
            return

        move = BattleMove(name=move_name)
        action = Action(participant, ActionType.MOVE, target, move, getattr(move, "priority", 0))
        participant.pending_action = action
        self.caller.msg(f"You prepare to use {move_name}.")


class CmdBattleSwitch(Command):
    """Switch your active Pokémon in battle.

    Usage:
      +battleswitch <slot>
    """

    key = "+battleswitch"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        slot = self.args.strip()
        if not slot:
            self.caller.msg("Usage: +battleswitch <slot>")
            return
        inst = getattr(self.caller.ndb, "battle_instance", None)
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
    """Use an item during battle.

    Usage:
      +battleitem <item>
    """

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
        inst = getattr(self.caller.ndb, "battle_instance", None)
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

