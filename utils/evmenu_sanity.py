# fusion2/utils/evmenu_sanity.py
from __future__ import annotations
from typing import Any, Dict, List, Tuple
import re

from evennia.utils.evmenu import EvMenuGotoAbortMessage

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
    Demonstrates tuple keys and regex-like routing using `_default`.
    """
    text = (
        "|wSubmenu|n\n"
        "Valid keys: 1/yes, 2/no. You can also type any |cthree digits|n (e.g. 123).\n"
        "Type anything else to see invalid-input handling."
    )
    options = [
        {"key": ("1", "yes", "y"), "desc": "Say yes", "goto": "node_said_yes"},
        {"key": ("2", "no", "n"), "desc": "Say no", "goto": "node_said_no"},
        {"key": ("b", "back"), "desc": "Back to start", "goto": "node_start"},
        # Fallback: inspect raw_string and decide where to go.
        {"key": "_default", "goto": _submenu_router},
    ]
    return text, options

def _submenu_router(caller, raw_string: str, **kwargs):
    """
    Fallback router for node_submenu: emulate regex handling.
    """
    s = (raw_string or "").strip()
    if re.fullmatch(r"\d{3}", s):
        return "node_digits", {"digits": s}
    # Abort the transition but print a single-line message; stay on the same node.
    raise EvMenuGotoAbortMessage("Enter 1/2, 'back', or any three digits (e.g. 123).")

def node_digits(caller, raw_string: str, digits: str = "", **kwargs):
    text = (
        f"|wRegex-like route ok.|n You entered: |c{digits}|n\n"
        "Try another 3-digit number or 'back'."
    )
    options = [
        {"key": ("back", "b"), "desc": "Back to submenu", "goto": "node_submenu"},
        # Keep accepting new three-digit inputs on this node via the same router.
        {"key": "_default", "goto": _submenu_router},
    ]
    return text, options

def node_input(caller, raw_string: str, **kwargs):
    """
    Free-form input test using `_default` to loop and echo.
    """
    s = (raw_string or "").strip()
    if s and s.lower() not in ("back", "b"):
        text = f"|wYou typed:|n {s}\n(Enter 'back' to return or type anything to keep echoing.)"
    else:
        text = "|wFree-form input test.|n Type anything (or 'back' to return)."
    options = [
        {"key": ("back", "b"), "desc": "Return to start", "goto": "node_start"},
        # Any other input loops back here and will be echoed.
        {"key": "_default", "goto": "node_input"},
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

    
