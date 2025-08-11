from __future__ import annotations

from evennia import Command
from evennia.utils.evmenu import get_input
import re

from utils.battle_display import render_move_gui
from utils.pokemon_utils import make_move_from_dex

NOT_IN_BATTLE_MSG = "You are not currently in battle."

try:
    from pokemon.battle import Action, ActionType, BattleMove
    if Action is None or ActionType is None or BattleMove is None:
        raise ImportError
except Exception:  # pragma: no cover - fallback if engine isn't loaded
    from pokemon.battle.engine import Action, ActionType, BattleMove


def _get_participant(inst, caller):
    """Return battle participant for caller or fallback to first."""
    if inst and getattr(inst, "battle", None):
        for part in getattr(inst.battle, "participants", []):
            if getattr(part, "player", None) is caller:
                return part
        if getattr(inst.battle, "participants", []):
            return inst.battle.participants[0]
    return None



class CmdBattleAttack(Command):
    """Queue a move to use in the current battle.

    Usage:
      +battle/attack <move> [target]
    """

    key = "+battle/attack"
    aliases = ["+attack", "+Attack", "+battleattack"]
    locks = "cmd:all()"
    help_category = "Pokemon/Battle"

    def parse(self):
        parts = self.args.split()
        self.move_name = parts[0] if parts else ""
        self.target_token = parts[1] if len(parts) > 1 else ""

    def func(self):
        if not getattr(self.caller.db, "battle_control", False):
            self.caller.msg("|rWe aren't waiting for you to command right now.")
            return
        from pokemon.battle.battleinstance import BattleSession

        inst = BattleSession.ensure_for_player(self.caller)
        if not inst or not inst.battle:
            self.caller.msg(NOT_IN_BATTLE_MSG)
            return
        participant = _get_participant(inst, self.caller)
        active = participant.active[0] if participant.active else None
        if not active:
            self.caller.msg("You have no active Pokémon.")
            return

        slots_qs = getattr(active, "activemoveslot_set", None)
        qs = []
        if slots_qs:
            try:
                qs = list(slots_qs.all().order_by("slot"))
            except Exception:
                try:
                    qs = list(slots_qs.order_by("slot"))
                except Exception:
                    qs = list(slots_qs)

        from pokemon.dex import MOVEDEX

        # build simple slot list and PP overrides
        letters = ["A", "B", "C", "D"]
        slots: list = []
        pp_overrides: dict[int, int] = {}
        if qs:
            for idx, slot_obj in enumerate(qs[:4]):
                move = slot_obj.move
                slots.append(move)
                cur_pp = getattr(slot_obj, "current_pp", None)
                if cur_pp is None:
                    move_key = move if isinstance(move, str) else getattr(move, "name", "")
                    dex = MOVEDEX.get(move_key.lower(), None)
                    max_pp = getattr(move, "pp", None) or (dex.pp if dex else None)
                    if max_pp is not None:
                        cur_pp = max_pp
                if cur_pp is not None:
                    pp_overrides[idx] = cur_pp
        else:
            for idx, move in enumerate(getattr(active, "moves", [])[:4]):
                slots.append(move)
                cur_pp = getattr(move, "current_pp", None)
                if cur_pp is None:
                    move_key = move if isinstance(move, str) else getattr(move, "name", "")
                    dex = MOVEDEX.get(move_key.lower(), None)
                    max_pp = getattr(move, "pp", None) or (dex.pp if dex else None)
                    if max_pp is not None:
                        cur_pp = max_pp
                if cur_pp is not None:
                    pp_overrides[idx] = cur_pp

        move_name = self.move_name

        def _process_move(selected: str) -> None:
            """Handle a chosen move name or letter."""

            if selected.lower() in {".abort", "abort", "cancel", "quit", "exit"}:
                self.caller.msg("Action cancelled.")
                return

            # handle selection by letter or name
            selected_move = None
            letter = selected.upper()
            if letter in letters:
                idx = letters.index(letter)
                if idx < len(slots):
                    selected_move = slots[idx]
            else:
                for mv in slots:
                    name = (
                        mv if isinstance(mv, str) else getattr(mv, "name", "")
                    )
                    if name.lower() == selected.lower():
                        selected_move = mv
                        break
            if selected_move is None:
                _prompt_move()
                return

            if hasattr(inst.battle, "opponents_of"):
                targets = inst.battle.opponents_of(participant)
            else:
                targets = [p for p in inst.battle.participants if p is not participant]
            pos_map = {}
            team = "A"
            if hasattr(inst, "_get_position_for_trainer"):
                pos_name, _ = inst._get_position_for_trainer(self.caller)
                if pos_name and pos_name.startswith("B"):
                    team = "B"
            opp_team = "B" if team == "A" else "A"
            for idx, part in enumerate(targets, 1):
                pos_map[f"{opp_team}{idx}"] = part
            target = None
            target_pos = ""
            if len(pos_map) == 1 and not self.target_token:
                target_pos, target = next(iter(pos_map.items()))
            elif self.target_token:
                token = self.target_token.upper()
                if re.fullmatch(r"[AB]\d+", token):
                    target_pos = token
                    target = pos_map.get(token)
                    if target is None:
                        self.caller.msg(f"Valid targets: {', '.join(pos_map.keys())}")
                        return
                else:
                    self.caller.msg(
                        "Please target by position (A1/B1/...). Names can change when switching."
                    )
                    return
            else:
                self.caller.msg(f"Valid targets: {', '.join(pos_map.keys())}")
                return

            move_name_sel = selected_move if isinstance(selected_move, str) else getattr(selected_move, "name", "")
            move_obj = make_move_from_dex(move_name_sel, battle=True)
            action = Action(
                participant,
                ActionType.MOVE,
                target,
                move_obj,
                getattr(move_obj, "priority", 0),
            )
            participant.pending_action = action
            self.caller.msg(f"You prepare to use {move_obj.name}.")
            if hasattr(inst, "queue_move"):
                try:
                    inst.queue_move(move_name_sel, target_pos, caller=self.caller)
                except Exception:
                    pass
            elif hasattr(inst, "maybe_run_turn"):
                try:
                    inst.maybe_run_turn()
                except Exception:
                    pass

        def _prompt_move() -> None:
            """Prompt the caller to select a move interactively."""

            def _callback(caller, prompt, result):
                choice = result.strip()
                _process_move(choice)
                return False

            get_input(
                self.caller,
                render_move_gui(slots, pp_overrides=pp_overrides),
                _callback,
            )

        # forced move checks
        encore = getattr(getattr(active, "volatiles", {}), "get", lambda *_: None)("encore")
        choice = getattr(getattr(active, "volatiles", {}), "get", lambda *_: None)("choicelock")
        if encore:
            move_name = encore
        elif choice:
            move_name = choice.get("move")
        else:
            pp_vals = [pp_overrides.get(i, 1) for i in range(len(slots))]
            if pp_vals and all(val == 0 for val in pp_vals):
                move_name = "Struggle"

        if not move_name:
            _prompt_move()
            return

        _process_move(move_name)


