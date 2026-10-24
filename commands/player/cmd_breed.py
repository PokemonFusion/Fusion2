"""Ordinary bounded breeding, owned egg collection and same-identity hatching."""

from evennia import Command


class CmdBreed(Command):
    """Breed two eligible Daycare parents, then collect and hatch one owned egg.

    Usage:
      +breed
      +breed check
      +breed start
      +breed collect <cycle UUID>
      +breed cancel <cycle UUID>
      +breed hatch <egg UUID>

    Start costs 500 trainer money; one egg is ready after 30 wall-clock minutes.
    Parents have a 24-hour cooldown. After collection, the egg needs another 20
    wall-clock minutes before hatch. Status and repeated start never advance time
    or reroll traits. Cancellation ends uncollected production without refund or
    resetting cooldown. Parents stay in Daycare until ordinary retrieval.

    Eggs can be consent traded; only the current owner can hatch one. Hatching
    changes the same Pokemon ID and never grants a second creature. Full parties
    receive collected eggs in a box. Unsupported forms/pairs fail before payment.
    """

    key = "+breed"
    aliases = ["+breeding"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        """Keep actor identities, fees, chosen traits and time on the server."""
        from pokemon.services.breeding import Breeding
        from pokemon.services.placement import PlacementError

        action, _, arguments = (self.args or "").strip().partition(" ")
        action = action.lower()
        try:
            service = Breeding(self.caller)
            if not action:
                lines = [service.describe(cycle) for cycle in service.cycles()]
                for egg in service.eggs():
                    lines.append(f"Owned egg/hatch {egg.pk}: {'hatched' if egg.hatched_at else 'egg'}; "
                        f"hatch ready {egg.hatch_ready_at.isoformat()}. Use +breed hatch {egg.pk}.")
                self.caller.msg("\n".join(lines) if lines else
                    "No breeding cycles or bred eggs. Deposit two parents with +daycare, then +breed check. "
                    "A new cycle costs 500 trainer money; use help breeding for timing and exclusions.")
            elif action == "check" and not arguments:
                result = service.check()
                self.caller.msg(f"Supported offspring: {result['offspring']}. Start available: {result['ready_to_start']}. "
                    f"Parent cooldown until: {result['cooldown_until'] or 'none'}. +breed start costs 500 trainer money; "
                    "one egg after 30 minutes, then 20 minutes to hatch after collection.")
            elif action == "start" and not arguments:
                self.caller.msg(service.describe(service.start()))
            elif action == "collect" and arguments:
                receipt = service.collect(arguments.strip())
                self.caller.msg(f"Collection receipt {receipt['cycle']}: egg {receipt['egg']} to your {receipt['location']}, "
                    f"slot {receipt['slot']}, box {receipt['box']}, position {receipt['position']}. "
                    f"Hatch after {receipt['hatch_ready_at']}; +breed hatch {receipt['egg']}. "
                    "Parents may now be retrieved from Daycare. Repeating returns this historical receipt.")
            elif action == "cancel" and arguments:
                receipt = service.cancel(arguments.strip())
                self.caller.msg(f"Cycle {receipt['cycle']}: cancelled; no egg created or refund. "
                    f"Parent cooldown remains until {receipt['cooldown_until']}. Parents can be retrieved with +daycare.")
            elif action == "hatch" and arguments:
                receipt = service.hatch(arguments.strip())
                self.caller.msg(f"Hatch receipt: {receipt['species']} [{receipt['pokemon']}], saved by character #{receipt['owner']}. "
                    "This is the same owned Pokemon ID. Repeating returns the saved historical result; later trades can change its owner.")
            else:
                self.caller.msg("Use +breed [check||start], +breed collect/cancel <cycle ID>, or +breed hatch <egg ID>.")
        except PlacementError as error:
            self.caller.msg(str(error))
