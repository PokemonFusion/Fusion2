from __future__ import annotations

"""EvMenu flow for selecting a battle move and target.

This menu mirrors the existing `+attack` command behavior but uses
:class:`~helpers.enhanced_evmenu.EnhancedEvMenu` for a more robust
input loop. It hides the default option list and parses user input via
`_default` handlers, allowing selection by letter, move name, or target
position. The menu can be triggered with `+attack /menu`.
"""

from typing import Any, Dict, List, Tuple
import re

from evennia.utils.evmenu import EvMenuGotoAbortMessage

from utils.battle_display import render_move_gui
from utils.pokemon_utils import make_move_from_dex

ABORT_WORDS = {".abort", "abort", "cancel", "quit", "exit"}
LETTERS = ["A", "B", "C", "D"]


def start(
    caller,
    raw_string: str,
    slots: List[Any],
    pp_overrides: Dict[int, int],
    inst=None,
    participant=None,
    **kwargs,
) -> Tuple[str, List[Dict[str, Any]]]:
    """Node 1: choose move by letter or exact name."""
    text = render_move_gui(slots, pp_overrides=pp_overrides)
    options = [
        {
            "key": "_default",
            "goto": (
                _route_move,
                {"slots": slots, "inst": inst, "participant": participant},
            ),
            "desc": "",
        }
    ]
    return text, options


def _route_move(
    caller,
    raw_string: str,
    slots: List[Any],
    inst=None,
    participant=None,
    **kwargs,
):
    """Router for the move-selection node."""
    s = (raw_string or "").strip()
    if not s:
        raise EvMenuGotoAbortMessage(
            "Type a letter (A–D) or a move name. Type 'quit' to cancel."
        )
    if s.lower() in ABORT_WORDS:
        caller.msg("Action cancelled.")
        return None, None

    move_obj = None
    letter = s.upper()
    if letter in LETTERS:
        idx = LETTERS.index(letter)
        if idx < len(slots):
            move = slots[idx]
            name = move if isinstance(move, str) else getattr(move, "name", "")
            move_obj = make_move_from_dex(name, battle=True)
    else:
        for mv in slots:
            name = mv if isinstance(mv, str) else getattr(mv, "name", "")
            if name.lower() == s.lower():
                move_obj = make_move_from_dex(name, battle=True)
                break

    if not move_obj:
        raise EvMenuGotoAbortMessage("Invalid move. Use A–D or exact name.")

    return "choose_target", {
        "move_obj": move_obj,
        "inst": inst,
        "participant": participant,
    }


def choose_target(
    caller,
    raw_string: str,
    move_obj,
    inst=None,
    participant=None,
    **kwargs,
) -> Tuple[str, List[Dict[str, Any]]]:
    """Node 2: choose target by position (A1/B1/...)."""
    if hasattr(inst.battle, "opponents_of"):
        targets = inst.battle.opponents_of(participant)
    else:  # pragma: no cover - fallback if engine lacks opponents_of
        targets = [p for p in inst.battle.participants if p is not participant]

    pos_map: Dict[str, Any] = {}
    team = "A"
    if hasattr(inst, "_get_position_for_trainer"):
        pos_name, _ = inst._get_position_for_trainer(caller)
        if pos_name and pos_name.startswith("B"):
            team = "B"
    opp_team = "B" if team == "A" else "A"
    for idx, part in enumerate(targets, 1):
        pos_map[f"{opp_team}{idx}"] = part

    if len(pos_map) == 1:
        target_pos, target = next(iter(pos_map.items()))
        _queue_move(caller, inst, participant, move_obj, target, target_pos)
        # Returning (text, None) marks this as a terminal node. No footer should be shown.
        return f"|gYou prepare to use {move_obj.name}.|n", None  # terminal: no further input, footer hidden

    lines = [
        "Valid targets: " + ", ".join(pos_map.keys()),
        "Enter position like A1 / B2, or 'quit' to cancel.",
    ]
    text = "\n".join(lines)
    options = [
        {
            "key": "_default",
            "goto": (
                _route_target,
                {"move_obj": move_obj, "inst": inst, "participant": participant},
            ),
            "desc": "",
        }
    ]
    return text, options


def _route_target(
    caller,
    raw_string: str,
    move_obj,
    inst=None,
    participant=None,
    **kwargs,
):
    """Router for the target-selection node."""
    s = (raw_string or "").strip().upper()
    if not s:
        raise EvMenuGotoAbortMessage("Enter a target position (e.g., A1/B1).")
    if s.lower() in ABORT_WORDS:
        caller.msg("Action cancelled.")
        return None, None
    if not re.fullmatch(r"[AB]\d+", s):
        raise EvMenuGotoAbortMessage(
            "Position must be like A1/B1 (names change when switching)."
        )

    if hasattr(inst.battle, "opponents_of"):
        targets = inst.battle.opponents_of(participant)
    else:  # pragma: no cover - fallback if engine lacks opponents_of
        targets = [p for p in inst.battle.participants if p is not participant]
    team = "A"
    if hasattr(inst, "_get_position_for_trainer"):
        pos_name, _ = inst._get_position_for_trainer(caller)
        if pos_name and pos_name.startswith("B"):
            team = "B"
    opp_team = "B" if team == "A" else "A"
    pos_map = {f"{opp_team}{i}": p for i, p in enumerate(targets, 1)}
    target = pos_map.get(s)
    if not target:
        raise EvMenuGotoAbortMessage("Not a valid target position for you.")

    _queue_move(caller, inst, participant, move_obj, target, s)
    # Returning (text, None) marks this as a terminal node. No footer should be shown.
    return f"|gYou prepare to use {move_obj.name}.|n", None  # terminal: no further input, footer hidden


def _queue_move(caller, inst, participant, move_obj, target, target_pos: str) -> None:
    """Use the same queue path as the current `+attack` command."""
    try:
        from pokemon.battle.engine import Action, ActionType
    except Exception:  # pragma: no cover - engine isn't available
        try:
            from pokemon.battle import Action, ActionType
        except Exception:  # pragma: no cover - nothing to queue against
            return
    if not ActionType:
        return

    action = Action(
        participant,
        ActionType.MOVE,
        target,
        move_obj,
        getattr(move_obj, "priority", 0),
    )
    participant.pending_action = action
    if hasattr(inst, "queue_move"):
        try:
            inst.queue_move(move_obj.name, target_pos, caller=caller)
        except Exception:  # pragma: no cover - engine optional
            pass
    elif hasattr(inst, "maybe_run_turn"):
        try:
            inst.maybe_run_turn()
        except Exception:  # pragma: no cover
            pass
