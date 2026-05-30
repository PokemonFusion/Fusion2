"""Persistence helpers for ephemeral battle encounters."""

from __future__ import annotations

from pokemon.services.pokemon_refs import build_encounter_ref


def create_encounter_pokemon(
	*,
	species: str,
	level: int,
	source_kind: str,
	gender: str = "",
	ability: str = "",
	nature: str = "",
	ivs: list[int] | None = None,
	evs: list[int] | None = None,
	held_item: str = "",
	current_hp: int = 0,
	status: str = "",
	move_names: list[str] | None = None,
	move_pp: list[int] | None = None,
	npc_trainer=None,
	template_key: str = "",
):
	from pokemon.models.core import EncounterPokemon

	encounter = EncounterPokemon.objects.create(
		species=species,
		level=level,
		source_kind=source_kind,
		gender=gender,
		ability=ability,
		nature=nature,
		ivs=list(ivs or [0, 0, 0, 0, 0, 0]),
		evs=list(evs or [0, 0, 0, 0, 0, 0]),
		held_item=held_item,
		current_hp=current_hp,
		status=status,
		move_names=list(move_names or []),
		move_pp=list(move_pp or []),
		npc_trainer=npc_trainer,
		template_key=template_key,
	)
	return encounter


def get_encounter_from_ref(model_id):
	from pokemon.models.core import EncounterPokemon
	from pokemon.services.pokemon_refs import parse_pokemon_ref

	kind, identifier = parse_pokemon_ref(model_id)
	if kind != "encounter" or not identifier:
		return None
	return EncounterPokemon.objects.filter(encounter_id=identifier).first()


def delete_encounter_by_ref(model_id) -> bool:
	encounter = get_encounter_from_ref(model_id)
	if encounter is None:
		return False
	encounter.delete()
	return True


def encounter_ref(encounter) -> str | None:
	return build_encounter_ref(getattr(encounter, "encounter_id", None))
