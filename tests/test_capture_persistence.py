import sys
import types
from contextlib import nullcontext
from types import SimpleNamespace

from pokemon.services.capture import finalize_wild_capture


class FakeOwnedPokemon:
    def __init__(self, unique_id="owned-1"):
        self.unique_id = unique_id
        self.trainer = None
        self.is_wild = True
        self.ai_trainer = "wild"
        self.is_battle_instance = True
        self.current_hp = 0
        self.level = 5
        self.met_level = None
        self.met_location = ""
        self.met_date = None
        self.obtained_method = ""
        self.original_trainer = None
        self.original_trainer_name = ""
        self.held_item = ""
        self.party_slot = None
        self.saved = 0

    def save(self):
        self.saved += 1


class FakeManager:
    def __init__(self, pokemon):
        self.pokemon = pokemon

    def select_for_update(self):
        return self

    def get(self, **kwargs):
        assert kwargs["unique_id"] == self.pokemon.unique_id
        return self.pokemon


class FakeStorage:
    def __init__(self, party_count=0):
        self.party = [object()] * party_count
        self.pk = None
        self.active_slots = []

    def get_party(self):
        return list(self.party)


class FakePlayer:
    def __init__(self, storage, battle_instance=None):
        self.storage = storage
        self.location = SimpleNamespace(key="Route 1")
        self.ndb = SimpleNamespace(battle_instance=battle_instance)


def _install_capture_stubs(monkeypatch, *, dbpoke=None, create_owned_pokemon=None, move_to_party=None, move_to_box=None):
    helper_mod = types.ModuleType("pokemon.helpers.pokemon_helpers")
    helper_mod.create_owned_pokemon = create_owned_pokemon or (lambda *args, **kwargs: dbpoke)
    monkeypatch.setitem(sys.modules, "pokemon.helpers.pokemon_helpers", helper_mod)

    core_mod = types.ModuleType("pokemon.models.core")
    core_mod.OwnedPokemon = type("OwnedPokemon", (), {"objects": FakeManager(dbpoke) if dbpoke is not None else None})
    monkeypatch.setitem(sys.modules, "pokemon.models.core", core_mod)

    storage_mod = types.ModuleType("pokemon.models.storage")
    storage_mod.assign_to_first_storage_box = lambda storage, mon: SimpleNamespace(name="Box 1", storage=storage)
    storage_mod.move_to_party = move_to_party or (lambda mon, storage, slot=None: setattr(mon, "party_slot", 1))
    storage_mod.move_to_box = move_to_box or (
        lambda mon, storage, box=None: box or SimpleNamespace(name="Box 1", storage=storage)
    )
    monkeypatch.setitem(sys.modules, "pokemon.models.storage", storage_mod)

    encounters_mod = types.ModuleType("pokemon.services.encounters")
    encounters_mod.get_encounter_from_ref = lambda model_id: SimpleNamespace(
        encounter_id=str(model_id).split(":", 1)[-1],
        species="Bulbasaur",
        level=5,
        gender="",
        nature="",
        ability="",
        ivs=[],
        evs=[],
        held_item="",
        delete=lambda: None,
    )
    monkeypatch.setitem(sys.modules, "pokemon.services.encounters", encounters_mod)

    refs_mod = types.ModuleType("pokemon.services.pokemon_refs")
    refs_mod.build_owned_ref = lambda identifier: f"owned:{identifier}"
    refs_mod.parse_pokemon_ref = lambda value: tuple(str(value).split(":", 1)) if ":" in str(value) else ("owned", str(value))
    monkeypatch.setitem(sys.modules, "pokemon.services.pokemon_refs", refs_mod)
    monkeypatch.setattr("pokemon.services.capture.get_encounter_from_ref", encounters_mod.get_encounter_from_ref)
    monkeypatch.setattr("pokemon.services.capture.build_owned_ref", refs_mod.build_owned_ref)
    monkeypatch.setattr("pokemon.services.capture.parse_pokemon_ref", refs_mod.parse_pokemon_ref)


