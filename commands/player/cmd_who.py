"""Local account `who` command customizations."""

from evennia.commands.default.account import CmdWho as DefaultCmdWho
from evennia.utils.evtable import EvTable

from commands.player.cmd_where import (
    CmdWhere,
    _display_name,
    _gender,
    _ic_status,
    _idle_string,
    _location_name,
)

STAFF_LOCK = (
    "cmd:perm(Helper) or perm(Validator) or perm(Builder) or perm(Admin) "
    "or perm(Developer) or perm(Wizards)"
)
WHO_TABLE_MIN_WIDTH = 100
WHO_TABLE_MAX_WIDTH = 140
WHO_SMALL_COLUMN_WIDTHS = {
    "on_for": 12,
    "idle": 9,
    "cmds": 9,
    "protocol": 12,
    "host": 16,
}
WHO_PLAYER_HEADERS = ("|cName|n", "|cIC|n", "|cIdle|n", "|cSex|n", "|cLocation|n")


def get_who_table_width(client_width) -> int:
    """Return the display budget for the staff `who` table."""

    try:
        width = int(client_width)
    except (TypeError, ValueError):
        width = WHO_TABLE_MIN_WIDTH
    return max(WHO_TABLE_MIN_WIDTH, min(width, WHO_TABLE_MAX_WIDTH))


def get_who_column_widths(table_width) -> tuple[int, int, int, int, int, int, int, int]:
    """Return per-column widths for the privileged `who` table."""

    table_width = get_who_table_width(table_width)
    fixed_width = sum(WHO_SMALL_COLUMN_WIDTHS.values())
    flexible_width = table_width - fixed_width
    account_width = max(16, flexible_width * 35 // 100)
    puppeting_width = max(14, flexible_width * 30 // 100)
    room_width = flexible_width - account_width - puppeting_width
    return (
        account_width,
        WHO_SMALL_COLUMN_WIDTHS["on_for"],
        WHO_SMALL_COLUMN_WIDTHS["idle"],
        puppeting_width,
        room_width,
        WHO_SMALL_COLUMN_WIDTHS["cmds"],
        WHO_SMALL_COLUMN_WIDTHS["protocol"],
        WHO_SMALL_COLUMN_WIDTHS["host"],
    )


def _short_gender(char) -> str:
    """Return the PF1-style one-letter gender marker."""

    gender = str(_gender(char) or "").strip()
    if not gender:
        return "?"
    marker = gender[0].upper()
    return marker if marker in {"M", "F", "N"} else "O"


def _who_value(text, color="|w") -> str:
    return f"{color}{text}|n"


class CmdWho(CmdWhere):
    """Show online puppets in a PF1-style player-facing table."""

    key = "who"
    aliases = ["3who"]
    locks = "cmd:all()"
    help_category = "General"

    def _show_table(self, chars, staff=False):
        table = EvTable(*WHO_PLAYER_HEADERS)
        for char in chars:
            table.add_row(
                _who_value(_display_name(char, staff=staff), "|c"),
                _who_value(_ic_status(char)),
                _who_value(_idle_string(char)),
                _who_value(_short_gender(char)),
                _who_value(_location_name(char, staff=staff), "|g"),
            )
        self.caller.msg(str(table))


class CmdStaffWho(DefaultCmdWho):
    """Width-aware staff variant of Evennia's account/session `who` command."""

    key = "@who"
    aliases = ["@doing", "staffwho"]
    locks = STAFF_LOCK
    help_category = "Admin"

    def styled_table(self, *args, **kwargs):
        # The privileged form has many columns; give it room in wider clients.
        if len(args) >= 8:
            table_width = get_who_table_width(self.client_width())
            kwargs.setdefault("width", table_width)
            table = super().styled_table(*args, **kwargs)
            for column, column_width in zip(table.table, get_who_column_widths(table_width), strict=False):
                column.options["width"] = column_width
            return table
        return super().styled_table(*args, **kwargs)
