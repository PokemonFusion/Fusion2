"""Commands for trainer/Pokemon fusion forms."""

from __future__ import annotations

try:  # pragma: no cover - Evennia can expose Command lazily in import-only tests
    from evennia import Command as _EvenniaCommand
except Exception:  # pragma: no cover
    _EvenniaCommand = None

if _EvenniaCommand is None:  # pragma: no cover - import-only fallback
    try:
        from evennia.commands.command import Command as _EvenniaCommand
    except Exception:
        _EvenniaCommand = object

Command = _EvenniaCommand

from utils.fusion import (
    PERMANENT,
    TEMPORARY,
    activate_permanent_form,
    activate_permanent_fusion,
    activate_temporary_fusion,
    deactivate_fusion,
    fusion_form_ids,
    get_active_fusion_pokemon,
    get_fusion_kind,
    resolve_owned_pokemon,
)
from utils.locks import require_no_battle_lock


def _parse_slot(raw: str) -> int | None:
    """Accept ``2``, ``slot2``, or ``slot 2`` and return a party slot."""

    cleaned = (raw or "").strip().lower()
    if not cleaned:
        return None
    tokens = cleaned.replace("=", " ").replace(",", " ").split()
    expanded = []
    for token in tokens:
        if token.startswith("slot") and token != "slot":
            expanded.append(token[4:])
        else:
            expanded.append(token)
    for token in expanded:
        try:
            slot = int(token)
        except (TypeError, ValueError):
            continue
        if 1 <= slot <= 6:
            return slot
    return None


def _get_slot_pokemon(caller, slot: int):
    getter = getattr(caller, "get_active_pokemon_by_slot", None)
    if callable(getter):
        return getter(slot)
    storage = getattr(caller, "storage", None)
    try:
        party = list(storage.get_party()) if storage else []
    except Exception:
        party = []
    return party[slot - 1] if 0 <= slot - 1 < len(party) else None


def _pokemon_display(pokemon) -> str:
    return str(getattr(pokemon, "name", None) or getattr(pokemon, "nickname", None) or getattr(pokemon, "species", "Pokemon"))


def _bond_value(pokemon) -> int:
    for attr in ("bond", "Bond", "friendship", "happiness"):
        value = getattr(pokemon, attr, None)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
    return 0


def _held_item(pokemon) -> str:
    value = getattr(pokemon, "held_item", None) or getattr(pokemon, "holding", None) or ""
    return str(value).strip()


def _is_breeding_locked(pokemon) -> bool:
    flags = getattr(pokemon, "flags", None) or []
    lower_flags = {str(flag).lower() for flag in flags}
    return bool(
        getattr(pokemon, "breed_timer", None)
        or getattr(pokemon, "breed_carrying", None)
        or "breeding" in lower_flags
        or "carrying_egg" in lower_flags
    )


def _validate_fusion_source(caller, slot: int, *, permanent: bool = False):
    pokemon = _get_slot_pokemon(caller, slot)
    if not pokemon:
        return None, f"No Pokemon in party slot {slot}."

    held = _held_item(pokemon)
    if held and held.lower() != "nothing":
        return None, "That Pokemon must not be holding an item before fusion."

    if getattr(pokemon, "is_egg", False):
        return None, "Eggs cannot be used for fusion."

    if _is_breeding_locked(pokemon):
        return None, "That Pokemon cannot fuse while breeding or carrying an egg."

    needed = 255 if permanent else 140
    bond = _bond_value(pokemon)
    if bond < needed:
        return None, f"Bond must be at least {needed} for this fusion. Current Bond: {bond}."

    return pokemon, ""


