import importlib.util
import os
import sys
import types
from contextlib import nullcontext


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


class FakeQuery(list):
	def first(self):
		return self[0] if self else None

	def order_by(self, *args):
		return self


class FakeBox:
	def __init__(self, name, pokemon=None):
		self.name = name
		self._pokemon = list(pokemon or [])

	def get_pokemon(self):
		return list(self._pokemon)


class FakeBoxManager:
	def __init__(self, boxes):
		self._boxes = boxes

	def all(self):
		return FakeQuery(self._boxes)


class FakePlacementQuery:
	def __init__(self, exists):
		self._exists = exists

	def exists(self):
		return self._exists


class FakePlacements:
	def __init__(self, party=None):
		self.party = set(party or [])

	def filter(self, **kwargs):
		pokemon = kwargs.get("pokemon")
		location_type = kwargs.get("location_type")
		return FakePlacementQuery(location_type == "party" and pokemon in self.party)


class FakeStorage:
	def __init__(self, boxes, *, party=None, active_by_slot=None, active_count=0):
		self.boxes = FakeBoxManager(boxes)
		self.party = list(party or [])
		self.placements = FakePlacements(party)
		self.active_by_slot = dict(active_by_slot or {})
		self._active_count = active_count

	def active_pokemon_count(self):
		return self._active_count

	def get_party(self):
		if self.active_by_slot:
			return [self.active_by_slot[key] for key in sorted(self.active_by_slot)]
		return list(self.party)


class FakePokemon:
	def __init__(self, unique_id, species, trainer=None, storage=None):
		self.unique_id = unique_id
		self.species = species
		self.nickname = ""
		self.trainer = trainer
		self.placement_storage = storage


class FakeOwnedManager:
	def __init__(self, pokemon):
		self.pokemon = list(pokemon)

	def filter(self, **kwargs):
		matches = self.pokemon
		if "unique_id" in kwargs:
			matches = [mon for mon in matches if mon.unique_id == kwargs["unique_id"]]
		if "trainer" in kwargs:
			matches = [mon for mon in matches if mon.trainer is kwargs["trainer"]]
		if "placement__storage" in kwargs:
			matches = [mon for mon in matches if mon.placement_storage is kwargs["placement__storage"]]
		return FakeQuery(matches)


class FakeOwnedPokemon:
	class DoesNotExist(Exception):
		pass


class FakeActiveSlots:
	def __init__(self, storage):
		self.storage = storage
		self.slot = None

	def select_related(self, *args):
		return self

	def filter(self, **kwargs):
		self.slot = kwargs.get("slot")
		return self

	def first(self):
		pokemon = self.storage.active_by_slot.get(self.slot)
		return types.SimpleNamespace(pokemon=pokemon) if pokemon else None


def load_user_module(monkeypatch):
	typeclasses = types.ModuleType("typeclasses.characters")
	typeclasses.Character = type("Character", (), {})
	monkeypatch.setitem(sys.modules, "typeclasses.characters", typeclasses)

	party_helpers = types.ModuleType("pokemon.helpers.party_helpers")
	party_helpers.get_active_party = lambda caller: []
	party_helpers.has_usable_pokemon = lambda caller: False
	monkeypatch.setitem(sys.modules, "pokemon.helpers.party_helpers", party_helpers)

	pokemon_helpers = types.ModuleType("pokemon.helpers.pokemon_helpers")
	pokemon_helpers.create_owned_pokemon = lambda *args, **kwargs: None
	monkeypatch.setitem(sys.modules, "pokemon.helpers.pokemon_helpers", pokemon_helpers)

	storage_mod = types.ModuleType("pokemon.models.storage")
	storage_mod.PokemonPlacement = types.SimpleNamespace(
		LocationType=types.SimpleNamespace(PARTY="party")
	)
	storage_mod.move_to_box = lambda *args, **kwargs: None
	storage_mod.move_to_party = lambda *args, **kwargs: None
	storage_mod.ensure_boxes = lambda storage: storage
	monkeypatch.setitem(sys.modules, "pokemon.models.storage", storage_mod)

	inventory_mod = types.ModuleType("utils.inventory")
	inventory_mod.Inventory = dict
	inventory_mod.InventoryMixin = type("InventoryMixin", (), {})
	monkeypatch.setitem(sys.modules, "utils.inventory", inventory_mod)

	generation_mod = types.ModuleType("pokemon.data.generation")
	generation_mod.generate_pokemon = lambda *args, **kwargs: None
	monkeypatch.setitem(sys.modules, "pokemon.data.generation", generation_mod)

	dex_mod = types.ModuleType("pokemon.dex")
	dex_mod.POKEDEX = {}
	monkeypatch.setitem(sys.modules, "pokemon.dex", dex_mod)

	objresolve_mod = types.ModuleType("pokemon.utils.objresolve")
	objresolve_mod.resolve_to_obj = lambda value: None
	monkeypatch.setitem(sys.modules, "pokemon.utils.objresolve", objresolve_mod)

	path = os.path.join(ROOT, "pokemon", "user.py")
	spec = importlib.util.spec_from_file_location("pokemon.user", path)
	mod = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = mod
	spec.loader.exec_module(mod)
	monkeypatch.setattr(mod.transaction, "atomic", lambda: nullcontext())
	return mod