def test_finalize_wild_capture_places_caught_mon_in_party(monkeypatch):
    dbpoke = FakeOwnedPokemon("owned-party")
    storage = FakeStorage(party_count=0)
    session_updates = []
    battle_instance = SimpleNamespace(
        temp_pokemon_ids=["encounter:owned-party"],
        storage=SimpleNamespace(set=lambda key, value: session_updates.append((key, value))),
    )
    player = FakePlayer(storage, battle_instance=battle_instance)
    trainer = SimpleNamespace(user=SimpleNamespace(key="Ash"))
    target = SimpleNamespace(
        model_id="encounter:owned-party",
        hp=7,
        level=12,
        item="Oran Berry",
        species="Bulbasaur",
        name="Bulbasaur",
    )

    monkeypatch.setattr("pokemon.services.capture._atomic_context", lambda: nullcontext())

    def fake_move_to_party(mon, resolved_storage, slot=None):
        assert mon is dbpoke
        assert resolved_storage is storage
        mon.party_slot = 1
        resolved_storage.party.append(mon)

    _install_capture_stubs(monkeypatch, dbpoke=dbpoke, move_to_party=fake_move_to_party)

    result = finalize_wild_capture(
        target_poke=target,
        player=player,
        trainer=trainer,
        battle_context=battle_instance,
        ball_name="Pokeball",
    )

    assert result.placement == "party"
    assert result.party_slot == 1
    assert dbpoke.trainer is trainer
    assert dbpoke.current_hp == 7
    assert dbpoke.met_level == 12
    assert dbpoke.met_location == "Route 1"
    assert dbpoke.obtained_method == "caught"
    assert dbpoke.original_trainer is trainer
    assert dbpoke.original_trainer_name == "Ash"
    assert dbpoke.held_item == "Oran Berry"
    assert dbpoke.saved == 1
    assert battle_instance.temp_pokemon_ids == []
    assert session_updates == [("temp_pokemon_ids", [])]


def test_finalize_wild_capture_routes_full_party_to_storage(monkeypatch):
    dbpoke = FakeOwnedPokemon("owned-box")
    storage = FakeStorage(party_count=6)
    player = FakePlayer(storage)
    trainer = SimpleNamespace(user=SimpleNamespace(key="Ash"))
    target = SimpleNamespace(
        model_id="encounter:owned-box",
        hp=4,
        level=8,
        held_item="Pecha Berry",
        species="Pidgey",
        name="Pidgey",
    )
    fake_box = SimpleNamespace(name="Box 9", storage=storage)

    monkeypatch.setattr("pokemon.services.capture._atomic_context", lambda: nullcontext())
    _install_capture_stubs(
        monkeypatch,
        dbpoke=dbpoke,
        move_to_box=lambda mon, resolved_storage, box=None: fake_box,
    )
    monkeypatch.setattr(sys.modules["pokemon.models.storage"], "assign_to_first_storage_box", lambda storage, mon: fake_box)

    result = finalize_wild_capture(
        target_poke=target,
        player=player,
        trainer=trainer,
        ball_name="Premier Ball",
    )

    assert result.placement == "storage"
    assert result.party_slot is None
    assert result.box_name == "Box 9"
    assert dbpoke.held_item == "Pecha Berry"


def test_finalize_wild_capture_creates_ownedpokemon_when_model_id_missing(monkeypatch):
    created = FakeOwnedPokemon("created-mon")
    storage = FakeStorage(party_count=0)
    player = FakePlayer(storage)
    trainer = SimpleNamespace(user=SimpleNamespace(key="Ash"))
    target = SimpleNamespace(
        model_id=None,
        hp=11,
        level=9,
        item="Sitrus Berry",
        species="Oddish",
        name="Oddish",
        gender="F",
        nature="Calm",
        ability="Chlorophyll",
        ivs=[1, 2, 3, 4, 5, 6],
        evs=[0, 0, 0, 0, 0, 0],
    )

    monkeypatch.setattr("pokemon.services.capture._atomic_context", lambda: nullcontext())
    _install_capture_stubs(monkeypatch, dbpoke=created, create_owned_pokemon=lambda *args, **kwargs: created)

    result = finalize_wild_capture(
        target_poke=target,
        player=player,
        trainer=trainer,
        ball_name="Nest Ball",
    )

    assert result.owned_pokemon_id == "owned:created-mon"
    assert result.placement == "party"
    assert created.current_hp == 11
    assert created.held_item == "Sitrus Berry"
    assert created.original_trainer is trainer
