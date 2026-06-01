from django.conf import settings
from evennia import Command, search_account, search_object
from evennia.accounts.models import AccountDB
from evennia.commands.default.account import CmdCharCreate as DefaultCmdCharCreate

from pokemon.models.storage import move_to_box
from utils.locks import require_no_battle_lock

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
            " the game as this character."
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
    """Trade a Pokemon with another character.

    Usage:
      +trade <pokemon_id>=<character>

    Examples:
      +trade abc123=Misty

    Notes:
      You cannot trade while either character is in battle.
    """

    key = "+trade"
    aliases = ["tradepokemon"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not require_no_battle_lock(self.caller):
            return
        if not self.args or "=" not in self.args:
            self.caller.msg("Usage: +trade <pokemon_id>=<character>")
            return
        pid, target_name = [part.strip() for part in self.args.split("=", 1)]
        target = self.caller.search(target_name)
        if not target:
            return
        if not require_no_battle_lock(target):
            return
        if target.account == self.caller.account:
            self.caller.msg("You cannot trade items between your own characters.")
            return
        pokemon = self.caller.get_pokemon_by_id(pid)
        if not pokemon:
            self.caller.msg("No such Pokemon.")
            return
        if pokemon in self.caller.storage.get_party():
            self.caller.storage.remove_active_pokemon(pokemon)
            target.storage.add_active_pokemon(pokemon)
        elif pokemon in self.caller.storage.get_stored_pokemon():
            move_to_box(pokemon, target.storage, target.get_box(1))
        else:
            self.caller.msg("You don't have that Pokemon.")
            return
        name = pokemon.nickname or pokemon.species
        self.caller.msg(f"You traded {name} to {target.key}.")
        target.msg(f"{self.caller.key} traded {name} to you.")