def make_user(mod, storage, trainer, pokemon, monkeypatch):
	FakeOwnedPokemon.objects = FakeOwnedManager(pokemon)

	class FakeTrainerModel:
		objects = types.SimpleNamespace(
			count=lambda: 0,
			get_or_create=lambda **kwargs: (trainer, True),
		)

	class FakeStorageModel:
		objects = types.SimpleNamespace(get_or_create=lambda **kwargs: (storage, True))

	def get_model(app_label, model_name):
		if model_name == "OwnedPokemon":
			return FakeOwnedPokemon
		if model_name == "Trainer":
			return FakeTrainerModel
		if model_name == "UserStorage":
			return FakeStorageModel
		raise AssertionError(model_name)

	monkeypatch.setattr(mod, "apps", types.SimpleNamespace(get_model=get_model))
	user = object.__new__(mod.User)
	storage.active_slots = FakeActiveSlots(storage)
	return user


def test_get_pokemon_by_id_is_scoped_to_owner(monkeypatch):
	mod = load_user_module(monkeypatch)
	trainer = object()
	storage = FakeStorage([FakeBox("Box 1")])
	owned = FakePokemon("owned", "Pikachu", trainer=trainer)
	placed = FakePokemon("placed", "Eevee", trainer=object(), storage=storage)
	other = FakePokemon("other", "Mew", trainer=object())
	user = make_user(mod, storage, trainer, [owned, placed, other], monkeypatch)

	assert user.get_pokemon_by_id("owned") is owned
	assert user.get_pokemon_by_id("placed") is placed
	assert user.get_pokemon_by_id("other") is None


def test_deposit_requires_party_ownership(monkeypatch):
	mod = load_user_module(monkeypatch)
	trainer = object()
	party_mon = FakePokemon("party", "Pikachu", trainer=trainer)
	boxed_mon = FakePokemon("boxed", "Eevee", trainer=trainer)
	box = FakeBox("Box 1", [boxed_mon])
	storage = FakeStorage([box], party=[party_mon])
	user = make_user(mod, storage, trainer, [party_mon, boxed_mon], monkeypatch)
	moved = []
	monkeypatch.setattr(mod, "move_to_box", lambda mon, storage, box: moved.append((mon, box)))

	assert user.deposit_pokemon("boxed") == "That Pokemon is not in your party."
	assert user.deposit_pokemon("party") == "Pikachu was deposited in Box 1."
	assert moved == [(party_mon, box)]


def test_withdraw_full_party_returns_swap_prompt(monkeypatch):
	mod = load_user_module(monkeypatch)
	trainer = object()
	boxed_mon = FakePokemon("boxed", "Eevee", trainer=trainer)
	storage = FakeStorage([FakeBox("Box 1", [boxed_mon])], active_count=6)
	user = make_user(mod, storage, trainer, [boxed_mon], monkeypatch)
	moved = []
	monkeypatch.setattr(mod, "move_to_party", lambda *args: moved.append(args))

	result = user.withdraw_pokemon("boxed")

	assert "Your party is full" in result
	assert moved == []


def test_swap_pokemon_moves_boxed_mon_into_slot(monkeypatch):
	mod = load_user_module(monkeypatch)
	trainer = object()
	boxed_mon = FakePokemon("boxed", "Eevee", trainer=trainer)
	party_mon = FakePokemon("party", "Pikachu", trainer=trainer)
	box = FakeBox("Box 1", [boxed_mon])
	storage = FakeStorage([box], active_by_slot={2: party_mon}, active_count=6)
	user = make_user(mod, storage, trainer, [boxed_mon, party_mon], monkeypatch)
	calls = []
	monkeypatch.setattr(mod, "move_to_box", lambda mon, storage, box: calls.append(("box", mon, box)))
	monkeypatch.setattr(mod, "move_to_party", lambda mon, storage, slot=None: calls.append(("party", mon, slot)))

	result = user.swap_pokemon("boxed", 2)

	assert result == "Eevee was swapped into slot 2; Pikachu was sent to Box 1."
	assert calls == [("box", party_mon, box), ("party", boxed_mon, 2)]


def test_pokestore_full_party_routes_box_selection_to_swap():
	import menus.pokestore as menu

	boxed_mon = FakePokemon("boxed", "Eevee")
	party = [FakePokemon(f"party-{i}", f"Poke{i}") for i in range(6)]
	storage = FakeStorage([FakeBox("Box 1", [boxed_mon])], party=party, active_count=6)
	caller = types.SimpleNamespace(storage=storage, msgs=[])
	caller.msg = caller.msgs.append

	text, _ = menu.node_box(caller, box_index=0)
	assert "swap with your party" in text

	text, _ = menu.node_box(caller, raw_input="1", box_index=0)
	assert text.startswith("Swap with which party slot?")


def test_pokestore_swap_slot_calls_player_swap():
	import menus.pokestore as menu

	boxed_mon = FakePokemon("boxed", "Eevee")
	party = [FakePokemon(f"party-{i}", f"Poke{i}") for i in range(6)]
	storage = FakeStorage([FakeBox("Box 1", [boxed_mon])], party=party, active_count=6)
	calls = []
	caller = types.SimpleNamespace(storage=storage, msgs=[])
	caller.msg = caller.msgs.append
	caller.swap_pokemon = lambda pid, slot, box: calls.append((pid, slot, box)) or "swapped"

	menu.node_choose_party_slot(caller, raw_input="2", box_index=0, poke_id="boxed")

	assert calls == [("boxed", 2, 1)]
	assert caller.msgs == ["swapped"]
