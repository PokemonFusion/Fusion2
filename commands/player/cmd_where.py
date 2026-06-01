from evennia import Command, SESSION_HANDLER
from evennia.objects.objects import DefaultCharacter
from evennia.utils import utils
from evennia.utils.evtable import EvTable


PLAYER_PRIVATE_ATTR = "where_private"
ROOM_PRIVATE_ATTR = "where_private"
STAFF_PERMISSIONS = (
    "Wizards",
    "Wizard",
    "Developer",
    "Developers",
    "Admin",
    "Admins",
    "Builder",
    "Builders",
)


def _db_bool(obj, attr_name):
    db = getattr(obj, "db", None)
    return bool(getattr(db, attr_name, False)) if db is not None else False


def _set_db_bool(obj, attr_name, value):
    setattr(obj.db, attr_name, bool(value))


def _check_perm(obj, perm):
    check = getattr(obj, "check_permstring", None)
    if callable(check) and check(perm):
        return True

    account = getattr(obj, "account", None)
    check = getattr(account, "check_permstring", None)
    return bool(callable(check) and check(perm))


def _is_staff(caller):
    return any(_check_perm(caller, perm) for perm in STAFF_PERMISSIONS)


def _is_character(obj):
    if not obj:
        return False
    is_typeclass = getattr(obj, "is_typeclass", None)
    if not callable(is_typeclass):
        return False
    return bool(is_typeclass(DefaultCharacter, exact=False))


def _online_characters():
    chars = []
    seen = set()
    for session in SESSION_HANDLER.get_sessions():
        get_puppet = getattr(session, "get_puppet", None)
        char = get_puppet() if callable(get_puppet) else None
        if not _is_character(char):
            continue

        ident = getattr(char, "id", None) or getattr(char, "dbref", None) or id(char)
        if ident in seen:
            continue

        seen.add(ident)
        chars.append(char)

    return sorted(chars, key=lambda char: (getattr(char, "key", "") or "").lower())


def _can_see_character(caller, char, staff=False):
    return staff or not _db_bool(char, "dark")


def _location_is_private(char):
    if _db_bool(char, PLAYER_PRIVATE_ATTR):
        return True
    location = getattr(char, "location", None)
    return bool(location and _db_bool(location, ROOM_PRIVATE_ATTR))


def _location_name(char, staff=False):
    location = getattr(char, "location", None)
    if not location:
        return "Nowhere"
    if not staff and _location_is_private(char):
        return "*Private*"
    return getattr(location, "key", None) or getattr(location, "name", None) or str(location)


def _idle_string(char):
    idle = getattr(char, "idle_time", None)
    return utils.time_format(idle, 1) if idle is not None else "0s"


def _gender(char):
    db = getattr(char, "db", None)
    return getattr(db, "gender", None) or "Unknown"


def _species(char):
    db = getattr(char, "db", None)
    return getattr(db, "fusion_species", None) or "Human"


def _ic_status(char):
    db = getattr(char, "db", None)
    return getattr(db, "ic_status", None) or getattr(db, "ICStatus", None) or "IC"


def _display_name(char, staff=False):
    name = getattr(char, "key", None) or getattr(char, "name", None) or str(char)
    if staff and _db_bool(char, "dark"):
        return f"{name} (Dark)"
    return name


def _room_control_allowed(caller, room, staff=False):
    if staff:
        return True

    access = getattr(caller, "access", None)
    if callable(access):
        for access_type in ("edit", "control", "delete"):
            try:
                if access(room, access_type):
                    return True
            except TypeError:
                continue

    return False


def _find_online_character(chars, query):
    query = query.strip().lower()
    exact = [char for char in chars if (getattr(char, "key", "") or "").lower() == query]
    if exact:
        return exact, "exact"

    prefix = [char for char in chars if (getattr(char, "key", "") or "").lower().startswith(query)]
    if prefix:
        return prefix, "prefix"

    contains = [char for char in chars if query in (getattr(char, "key", "") or "").lower()]
    return contains, "contains"


class CmdWhere(Command):
    """Find online characters and their visible locations.

    Usage:
      +where
      +where <character>
      +where #private
      +where #public
      +where #roomprivate
      +where #roompublic

    Aliases:
      where, wa

    Notes:
      Location privacy hides your room from regular players, not from staff.
      The short legacy forms #p, #!p, #r, and #!r also work.
    """

    key = "+where"
    aliases = ["where", "wa"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()
        lowered = args.lower()
        staff = _is_staff(caller)

        if lowered in {"#help", "help", "/help"}:
            caller.msg(
                "Usage: +where [character] | +where #private | +where #public | "
                "+where #roomprivate | +where #roompublic"
            )
            return

        if lowered in {"#private", "#p", "#hide"}:
            _set_db_bool(caller, PLAYER_PRIVATE_ATTR, True)
            caller.msg("Your location is now hidden from +where.")
            return

        if lowered in {"#public", "#!p", "#show"}:
            _set_db_bool(caller, PLAYER_PRIVATE_ATTR, False)
            caller.msg("Your location is now visible on +where.")
            return

        if lowered in {"#roomprivate", "#r"}:
            room = getattr(caller, "location", None)
            if not room:
                caller.msg("You have no current room to hide.")
                return
            if not _room_control_allowed(caller, room, staff=staff):
                caller.msg("You do not have permission to change this room's +where privacy.")
                return
            _set_db_bool(room, ROOM_PRIVATE_ATTR, True)
            caller.msg("This room is now hidden from +where.")
            return

        if lowered in {"#roompublic", "#!r"}:
            room = getattr(caller, "location", None)
            if not room:
                caller.msg("You have no current room to reveal.")
                return
            if not _room_control_allowed(caller, room, staff=staff):
                caller.msg("You do not have permission to change this room's +where privacy.")
                return
            _set_db_bool(room, ROOM_PRIVATE_ATTR, False)
            caller.msg("This room is now visible on +where.")
            return

        if lowered.startswith("#") and lowered not in {"#alpha", "#location", "#loc"}:
            caller.msg("Unknown +where option. Use +where #help for usage.")
            return

        visible_chars = [
            char for char in _online_characters() if _can_see_character(caller, char, staff=staff)
        ]

        if args and not lowered.startswith("#"):
            matches, _match_type = _find_online_character(visible_chars, args.split()[0])
            if not matches:
                caller.msg("I don't know who that is.")
                return
            if len(matches) > 1:
                names = ", ".join(_display_name(char, staff=staff) for char in matches[:8])
                if len(matches) > 8:
                    names += ", ..."
                caller.msg(f"Multiple online characters match: {names}")
                return
            self._show_table([matches[0]], staff=staff)
            return

        if not visible_chars:
            caller.msg("No online characters found.")
            return

        self._show_table(visible_chars, staff=staff)

    def _show_table(self, chars, staff=False):
        table = EvTable("Name", "IC", "Gender", "Species", "Idle", "Location")
        for char in chars:
            table.add_row(
                _display_name(char, staff=staff),
                _ic_status(char),
                _gender(char),
                _species(char),
                _idle_string(char),
                _location_name(char, staff=staff),
            )
        self.caller.msg(str(table))
