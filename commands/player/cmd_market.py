"""Ordinary fixed-price marketplace commands over atomic owned-asset services."""

from evennia import Command


class CmdMarket(Command):
    """Browse, inspect, list and buy hatched Pokemon using trainer money.

    Usage:
      +market
      +market mine
      +market list <your party slot/UUID>=<price>
      +market inspect <listing UUID>
      +market buy <listing UUID>
      +market cancel <listing UUID>

    Listings last 24 hours. Inspect the exact Pokemon and price before buying.
    Prices are 1 to 1,000,000 trainer money, with no fee. Full parties use boxes.
    Eggs use consent trading. Purchases preserve HP/PP and never grant EXP or
    trigger evolution. +market mine reclaims your expired reservations.
    """

    key = "+market"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        """Never accept seller/buyer identities or currency values from the client."""
        from pokemon.services.marketplace import Marketplace
        from pokemon.services.placement import PlacementError

        action, _, arguments = (self.args or "").strip().partition(" ")
        action = action.lower()
        try:
            service = Marketplace(self.caller)
            if not action or action == "mine":
                listings = service.mine() if action == "mine" else service.browse()
                lines = [f"{row.pk}: {row.snapshot['summary']['name']} ({row.snapshot['summary']['species']}), "
                         f"{row.price} trainer money; {row.state}. +market inspect {row.pk}" for row in listings]
                self.caller.msg("Marketplace (up to 30):\n" + "\n".join(lines) if lines else
                    "No listings. Use +market list <your slot/UUID>=<price>, or +market mine for your outcomes.")
            elif action == "list" and "=" in arguments:
                selector, price = [part.strip() for part in arguments.split("=", 1)]
                if len(price) > 7 or not price.isascii() or not price.isdecimal():
                    raise PlacementError("Choose a whole price from 1 to 1,000,000.")
                self.caller.msg(service.describe(service.create(selector, int(price))))
            elif action == "inspect" and arguments:
                self.caller.msg(service.inspect(arguments.strip()))
            elif action == "buy" and arguments:
                receipt = service.buy(arguments.strip())
                self.caller.msg(f"Purchase {receipt['purchase']} completed for {receipt['price']} trainer money. "
                                f"Listing {receipt['listing']}; both money and Pokemon are saved. "
                                "Repeating this purchase returns the same receipt.")
            elif action == "cancel" and arguments:
                self.caller.msg(service.describe(service.close(arguments.strip())))
            else:
                self.caller.msg("Use +market [mine], +market list <your slot/UUID>=<price>, "
                                "+market inspect/buy/cancel <listing UUID>.")
        except PlacementError as error:
            self.caller.msg(str(error))
