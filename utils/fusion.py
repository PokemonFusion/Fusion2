"""Utilities for handling trainer and Pokemon fusions.

In Pokemon Fusion, fusion means an anthro Pokemon form made from a trainer
and a Pokemon. These helpers keep the current active form on the character
while leaving the Pokemon rows as the source of species, moves, and stats.
"""

from __future__ import annotations

from typing import Any, Iterable, Tuple

from pokemon.dex import POKEDEX

TEMPORARY = "temporary"
PERMANENT = "permanent"
FUSION_BOOST_CONFIG_KEY = "fusion2_fusion_stat_boost_enabled"
DEFAULT_FUSION_BOOST_ENABLED = True

ACTIVE_FUSION_ATTRS = (
    "fusion_id",
    "fusion_species",
    "fusion_ability",
    "fusion_nature",
    "fusion_kind",
    "fusion_temp_slot",
)


def _db(character) -> Any:
    return getattr(character, "db", None)


def _server_config():
    """Return Evennia's ServerConfig model lazily for runtime settings."""

    from evennia.server.models import ServerConfig

    return ServerConfig


def _coerce_bool(value: Any, *, default: bool = True) -> bool:
    """Convert persisted config values into a boolean."""

    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on", "enabled"}:
        return True
    if normalized in {"0", "false", "no", "n", "off", "disabled"}:
        return False
    return default


def is_fusion_boost_enabled(default: bool = DEFAULT_FUSION_BOOST_ENABLED) -> bool:
    """Return whether active fusion forms receive the battle stat boost."""

    try:
        raw = _server_config().objects.conf(FUSION_BOOST_CONFIG_KEY, default=default)
    except Exception:
        return default
    return _coerce_bool(raw, default=default)


def set_fusion_boost_enabled(enabled: bool | None) -> bool:
    """Persist the active-fusion battle boost setting.

    Passing ``None`` clears the live override and returns the defaulted value.
    """

    config = _server_config()
    if enabled is None:
        config.objects.conf(FUSION_BOOST_CONFIG_KEY, delete=True)
    else:
        config.objects.conf(FUSION_BOOST_CONFIG_KEY, bool(enabled))
    return is_fusion_boost_enabled()


def _db_get(character, attr: str, default: Any = None) -> Any:
    db = _db(character)
    if db is None:
        return default
    getter = getattr(db, "get", None)
    if callable(getter):
        try:
            return getter(attr, default)
        except TypeError:
            pass
    return getattr(db, attr, default)


def _db_set(character, attr: str, value: Any) -> None:
    db = _db(character)
    if db is not None:
        setattr(db, attr, value)


def _db_clear(character, attr: str) -> None:
    db = _db(character)
    if db is None:
        return
    try:
        delattr(db, attr)
    except Exception:
        try:
            setattr(db, attr, None)
        except Exception:
            pass


def _display_name(pokemon: Any) -> str:
    return str(getattr(pokemon, "name", None) or getattr(pokemon, "nickname", None) or getattr(pokemon, "species", "Pokemon"))


def _pokemon_id(pokemon: Any) -> str | None:
    value = getattr(pokemon, "unique_id", None) or getattr(pokemon, "id", None) or getattr(pokemon, "model_id", None)
    return str(value) if value is not None else None


def _pokemon_species(pokemon: Any) -> str:
    species = getattr(pokemon, "species", None) or getattr(pokemon, "name", "Pokemon")
    return str(getattr(species, "name", species))


def _pokemon_xp(pokemon: Any) -> int:
    for attr in ("total_exp", "xp", "experience"):
        value = getattr(pokemon, attr, None)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0
    return 0


def _growth_from_pokemon(pokemon: Any) -> str:
    growth = getattr(pokemon, "growth_rate", None)
    if growth:
        return str(growth)
    name = getattr(pokemon, "species", getattr(pokemon, "name", None))
    if name:
        species = POKEDEX.get(name) or POKEDEX.get(str(name).lower()) or POKEDEX.get(str(name).capitalize())
        if species:
            return species.raw.get("growthRate", "medium_fast")
    return "medium_fast"


def _level_for_exp(exp: int, growth_rate: str = "medium_fast") -> int:
    try:
        from pokemon.models.stats import level_for_exp

        return level_for_exp(int(exp), growth_rate)
    except Exception:
        return max(1, min(100, int(round((int(exp or 0)) ** (1 / 3))) if exp else 1))


def _trainer_xp(character) -> int | None:
    for attr in ("trainer_xp", "txp", "total_exp", "xp", "experience"):
        value = _db_get(character, attr, None)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0
    return None


def _fighter_xp(character, fallback: int = 0) -> int:
    for attr in ("fighter_xp", "fxp", "total_exp", "xp", "experience"):
        value = _db_get(character, attr, None)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0
    return fallback


def _set_fighter_xp(character, amount: int) -> None:
    _db_set(character, "total_exp", max(0, int(amount)))


