from __future__ import annotations

from evennia import Command

NOT_IN_BATTLE_MSG = "You are not currently in battle."

from pokemon.battle import Action, ActionType, BattleMove
from utils.battle_display import render_move_gui


class CmdBattleAttack(Command):
    """Queue a move to use in the current battle.

    Usage:
      +battleattack <move> [target]
    """

    key = "+battleattack"
    locks = "cmd:all()"
    help_category = "Pokemon/Battle"

    def parse(self):
        parts = self.args.split()
        self.move_name = parts[0] if parts else ""
        self.target_name = parts[1] if len(parts) > 1 else ""

    def func(self):
        if not getattr(self.caller.db, "battle_control", False):
            self.caller.msg("|rWe aren't waiting for you to command right now.")
            return
        inst = getattr(self.caller.ndb, "battle_instance", None)
        if not inst:
            room = getattr(self.caller, "location", None)
            bmap = getattr(getattr(room, "ndb", None), "battle_instances", None)
            if isinstance(bmap, dict):
                inst = bmap.get(getattr(self.caller, "id", None))
                if inst:
                    self.caller.ndb.battle_instance = inst
        if not inst or not inst.battle:
            self.caller.msg(NOT_IN_BATTLE_MSG)
            return
        participant = inst.battle.participants[0]
        active = participant.active[0] if participant.active else None
        if not active:
            self.caller.msg("You have no active Pokémon.")
            return

        slots = getattr(active, "activemoveslot_set", None)
        if slots:
            try:
                qs = list(slots.all().order_by("slot"))
            except Exception:
                qs = list(slots)
        else:
            qs = []

        from pokemon.dex import MOVEDEX

        # build move data for display
        letters = ["A", "B", "C", "D"]
        moves_map = {}
        for slot_obj, letter in zip(qs, letters):
            move = slot_obj.move
            dex = MOVEDEX.get(move.name.lower(), None)
            max_pp = getattr(move, "pp", None)
            if dex and not max_pp:
                max_pp = dex.pp
            cur_pp = getattr(slot_obj, "current_pp", None)
            moves_map[letter] = {
                "name": move.name,
                "type": getattr(move, "type", None) or (dex.type if dex else None),
                "category": getattr(move, "category", None) or (dex.category if dex else None),
                "pp": (
                    cur_pp if cur_pp is not None else max_pp,
                    max_pp or 0,
                ),
                "power": getattr(move, "power", 0) or (dex.power if dex else 0),
                "accuracy": getattr(move, "accuracy", 100) if getattr(move, "accuracy", None) is not None else (dex.accuracy if dex else 100),
            }

        move_name = self.move_name
        # forced move checks
        encore = getattr(getattr(active, "volatiles", {}), "get", lambda *_: None)("encore")
        choice = getattr(getattr(active, "volatiles", {}), "get", lambda *_: None)("choicelock")
        if encore:
            move_name = encore
        elif choice:
            move_name = choice.get("move")
        else:
            pp_vals = [info["pp"][0] for info in moves_map.values() if info and info["pp"][0] is not None]
            if pp_vals and all(val == 0 for val in pp_vals):
                move_name = "Struggle"

        if not move_name:
            self.caller.msg(render_move_gui(moves_map))
            return

        if move_name.lower() in {".abort", "abort"}:
            self.caller.msg("Action cancelled.")
            return

        # handle selection by letter
        letter = move_name.upper()
        if letter in moves_map:
            move_name = moves_map[letter]["name"]
        else:
            found = False
            for info in moves_map.values():
                if info["name"].lower() == move_name.lower():
                    move_name = info["name"]
                    found = True
                    break
            if not found:
                self.caller.msg(render_move_gui(moves_map))
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
    help_category = "Pokemon/Battle"

    def func(self):
        slot = self.args.strip()
        inst = getattr(self.caller.ndb, "battle_instance", None)
        if not inst:
            room = getattr(self.caller, "location", None)
            bmap = getattr(getattr(room, "ndb", None), "battle_instances", None)
            if isinstance(bmap, dict):
                inst = bmap.get(getattr(self.caller, "id", None))
                if inst:
                    self.caller.ndb.battle_instance = inst
        if not inst or not inst.battle:
            self.caller.msg(NOT_IN_BATTLE_MSG)
            return
        participant = inst.battle.participants[0]

        if not slot:
            lines = []
            for idx, poke in enumerate(participant.pokemons, 1):
                status = " (fainted)" if getattr(poke, "hp", 0) <= 0 else ""
                active = " (active)" if poke in participant.active else ""
                lines.append(f"{idx}. {poke.name}{active}{status}")
            lines.append("0. Cancel")
            self.caller.ndb.switch_prompt = True
            self.caller.msg(
                "Choose a Pokémon to switch to or 0 to cancel:\n" + "\n".join(lines)
            )
            return

        if slot.lower() in {"0", "cancel", "quit", "exit", "abort", ".abort"}:
            if getattr(self.caller.ndb, "switch_prompt", False):
                self.caller.msg("Switch cancelled.")
                self.caller.ndb.switch_prompt = False
            else:
                self.caller.msg("Usage: +battleswitch <slot>")
            return
        try:
            index = int(slot) - 1
            pokemon = participant.pokemons[index]
        except (ValueError, IndexError):
            self.caller.msg("Invalid Pokémon slot.")
            self.caller.ndb.switch_prompt = False
            return
        if pokemon in participant.active:
            self.caller.msg(f"{pokemon.name} is already active.")
            self.caller.ndb.switch_prompt = False
            return
        if getattr(pokemon, "hp", 0) <= 0:
            self.caller.msg(f"{pokemon.name} has fainted and cannot battle.")
            self.caller.ndb.switch_prompt = False
            return
        action = Action(participant, ActionType.SWITCH)
        action.target = pokemon
        participant.pending_action = action
        self.caller.msg(f"You prepare to switch to {pokemon.name}.")
        self.caller.ndb.switch_prompt = False
        if hasattr(inst, "run_turn"):
            try:
                inst.run_turn()
            except Exception:
                pass


class CmdBattleItem(Command):
    """Use an item during battle.

    Usage:
      +battleitem <item>
    """

    key = "+battleitem"
    locks = "cmd:all()"
    help_category = "Pokemon/Battle"

    def func(self):
        item_name = self.args.strip()
        if not item_name:
            self.caller.msg("Usage: +battleitem <item>")
            return
        if not self.caller.has_item(item_name):
            self.caller.msg(f"You do not have any {item_name}.")
            return
        inst = getattr(self.caller.ndb, "battle_instance", None)
        if not inst:
            room = getattr(self.caller, "location", None)
            bmap = getattr(getattr(room, "ndb", None), "battle_instances", None)
            if isinstance(bmap, dict):
                inst = bmap.get(getattr(self.caller, "id", None))
                if inst:
                    self.caller.ndb.battle_instance = inst
        if not inst or not inst.battle:
            self.caller.msg(NOT_IN_BATTLE_MSG)
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

