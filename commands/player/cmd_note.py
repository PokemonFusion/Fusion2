from evennia import Command, search_account, search_object
from evennia.utils.evtable import EvTable

from utils.staff_notes import (
    StaffNoteError,
    add_staff_note,
    delete_staff_note,
    get_staff_note,
    list_staff_notes,
)
from utils.staff_roster import account_name, is_staff_account


STAFF_LOCK = (
    "cmd:perm(Helper) or perm(Validator) or perm(Builder) or perm(Admin) "
    "or perm(Developer) or perm(Wizards)"
)


def _caller_account(command):
    return getattr(command, "account", None) or getattr(command, "caller", None)


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    try:
        return list(value)
    except TypeError:
        return [value]


def _clean_target_query(query: str, prefixes: tuple[str, ...]) -> str | None:
    raw = (query or "").strip()
    lowered = raw.lower()
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return raw[len(prefix) :].strip()
    return None


def _is_character(obj) -> bool:
    check = getattr(obj, "is_typeclass", None)
    return bool(callable(check) and check("typeclasses.characters.Character", exact=False))


def _object_name(obj) -> str:
    return getattr(obj, "key", None) or getattr(obj, "name", None) or str(obj)


def _target_label(target_info: dict) -> str:
    return f"{target_info['kind']} {_object_name(target_info['target'])}"


def _search_accounts(query: str) -> list[dict]:
    matches = _as_list(search_account(query, exact=True))
    return [{"kind": "account", "target": match} for match in matches if match]


def _search_characters(query: str) -> list[dict]:
    try:
        matches = search_object(query, exact=True, typeclass="typeclasses.characters.Character")
    except TypeError:
        matches = search_object(query)
    return [{"kind": "character", "target": match} for match in _as_list(matches) if match and _is_character(match)]


def _search_note_targets(query: str) -> list[dict]:
    raw = (query or "").strip()
    if not raw:
        return []

    account_query = _clean_target_query(raw, ("account:", "account/", "acct:", "*"))
    if account_query is not None:
        return _search_accounts(account_query)

    character_query = _clean_target_query(raw, ("character:", "character/", "char:"))
    if character_query is not None:
        return _search_characters(character_query)

    return _search_accounts(raw) + _search_characters(raw)


def _target_and_note_id(raw: str, lhs: str = "", rhs: str = "") -> tuple[str, str]:
    if rhs:
        return (lhs or "").strip(), rhs.strip()

    parts = (raw or "").strip().rsplit(None, 1)
    if len(parts) != 2:
        return "", ""
    return parts[0].strip(), parts[1].strip()


def _preview(text: str, width: int = 58) -> str:
    clean = " ".join(str(text or "").split())
    if len(clean) <= width:
        return clean
    return f"{clean[: width - 3].rstrip()}..."


class CmdNote(Command):
    """Manage staff-only notes on accounts and characters.

    Usage:
      +note <target>
      +note/show <target>=<id>
      +note/add <target>=<note>
      +note/del <target>=<id>

    Target prefixes:
      *<account>, account:<account>, char:<character>
    """

    key = "+note"
    aliases = ["+notes", "note"]
    locks = STAFF_LOCK
    help_category = "Staff"
    account_caller = True

    def func(self):
        account = _caller_account(self)
        if not is_staff_account(account):
            self.caller.msg("Only staff can use staff notes.")
            return

        switches = {switch.lower() for switch in getattr(self, "switches", []) or []}
        if "help" in switches or (self.args or "").strip().lower() in {"help", "#help"}:
            self._show_help()
            return

        if "add" in switches or "set" in switches:
            self._add_note(account)
            return

        if "show" in switches or "read" in switches:
            self._show_note()
            return

        if "del" in switches or "delete" in switches or "rem" in switches:
            self._delete_note()
            return

        self._list_notes()

    def _show_help(self):
        self.caller.msg(
            "Usage: +note <target> | +note/show <target>=<id> | "
            "+note/add <target>=<note> | +note/del <target>=<id>. "
            "Use *Account or account:<name> for account notes, char:<name> for character notes."
        )

    def _resolve_one_target(self, target_query: str):
        matches = _search_note_targets(target_query)
        if not matches:
            self.caller.msg("No matching account or character found.")
            return None
        if len(matches) > 1:
            names = ", ".join(_target_label(match) for match in matches[:8])
            if len(matches) > 8:
                names += ", ..."
            self.caller.msg(f"Multiple targets match: {names}")
            return None
        return matches[0]

    def _list_notes(self):
        target_query = (self.args or "").strip()
        if not target_query:
            self.caller.msg("Usage: +note <target>")
            return

        target_info = self._resolve_one_target(target_query)
        if not target_info:
            return

        notes = list_staff_notes(target_info["target"])
        if not notes:
            self.caller.msg(f"No staff notes found for {_target_label(target_info)}.")
            return

        table = EvTable("ID", "By", "Created", "Note")
        for note in notes:
            table.add_row(note["id"], note["author"] or "-", note["created_at"] or "-", _preview(note["text"]))
        self.caller.msg(f"Staff Notes for {_target_label(target_info)}:\n{table}")

    def _add_note(self, account):
        if not getattr(self, "lhs", "") or not getattr(self, "rhs", ""):
            self.caller.msg("Usage: +note/add <target>=<note>")
            return

        target_info = self._resolve_one_target(self.lhs)
        if not target_info:
            return

        try:
            note = add_staff_note(target_info["target"], account, self.rhs)
        except StaffNoteError as err:
            self.caller.msg(str(err))
            return

        self.caller.msg(f"Staff note #{note['id']} added to {_target_label(target_info)}.")

    def _show_note(self):
        target_query, note_id = _target_and_note_id(self.args, getattr(self, "lhs", ""), getattr(self, "rhs", ""))
        if not target_query or not note_id:
            self.caller.msg("Usage: +note/show <target>=<id>")
            return

        target_info = self._resolve_one_target(target_query)
        if not target_info:
            return

        try:
            note = get_staff_note(target_info["target"], note_id)
        except StaffNoteError as err:
            self.caller.msg(str(err))
            return

        self.caller.msg(
            f"Staff note #{note['id']} for {_target_label(target_info)}\n"
            f"By: {note['author'] or account_name(_caller_account(self))}\n"
            f"Created: {note['created_at'] or '-'}\n\n"
            f"{note['text']}"
        )

    def _delete_note(self):
        target_query, note_id = _target_and_note_id(self.args, getattr(self, "lhs", ""), getattr(self, "rhs", ""))
        if not target_query or not note_id:
            self.caller.msg("Usage: +note/del <target>=<id>")
            return

        target_info = self._resolve_one_target(target_query)
        if not target_info:
            return

        try:
            note = delete_staff_note(target_info["target"], note_id)
        except StaffNoteError as err:
            self.caller.msg(str(err))
            return

        self.caller.msg(f"Staff note #{note['id']} removed from {_target_label(target_info)}.")
