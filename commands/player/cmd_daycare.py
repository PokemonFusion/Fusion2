"""Ordinary Daycare deposit, reconnect/status and safe retrieval."""

from evennia import Command


class CmdDaycare(Command):
    """Keep up to two Pokemon in Daycare without passive EXP or healing.

    Usage:
      +daycare
      +daycare deposit <your party slot/UUID>
      +daycare retrieve <entry UUID>
      +daycare herb <recipient party slot/UUID>=<donor party slot/UUID>/<exact move>
      +daycare herb confirm
      +daycare herb cancel

    Deposit costs 100 trainer money per stay; retrieval is free. Eggs and reserved
    Pokemon cannot be deposited. Deposited Pokemon cannot battle or enter other
    systems. Retrieve returns the same Pokemon to a free party slot, or a box if
    full. Breeding is separate. Status and receipts survive reconnect.

    At a configured Daycare, free Mirror Herb teaching uses two hatched owned
    ordinary party members. The recipient holds a Mirror Herb and has an empty
    active slot; the donor actively knows an exact native Gen 9 egg move for the
    recipient (zero donor PP is allowed). Review and confirm within five minutes.
    No Herb is consumed and no egg, fee, gender or Egg Group pairing is needed.
    Existing knowledge and PP are preserved; this does not refresh a known move.
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
            if action == "herb":
                from pokemon.services.mirror_herb import MirrorHerbTeaching

                teaching = MirrorHerbTeaching(self.caller)
                text = arguments.strip()
                if text.casefold() == "confirm":
                    result = teaching.confirm()
                elif text.casefold() == "cancel":
                    result = teaching.cancel()
                else:
                    recipient, equals, donor_move = text.partition("=")
                    donor, slash, move = donor_move.partition("/")
                    if not equals or not slash or not all(value.strip() for value in (recipient, donor, move)):
                        raise PlacementError("Use +daycare herb <recipient>=<donor>/<exact move>, then +daycare herb confirm.")
                    result = teaching.review(recipient.strip(), donor.strip(), move.strip())
                teaching.notify(result)
            elif not action:
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
        except (PlacementError, ValueError) as error:
            self.caller.msg(str(error))
