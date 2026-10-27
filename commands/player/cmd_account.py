from django.conf import settings
from evennia import Command, search_account, search_object
from evennia.accounts.models import AccountDB
from evennia.commands.default.account import CmdCharCreate as DefaultCmdCharCreate

# Preserve the legacy command module's public imports while trading is disabled.
from pokemon.models.storage import move_to_box as move_to_box
from utils.locks import require_no_battle_lock as require_no_battle_lock

STAFF_LOCK = (
    "cmd:perm(Helper) or perm(Validator) or perm(Builder) or perm(Admin) "
    "or perm(Developer) or perm(Wizards)"
)


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    try:
        return list(value)
    except TypeError:
        return [value]


def _display_name(obj) -> str:
    return getattr(obj, "key", None) or getattr(obj, "username", None) or getattr(obj, "name", None) or str(obj)


def _character_label(character) -> str:
    name = _display_name(character)
    dbref = getattr(character, "dbref", None)
    return f"{name} ({dbref})" if dbref else name


def _is_character(obj) -> bool:
    check = getattr(obj, "is_typeclass", None)
    return bool(callable(check) and check("typeclasses.characters.Character", exact=False))


def _same_character(left, right) -> bool:
    if left is right:
        return True
    for attr in ("id", "dbref"):
        left_value = getattr(left, attr, None)
        right_value = getattr(right, attr, None)
        if left_value is not None and right_value is not None and left_value == right_value:
            return True
    return False


def _account_characters(account) -> list:
    characters = getattr(account, "characters", None)
    if characters is None:
        return []
    try:
        return [character for character in list(characters) if character]
    except TypeError:
        all_characters = characters.all() if hasattr(characters, "all") else []
        return [character for character in all_characters if character]
    except Exception:
        return []


def _accounts_for_character(character) -> list:
    owners = []
    for account in AccountDB.objects.all():
        if any(_same_character(candidate, character) for candidate in _account_characters(account)):
            owners.append(account)
    return owners


def _search_accounts(query: str) -> list:
    return [match for match in _as_list(search_account(query, exact=True)) if match]


def _search_characters(query: str) -> list:
    try:
        matches = search_object(query, exact=True, typeclass="typeclasses.characters.Character")
    except TypeError:
        matches = search_object(query)
    return [match for match in _as_list(matches) if match and _is_character(match)]


class CmdCharCreate(DefaultCmdCharCreate):
    """Create a new character with a maximum-per-account limit.

    Usage:
      charcreate <name>
    """

    help_category = "General"

    def func(self):
        """Create the new character and direct players to ``goic``."""
        account = self.account
        max_chars = settings.MAX_NR_CHARACTERS
        if max_chars is not None and len(account.characters) >= max_chars:
            self.msg(f"You already have the maximum number of characters ({max_chars}).")
            return
        if not self.args:
            self.msg("Usage: charcreate <name>")
            return
        key = self.lhs
        description = self.rhs or "This is a character."
        new_character, errors = account.create_character(key=key, description=description, ip=self.session.address)
        if errors:
            self.msg(errors)
        if not new_character:
            return
        self.msg(
            f"Created new character {new_character.key}. Use |wgoic {new_character.key}|n to enter"
            " the game as this character.\n"
            "After entering, type |wchargen|n to choose your character type and finish setup.\n"
            "Type |whelp getting started|n whenever you need the beginner guide."
        )