class CmdTempFuse(Command):
    """Temporarily fuse with one of your party Pokemon.

    Usage:
      +fuse/temp <slot>
      +tempfuse slot<slot>

    Examples:
      +fuse/temp 2
      +tempfuse slot2

    Notes:
      Temporary fusion requires Bond 140, no held item, and no active battle.
      The fused Pokemon leaves your party until you use +unfuse.
    """

    key = "+fuse/temp"
    aliases = ["+tempfuse", "+fusion/temp"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not require_no_battle_lock(self.caller):
            return
        slot = _parse_slot(self.args)
        if not slot:
            self.caller.msg("Usage: +fuse/temp <slot>")
            return
        pokemon, error = _validate_fusion_source(self.caller, slot, permanent=False)
        if error:
            self.caller.msg(error)
            return
        ok, message = activate_temporary_fusion(self.caller, pokemon, slot=slot)
        self.caller.msg(message if ok else f"|r{message}|n")


class CmdPermFuse(Command):
    """Permanently unlock a fusion form from one of your party Pokemon.

    Usage:
      +fuse/permanent <slot> confirm
      +permfuse slot<slot> confirm

    Examples:
      +fuse/permanent 2 confirm
      +permfuse slot2 confirm

    Notes:
      Permanent fusion requires Bond 255 and consumes that Pokemon as a
      separate party member. Use +fusion to switch between unlocked forms.
    """

    key = "+fuse/permanent"
    aliases = ["+permfuse", "+fuse/perm", "+fusion/perm"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not require_no_battle_lock(self.caller):
            return
        slot = _parse_slot(self.args)
        if not slot:
            self.caller.msg("Usage: +fuse/permanent <slot> confirm")
            return
        tokens = {part.strip().lower() for part in (self.args or "").split()}
        if not ({"confirm", "yes", "y"} & tokens):
            self.caller.msg(
                "Permanent fusion cannot be undone into a separate Pokemon. "
                "Repeat with |wconfirm|n to continue."
            )
            return
        pokemon, error = _validate_fusion_source(self.caller, slot, permanent=True)
        if error:
            self.caller.msg(error)
            return
        ok, message = activate_permanent_fusion(self.caller, pokemon)
        self.caller.msg(message if ok else f"|r{message}|n")


class CmdUnfuse(Command):
    """Leave your current fusion form.

    Usage:
      +unfuse
      +fuse/off

    Examples:
      +unfuse

    Notes:
      Temporary fusion returns the Pokemon to party or storage. Permanent
      fusion only returns you to human form; the Pokemon remains part of you.
    """

    key = "+unfuse"
    aliases = ["+fuse/off", "+fusion/off"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not require_no_battle_lock(self.caller):
            return
        ok, message = deactivate_fusion(self.caller)
        self.caller.msg(message if ok else f"|r{message}|n")


class CmdFusionForms(Command):
    """List or select permanent fusion forms.

    Usage:
      +fusion
      +fusion <number||pokemon_id||species>

    Examples:
      +fusion
      +fusion 1
      +forms Pikachu

    Notes:
      +fusion only selects permanent forms. Use +fuse/temp for temporary
      fusion and +unfuse to return to human form.
    """

    key = "+fusion"
    aliases = ["+forms", "+form"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def _forms(self):
        forms = []
        for pid in fusion_form_ids(self.caller):
            pokemon = resolve_owned_pokemon(self.caller, pid)
            if pokemon:
                forms.append(pokemon)
        return forms

    def _match_form(self, forms, raw: str):
        query = (raw or "").strip().lower()
        if not query:
            return None
        if query.isdigit():
            idx = int(query)
            if 1 <= idx <= len(forms):
                return forms[idx - 1]
        for pokemon in forms:
            pid = str(getattr(pokemon, "unique_id", "") or getattr(pokemon, "id", "")).lower()
            species = str(getattr(pokemon, "species", "")).lower()
            name = _pokemon_display(pokemon).lower()
            if pid.startswith(query) or species == query or name == query:
                return pokemon
        return None

    def func(self):
        if not require_no_battle_lock(self.caller):
            return
        forms = self._forms()
        active = get_active_fusion_pokemon(self.caller)
        kind = get_fusion_kind(self.caller)

        if not (self.args or "").strip():
            lines = ["|wFusion Forms|n"]
            if active:
                label = "temporary" if kind == TEMPORARY else "permanent"
                lines.append(f"Current: {_pokemon_display(active)} ({label})")
            else:
                lines.append("Current: human form")
            if forms:
                lines.append("Unlocked permanent forms:")
                active_id = str(getattr(active, "unique_id", "") or getattr(active, "id", "")) if active else ""
                for idx, pokemon in enumerate(forms, 1):
                    marker = " *" if active_id and str(getattr(pokemon, "unique_id", "") or getattr(pokemon, "id", "")) == active_id else ""
                    lines.append(f"  {idx}: {_pokemon_display(pokemon)}{marker}")
            else:
                lines.append("Unlocked permanent forms: none")
            lines.append("Use |w+fusion <number>|n to take a permanent form.")
            self.caller.msg("\n".join(lines))
            return

        pokemon = self._match_form(forms, self.args)
        if not pokemon:
            self.caller.msg("No matching permanent fusion form. Use +fusion to list forms.")
            return
        ok, message = activate_permanent_form(self.caller, pokemon)
        self.caller.msg(message if ok else f"|r{message}|n")


class CmdFusionOrder(Command):
    """Choose whether your fusion form enters battle first.

    Usage:
      +fusion/order [first||normal]
      +mefirst

    Examples:
      +fusion/order first
      +fusion/order normal
      +mefirst

    Notes:
      With no argument, this toggles between first and normal party order.
    """

    key = "+fusion/order"
    aliases = ["+mefirst"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        db = getattr(self.caller, "db", None)
        current = getattr(db, "fusion_battle_order", "normal") if db is not None else "normal"
        arg = (self.args or "").strip().lower()
        if arg in {"first", "front", "on", "yes"}:
            new = "first"
        elif arg in {"normal", "party", "last", "off", "no"}:
            new = "normal"
        elif arg:
            self.caller.msg("Usage: +fusion/order [first||normal]")
            return
        else:
            new = "normal" if current == "first" else "first"
        if db is not None:
            db.fusion_battle_order = new
        if new == "first":
            self.caller.msg("Your active fusion form will enter battle first.")
        else:
            self.caller.msg("Your active fusion form will follow normal party order.")


class CmdFusionFight(Command):
    """Toggle whether your active fusion form joins battles.

    Usage:
      +fusion/fight [on||off]
      +mefight

    Examples:
      +fusion/fight on
      +fusion/fight off
      +mefight

    Notes:
      This only affects the active fusion form. It does not change party
      Pokemon participation.
    """

    key = "+fusion/fight"
    aliases = ["+mefight"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        db = getattr(self.caller, "db", None)
        current = getattr(db, "fusion_participates", True) if db is not None else True
        arg = (self.args or "").strip().lower()
        if arg in {"on", "yes", "true", "1"}:
            new = True
        elif arg in {"off", "no", "false", "0"}:
            new = False
        elif arg:
            self.caller.msg("Usage: +fusion/fight [on||off]")
            return
        else:
            new = not current
        if db is not None:
            db.fusion_participates = new
        if new:
            self.caller.msg("Your active fusion form will participate in battles.")
        else:
            self.caller.msg("Your active fusion form will stay out of battles.")