def _set_character_fusion_view(character, pokemon: Any, *, kind: str) -> None:
    _db_set(character, "fusion_id", _pokemon_id(pokemon))
    _db_set(character, "fusion_species", _pokemon_species(pokemon))
    _db_set(character, "fusion_ability", getattr(pokemon, "ability", None))
    _db_set(character, "fusion_nature", getattr(pokemon, "nature", None))
    _db_set(character, "fusion_kind", kind)
    _db_set(character, "morphology", "Fusion")


def _clear_character_fusion_view(character) -> None:
    for attr in ACTIVE_FUSION_ATTRS:
        _db_clear(character, attr)
    _db_set(character, "morphology", "Human")


def _is_in_party(storage: Any, pokemon: Any) -> bool:
    if storage is None or pokemon is None:
        return False
    checker = getattr(pokemon, "in_party", None)
    if isinstance(checker, bool):
        return checker
    placements = getattr(storage, "placements", None)
    if placements is not None:
        try:
            from pokemon.models.storage import PokemonPlacement

            return placements.filter(
                pokemon=pokemon,
                location_type=PokemonPlacement.LocationType.PARTY,
            ).exists()
        except Exception:
            pass
    try:
        return pokemon in list(storage.get_party())
    except Exception:
        return False


def _party_slot(storage: Any, pokemon: Any) -> int | None:
    slot = getattr(pokemon, "party_slot", None)
    if slot:
        try:
            return int(slot)
        except (TypeError, ValueError):
            return None
    active_slots = getattr(storage, "active_slots", None)
    if active_slots is not None:
        try:
            rel = active_slots.filter(pokemon=pokemon).first()
            return int(rel.slot) if rel else None
        except Exception:
            pass
    return None


def _remove_from_party(character, pokemon: Any) -> None:
    storage = getattr(character, "storage", None)
    remover = getattr(storage, "remove_active_pokemon", None)
    if callable(remover):
        remover(pokemon)


def _return_to_party_or_box(character, pokemon: Any, preferred_slot: int | None = None) -> str:
    storage = getattr(character, "storage", None)
    if storage is None:
        return f"{_display_name(pokemon)} is no longer fused."

    if callable(getattr(storage, "add_active_pokemon", None)):
        try:
            if preferred_slot:
                storage.add_active_pokemon(pokemon, preferred_slot)
            else:
                storage.add_active_pokemon(pokemon)
            slot = _party_slot(storage, pokemon) or preferred_slot
            suffix = f" slot {slot}" if slot else " your party"
            return f"{_display_name(pokemon)} returned to{suffix}."
        except Exception:
            pass

    try:
        from pokemon.models.storage import move_to_box

        boxes = getattr(storage, "boxes", None)
        box = boxes.all().order_by("id").first() if boxes is not None else None
        box = move_to_box(pokemon, storage, box)
        return f"{_display_name(pokemon)} was sent to {box.name}."
    except Exception:
        return f"{_display_name(pokemon)} is no longer fused."


def resolve_owned_pokemon(character, pokemon_id: str | None) -> Any | None:
    """Return a trainer-owned Pokemon matching ``pokemon_id``."""

    if not pokemon_id:
        return None

    finder = getattr(character, "get_pokemon_by_id", None)
    if callable(finder):
        try:
            found = finder(str(pokemon_id))
            if found:
                return found
        except Exception:
            pass

    try:
        from pokemon.models.core import OwnedPokemon

        trainer = getattr(character, "trainer", None)
        return OwnedPokemon.objects.filter(unique_id=pokemon_id, trainer=trainer).first()
    except Exception:
        return None


def record_fusion(result: Any, trainer: Any, pokemon: Any, permanent: bool = False) -> None:
    """Ensure ``result`` is present in ``trainer``'s active party.

    This is kept for compatibility with older chargen/admin paths. Permanent
    fusions also copy the source Pokemon growth rate onto the result when that
    field exists on the object.
    """

    if permanent:
        try:
            setattr(result, "growth_rate", _growth_from_pokemon(pokemon))
        except Exception:
            pass

    storage = getattr(getattr(trainer, "user", None), "storage", None)
    if storage and not getattr(result, "in_party", False):
        storage.add_active_pokemon(result)


def get_fusion_parents(result: Any) -> Tuple[Any, Any]:
    """Return ``(None, None)`` as fusion records are no longer stored."""

    return None, None


def fusion_form_ids(character) -> list[str]:
    """Return permanent fusion form ids stored on ``character``."""

    raw = _db_get(character, "fusion_forms", None) or []
    if isinstance(raw, dict):
        raw = list(raw.values())
    if isinstance(raw, (str, bytes)):
        raw = [raw]
    ids = [str(value) for value in raw if value]

    active = _db_get(character, "fusion_id", None)
    if active and get_fusion_kind(character) == PERMANENT and str(active) not in ids:
        ids.append(str(active))
    return ids


