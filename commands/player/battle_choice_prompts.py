"""Player-facing move and reserve prompts with captured turn/actor identity."""

from __future__ import annotations

import re


def split_actor(text):
    """Separate an optional leading field position from a command argument."""
    parts = text.strip().split(None, 1)
    if parts and re.fullmatch(r"[AB][12]", parts[0], re.IGNORECASE):
        return parts[0].upper(), parts[1] if len(parts) > 1 else ""
    return None, text.strip()


def attack_prompt(inst, caller, move_name, target=None, actor=None):
    """Submit a move or prompt for a legal move and explicit target."""
    from evennia.utils.evmenu import get_input

    from pokemon.battle._shared import _normalize_key
    from pokemon.battle.legal_actions import LegalActions
    from utils.battle_display import render_move_gui
    try:
        choices = inst.choices_for(caller)
        position, pokemon = choices.actor(actor)
        choices._check(position, pokemon)
    except ValueError as error:
        caller.msg(str(error))
        return
    slots = list(getattr(pokemon, "moves", []))[:4]
    legal = choices.legal_moves(pokemon)
    if legal and all(action.move.key.lower() == "struggle" for action in legal):
        slots = [legal[0].move]
    pp = {index: next((action.move.pp for action in legal
                       if _normalize_key(action.move.key) == _normalize_key(move.name)), 0)
          for index, move in enumerate(slots)}

    def submit(text, selected_target=None):
        """Reject stale interactive input before interpreting a move selection."""
        if text.lower() in {"cancel", "quit", "exit", "abort", ".abort", "0"}:
            caller.msg("Action cancelled.")
            return False
        parts = text.rsplit(None, 1)
        if len(parts) == 2 and re.fullmatch(r"[AB][12]", parts[1], re.IGNORECASE):
            text, selected_target = parts
        if len(text) == 1 and text.upper() in "ABCD" and ord(text.upper()) - ord("A") < len(slots):
            text = slots[ord(text.upper()) - ord("A")].name
        try:
            choices._check(position, pokemon)
            choices.move(text, selected_target, actor=position)
        except ValueError as error:
            caller.msg(str(error))
        return False

    if move_name:
        submit(move_name, target)
        return
    fields = ", ".join(f"{name}: {pos.pokemon.name}" for name, pos in inst.data.turndata.positions.items()
                       if LegalActions.conscious(pos.pokemon))
    prompt = f"Move for {position} ({pokemon.name}):\n" + render_move_gui(slots, pp_overrides=pp)
    prompt += "\n" + fields + "\nChoose a letter/name and target (e.g. A B1), or cancel. Spread/self moves need no target."
    get_input(caller, prompt, lambda _caller, _prompt, result: submit(result.strip()))


def switch_prompt(inst, caller, selection, actor=None):
    """Submit or list legal reserves for one captured field position."""
    from evennia.utils.evmenu import get_input

    from pokemon.battle.legal_actions import LegalActions
    try:
        choices = inst.choices_for(caller)
        position, pokemon = choices.actor(actor)
        choices._check(position, pokemon)
    except ValueError as error:
        caller.msg(str(error))
        return

    def submit(text):
        """Keep menu callbacks from switching a replaced actor or later turn."""
        if text.lower() in {"cancel", "quit", "exit", "abort", ".abort", "0"}:
            caller.msg("Switch cancelled.")
            return False
        try:
            choices._check(position, pokemon)
            choices.switch(text, actor=position)
        except ValueError as error:
            caller.msg(str(error))
        return False

    if selection:
        submit(selection)
        return
    reserves = LegalActions(inst.battle, choices.participant, pokemon).switches()
    lines = [f"{index}. {mon.name}" for index, mon in enumerate(choices.participant.pokemons, 1)
             if any(action.pokemon is mon for action in reserves)]
    if not lines:
        caller.msg(f"{position} has no legal reserve to switch in.")
        return
    get_input(caller, f"Switch {position} ({pokemon.name}) to:\n" + "\n".join(lines) + "\n0. Cancel",
              lambda _caller, _prompt, result: submit(result.strip()))
