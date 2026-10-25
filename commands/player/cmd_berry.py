"""Ordinary Oran nursery operations and explicitly selected flavor snacks."""

from evennia import Command


class CmdBerry(Command):
    """Tend your private bed at a Berry Nursery or feed a selected flavor snack.

    Usage:
      +berry help
      +berry status
      +berry plant Oran Berry
      +berry water
      +berry harvest
      +berry snack Razz Berry=<party slot, unique name, full ID or fusion>
      +berry snack Bluk Berry=<target>

    Growing costs one bag Oran seed. Four one-hour stages count offline time;
    water free once in each stage for yield 1-5. Ready crops do not decay.
    Harvest once, then replant explicitly. Find the optional nursery through its
    nursery/back exits and use +store to buy finite stock. No held seed or tool.
    Each selected snack is a PF2 equivalent that heals up to 10 HP outside battle,
    independently of growing. No contest/lure/friendship or automatic +use alias.
    Accepted snacks: Razz, Bluk, Nanab, Pinap, Wepear, Cornn, Magost, Nomel,
    Rabuta, Belue, Durin, Pamtre, Spelon and Watmel Berry.
    """

    key = "+berry"
    locks = "cmd:all()"
    help_category = "Pokemon/Items"

    def func(self):
        """Keep parser/discovery here and all durable checks in the shared services."""
        from pokemon.names import normalize_name
        from pokemon.services.berry_growing import BerryGrowing
        from pokemon.services.berry_snack import BerrySnack

        text = self.args.strip()
        operation, _, argument = text.partition(" ")
        operation = operation.casefold()
        if operation == "help":
            self.caller.msg(self.__doc__)
            return
        try:
            if operation == "snack":
                item, separator, target = argument.partition("=")
                canonical = BerrySnack.canonical_name(item)
                if canonical is None or not separator or not target.strip():
                    raise ValueError("Use +berry snack <accepted berry>=<party slot, unique name, full ID or fusion>. "
                                     "See +berry help for the accepted snacks.")
                service = BerrySnack(self.caller)
                used = service.use(canonical, target.strip())
                if used:
                    service.notify_success(canonical, target.strip())
                elif used is not None:
                    self.caller.msg(f"{canonical} had no effect. No item was consumed.")
                return
            growing = BerryGrowing(self.caller)
            if not operation or operation == "status":
                if argument:
                    raise ValueError("Use +berry status to inspect your own bed.")
                state = growing.status()
                if not state["cycle"]:
                    self.caller.msg("Your bed is empty. Plant one bag Oran Berry with +berry plant Oran Berry.")
                else:
                    label = "ready to harvest" if state["ready"] else f"growing stage {state['stage'] + 1}/4"
                    self.caller.msg(f"Oran Berry: {label}; ready at {state['ready_at']}; "
                                    f"yield {state['yield']}; cycle {state['cycle']}.")
                return
            if operation == "plant":
                if normalize_name(argument) != "oranberry":
                    raise ValueError("Only +berry plant Oran Berry is supported.")
            elif operation not in {"water", "harvest"} or argument:
                raise ValueError("Use +berry help for growing and snack commands.")
            result = growing.operate(operation, cycle=growing.cycle())
            if not result["changed"]:
                self.caller.msg(result["message"])
        except ValueError as error:
            self.caller.msg(str(error))
        except Exception:
            from evennia.utils import logger

            logger.log_trace("Berry request failed")
            self.caller.msg("Berry request could not be saved. Nothing was changed; try again.")
