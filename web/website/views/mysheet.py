from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from pokemon.models.core import OwnedPokemon
from pokemon.models.storage import UserStorage
from pokemon.models.trainer import Trainer


def _as_list(value) -> list:
	"""Return ``value`` as a list while tolerating unavailable managers."""

	if value is None:
		return []
	try:
		if hasattr(value, "all"):
			value = value.all()
		return list(value)
	except Exception:
		return []


def _character_id(character):
	"""Return the underlying Evennia object id for a character-like object."""

	for candidate in (character, getattr(character, "dbobj", None), getattr(character, "obj", None)):
		identifier = getattr(candidate, "id", None)
		if identifier is not None:
			return identifier
	return None


def _trainer_for_character(character):
	"""Fetch an existing trainer record without invoking typeclass creators."""

	char_id = _character_id(character)
	if char_id is None:
		return None
	try:
		return Trainer.objects.filter(user_id=char_id).first()
	except Exception:
		return None


def _storage_for_character(character):
	"""Fetch existing storage for a character, if present."""

	char_id = _character_id(character)
	if char_id is None:
		return None
	try:
		return UserStorage.objects.filter(user_id=char_id).first()
	except Exception:
		return None


def _ordered_unique(pokemon):
	"""Return Pokemon records in order, dropping duplicate identities."""

	seen = set()
	unique = []
	for mon in pokemon:
		key = getattr(mon, "unique_id", None) or getattr(mon, "pk", None) or id(mon)
		if key in seen:
			continue
		seen.add(key)
		unique.append(mon)
	return unique


def _owned_pokemon_for_trainer(trainer):
	"""Return all Pokemon for ``trainer`` with party slots available."""

	if not trainer:
		return []
	try:
		queryset = OwnedPokemon.objects.filter(trainer=trainer).prefetch_related("active_slots")
		if hasattr(queryset, "order_by"):
			queryset = queryset.order_by("species", "nickname")
		return list(queryset)
	except Exception:
		return []


def _storage_party(storage):
	"""Return party Pokemon from storage without mutating it."""

	if not storage:
		return []
	try:
		return _as_list(storage.get_party())
	except Exception:
		return []


def _storage_boxed(storage):
	"""Return boxed Pokemon from storage without mutating it."""

	if not storage:
		return []
	try:
		return _as_list(storage.get_stored_pokemon())
	except Exception:
		return []


def _trainer_inventory(trainer):
	"""Return inventory entries ordered for display."""

	if not trainer:
		return []
	try:
		return list(trainer.list_inventory())
	except Exception:
		return []


def _trainer_badges(trainer):
	"""Return badge records ordered for display."""

	if not trainer:
		return []
	try:
		badges = trainer.badges.all()
		if hasattr(badges, "order_by"):
			badges = badges.order_by("region", "name")
		return list(badges)
	except Exception:
		return []


def _seen_count(trainer) -> int:
	"""Return the number of seen species for ``trainer``."""

	if not trainer:
		return 0
	try:
		return trainer.seen_pokemon.count()
	except Exception:
		return 0


def _character_entries(account, characters=None) -> list[dict]:
	"""Build read-only Player Hub entries for an account."""

	if characters is None:
		try:
			characters = account.characters
		except Exception:
			characters = []

	entries = []
	for character in _as_list(characters):
		trainer = _trainer_for_character(character)
		storage = _storage_for_character(character)
		all_pokemon = _owned_pokemon_for_trainer(trainer)
		party = _ordered_unique(_storage_party(storage) or [mon for mon in all_pokemon if getattr(mon, "in_party", False)])
		storage_boxed = _storage_boxed(storage)
		boxed = _ordered_unique(
			[
				*storage_boxed,
				*[mon for mon in all_pokemon if mon not in party and mon not in storage_boxed],
			]
		)
		if not all_pokemon:
			all_pokemon = _ordered_unique([*party, *boxed])
		inventory = _trainer_inventory(trainer)
		badges = _trainer_badges(trainer)
		entries.append(
			{
				"character": character,
				"character_id": _character_id(character),
				"trainer": trainer,
				"storage": storage,
				"pokemon": all_pokemon,
				"party": party,
				"boxed": boxed,
				"inventory": inventory,
				"badges": badges,
				"seen_count": _seen_count(trainer),
				"caught_count": len({getattr(mon, "species", "") for mon in all_pokemon if getattr(mon, "species", "")}),
				"total_pokemon": len(all_pokemon),
			}
		)
	return entries


def build_player_hub_entries(account, characters=None) -> list[dict]:
	"""Public helper for legacy character-sheet routes."""

	return _character_entries(account, characters=characters)


class MySheetView(LoginRequiredMixin, TemplateView):
	"""Display the read-only Player Hub for the logged in account."""

	template_name = "website/character_sheet.html"
	page_title = "Player Hub"

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context["characters"] = _character_entries(self.request.user)
		context["page_title"] = self.page_title
		return context
