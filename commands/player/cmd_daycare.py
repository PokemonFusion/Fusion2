"""Ordinary Daycare deposit, reconnect/status and safe retrieval."""

from evennia import Command


class CmdDaycare(Command):
    """Keep up to two Pokemon in Daycare without passive EXP or healing.

    Usage:
      +daycare
      +daycare deposit <your party slot/UUID>
      +daycare retrieve <entry UUID>

    Deposit costs 100 trainer money per stay; retrieval is free. Eggs and reserved
    Pokemon cannot be deposited. Deposited Pokemon cannot battle or enter other
    systems. Retrieve returns the same Pokemon to a free party slot, or a box if
    full. Breeding is separate. Status and receipts survive reconnect.
    """

    key = "+daycare"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        """Resolve every reply through the acting character's current custody."""
        from pokemon.services.daycare import Daycare
        from pokemon.services.placement import PlacementError

        action, _, arguments = (self.args or "").strip().partition(" ")
        action = action.lower()
        try:
            service = Daycare(self.caller)
            if not action:
                entries = service.entries()
                self.caller.msg("Daycare (active entries first):\n" + "\n".join(service.describe(entry) for entry in entries)
                    if entries else "Your Daycare is empty. Use +daycare deposit <your slot/UUID>; 100 trainer money, retrieval free.")
            elif action == "deposit" and arguments:
                self.caller.msg(service.describe(service.deposit(arguments.strip())))
            elif action == "retrieve" and arguments:
                receipt = service.retrieve(arguments.strip())
                self.caller.msg(f"Daycare retrieval {receipt['entry']} saved: Pokemon {receipt['pokemon']} "
                    f"to your {receipt['location']}, slot {receipt['slot']}, box {receipt['box']}, "
                    f"position {receipt['position']}. No retrieval fee. Repeating returns this historical receipt.")
            else:
                self.caller.msg("Use +daycare, +daycare deposit <your slot/UUID>, or +daycare retrieve <entry UUID>.")
        except PlacementError as error:
            self.caller.msg(str(error))
