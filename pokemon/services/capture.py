"""Capture persistence services for wild battles."""

from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from pokemon.services.pokemon_refs import build_owned_ref, parse_pokemon_ref


def _current_held_item(target_poke, encounter) -> str:
	"""Prefer live battle state; explicit empty values mean the item is gone."""
	missing = object()
	item = getattr(target_poke, "item", missing)
	if item is missing:
		item = getattr(target_poke, "held_item", missing)
	if item is missing:
		item = encounter.held_item
	return str(getattr(item, "name", item) or "")


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


@dataclass(frozen=True)
class CapturePlacementResult:
	"""Details about the permanent placement for a caught Pokémon."""

	owned_pokemon_id: str
	placement: str
	party_slot: int | None
	box_name: str | None
	should_prompt_nickname: bool


def _receipt_result(receipt, *, retry=False):
	"""Return the original committed result without repeating nickname prompts."""
	return CapturePlacementResult(
		owned_pokemon_id=build_owned_ref(receipt.owned_id),
		placement=receipt.location,
		party_slot=receipt.party_slot,
		box_name=receipt.box_name,
		should_prompt_nickname=not retry,
	)


def finalize_wild_capture(
	*, target_poke, player=None, trainer=None, battle_context=None, ball_name: str = "",
) -> CapturePlacementResult:
	"""Claim a persisted wild encounter exactly once and atomically place it.

	An encounter UUID is mandatory. A missing/deleted encounter without a receipt
	is rejected, never reconstructed from an untrusted or stale battle object.
	Receipts survive release so a late request cannot resurrect a captured Pokemon.
	"""
	from uuid import UUID

	from django.db import transaction

	from pokemon.helpers.pokemon_helpers import create_owned_pokemon
	from pokemon.models.core import EncounterPokemon
	from pokemon.models.storage import CaptureReceipt
	from pokemon.services.placement import PlacementError, PlacementService

	storage = getattr(player, "storage", None)
	if storage is None:
		raise PlacementError("Capturing player has no storage.")
	model_id = getattr(target_poke, "model_id", None)
	kind, identifier = parse_pokemon_ref(model_id)
	if kind != "encounter" or not identifier:
		raise PlacementError("Capture requires a persisted wild encounter reference.")
	try:
		encounter_id = UUID(str(identifier))
	except (TypeError, ValueError) as error:
		raise PlacementError("Invalid encounter reference.") from error

	with PlacementService(storage).locked() as storage:
		if trainer is None or trainer.user_id != storage.user_id:
			raise PlacementError("Capturing trainer does not own this storage.")

		def existing_result():
			"""Look up the durable claim, including claims made by another owner."""
			receipt = CaptureReceipt.objects.filter(encounter_id=encounter_id).first()
			if receipt is None:
				return None
			if receipt.storage_id != storage.pk:
				raise PlacementError("Encounter has already been captured by another trainer.")
			return _receipt_result(receipt, retry=True)

		result = existing_result()
		if result is None:
			# A competing owner's capture may delete the encounter while we wait.
			encounter = EncounterPokemon.objects.select_for_update().filter(pk=encounter_id).first()
			if encounter is None:
				result = existing_result()
				if result is None:
					raise PlacementError("Wild encounter no longer exists.")
			else:
				if encounter.source_kind != EncounterPokemon.SourceKind.WILD:
					raise PlacementError("Only wild encounters can be captured.")
				dbpoke = create_owned_pokemon(
					encounter.species, trainer, encounter.level,
					gender=encounter.gender, nature=encounter.nature, ability=encounter.ability,
					ivs=list(encounter.ivs), evs=list(encounter.evs), held_item=_current_held_item(target_poke, encounter),
					active_move_names=list(encounter.move_names),
				)
				dbpoke.current_hp = max(0, int(getattr(target_poke, "hp", encounter.current_hp) or 0))
				dbpoke.met_level = encounter.level
				dbpoke.met_location = _battle_location_name(player=player, battle_context=battle_context)
				dbpoke.met_date = timezone.now()
				dbpoke.obtained_method = "caught"
				dbpoke.original_trainer = trainer
				dbpoke.original_trainer_name = trainer.user.key
				if ball_name and hasattr(dbpoke, "pokeball"):
					dbpoke.pokeball = ball_name
				dbpoke.save()
				placement = dbpoke.placement
				receipt = CaptureReceipt.objects.create(
					encounter_id=encounter_id, storage=storage, pokemon=dbpoke, owned_id=dbpoke.pk,
					location="party" if placement.location_type == "party" else "storage",
					party_slot=placement.slot,
					box_name=placement.box.name if placement.box_id else None,
				)
				encounter.delete()
				result = _receipt_result(receipt)
		# Defer non-transactional battle tracking until the OUTERMOST commit.
		transaction.on_commit(lambda: _update_temp_tracking(
			player=player, battle_context=battle_context, model_id=model_id,
		))
	return result


__all__ = ["CapturePlacementResult", "finalize_wild_capture"]
