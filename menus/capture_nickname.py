"""Nickname choices shown after a captured Pokémon's battle has cleaned up."""

from pokemon.services.capture_nicknames import CaptureNicknames
from utils.locks import _has_active_battle_ref


def start_capture_nickname(caller):
    """Open or resume pending choices without interrupting a battle or menu."""
    if getattr(caller.db, "in_battle", False) or getattr(caller.ndb, "battle_instance", None):
        return False
    if _has_active_battle_ref(getattr(caller.db, "battle_lock", None)):
        return False
    if getattr(caller.ndb, "_evmenu", None):
        return False
    if not CaptureNicknames(caller).pending():
        return False
    attributes = getattr(caller, "attributes", None)
    saved = attributes.get("_menutree_saved") if attributes else None
    if saved and saved[1] != ("menus.capture_nickname",):
        return False
    from evennia.utils.evmenu import EvMenu

    EvMenu(caller, "menus.capture_nickname", startnode="nickname_offer", cmd_on_exit=None, persistent=True)
    return True


def nickname_offer(caller, raw_string=None, **kwargs):
    """Ask yes/no for the next caught Pokémon; no IDs are inferred from names."""
    pending = CaptureNicknames(caller).pending()
    if not pending:
        return "Nickname choices complete.", None
    entry = pending[0]
    data = {"pokemon_id": entry["pokemon_id"]}
    return f"Would you like to give {entry['species']} a nickname? (yes/no)", [
        {"key": ("yes", "y"), "goto": ("nickname_enter", data)},
        {"key": ("no", "n"), "goto": (_keep_name, data)},
    ]


def nickname_enter(caller, raw_string=None, **kwargs):
    """Accept a nickname with spaces, or an explicit cancellation."""
    return "Enter a nickname (1–50 characters), or 'cancel' to keep its name.", [
        {"key": "cancel", "goto": (_keep_name, kwargs)},
        {"key": "_default", "goto": (_save_name, kwargs)},
    ]


def _keep_name(caller, raw_string=None, **kwargs):
    """Decline a nickname and advance to any other queued catch."""
    name = CaptureNicknames(caller).complete(kwargs["pokemon_id"])
    caller.msg(f"Kept {name}'s name." if name else "That captured Pokémon is no longer available.")
    return "nickname_offer"


def _save_name(caller, raw_string=None, **kwargs):
    """Persist a valid name and keep invalid input in the same prompt."""
    try:
        name = CaptureNicknames(caller).complete(kwargs["pokemon_id"], raw_string or "")
    except ValueError as error:
        caller.msg(str(error))
        return "nickname_enter", kwargs
    caller.msg(f"Your Pokémon is now named {name}." if name else "That captured Pokémon is no longer available.")
    return "nickname_offer"