def remember_permanent_form(character, pokemon: Any) -> None:
    """Record ``pokemon`` as an unlocked permanent fusion form."""

    pid = _pokemon_id(pokemon)
    if not pid:
        return
    ids = fusion_form_ids(character)
    if pid not in ids:
        ids.append(pid)
    _db_set(character, "fusion_forms", ids)


def get_fusion_kind(character) -> str | None:
    kind = _db_get(character, "fusion_kind", None)
    if kind in {TEMPORARY, PERMANENT}:
        return kind
    active = _db_get(character, "fusion_id", None)
    if active:
        return PERMANENT
    return None


def get_active_fusion_pokemon(character) -> Any | None:
    """Return the active fusion Pokemon, annotated for battle if present."""

    pokemon = resolve_owned_pokemon(character, _db_get(character, "fusion_id", None))
    if not pokemon:
        return None

    kind = get_fusion_kind(character) or PERMANENT
    pokemon_xp = _pokemon_xp(pokemon)
    growth = _growth_from_pokemon(pokemon)
    if kind == TEMPORARY:
        txp = _trainer_xp(character)
        effective_xp = min(txp, pokemon_xp) if txp is not None else pokemon_xp
    else:
        effective_xp = _fighter_xp(character, fallback=pokemon_xp)

    setattr(pokemon, "_pf2_active_fusion", True)
    setattr(pokemon, "_pf2_fusion_kind", kind)
    setattr(pokemon, "_pf2_fusion_xp", effective_xp)
    setattr(pokemon, "_pf2_fusion_level", _level_for_exp(effective_xp, growth))
    return pokemon


def get_battle_party_with_fusion(character, base_party: Iterable | None = None) -> list:
    """Return the battle party including the active fusion form when enabled."""

    storage = getattr(character, "storage", None)
    if base_party is None:
        try:
            party = list(storage.get_party()) if storage is not None else []
        except Exception:
            party = []
    else:
        party = list(base_party)

    active = get_active_fusion_pokemon(character)
    if not active or _db_get(character, "fusion_participates", True) is False:
        return party

    active_id = _pokemon_id(active)
    party = [mon for mon in party if _pokemon_id(mon) != active_id]
    if _db_get(character, "fusion_battle_order", "normal") == "first":
        return [active] + party
    return party + [active]


def deactivate_fusion(character) -> tuple[bool, str]:
    """Turn off the current fusion and return ``(success, message)``."""

    active_id = _db_get(character, "fusion_id", None)
    if not active_id:
        return True, "You are not currently fused."

    pokemon = resolve_owned_pokemon(character, active_id)
    kind = get_fusion_kind(character) or PERMANENT
    message = "You returned to human form."

    if pokemon and kind == TEMPORARY:
        preferred = _db_get(character, "fusion_temp_slot", None)
        try:
            preferred = int(preferred) if preferred else None
        except (TypeError, ValueError):
            preferred = None
        message = _return_to_party_or_box(character, pokemon, preferred)
    elif pokemon:
        remember_permanent_form(character, pokemon)
        if _is_in_party(getattr(character, "storage", None), pokemon):
            _remove_from_party(character, pokemon)

    _clear_character_fusion_view(character)
    return True, message


def activate_temporary_fusion(character, pokemon: Any, *, slot: int | None = None) -> tuple[bool, str]:
    """Activate a temporary fusion with ``pokemon``."""

    ok, message = deactivate_fusion(character)
    if not ok:
        return ok, message

    original_slot = slot or _party_slot(getattr(character, "storage", None), pokemon)
    _remove_from_party(character, pokemon)
    _set_character_fusion_view(character, pokemon, kind=TEMPORARY)
    if original_slot:
        _db_set(character, "fusion_temp_slot", int(original_slot))
    return True, f"You temporarily fused with {_display_name(pokemon)}."


def activate_permanent_fusion(character, pokemon: Any) -> tuple[bool, str]:
    """Unlock and activate a permanent fusion form with ``pokemon``."""

    ok, message = deactivate_fusion(character)
    if not ok:
        return ok, message

    remember_permanent_form(character, pokemon)
    _remove_from_party(character, pokemon)
    gained = _pokemon_xp(pokemon) // 3
    _set_fighter_xp(character, _fighter_xp(character) + gained)
    _set_character_fusion_view(character, pokemon, kind=PERMANENT)
    return True, f"You permanently fused with {_display_name(pokemon)}."


def activate_permanent_form(character, pokemon: Any) -> tuple[bool, str]:
    """Switch to an already unlocked permanent fusion form."""

    remember_permanent_form(character, pokemon)
    ok, message = deactivate_fusion(character)
    if not ok:
        return ok, message
    _remove_from_party(character, pokemon)
    _set_character_fusion_view(character, pokemon, kind=PERMANENT)
    return True, f"You took your {_pokemon_species(pokemon)} fusion form."