class CmdBattleSwitch(Command):
    """Switch your active Pokémon in battle.

    Usage:
      +battle/switch <slot>
    """

    key = "+battle/switch"
    aliases = ["+switch", "+Switch", "+battleswitch"]
    locks = "cmd:all()"
    help_category = "Pokemon/Battle"

    def func(self):
        if not getattr(self.caller.db, "battle_control", False):
            self.caller.msg("|rWe aren't waiting for you to command right now.")
            return
        slot = self.args.strip()
        from pokemon.battle.battleinstance import BattleSession

        inst = BattleSession.ensure_for_player(self.caller)
        if not inst or not inst.battle:
            self.caller.msg(NOT_IN_BATTLE_MSG)
            return
        participant = _get_participant(inst, self.caller)

        if not slot:
            lines = []
            for idx, poke in enumerate(participant.pokemons, 1):
                status = " (fainted)" if getattr(poke, "hp", 0) <= 0 else ""
                active = " (active)" if poke in participant.active else ""
                lines.append(f"{idx}. {poke.name}{active}{status}")
            lines.append("0. Cancel")

            def _callback(caller, prompt, result):
                choice = result.strip().lower()
                if choice in {"0", "cancel", "quit", "exit", "abort", ".abort"}:
                    caller.msg("Switch cancelled.")
                    return False
                try:
                    idx = int(choice) - 1
                    poke = participant.pokemons[idx]
                except (ValueError, IndexError):
                    caller.msg("Invalid Pokémon slot.")
                    return True
                if poke in participant.active:
                    caller.msg(f"{poke.name} is already active.")
                    return True
                if getattr(poke, "hp", 0) <= 0:
                    caller.msg(f"{poke.name} has fainted and cannot battle.")
                    return True
                action = Action(participant, ActionType.SWITCH, priority=6)
                action.target = poke
                participant.pending_action = action
                caller.msg(f"You prepare to switch to {poke.name}.")
                if hasattr(inst, "queue_switch"):
                    try:
                        inst.queue_switch(idx + 1, caller=self.caller)
                    except Exception:
                        pass
                elif hasattr(inst, "maybe_run_turn"):
                    try:
                        inst.maybe_run_turn()
                    except Exception:
                        pass
                return False

            prompt = "Choose a Pokémon to switch to or 0 to cancel:\n" + "\n".join(lines)
            get_input(self.caller, prompt, _callback)
            return

        if slot.lower() in {"0", "cancel", "quit", "exit", "abort", ".abort"}:
            self.caller.msg("Switch cancelled.")
            return
        try:
            index = int(slot) - 1
            pokemon = participant.pokemons[index]
        except (ValueError, IndexError):
            self.caller.msg("Invalid Pokémon slot.")
            return
        if pokemon in participant.active:
            self.caller.msg(f"{pokemon.name} is already active.")
            return
        if getattr(pokemon, "hp", 0) <= 0:
            self.caller.msg(f"{pokemon.name} has fainted and cannot battle.")
            return
        action = Action(participant, ActionType.SWITCH, priority=6)
        action.target = pokemon
        participant.pending_action = action
        self.caller.msg(f"You prepare to switch to {pokemon.name}.")
        if hasattr(inst, "queue_switch"):
            try:
                inst.queue_switch(index + 1, caller=self.caller)
            except Exception:
                pass
        elif hasattr(inst, "maybe_run_turn"):
            try:
                inst.maybe_run_turn()
            except Exception:
                pass


