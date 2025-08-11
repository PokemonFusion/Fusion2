# fusion2/utils/evmenu_sanity.py
from __future__ import annotations
from typing import Any, Dict, List, Tuple

# Each node returns (text, options). `options` is a list of dicts. Keys:
#  - "key": a string, tuple of aliases, or a regex
#  - "desc": shown next to the key in the option list
#  - "goto": next node name (str) or a callable returning a node name/(text, options)
#  - "exec": (optional) callable run before goto; return value is ignored

def node_start(caller, raw_string: str, **kwargs) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Basic branching node. Good to test: normal selection, invalid key, and quit.
    """
    text = (
        "|wEvMenu sanity start|n\n"
        "Try entering an invalid key to see default behavior.\n"
        "Try numbers, letters, blank lines, and long strings.\n"
        "Type |yq|n to quit (EvMenu default), or make a valid selection."
    )
    options = [
        {"key": ("1", "a", "alpha"), "desc": "Go to a submenu with more options", "goto": "node_submenu"},
        {"key": ("2", "input"), "desc": "Free-form input test", "goto": "node_input"},
        {"key": ("3", "exec"), "desc": "Run exec() before goto", "exec": _count_bump, "goto": "node_exec_result"},
        {"key": ("4", "loop"), "desc": "Return to this node (self-loop)", "goto": "node_start"},
    ]
    return text, options

def node_submenu(caller, raw_string: str, **kwargs):
    """
    Demonstrates tuple keys, regex, and a goto callable.
    """
    text = (
        "|wSubmenu|n\n"
        "Valid keys: 1/yes, 2/no, or anything matching regex ^[0-9]{3}$.\n"
        "Type anything else to observe invalid-input handling."
    )
    options = [
        {"key": ("1", "yes", "y"), "desc": "Say yes", "goto": "node_said_yes"},
        {"key": ("2", "no", "n"), "desc": "Say no", "goto": "node_said_no"},
        {"key": r"^[0-9]{3}$", "desc": "Any three digits -> callable goto", "goto": _goto_digits},
        {"key": ("b", "back"), "desc": "Back to start", "goto": "node_start"},
    ]
    return text, options

def node_input(caller, raw_string: str, **kwargs):
    """
    Free-form input node—any input gets echoed. Blank input is useful to test default errors.
    EvMenu will keep you on this node after invalid input unless you change goto logic.
    """
    # If raw_string is non-empty, 'accept' it; else re-prompt.
    if raw_string and raw_string.strip():
        text = f"|wYou typed:|n {raw_string.strip()}\n(Enter 'back' to return or anything else to keep echoing.)"
        options = [
            {"key": ("back", "b"), "desc": "Return to start", "goto": "node_start"},
            # Keep a catch-all regex here so *valid* input also 'loops' predictably
            {"key": r"^.*$", "desc": "Keep echoing", "goto": "node_input"},
        ]
        return text, options

    # First entry or blank input: show instructions with clear prompt.
    text = "|wFree-form input test.|n Type anything (or 'back' to return)."
    options = [
        {"key": ("back", "b"), "desc": "Return to start", "goto": "node_start"},
        {"key": r"^.*$", "desc": "Echo whatever you type", "goto": "node_input"},
    ]
    return text, options

def node_exec_result(caller, raw_string: str, **kwargs):
    """
    Shows that exec() ran and that state persisted on the caller (db/ndb).
    """
    bumped = getattr(caller.ndb, "evmenu_counter", 0)
    text = f"|wExec test|n – counter on caller.ndb is now: |c{bumped}|n"
    options = [
        {"key": ("1", "again"), "desc": "Bump again", "exec": _count_bump, "goto": "node_exec_result"},
        {"key": ("back", "b"), "desc": "Back to start", "goto": "node_start"},
    ]
    return text, options

def node_said_yes(caller, raw_string: str, **kwargs):
    text = "|gYou chose YES.|n"
    options = [{"key": ("back", "b"), "desc": "Back to submenu", "goto": "node_submenu"}]
    return text, options

def node_said_no(caller, raw_string: str, **kwargs):
    text = "|rYou chose NO.|n"
    options = [{"key": ("back", "b"), "desc": "Back to submenu", "goto": "node_submenu"}]
    return text, options

# ---------- helpers ----------

def _count_bump(caller, raw_string: str, **kwargs):
    caller.ndb.evmenu_counter = (getattr(caller.ndb, "evmenu_counter", 0) or 0) + 1

def _goto_digits(caller, raw_string: str, **kwargs):
    """
    Example callable goto – respond differently based on what matched the regex.
    """
    digits = raw_string.strip()
    return (
        f"|wRegex matched:|n {digits}\n"
        "Try other three-digit numbers, or 'back' to return."
    ), [
        {"key": ("back", "b"), "desc": "Back to submenu", "goto": "node_submenu"},
        {"key": r"^[0-9]{3}$", "desc": "Try another 3-digit number", "goto": _goto_digits},
    ]
