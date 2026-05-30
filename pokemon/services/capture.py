"""Capture persistence services for wild battles."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone
from pokemon.services.encounters import get_encounter_from_ref
from pokemon.services.pokemon_refs import build_owned_ref, parse_pokemon_ref


def _atomic_context():
	try:
		from django.db import transaction
	except Exception:  # pragma: no cover - lightweight test environments
		return nullcontext()
	return transaction.atomic()


def _load_encounter(model_id):
	kind, identifier = parse_pokemon_ref(model_id)
	if kind != "encounter" or not identifier:
		return None
	return get_encounter_from_ref(model_id)


def _lock_storage(storage):
	if storage is None:
		return None
	manager = getattr(storage.__class__, "objects", None)
	select_for_update = getattr(manager, "select_for_update", None)
	if callable(select_for_update) and getattr(storage, "pk", None) is not None:
		return select_for_update().get(pk=storage.pk)
	return storage


def _lock_active_slots(storage) -> None:
	if storage is None:
		return
	slots = getattr(storage, "active_slots", None)
	select_for_update = getattr(slots, "select_for_update", None)
	if callable(select_for_update):
		try:
			list(select_for_update())
		except Exception:
			pass


def _battle_location_name(player=None, battle_context=None) -> str:
	for source in (getattr(player, "location", None), getattr(battle_context, "room", None), battle_context):
		if source is None:
			continue
		for attr in ("key", "name"):
			value = getattr(source, attr, None)
			if value:
				return str(value)
	return ""


def _update_temp_tracking(player=None, battle_context=None, model_id=None) -> None:
	if model_id is None:
		return
	session = getattr(getattr(player, "ndb", None), "battle_instance", None)
	if session is None and battle_context is not None and hasattr(battle_context, "temp_pokemon_ids"):
		session = battle_context
	if session is None:
		return

	model_key = str(model_id)
	temp_ids = list(getattr(session, "temp_pokemon_ids", []) or [])
	filtered = [pid for pid in temp_ids if str(pid) != model_key]
	if len(filtered) != len(temp_ids):
		session.temp_pokemon_ids = filtered
		storage = getattr(session, "storage", None)
		if storage and hasattr(storage, "set"):
			try:
				storage.set("temp_pokemon_ids", list(filtered))
			except Exception:
				pass


def _timestamp_now():
	try:
		return timezone.now()
	except Exception:  # pragma: no cover - lightweight tests without Django settings
		return datetime.utcnow()


@dataclass(frozen=True)
class CapturePlacementResult:
	"""Details about the permanent placement for a caught Pokémon."""

	owned_pokemon_id: str
	placement: str
	party_slot: int | None
	box_name: str | None
	should_prompt_nickname: bool


def finalize_wild_capture(
	*,
	target_poke,
	player=None,
	trainer=None,
	battle_context=None,
	ball_name: str = "",
) -> CapturePlacementResult:
	"""Persist a successful wild capture and place it safely."""

	storage = getattr(player, "storage", None)
	if storage is None:
		raise ValueError("Capturing player has no storage.")

	with _atomic_context():
		from pokemon.helpers.pokemon_helpers import create_owned_pokemon
		from pokemon.models.storage import (
			assign_to_first_storage_box,
			move_to_box,
			move_to_party,
		)

		storage = _lock_storage(storage)
		_lock_active_slots(storage)

		model_id = getattr(target_poke, "model_id", None)
		encounter = _load_encounter(model_id) if model_id is not None else None
		source = encounter or target_poke
		held_item = getattr(source, "item", None) or getattr(source, "held_item", None)
		held_name = getattr(held_item, "name", held_item)
		move_names = list(getattr(source, "move_names", None) or [])
		if not move_names:
			move_names = [getattr(move, "name", move) for move in getattr(source, "moves", []) or []]
		dbpoke = create_owned_pokemon(
			getattr(source, "species", None) or getattr(source, "name", ""),
			trainer,
			getattr(source, "level", 1),
			gender=getattr(source, "gender", ""),
			nature=getattr(source, "nature", ""),
			ability=getattr(source, "ability", ""),
			ivs=list(getattr(source, "ivs", []) or []),
			evs=list(getattr(source, "evs", []) or []),
			held_item=str(held_name or ""),
			active_move_names=move_names,
		)

		dbpoke.trainer = trainer
		dbpoke.current_hp = max(0, int(getattr(target_poke, "hp", getattr(dbpoke, "current_hp", 0)) or 0))
		dbpoke.met_level = getattr(target_poke, "level", getattr(dbpoke, "level", None))
		dbpoke.met_location = _battle_location_name(player=player, battle_context=battle_context)
		dbpoke.met_date = _timestamp_now()
		dbpoke.obtained_method = "caught"
		if trainer is not None:
			dbpoke.original_trainer = trainer
			user = getattr(trainer, "user", None)
			if user is not None:
				dbpoke.original_trainer_name = getattr(user, "key", "") or getattr(user, "name", "")

		held_item = getattr(target_poke, "item", None) or getattr(target_poke, "held_item", None)
		held_name = getattr(held_item, "name", held_item)
		if held_name is not None:
			dbpoke.held_item = str(held_name)

		if ball_name and hasattr(dbpoke, "pokeball"):
			setattr(dbpoke, "pokeball", ball_name)

		if hasattr(dbpoke, "save"):
			dbpoke.save()

		party = storage.get_party() if hasattr(storage, "get_party") else []
		party_count = len(list(party or []))
		if party_count < 6:
			move_to_party(dbpoke, storage)
			result = CapturePlacementResult(
				owned_pokemon_id=str(build_owned_ref(getattr(dbpoke, "unique_id", getattr(dbpoke, "id", ""))) or ""),
				placement="party",
				party_slot=getattr(dbpoke, "party_slot", None),
				box_name=None,
				should_prompt_nickname=True,
			)
		else:
			box = assign_to_first_storage_box(storage, dbpoke)
			box = move_to_box(dbpoke, storage, box)
			result = CapturePlacementResult(
				owned_pokemon_id=str(build_owned_ref(getattr(dbpoke, "unique_id", getattr(dbpoke, "id", ""))) or ""),
				placement="storage",
				party_slot=None,
				box_name=getattr(box, "name", None),
				should_prompt_nickname=True,
			)
		if encounter is not None and hasattr(encounter, "delete"):
			encounter.delete()

	_update_temp_tracking(player=player, battle_context=battle_context, model_id=model_id)
	return result


__all__ = ["CapturePlacementResult", "finalize_wild_capture"]
