"""Command for using an item during battle."""

from __future__ import annotations

from evennia import Command

from pokemon.items import is_capture_ball
from pokemon.services.battle_items import BattleItemCapability
from world.system_init import get_system

from .cmd_battle_utils import NOT_IN_BATTLE_MSG, _get_participant

try:  # pragma: no cover - battle engine may not be available in tests
    from pokemon.battle import Action, ActionType  # type: ignore[attr-defined]

    if Action is None or ActionType is None:  # type: ignore[truthy-bool]
        raise ImportError
except Exception:  # pragma: no cover - fallback if engine isn't loaded
    from pokemon.battle.engine import Action, ActionType  # type: ignore[attr-defined]


class CmdBattleItem(Command):
    """Use an item during battle.

    Usage:
      +battle/item <item>
      +item <acting slot> <item>
      +item [acting slot] <item>=<party slot>[/<move slot or name>]

    Examples:
      +item Potion
      +battle/item Poke Ball
      +item Revive=2
      +item A1 Max Ether=3/Water Gun

    Notes:
      This queues an item as your battle action. Field-use items use +use.
      Supported: battle medicine (including revival and PP restoration) and
      reviewed recovery foods/berries (including Leppa/Mystery selected-move
      PP) and capture balls in wild battles. Use +item Max Honey=3 to revive
      a reserve, or +item A1 Leppa Berry=3/Water Gun. Flavor/EV berries,
      Sacred Ash and other unsupported items are rejected before queuing.
      A supported medicine that has no effect still spends its queued action,
      but consumes no item. Smoke Ball uses +hold before battle, then +flee.
    """

    key = "+battle/item"
    aliases = ["+item", "+Item", "+battleitem"]
    locks = "cmd:all()"
    help_category = "Pokemon/Battle"

    def func(self):
        """Execute the battle item command."""

        if not getattr(self.caller.db, "battle_control", False):
            self.caller.msg("|rWe aren't waiting for you to command right now.")
            return

        from .battle_choice_prompts import split_actor
        actor, item_name = split_actor(self.args)
        item_name, separator, target = item_name.partition("=")
        item_name = item_name.strip()
        target = target.strip() if separator else None
        if not item_name:
            self.caller.msg("Usage: +battle/item <item>")
            return

        try:
            BattleItemCapability.validate(item_name)
        except ValueError as error:
            self.caller.msg(str(error))
            return

        if not self.caller.has_item(item_name):
            self.caller.msg(f"You do not have any {item_name}.")
            return

        system = get_system()
        manager = getattr(system, "battle_manager", None)
        inst = manager.for_player(self.caller) if manager else None

        if not inst:
            try:  # pragma: no cover - battle session may be absent in tests
                from pokemon.battle.battleinstance import BattleSession
            except Exception:  # pragma: no cover

                class BattleSession:  # type: ignore[override]
                    """Fallback for environments without the battle engine."""

                    @staticmethod
                    def ensure_for_player(caller):
                        """Return a cached battle instance if present."""

                        return getattr(caller.ndb, "battle_instance", None)

            inst = BattleSession.ensure_for_player(self.caller)

        if not inst or not getattr(inst, "battle", None):
            self.caller.msg(NOT_IN_BATTLE_MSG)
            return
        if callable(getattr(inst, "choices_for", None)):
            try:
                inst.choices_for(self.caller).item(item_name, target=target, actor=actor)
            except ValueError as error:
                self.caller.msg(str(error))
            return

        try:
            BattleItemCapability.validate(item_name, battle=inst.battle)
        except ValueError as error:
            self.caller.msg(str(error))
            return
        participant = _get_participant(inst, self.caller)
        is_ball = is_capture_ball(item_name)
        target = inst.battle.opponent_of(participant) if is_ball else participant
        action = Action(
            participant,
            ActionType.ITEM,
            target,
            item=item_name,
            priority=6,
        )
        participant.pending_action = action

        self.caller.msg(f"You prepare to use {item_name}.")

        if hasattr(inst, "queue_item"):
            try:
                inst.queue_item(item_name, caller=self.caller)
            except Exception:  # pragma: no cover - queue behaviour is engine specific
                pass
        elif hasattr(inst, "maybe_run_turn"):
            try:
                inst.maybe_run_turn(actor=self.caller)
            except Exception:  # pragma: no cover - queue behaviour is engine specific
                pass
