"""Command for queuing a move in battle."""

from __future__ import annotations

import re

from evennia import Command
from evennia.utils.evmenu import get_input

try:  # pragma: no cover - EvMenu may not be available during tests
    from utils.enhanced_evmenu import EnhancedEvMenu
except Exception:  # pragma: no cover
    EnhancedEvMenu = None  # type: ignore

from utils.battle_display import render_move_gui
from world.system_init import get_system

from .cmd_battle_utils import NOT_IN_BATTLE_MSG, _get_participant
from pokemon.battle._shared import _normalize_key, ensure_movedex_aliases

try:  # pragma: no cover - battle engine may not be available in tests
    from pokemon.battle import Action, ActionType, BattleMove

    if Action is None or ActionType is None or BattleMove is None:  # type: ignore[truthy-bool]
        raise ImportError
except Exception:  # pragma: no cover - fallback if engine isn't loaded
    from pokemon.battle.engine import Action, ActionType, BattleMove


class CmdBattleAttack(Command):
    """Queue a move to use in the current battle.

    Usage:
      +battle/attack <move> [target]
      +attack /menu  (interactive menu)
    """

    key = "+battle/attack"
    aliases = ["+attack", "+Attack", "+battleattack"]
    locks = "cmd:all()"
    help_category = "Pokemon/Battle"

    def parse(self):
        self.switch_menu = False
        raw = self.args or ""
        if raw.startswith("/menu"):
            self.switch_menu = True
            raw = raw[len("/menu") :].strip()
        parts = raw.split()
        self.move_name = parts[0] if parts else ""
        self.target_token = parts[1] if len(parts) > 1 else ""

    def func(self):
        if not getattr(self.caller.db, "battle_control", False):
            self.caller.msg("|rWe aren't waiting for you to command right now.")
            return
        system = get_system()
        manager = getattr(system, "battle_manager", None)
        inst = manager.for_player(self.caller) if manager else None
        if not inst:
            try:  # pragma: no cover - battle session may be absent in tests
                from pokemon.battle.battleinstance import BattleSession
            except Exception:  # pragma: no cover

                class BattleSession:  # type: ignore[override]
                    @staticmethod
                    def ensure_for_player(caller):
                        return getattr(caller.ndb, "battle_instance", None)

            inst = BattleSession.ensure_for_player(self.caller)
        if not inst or not getattr(inst, "battle", None):
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

        ensure_movedex_aliases(MOVEDEX)

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
                    norm = _normalize_key(move_key or "")
                    dex = MOVEDEX.get(norm, None)
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
                    norm = _normalize_key(move_key or "")
                    dex = MOVEDEX.get(norm, None)
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
            sel_index = None
            letter = selected.upper()
            if letter in letters:
                idx = letters.index(letter)
                if idx < len(slots):
                    selected_move = slots[idx]
                    sel_index = idx
            else:
                for idx, mv in enumerate(slots):
                    name = mv if isinstance(mv, str) else getattr(mv, "name", "")
                    if name.lower() == selected.lower():
                        selected_move = mv
                        sel_index = idx
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
                    self.caller.msg("Please target by position (A1/B1/...). Names can change when switching.")
                    return
            else:
                self.caller.msg(f"Valid targets: {', '.join(pos_map.keys())}")
                return

            move_name_sel = selected_move if isinstance(selected_move, str) else getattr(selected_move, "name", "")
            move_pp = pp_overrides.get(sel_index) if sel_index is not None else None
            move_obj = BattleMove(move_name_sel, pp=move_pp)
            # key on BattleMove is already normalized by engine.__post_init__;
            # MOVEDEX expects normalized keys.
            dex_entry = MOVEDEX.get(getattr(move_obj, "key", move_name_sel))
            priority = dex_entry.raw.get("priority", 0) if dex_entry else 0
            move_obj.priority = priority
            action = Action(
                participant,
                ActionType.MOVE,
                target,
                move_obj,
                priority,
            )
            participant.pending_action = action
            self.caller.msg(f"You prepare to use {move_obj.name}.")
            if hasattr(inst, "queue_move"):
                try:
                    inst.queue_move(getattr(move_obj, "key", move_name_sel), target_pos, caller=self.caller)
                except Exception:
                    pass
            elif hasattr(inst, "maybe_run_turn"):
                try:
                    inst.maybe_run_turn(actor=self.caller)
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
            if self.switch_menu and EnhancedEvMenu:
                from menus import battle_move as battle_move_menu

                EnhancedEvMenu(
                    self.caller,
                    battle_move_menu,
                    startnode="start",
                    cmd_on_exit=None,  # don't auto-look after menu ends
                    start_kwargs=dict(
                        slots=slots,
                        pp_overrides=pp_overrides,
                        inst=inst,
                        participant=participant,
                    ),
                    numbered_options=False,
                    show_options=False,
                    show_footer=True,  # shown on input nodes; hidden on terminal nodes by formatter
                    menu_title="Move Select",
                    footer_prompt="A–D or name",
                    invalid_message="Invalid. Type A–D, exact name, or 'quit'.",
                )
                return
            _prompt_move()
            return

        _process_move(move_name)