class CmdBattleItem(Command):
    """Use an item during battle.

    Usage:
      +battle/item <item>
    """

    key = "+battle/item"
    aliases = ["+item", "+Item", "+battleitem"]
    locks = "cmd:all()"
    help_category = "Pokemon/Battle"

    def func(self):
        if not getattr(self.caller.db, "battle_control", False):
            self.caller.msg("|rWe aren't waiting for you to command right now.")
            return
        item_name = self.args.strip()
        if not item_name:
            self.caller.msg("Usage: +battle/item <item>")
            return
        if not self.caller.has_item(item_name):
            self.caller.msg(f"You do not have any {item_name}.")
            return
        from pokemon.battle.battleinstance import BattleSession

        inst = BattleSession.ensure_for_player(self.caller)
        if not inst or not inst.battle:
            self.caller.msg(NOT_IN_BATTLE_MSG)
            return
        participant = _get_participant(inst, self.caller)
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
        if hasattr(inst, "queue_item"):
            try:
                inst.queue_item(item_name, caller=self.caller)
            except Exception:
                pass
        elif hasattr(inst, "maybe_run_turn"):
            try:
                inst.maybe_run_turn()
            except Exception:
                pass


class CmdBattleFlee(Command):
    """Attempt to flee from battle.

    Usage:
      +battle/flee
    """

    key = "+battle/flee"
    aliases = ["+flee", "+Flee", "+battleflee"]
    locks = "cmd:all()"
    help_category = "Pokemon/Battle"

    def func(self):
        if not getattr(self.caller.db, "battle_control", False):
            self.caller.msg("|rWe aren't waiting for you to command right now.")
            return
        from pokemon.battle.battleinstance import BattleSession

        inst = BattleSession.ensure_for_player(self.caller)
        if not inst or not inst.battle:
            self.caller.msg(NOT_IN_BATTLE_MSG)
            return
        participant = _get_participant(inst, self.caller)
        action = Action(participant, ActionType.RUN, priority=9)
        participant.pending_action = action
        self.caller.msg("You attempt to flee!")
        if hasattr(inst, "queue_run"):
            try:
                inst.queue_run(caller=self.caller)
            except Exception:
                pass
        elif hasattr(inst, "maybe_run_turn"):
            try:
                inst.maybe_run_turn()
            except Exception:
                pass

