"""Helpers for typed battle Pokemon references."""

from __future__ import annotations

from typing import Tuple


OWNED_PREFIX = "owned"
ENCOUNTER_PREFIX = "encounter"


def build_owned_ref(identifier) -> str | None:
	if identifier in (None, ""):
		return None
	return f"{OWNED_PREFIX}:{identifier}"


def build_encounter_ref(identifier) -> str | None:
	if identifier in (None, ""):
		return None
	return f"{ENCOUNTER_PREFIX}:{identifier}"


def parse_pokemon_ref(value) -> Tuple[str | None, str | None]:
	if value in (None, ""):
		return None, None
	text = str(value).strip()
	if not text:
		return None, None
	if ":" not in text:
		return OWNED_PREFIX, text
	kind, identifier = text.split(":", 1)
	kind = kind.strip().lower() or None
	identifier = identifier.strip() or None
	return kind, identifier


def is_owned_ref(value) -> bool:
	kind, _ = parse_pokemon_ref(value)
	return kind == OWNED_PREFIX


def is_encounter_ref(value) -> bool:
	kind, _ = parse_pokemon_ref(value)
	return kind == ENCOUNTER_PREFIX
