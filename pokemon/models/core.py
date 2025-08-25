"""Core models for Pokémon, including base and owned Pokémon classes."""

import math
import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models
from evennia.utils.idmapper.models import SharedMemoryModel

from .enums import Gender, Nature
from .validators import validate_evs, validate_ivs

# Maximum multiplier to calculate PP when fully boosted (e.g. PP Max or 3 PP Ups)
MAX_PP_MULTIPLIER = 1.6


class SpeciesEntry(models.Model):
	"""Pokédex species entry."""

	name = models.CharField(max_length=50, unique=True)
	dex_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)

	def __str__(self) -> str:
		return self.name


class BasePokemon(models.Model):
	"""Abstract base model for Pokémon."""

	species = models.CharField(max_length=50, default="")
	level = models.PositiveSmallIntegerField(default=1)
	ability = models.CharField(max_length=50, blank=True)
	nature = models.CharField(max_length=20, blank=True, choices=Nature.choices)
	gender = models.CharField(max_length=10, blank=True, choices=Gender.choices)
	ivs = ArrayField(
		models.PositiveSmallIntegerField(),
		size=6,
		default=list,
		validators=[validate_ivs],
	)
	evs = ArrayField(
		models.PositiveSmallIntegerField(),
		size=6,
		default=list,
		validators=[validate_evs],
	)
	held_item = models.CharField(max_length=50, blank=True)

	def clean(self):
		super().clean()
		validate_ivs(self.ivs)
		validate_evs(self.evs)

	class Meta:
		abstract = True

	def _lookup_species_types(self) -> list[str]:
		"""Return a list of types for this Pokémon's species."""

		species_name = self.species
		try:  # pragma: no cover - data source may be unavailable in tests
			from pokemon.dex import POKEDEX  # type: ignore

			entry = (
				POKEDEX.get(species_name) or POKEDEX.get(species_name.lower()) or POKEDEX.get(species_name.capitalize())
			)

			if entry:
				types = getattr(entry, "types", None)
				if types is None and isinstance(entry, dict):
					types = entry.get("types")
				if types:
					return [str(t).title() for t in types if t]
		except Exception:
			pass
		return []

	@property
	def types(self) -> list[str]:
		"""Return this Pokémon's type or types as a list of names."""

		override = getattr(self, "_types_override", None)
		if override is not None:
			return override

		ts = self._lookup_species_types()
		if ts:
			return ts

		data = getattr(self, "data", {}) or {}
		t_from_json = data.get("type") or data.get("types")
		if isinstance(t_from_json, str):
			return [p.strip().title() for p in t_from_json.replace(",", "/").split("/") if p.strip()]
		if isinstance(t_from_json, (list, tuple)):
			return [str(p).title() for p in t_from_json if p]

		return []

	@types.setter
	def types(self, value: list[str]) -> None:
		"""Allow manually overriding the computed types."""

		self._types_override = value

	@property
	def primary_type(self) -> str | None:
		"""Return the first type if available."""

		return self.types[0] if self.types else None

	@property
	def secondary_type(self) -> str | None:
		"""Return the second type if present."""

		return self.types[1] if len(self.types) > 1 else None


class Pokemon(BasePokemon):
	"""Simple Pokémon instance used for starter and storage boxes."""

	type_ = models.CharField(max_length=255)
	data = models.JSONField(default=dict, blank=True)
	temporary = models.BooleanField(default=False, db_index=True)
	trainer = models.ForeignKey(
		"Trainer",
		on_delete=models.CASCADE,
		related_name="owned_pokemon",
		null=True,
		blank=True,
		db_index=True,
	)

	def __str__(self):
		owner = f" owned by {self.trainer.user.key}" if self.trainer else ""
		return f"{self.id}: {self.species} (Level {self.level}, Type: {self.type_}, Ability: {self.ability})" + owner


