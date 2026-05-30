import importlib
from types import SimpleNamespace

backfill_pokemon_placements = importlib.import_module(
	"pokemon.migrations.0035_encounterpokemon_npctemplate_pokemonplacement"
).backfill_pokemon_placements
migrate_legacy_ownedpokemon_temp_rows = importlib.import_module(
	"pokemon.migrations.0037_remove_ownedpokemon_temp_fields"
).migrate_legacy_ownedpokemon_temp_rows


class FakeQuerySet(list):
	def order_by(self, *fields):
		return self

	def select_related(self, *fields):
		return self

	def all(self):
		return self


class FakePlacementManager:
	def __init__(self):
		self.calls = []

	def update_or_create(self, *, pokemon, defaults):
		self.calls.append((pokemon, defaults))
		return SimpleNamespace(pokemon=pokemon, **defaults), True


class FakeCreateManager:
	def __init__(self):
		self.calls = []

	def create(self, **kwargs):
		self.calls.append(kwargs)
		return SimpleNamespace(**kwargs)


def _storage_with(active_slots=None, boxes=None, stored=None):
	return SimpleNamespace(
		active_slots=FakeQuerySet(active_slots or []),
		boxes=FakeQuerySet(boxes or []),
		stored_pokemon=FakeQuerySet(stored or []),
	)


class FakeLegacyPokemon:
	def __init__(
		self,
		*,
		pk,
		species,
		level=1,
		trainer_id=None,
		ai_trainer=None,
		is_wild=False,
		is_template=False,
		is_battle_instance=False,
		nickname="",
		ability="",
		nature="",
		gender="",
		ivs=None,
		evs=None,
		held_item="",
		move_names=None,
	):
		self.pk = pk
		self.species = species
		self.level = level
		self.trainer_id = trainer_id
		self.ai_trainer = ai_trainer
		self.ai_trainer_id = getattr(ai_trainer, "pk", None)
		self.is_wild = is_wild
		self.is_template = is_template
		self.is_battle_instance = is_battle_instance
		self.nickname = nickname
		self.ability = ability
		self.nature = nature
		self.gender = gender
		self.ivs = ivs or [0, 0, 0, 0, 0, 0]
		self.evs = evs or [0, 0, 0, 0, 0, 0]
		self.held_item = held_item
		self.learned_moves = FakeQuerySet([SimpleNamespace(name=name) for name in (move_names or [])])
		self.deleted = False

	def delete(self):
		self.deleted = True


def test_backfill_pokemon_placements_prioritizes_party_then_box_then_stored():
	pokemon_a = SimpleNamespace(pk=1)
	pokemon_b = SimpleNamespace(pk=2)
	pokemon_c = SimpleNamespace(pk=3)

	box = SimpleNamespace(pk=9, pokemon=FakeQuerySet([pokemon_b, pokemon_a]))
	storage = _storage_with(
		active_slots=[SimpleNamespace(slot=2, pokemon=pokemon_a)],
		boxes=[box],
		stored=[pokemon_c, pokemon_b],
	)

	placement_manager = FakePlacementManager()
	apps = SimpleNamespace(
		get_model=lambda app, name: {
			("pokemon", "UserStorage"): SimpleNamespace(objects=FakeQuerySet([storage])),
			("pokemon", "PokemonPlacement"): SimpleNamespace(objects=placement_manager),
		}[(app, name)]
	)

	backfill_pokemon_placements(apps, None)

	assert len(placement_manager.calls) == 3

	by_pk = {pokemon.pk: defaults for pokemon, defaults in placement_manager.calls}
	assert by_pk[1]["location_type"] == "party"
	assert by_pk[1]["slot"] == 2

	assert by_pk[2]["location_type"] == "box"
	assert by_pk[2]["box"] is box
	assert by_pk[2]["box_position"] == 1

	assert by_pk[3]["location_type"] == "box"
	assert by_pk[3]["box"] is box
	assert by_pk[3]["box_position"] == 1


def test_migrate_legacy_ownedpokemon_temp_rows_converts_templates_and_purges_temp_rows():
	npc_trainer = SimpleNamespace(pk=77, name="Brock")
	legacy_template = FakeLegacyPokemon(
		pk=1,
		species="Onix",
		level=12,
		ai_trainer=npc_trainer,
		is_template=True,
		nickname="lead",
		held_item="Hard Stone",
		move_names=["Tackle", "Bind"],
	)
	legacy_npc_roster = FakeLegacyPokemon(
		pk=2,
		species="Geodude",
		level=10,
		ai_trainer=npc_trainer,
		move_names=["Defense Curl"],
	)
	legacy_wild = FakeLegacyPokemon(pk=3, species="Zubat", is_wild=True)
	permanent = FakeLegacyPokemon(pk=4, species="Pikachu", trainer_id=9)

	template_manager = FakeCreateManager()
	apps = SimpleNamespace(
		get_model=lambda app, name: {
			("pokemon", "OwnedPokemon"): SimpleNamespace(objects=FakeQuerySet([legacy_template, legacy_npc_roster, legacy_wild, permanent])),
			("pokemon", "NPCPokemonTemplate"): SimpleNamespace(objects=template_manager),
		}[(app, name)]
	)

	migrate_legacy_ownedpokemon_temp_rows(apps, None)

	assert len(template_manager.calls) == 2
	assert template_manager.calls[0]["npc_trainer"] is npc_trainer
	assert template_manager.calls[0]["template_key"] == "lead"
	assert template_manager.calls[0]["species"] == "Onix"
	assert template_manager.calls[0]["move_names"] == ["Tackle", "Bind"]
	assert template_manager.calls[0]["sort_order"] == 1
	assert template_manager.calls[1]["species"] == "Geodude"
	assert template_manager.calls[1]["sort_order"] == 2

	assert legacy_template.deleted is True
	assert legacy_npc_roster.deleted is True
	assert legacy_wild.deleted is True
	assert permanent.deleted is False
