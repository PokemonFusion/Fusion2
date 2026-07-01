from evennia import search_object
from evennia.commands.default.muxcommand import MuxCommand
from evennia.objects.objects import DefaultCharacter
from evennia.utils.evtable import EvTable

from utils.character_profiles import (
    ProfileError,
    delete_profile_field,
    get_profile_fields,
    set_profile_field,
    set_profile_field_privacy,
    visible_profile_fields,
)


def _is_character(obj):
    check = getattr(obj, "is_typeclass", None)
    return bool(callable(check) and check(DefaultCharacter, exact=False))


def _character_name(character):
    return getattr(character, "key", None) or getattr(character, "name", None) or str(character)


def _caller_character(command):
    session = getattr(command, "session", None)
    get_puppet = getattr(session, "get_puppet", None)
    if callable(get_puppet):
        puppet = get_puppet()
        if _is_character(puppet):
            return puppet

    for attr in ("character", "obj", "caller"):
        candidate = getattr(command, attr, None)
        if _is_character(candidate):
            return candidate

    return None


def _search_character(query):
    matches = search_object(query, exact=False, typeclass="typeclasses.characters.Character")
    return [match for match in matches if _is_character(match)]


class CmdProfile(MuxCommand):
    """View and edit RP profile fields.

    Usage:
      +profile [character]
      +profile/set <field>=<text>
      +profile/del <field>
      +profile/private <field>
      +profile/public <field>

    Aliases:
      +finger, +info
    """

    key = "+profile"
    aliases = ["+finger", "+info"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        switches = {switch.lower() for switch in getattr(self, "switches", []) or []}

        if "help" in switches or (self.args or "").strip().lower() in {"#help", "help"}:
            self._show_help()
            return

        if "set" in switches:
            self._set_field()
            return

        if "del" in switches or "delete" in switches or "rem" in switches:
            self._delete_field()
            return

        if "private" in switches or "priv" in switches:
            self._set_privacy(private=True)
            return

        if "public" in switches:
            self._set_privacy(private=False)
            return

        self._show_profile()

    def _show_help(self):
        self.caller.msg(
            "Usage: +profile [character] | +profile/set <field>=<text> | "
            "+profile/del <field> | +profile/private <field> | +profile/public <field>"
        )

    def _set_field(self):
        character = _caller_character(self)
        if not character:
            self.caller.msg("You must be in-character to edit your profile.")
            return
        if not getattr(self, "lhs", "") or not getattr(self, "rhs", ""):
            self.caller.msg("Usage: +profile/set <field>=<text>")
            return
        try:
            field = set_profile_field(character, self.lhs, self.rhs)
        except ProfileError as err:
            self.caller.msg(str(err))
            return
        self.caller.msg(f"Profile field '{field['label']}' saved.")

    def _delete_field(self):
        character = _caller_character(self)
        if not character:
            self.caller.msg("You must be in-character to edit your profile.")
            return
        field = (self.args or "").strip()
        if not field:
            self.caller.msg("Usage: +profile/del <field>")
            return
        if delete_profile_field(character, field):
            self.caller.msg(f"Profile field '{field}' deleted.")
        else:
            self.caller.msg("No such profile field.")

    def _set_privacy(self, private):
        character = _caller_character(self)
        if not character:
            self.caller.msg("You must be in-character to edit your profile.")
            return
        field = (self.args or "").strip()
        if not field:
            action = "private" if private else "public"
            self.caller.msg(f"Usage: +profile/{action} <field>")
            return
        try:
            updated = set_profile_field_privacy(character, field, private)
        except ProfileError as err:
            self.caller.msg(str(err))
            return
        state = "private" if private else "public"
        self.caller.msg(f"Profile field '{updated['label']}' is now {state}.")

    def _show_profile(self):
        args = (self.args or "").strip()
        viewer = _caller_character(self) or self.caller
        target = viewer if _is_character(viewer) else None
        if args:
            matches = _search_character(args)
            if not matches:
                self.caller.msg("No matching character found.")
                return
            if len(matches) > 1:
                names = ", ".join(_character_name(match) for match in matches[:8])
                if len(matches) > 8:
                    names += ", ..."
                self.caller.msg(f"Multiple characters match: {names}")
                return
            target = matches[0]
        elif not target:
            self.caller.msg("Usage: +profile <character>")
            return

        fields = visible_profile_fields(target, viewer)
        if not fields:
            self.caller.msg(f"{_character_name(target)} has no visible profile fields.")
            return

        table = EvTable("Field", "Profile")
        all_fields = get_profile_fields(target)
        for key, field in fields.items():
            label = field["label"]
            if all_fields.get(key, {}).get("private"):
                label = f"{label} <PRIVATE>"
            table.add_row(label, field["text"])

        self.caller.msg(f"Profile for {_character_name(target)}:\n{table}")


class CmdAccountProfile(CmdProfile):
    """Account-level access to global profile viewing while OOC."""

    account_caller = True
