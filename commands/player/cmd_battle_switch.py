"""Command to switch active Pokémon during battle."""

from __future__ import annotations

from evennia import Command
from evennia.utils.evmenu import get_input

from .cmd_battle_utils import NOT_IN_BATTLE_MSG, _get_participant

try:  # pragma: no cover - battle engine may not be available in tests
    from pokemon.battle import Action, ActionType
    if Action is None or ActionType is None:  # type: ignore[truthy-bool]
        raise ImportError
except Exception:  # pragma: no cover - fallback if engine isn't loaded
    from pokemon.battle.engine import Action, ActionType


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
        try:  # pragma: no cover - battle session may be absent in tests
            from pokemon.battle.battleinstance import BattleSession
        except Exception:  # pragma: no cover
            class BattleSession:  # type: ignore[override]
                @staticmethod
                def ensure_for_player(caller):
                    return getattr(caller.ndb, "battle_instance", None)

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

