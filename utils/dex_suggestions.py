"""Shared fuzzy-name helpers for dex-backed commands."""

from __future__ import annotations

from difflib import get_close_matches
from typing import Iterable


def normalize_dex_key(name: object) -> str:
	"""Normalize user-facing dex names for tolerant comparisons."""

	return str(name or "").replace(" ", "").replace("-", "").replace("'", "").lower()


def _get_value(obj: object, key: str, default=None):
	if isinstance(obj, dict):
		return obj.get(key, default)
	return getattr(obj, key, default)


def _display_names_from_mapping(mapping: object) -> list[str]:
	names: dict[str, str] = {}
	items = getattr(mapping, "items", None)
	if not items:
		return []

	for key, entry in items():
		name = _get_value(entry, "name")
		if name:
			name_text = str(name)
			names[normalize_dex_key(name_text)] = name_text
		if key:
			key_text = str(key)
			names.setdefault(normalize_dex_key(key_text), key_text)
	return sorted(names.values())


def _pokemon_names() -> list[str]:
	try:
		from pokemon.dex import POKEDEX
	except Exception:
		return []
	return _display_names_from_mapping(POKEDEX)


def _move_names() -> list[str]:
	names: dict[str, str] = {}
	try:
		from pokemon.dex import MOVEDEX
	except Exception:
		MOVEDEX = {}
	for name in _display_names_from_mapping(MOVEDEX):
		names.setdefault(normalize_dex_key(name), name)

	try:
		from pokemon.data.text import MOVES_TEXT
	except Exception:
		MOVES_TEXT = {}
	for key, entry in getattr(MOVES_TEXT, "items", lambda: [])():
		display = _get_value(entry, "name", key)
		names.setdefault(normalize_dex_key(display), str(display))
	return sorted(names.values())


def _item_names() -> list[str]:
	names: dict[str, str] = {}
	try:
		from pokemon.dex import ITEMDEX
	except Exception:
		ITEMDEX = {}
	for name in _display_names_from_mapping(ITEMDEX):
		names.setdefault(normalize_dex_key(name), name)

	try:
		from pokemon.data.text import ITEMS_TEXT
	except Exception:
		ITEMS_TEXT = {}
	for key, entry in getattr(ITEMS_TEXT, "items", lambda: [])():
		display = _get_value(entry, "name", key)
		names.setdefault(normalize_dex_key(display), str(display))
	return sorted(names.values())


def _learnset_names() -> list[str]:
	try:
		from pokemon.data.learnsets.learnsets import LEARNSETS
	except Exception:
		return []
	return sorted(str(name) for name in getattr(LEARNSETS, "keys", lambda: [])())


def suggest_name(query: str, candidates: Iterable[object], *, cutoff: float = 0.74) -> str | None:
	"""Return the closest display candidate for ``query``, if one is likely."""

	query_key = normalize_dex_key(query)
	if not query_key:
		return None

	lookup: dict[str, str] = {}
	for candidate in candidates:
		if candidate is None:
			continue
		display = str(candidate)
		key = normalize_dex_key(display)
		if key and key != query_key:
			lookup.setdefault(key, display)
	if not lookup:
		return None

	match = get_close_matches(query_key, lookup.keys(), n=1, cutoff=cutoff)
	if not match:
		return None
	return lookup[match[0]]


def append_suggestion(message: str, query: str, suggestion: str | None) -> str:
	if suggestion:
		return f"{message} Did you mean {suggestion}?"
	return message


def suggest_pokemon_name(query: str) -> str | None:
	return suggest_name(query, _pokemon_names())


def suggest_move_name(query: str) -> str | None:
	return suggest_name(query, _move_names())


def suggest_item_name(query: str) -> str | None:
	return suggest_name(query, _item_names())


def suggest_learnset_name(query: str) -> str | None:
	return suggest_name(query, _learnset_names())


def is_known_species(name: str) -> bool:
	key = normalize_dex_key(name)
	return bool(key and any(normalize_dex_key(candidate) == key for candidate in _pokemon_names()))


def is_species_not_found_error(err: Exception) -> bool:
	text = str(err)
	return "not found in Pokedex" in text or "Unknown species" in text


def species_not_found_message(species: str) -> str:
	message = f"Species '{species}' was not found in the Pokedex."
	return append_suggestion(message, species, suggest_pokemon_name(species))


def pokemon_not_found_message(query: str, base_message: str) -> str:
	return append_suggestion(base_message, query, suggest_pokemon_name(query))


def move_not_found_message(query: str, base_message: str) -> str:
	return append_suggestion(base_message, query, suggest_move_name(query))


def item_not_found_message(query: str, base_message: str) -> str:
	return append_suggestion(base_message, query, suggest_item_name(query))


def learnset_not_found_message(query: str, base_message: str) -> str:
	return append_suggestion(base_message, query, suggest_learnset_name(query))
