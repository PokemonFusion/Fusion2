"""Commands for interacting with Poké Ball vendors."""

from __future__ import annotations

from evennia import Command


class CmdVend(Command):
    """Dispense Poké Balls from a nearby vending machine.

    Usage:
      vend [vendor]
      vend [vendor] <amount>
      vend <amount>
    """

    key = "vend"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        location = self.caller.location
        if not location:
            self.caller.msg("There is no vending machine here.")
            return

        args = self.args.strip()
        amount = 1
        target = None

        if args:
            parts = args.rsplit(" ", 1)
            maybe_amount = parts[-1]
            name_part = args
            if maybe_amount.isdigit():
                amount = int(maybe_amount)
                name_part = " ".join(parts[:-1]).strip()
            if name_part:
                target = self.caller.search(name_part, location=location)
                if not target:
                    return
        vendors = [obj for obj in location.contents if hasattr(obj, "vend_item")]
        if target is None:
            if not vendors:
                self.caller.msg("There is no vending machine here.")
                return
            if len(vendors) > 1:
                self.caller.msg("Specify which vending machine to use.")
                return
            target = vendors[0]
        elif not hasattr(target, "vend_item"):
            self.caller.msg("That doesn't appear to be a vending machine.")
            return

        if amount <= 0:
            self.caller.msg("You must request at least one item.")
            return

        result = target.vend_item(self.caller, amount)
        if result is False:
            self.caller.msg("The vending machine refuses to vend right now.")