class OwnedPokemon(SharedMemoryModel, BasePokemon):
	"""Persistent data for a player's Pokémon."""

	unique_id = models.UUIDField(
		primary_key=True,
		default=uuid.uuid4,
		editable=False,
		db_index=True,
	)
	created_at = models.DateTimeField(auto_now_add=True)
	trainer = models.ForeignKey(
		"Trainer",
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		db_index=True,
	)
	is_wild = models.BooleanField(default=False, db_index=True)
	ai_trainer = models.ForeignKey(
		"NPCTrainer",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		db_index=True,
		related_name="wild_or_ai_pokemon",
	)
	is_template = models.BooleanField(default=False, db_index=True)
	is_battle_instance = models.BooleanField(default=False, db_index=True)
	nickname = models.CharField(max_length=50, blank=True)
	is_shiny = models.BooleanField(default=False, db_index=True)
	met_location = models.CharField(max_length=100, blank=True)
	met_level = models.PositiveSmallIntegerField(null=True, blank=True)
	met_date = models.DateTimeField(null=True, blank=True)
	obtained_method = models.CharField(max_length=50, blank=True)
	original_trainer = models.ForeignKey(
		"Trainer",
		on_delete=models.SET_NULL,
		null=True,
		related_name="original_pokemon",
	)
	original_trainer_name = models.CharField(max_length=100, blank=True)
	is_egg = models.BooleanField(default=False)
	hatch_steps = models.PositiveIntegerField(null=True, blank=True)
	friendship = models.PositiveSmallIntegerField(default=70)
	flags = ArrayField(models.CharField(max_length=50), blank=True, default=list)
	tera_type = models.CharField(max_length=20, blank=True)
	current_hp = models.PositiveIntegerField(default=0)
	total_exp = models.BigIntegerField(default=0)
	learned_moves = models.ManyToManyField(
		"Move",
		related_name="owners",
		through="PokemonLearnedMove",
	)
	active_moveset = models.ForeignKey(
		"pokemon.Moveset",
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="active_for",
	)

	def __str__(self):
		return f"{self.nickname or self.species} ({self.unique_id})"

	@property
	def name(self) -> str:
		"""Return nickname if set, otherwise the species."""
		return self.nickname or self.species

	@property
	def computed_level(self) -> int:
		"""Return the Pokémon's level derived from its stored experience."""
		from .stats import level_for_exp  # pragma: no cover

		return level_for_exp(self.total_exp)

	@property
	def active_moves(self):
		"""Return active moves ordered by slot."""
		return [s.move for s in self.activemoveslot_set.order_by("slot")]

	@property
	def party_slot(self) -> int | None:
		"""Return 1-6 if this Pokémon is in the active party."""
		try:
			slot_rel = self.active_slots.first()
			return slot_rel.slot if slot_rel else None
		except Exception:
			return None

	@property
	def in_party(self) -> bool:
		return self.party_slot is not None

	def set_level(self, level: int) -> None:
		"""Set ``total_exp`` and persist the corresponding level."""
		from .stats import exp_for_level  # pragma: no cover

		self.total_exp = exp_for_level(level)
		self.level = level
		try:
			from pokemon.helpers.pokemon_helpers import refresh_stats

			refresh_stats(self)
		except Exception:  # pragma: no cover - optional
			pass

	def heal(self) -> None:
		"""Fully restore HP, clear status, and reset PP."""
		from pokemon.helpers.pokemon_helpers import get_max_hp

		max_hp = get_max_hp(self)
		if hasattr(self, "current_hp"):
			self.current_hp = max_hp
		if hasattr(self, "status"):
			self.status = ""
		try:
			from pokemon.dex import MOVEDEX  # type: ignore
		except Exception:
			try:
				from pokemon.data.moves import py_dict as MOVEDEX  # type: ignore
			except Exception:  # pragma: no cover - optional
				MOVEDEX = {}

		try:
			from pokemon.battle.engine import _normalize_key
		except Exception:  # pragma: no cover - fallback normaliser

			def _normalize_key(val: str) -> str:
				return val.replace(" ", "").replace("-", "").replace("'", "").lower()

		bonuses: dict[str, int] = {}
		manager = getattr(self, "pp_boosts", None)
		if manager is not None:
			try:
				iterable = manager.all()
			except Exception:  # pragma: no cover
				iterable = manager
			for b in iterable:
				name = _normalize_key(getattr(getattr(b, "move", None), "name", ""))
				bonuses[name] = getattr(b, "bonus_pp", 0)

		slots = getattr(self, "activemoveslot_set", None)
		if slots is not None:
			try:
				slot_iter = slots.all()
			except Exception:  # pragma: no cover
				slot_iter = slots
		else:
			slot_iter = []

		updated = []
		for slot in slot_iter:
			move_name = getattr(getattr(slot, "move", None), "name", "")
			norm = _normalize_key(move_name)
			md = MOVEDEX.get(norm)
			base = None
			if md is not None:
				base = getattr(md, "pp", None)
				if base is None and isinstance(md, dict):
					base = md.get("pp")
			bonus = bonuses.get(norm, 0)
			if base is not None:
				slot.current_pp = int(base) + int(bonus)
				updated.append(slot)

		if updated:
			try:
				slots.bulk_update(updated, ["current_pp"])
			except Exception:  # pragma: no cover - fallback for stubs
				for slot in updated:
					try:
						slot.save()
					except Exception:
						pass

		try:
			self.save()
		except Exception:  # pragma: no cover
			pass

	def learn_level_up_moves(self, *, caller=None, prompt: bool = False) -> None:
		"""Teach any moves this Pokémon should know at its level.

		This method is kept for backwards compatibility and simply delegates
		to :mod:`pokemon.services.move_management`.
		"""

		from pokemon.services import move_management

		move_management.learn_level_up_moves(self, caller=caller, prompt=prompt)

	def apply_active_moveset(self) -> None:
		"""Sync the active moveset to the active move slots and heal the Pokémon.

		The heavy lifting is performed in :mod:`pokemon.services.move_management`.
		"""

		from pokemon.services import move_management

		move_management.apply_active_moveset(self)
		self.heal()

	def get_max_hp(self) -> int:
		"""Return max HP for this Pokémon."""
		try:  # pragma: no cover - optional dependency
			from pokemon.helpers.pokemon_helpers import get_max_hp

			return get_max_hp(self)
		except Exception:
			return self.current_hp

	def apply_pp_up(self, move_name: str) -> bool:
		"""Apply a PP Up to the given move and return success."""
		return self._apply_pp_boost(move_name, 1)

	def apply_pp_max(self, move_name: str) -> bool:
		"""Apply a PP Max to the given move and return success."""
		return self._apply_pp_boost(move_name, 3)

	def _apply_pp_boost(self, move_name: str, count: int) -> bool:
		try:
			from pokemon.dex import MOVEDEX  # type: ignore
		except Exception:
			return False

		move = self.learned_moves.filter(name__iexact=move_name).first()
		if not move:
			return False

		slots = self.activemoveslot_set.filter(move=move)
		boost, _ = self.pp_boosts.get_or_create(move=move)
		base_pp = MOVEDEX.get(move.name.lower(), {}).get("pp")
		if base_pp is None:
			return False
		max_bonus = math.floor(base_pp * MAX_PP_MULTIPLIER) - base_pp
		if boost.bonus_pp + count > max_bonus:
			return False
		boost.bonus_pp += count
		boost.save()

		updated = []
		for slot in slots:
			if base_pp is not None:
				slot.current_pp = base_pp + boost.bonus_pp
				updated.append(slot)
		if updated:
			try:
				slots.bulk_update(updated, ["current_pp"])
			except Exception:  # pragma: no cover
				for slot in updated:
					try:
						slot.save()
					except Exception:
						pass
		try:
			self.save()
		except Exception:
			pass
		return True


class BattleSlot(SharedMemoryModel):
	"""Ephemeral per-battle state for a Pokémon."""

	pokemon = models.OneToOneField("OwnedPokemon", on_delete=models.CASCADE, primary_key=True)
	battle_id = models.PositiveIntegerField(db_index=True)
	battle_team = models.PositiveSmallIntegerField(db_index=True)
	current_hp = models.PositiveIntegerField()
	status = models.CharField(max_length=20)
	fainted = models.BooleanField(default=False)

	def __str__(self):  # pragma: no cover - simple repr
		return f"Battle {self.battle_id}: {self.pokemon}"