class CmdAlts(Command):
    """List characters for an account or find a character's account.

    Usage:
      @alts <account>
      @alts/account <account>
      @alts/char <character>
    """

    key = "@alts"
    locks = STAFF_LOCK
    help_category = "Admin"

    def func(self):
        args = (self.args or "").strip()
        if not args:
            self.msg("Usage: @alts <account> | @alts/char <character>")
            return

        switches = {switch.lower() for switch in getattr(self, "switches", []) or []}
        if "char" in switches or "character" in switches:
            self._show_character_accounts(args)
            return

        if "account" in switches or "acct" in switches:
            self._show_account_characters(args)
            return

        if self._show_account_characters(args, quiet=True):
            return

        if self._show_character_accounts(args, quiet=True):
            return

        self.msg("No matching account or character found.")

    def _show_account_characters(self, query: str, quiet: bool = False) -> bool:
        results = _search_accounts(query)
        if not results:
            if not quiet:
                self.msg("No matching account found.")
            return False
        if len(results) > 1:
            names = ", ".join(_display_name(account) for account in results[:8])
            if len(results) > 8:
                names += ", ..."
            self.msg(f"Multiple accounts match: {names}")
            return True

        account = results[0]
        characters = _account_characters(account)
        names = ", ".join(_character_label(char) for char in characters) if characters else "None"
        self.msg(f"Characters for {_display_name(account)}: {names}")
        return True

    def _show_character_accounts(self, query: str, quiet: bool = False) -> bool:
        matches = _search_characters(query)
        if not matches:
            if not quiet:
                self.msg("No matching character found.")
            return False
        if len(matches) > 1:
            names = ", ".join(_character_label(match) for match in matches[:8])
            if len(matches) > 8:
                names += ", ..."
            self.msg(f"Multiple characters match: {names}")
            return True

        character = matches[0]
        owners = _accounts_for_character(character)
        if not owners:
            self.msg(f"No account found for character {_character_label(character)}.")
            return True

        owner_names = ", ".join(_display_name(account) for account in owners)
        if len(owners) == 1:
            account = owners[0]
            alts = ", ".join(_character_label(char) for char in _account_characters(account)) or "None"
            self.msg(
                f"{_character_label(character)} is on account {owner_names}. "
                f"Characters on that account: {alts}"
            )
            return True

        self.msg(f"{_character_label(character)} is on accounts: {owner_names}")
        return True


class CmdTradePokemon(Command):
    """Offer, inspect and consent to durable Pokemon trades.

    Usage:
      +trade
      +trade offer <character>=<your party slot or Pokemon UUID>
      +trade inspect <offer UUID>
      +trade counter <offer UUID>=<your party slot or Pokemon UUID>
      +trade accept <offer UUID>
      +trade decline <offer UUID>
      +trade cancel <offer UUID>

    Offers last 15 minutes. Gifts require acceptance. For a swap, the recipient
    counters with their own Pokemon, then the original proposer accepts the new
    offer. Inspect an offer before accepting or countering it. Every counteroffer
    requires a new inspection and consent. Party and boxed Pokemon are
    supported; use a unique UUID prefix of at least eight characters for boxes.
    No fees; full parties use boxes. Trade-trigger evolution is deferred: use the
    documented manual evolution equivalents. Expired/stale offers cannot complete;
    cancel them to release their reservations. +trade lists outcomes after reconnect.
    """

    key = "+trade"
    aliases = ["tradepokemon"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        """Keep every user mutation behind fresh character-scoped offer services."""
        raw = (self.args or "").strip()
        action, _, arguments = raw.partition(" ")
        action = action.lower()
        if raw and action not in {"offer", "counter", "inspect", "accept", "cancel", "decline"}:
            self.caller.msg("Use +trade offer <character>=<your slot/UUID>. Gifts require recipient acceptance; +trade lists your offers.")
            return
        from pokemon.services.placement import PlacementError
        from pokemon.services.trading import TradeOffers

        try:
            service = TradeOffers(self.caller)
            if not raw:
                offers = service.offers()
                self.caller.msg("Trade offers (up to 30, pending first):\n" + "\n".join(service.list_line(offer) for offer in offers)
                    if offers else "No trade offers. Use +trade offer <character>=<your slot/UUID>. Gifts require acceptance.")
            elif action == "offer" and "=" in arguments:
                recipient, selector = [value.strip() for value in arguments.split("=", 1)]
                self.caller.msg(service.describe(service.propose(recipient, selector)))
            elif action == "counter" and "=" in arguments:
                identifier, selector = [value.strip() for value in arguments.split("=", 1)]
                self.caller.msg(service.describe(service.counter(identifier, selector)))
            elif action == "inspect" and arguments:
                self.caller.msg(service.inspect(arguments.strip()))
            elif action == "accept" and arguments:
                receipt = service.accept(arguments.strip())
                self.caller.msg("Trade completed: " + receipt["transfer"] + ". Both sides are saved. Use +trade to inspect the receipt.")
            elif action in {"cancel", "decline"} and arguments:
                operation = service.close(arguments.strip(), decline=action == "decline")
                self.caller.msg(service.describe(operation))
            else:
                self.caller.msg("Use +trade offer <character>=<your slot/UUID>, or +trade inspect/accept/counter/decline/cancel <offer UUID>.")
        except PlacementError as error:
            self.caller.msg(str(error) + " No Pokemon changed owner. Use +trade to inspect or cancel the offer.")
