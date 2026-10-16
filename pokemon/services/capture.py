"""Capture persistence services for wild battles."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from pokemon.names import normalize_name
from pokemon.services.battle_items import ItemUnavailable
from pokemon.services.pokemon_refs import build_owned_ref, parse_pokemon_ref
from pokemon.services.status_persistence import PersistentStatus


def _current_held_item(target_poke, encounter) -> str:
	"""Prefer live battle state; explicit empty values mean the item is gone."""
	missing = object()
	item = getattr(target_poke, "item", missing)
	if item is missing:
		item = getattr(target_poke, "held_item", missing)
	if item is missing:
		item = encounter.held_item
	return str(getattr(item, "name", item) or "")


def _preserve_captured_pp(owned, target_poke, encounter) -> None:
	"""Copy remaining PP by move identity, preferring current battle values."""
	remaining = {
		normalize_name(name): pp
		for name, pp in zip(encounter.move_names, encounter.move_pp)
		if pp is not None
	}
	for move in getattr(target_poke, "moves", []) or []:
		pp = getattr(move, "pp", None)
		if pp is not None:
			remaining[normalize_name(move.name)] = pp
	for slot in owned.activemoveslot_set.select_related("move").order_by("slot"):
		key = normalize_name(slot.move.name)
		if key not in remaining:
			continue
		pp = max(0, int(remaining[key]))
		if slot.current_pp is not None:
			pp = min(pp, slot.current_pp)
		slot.current_pp = pp
		slot.save(update_fields=["current_pp"])


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


@dataclass(frozen=True)
class CaptureAttemptResult:
	"""A new throw's outcome, or the original placement on a successful replay."""

	outcome: object | None = None
	placement: CapturePlacementResult | None = None


class WildCaptureAttempt:
	"""Serialize a throw's ball debit with the durable successful capture claim."""

	def __init__(self, *, target_poke, player, trainer, battle_context=None, ball_name=""):
		"""Bind one encounter snapshot and its character-scoped item owner."""
		self.target_poke = target_poke
		self.player = player
		self.trainer = trainer
		self.battle_context = battle_context
		self.ball_name = ball_name

	def _existing_capture(self, storage):
		"""Reject missing/foreign encounters before rolling or spending a ball."""
		from pokemon.models.core import EncounterPokemon
		from pokemon.models.storage import CaptureReceipt
		from pokemon.services.placement import PlacementError

		if self.trainer is None or self.trainer.user_id != storage.user_id:
			raise PlacementError("Capturing trainer does not own this storage.")
		kind, identifier = parse_pokemon_ref(getattr(self.target_poke, "model_id", None))
		if kind != "encounter" or not identifier:
			raise PlacementError("Capture requires a persisted wild encounter reference.")
		try:
			encounter_id = UUID(identifier)
		except (TypeError, ValueError) as error:
			raise PlacementError("Invalid encounter reference.") from error

		def receipt_result():
			"""Check again after waiting for another owner's encounter lock."""
			receipt = CaptureReceipt.objects.filter(encounter_id=encounter_id).first()
			if receipt is None:
				return None
			if receipt.storage_id != storage.pk:
				raise PlacementError("Encounter has already been captured by another trainer.")
			return _receipt_result(receipt, retry=True)

		result = receipt_result()
		if result is not None:
			return result
		encounter = EncounterPokemon.objects.select_for_update().filter(pk=encounter_id).first()
		if encounter is None:
			result = receipt_result()
			if result is None:
				raise PlacementError("Wild encounter no longer exists.")
			return result
		if encounter.source_kind != EncounterPokemon.SourceKind.WILD:
			raise PlacementError("Only wild encounters can be captured.")
		return None

	def resolve(self, *, roll, consume_ball) -> CaptureAttemptResult:
		"""Check receipts before debit; commit debit and placement together."""
		from pokemon.services.placement import PlacementService

		storage = getattr(self.player, "storage", None)
		# Pure battle simulations have no persistent storage or database rows.
		lock = PlacementService(storage).locked() if getattr(storage, "pk", None) is not None else nullcontext()
		try:
			with lock as locked_storage:
				if locked_storage is not None:
					existing = self._existing_capture(locked_storage)
					if existing is not None:
						transaction.on_commit(lambda: _update_temp_tracking(
							player=self.player, battle_context=self.battle_context,
							model_id=getattr(self.target_poke, "model_id", None),
						))
						return CaptureAttemptResult(placement=existing)
				if not consume_ball():
					raise ItemUnavailable
				outcome = roll()
				placement = None
				if getattr(outcome, "caught", bool(outcome)):
					placement = finalize_wild_capture(
						target_poke=self.target_poke, player=self.player, trainer=self.trainer,
						battle_context=self.battle_context, ball_name=self.ball_name,
					)
				return CaptureAttemptResult(outcome, placement)
		except ItemUnavailable:
			return CaptureAttemptResult()


def finalize_wild_capture(
	*, target_poke, player=None, trainer=None, battle_context=None, ball_name: str = "",
) -> CapturePlacementResult:
	"""Claim a persisted wild encounter exactly once and atomically place it.

	An encounter UUID is mandatory. A missing/deleted encounter without a receipt
	is rejected, never reconstructed from an untrusted or stale battle object.
	Receipts survive release so a late request cannot resurrect a captured Pokemon.
	"""
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
				_preserve_captured_pp(dbpoke, target_poke, encounter)
				dbpoke.current_hp = max(0, int(getattr(target_poke, "hp", encounter.current_hp) or 0))
				PersistentStatus.from_pokemon(target_poke, battle=True).apply_to_model(dbpoke)
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
				# Prompt intent commits with the catch, including retries after a
				# disconnect before the battle's UI has finished cleaning up.
				from pokemon.services.capture_nicknames import CaptureNicknames

				CaptureNicknames(player).queue(dbpoke, species=encounter.species)
				encounter.delete()
				result = _receipt_result(receipt)
		# Defer non-transactional battle tracking until the OUTERMOST commit.
		transaction.on_commit(lambda: _update_temp_tracking(
			player=player, battle_context=battle_context, model_id=model_id,
		))
	return result


__all__ = ["CaptureAttemptResult", "CapturePlacementResult", "WildCaptureAttempt", "finalize_wild_capture"]
