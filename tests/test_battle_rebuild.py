import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Minimal Evennia stub
try:
    import evennia  # type: ignore
    evennia.search_object = lambda *a, **k: []
    evennia.create_object = lambda cls, key=None: cls()
    evennia.utils = types.ModuleType("evennia.utils")
    evennia.utils.ansi = types.SimpleNamespace(
        parse_ansi=lambda s: s,
        RED=lambda s: s,
        GREEN=lambda s: s,
        YELLOW=lambda s: s,
        BLUE=lambda s: s,
        MAGENTA=lambda s: s,
        CYAN=lambda s: s,
        strip_ansi=lambda s: s,
    )
    sys.modules["evennia.utils"] = evennia.utils
    evennia.server = types.ModuleType("evennia.server")
    evennia.server.models = types.ModuleType("evennia.server.models")
    class DummySC:
        store = {}

        @classmethod
        def conf(cls, key, value=None, default=None, delete=False):
            if delete:
                cls.store.pop(key, None)
                return
            if value is not None:
                cls.store[key] = value
            return cls.store.get(key, default)

    DummySC.objects = DummySC

    evennia.server.models.ServerConfig = DummySC
    DummySC.objects = DummySC
    sys.modules["evennia.server"] = evennia.server
    sys.modules["evennia.server.models"] = evennia.server.models
except Exception:
    evennia = types.ModuleType("evennia")
    evennia.search_object = lambda *a, **k: []
    evennia.DefaultRoom = type("DefaultRoom", (), {})
    evennia.objects = types.SimpleNamespace(objects=types.SimpleNamespace(DefaultRoom=evennia.DefaultRoom))
    evennia.utils = types.ModuleType("evennia.utils")
    evennia.utils.ansi = types.SimpleNamespace(
        parse_ansi=lambda s: s,
        RED=lambda s: s,
        GREEN=lambda s: s,
        YELLOW=lambda s: s,
        BLUE=lambda s: s,
        MAGENTA=lambda s: s,
        CYAN=lambda s: s,
        strip_ansi=lambda s: s,
    )
    sys.modules["evennia.utils"] = evennia.utils
    evennia.server = types.ModuleType("evennia.server")
    evennia.server.models = types.ModuleType("evennia.server.models")

    class DummySC:
        store = {}

        @classmethod
        def conf(cls, key, value=None, default=None, delete=False):
            if delete:
                cls.store.pop(key, None)
                return
            if value is not None:
                cls.store[key] = value
            return cls.store.get(key, default)

    evennia.server.models.ServerConfig = DummySC
    DummySC.objects = DummySC
    sys.modules["evennia"] = evennia
    sys.modules["evennia.server"] = evennia.server
    sys.modules["evennia.server.models"] = evennia.server.models

# Stub battle interface and helpers
iface = types.ModuleType("pokemon.battle.interface")
iface.add_watcher = lambda *a, **k: None
iface.remove_watcher = lambda *a, **k: None
iface.notify_watchers = lambda *a, **k: None
sys.modules["pokemon.battle.interface"] = iface

# Stub generation and spawn modules
gen_mod = types.ModuleType("pokemon.generation")

class DummyInst:
    def __init__(self, name, level):
        self.species = types.SimpleNamespace(name=name)
        self.level = level
        self.stats = types.SimpleNamespace(hp=100)
        self.moves = ["tackle"]
        self.ability = None

def generate_pokemon(name, level=5):
    return DummyInst(name, level)

gen_mod.generate_pokemon = generate_pokemon
gen_mod.NATURES = {}
sys.modules["pokemon.generation"] = gen_mod

spawn_mod = types.ModuleType("world.pokemon_spawn")
spawn_mod.get_spawn = lambda loc: None
sys.modules["world.pokemon_spawn"] = spawn_mod

# Load supporting battle modules from real files
bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
bd_mod = importlib.util.module_from_spec(bd_spec)
sys.modules[bd_spec.name] = bd_mod
bd_spec.loader.exec_module(bd_mod)

st_path = os.path.join(ROOT, "pokemon", "battle", "state.py")
st_spec = importlib.util.spec_from_file_location("pokemon.battle.state", st_path)
st_mod = importlib.util.module_from_spec(st_spec)
sys.modules[st_spec.name] = st_mod
st_spec.loader.exec_module(st_mod)

storage_path = os.path.join(ROOT, "pokemon", "battle", "storage.py")
storage_spec = importlib.util.spec_from_file_location(
    "pokemon.battle.storage", storage_path
)
storage_mod = importlib.util.module_from_spec(storage_spec)
sys.modules[storage_spec.name] = storage_mod
storage_spec.loader.exec_module(storage_mod)
BattleDataWrapper = storage_mod.BattleDataWrapper

eng_path = os.path.join(ROOT, "pokemon", "battle", "engine.py")
eng_spec = importlib.util.spec_from_file_location("pokemon.battle.engine", eng_path)
eng_mod = importlib.util.module_from_spec(eng_spec)
sys.modules[eng_spec.name] = eng_mod
eng_spec.loader.exec_module(eng_mod)

handler_path = os.path.join(ROOT, "pokemon", "battle", "handler.py")
h_spec = importlib.util.spec_from_file_location("pokemon.battle.handler", handler_path)
h_mod = importlib.util.module_from_spec(h_spec)
sys.modules[h_spec.name] = h_mod
h_spec.loader.exec_module(h_mod)
BattleHandler = h_mod.BattleHandler

bi_path = os.path.join(ROOT, "pokemon", "battle", "battleinstance.py")
bi_spec = importlib.util.spec_from_file_location("pokemon.battle.battleinstance", bi_path)
bi_mod = importlib.util.module_from_spec(bi_spec)
sys.modules[bi_spec.name] = bi_mod
bi_spec.loader.exec_module(bi_mod)
BattleSession = bi_mod.BattleSession

class DummyRoom:
    def __init__(self, rid=1):
        self.id = rid
        self.db = types.SimpleNamespace()
        self.ndb = types.SimpleNamespace()

class DummyStorage:
    def get_party(self):
        return []

class DummyPlayer:
    def __init__(self, pid, room):
        self.key = f"Player{pid}"
        self.id = pid
        self.db = types.SimpleNamespace()
        self.ndb = types.SimpleNamespace()
        self.location = room
        self.storage = DummyStorage()

    def msg(self, text):
        pass


def test_rebuild_ndb_restores_instance():
    room = DummyRoom()
    p1 = DummyPlayer(1, room)
    p2 = DummyPlayer(2, room)
    inst = BattleSession(p1, p2)
    inst.start_pvp()

    # clear ndb references as if after reload
    p1.ndb.battle_instance = None
    p2.ndb.battle_instance = None
    room.ndb.battle_instances = {}

    handler = BattleHandler()
    handler.register(inst)
    handler.rebuild_ndb()

    assert p1.ndb.battle_instance is inst
    assert p2.ndb.battle_instance is inst
    assert room.ndb.battle_instances[inst.battle_id] is inst


def test_restore_registers_instance():
    room = DummyRoom()
    p1 = DummyPlayer(1, room)
    p2 = DummyPlayer(2, room)
    inst = BattleSession(p1, p2)
    inst.start_pvp()

    # Simulate reload by clearing ndb references and handler state
    p1.ndb.battle_instance = None
    p2.ndb.battle_instance = None
    room.ndb.battle_instances = {}

    bi_mod.battle_handler.clear()
    restored = BattleSession.restore(room, inst.battle_id)

    # restore should populate the room's map and return the instance
    assert restored is not None
    assert room.ndb.battle_instances[inst.battle_id] is restored


def test_trainer_ids_saved_and_restored():
    room = DummyRoom()
    p1 = DummyPlayer(1, room)
    p2 = DummyPlayer(2, room)
    inst = BattleSession(p1, p2)
    inst.start_pvp()

    storage = BattleDataWrapper(room, inst.battle_id)
    assert storage.get("trainers") == {"teamA": [1], "teamB": [2]}

    p1.ndb.battle_instance = None
    p2.ndb.battle_instance = None
    room.ndb.battle_instances = {}

    orig_search = bi_mod.search_object
    bi_mod.search_object = lambda oid: [p1] if str(oid).lstrip("#") == "1" else ([p2] if str(oid).lstrip("#") == "2" else [])
    try:
        restored = BattleSession.restore(room, inst.battle_id)
    finally:
        bi_mod.search_object = orig_search

    assert restored.player is p1
    assert restored.opponent is p2


def test_pokemon_serialization_minimal():
    poke = bd_mod.Pokemon("Bulbasaur", level=5, hp=20, max_hp=30, model_id="abc")
    poke.ability = "Overgrow"
    poke.data = {"foo": "bar"}
    data = poke.to_dict()

    assert "name" not in data
    assert "level" not in data
    assert "max_hp" not in data
    assert "moves" not in data
    assert "data" not in data
    assert "ability" not in data
    assert data.get("model_id") == "abc"
    assert data.get("current_hp") == 20

    restored = bd_mod.Pokemon.from_dict(data)
    assert restored.model_id == "abc"
    assert restored.hp == 20


def test_from_dict_calculates_max_hp():
    fake_models = types.ModuleType("pokemon.models")

    class FakeOwned:
        class Manager:
            def get(self, unique_id=None):
                return FakeOwned()

        objects = Manager()

        def __init__(self):
            self.name = "Bulbasaur"
            self.species = "Bulbasaur"
            self.level = 5
            self.data = {"ivs": {}, "evs": {}, "nature": "Hardy"}
            class MS(list):
                def order_by(self, field):
                    return self
            class Moveset:
                def __init__(self):
                    self.index = 0
                    self.slots = MS([
                        types.SimpleNamespace(
                            move=types.SimpleNamespace(name="tackle"), slot=1
                        )
                    ])
            self.movesets = [Moveset()]
            self.active_moveset = self.movesets[0]
            self.current_hp = 5

    fake_models.OwnedPokemon = FakeOwned
    orig_models = sys.modules.get("pokemon.models")
    sys.modules["pokemon.models"] = fake_models

    helpers_mod = types.ModuleType("pokemon.utils.pokemon_helpers")
    helpers_mod.get_max_hp = lambda mon: 42
    orig_helpers = sys.modules.get("pokemon.utils.pokemon_helpers")
    sys.modules["pokemon.utils.pokemon_helpers"] = helpers_mod

    try:
        poke = bd_mod.Pokemon.from_dict({"model_id": "uid"})
    finally:
        if orig_models is not None:
            sys.modules["pokemon.models"] = orig_models
        else:
            sys.modules.pop("pokemon.models", None)
        if orig_helpers is not None:
            sys.modules["pokemon.utils.pokemon_helpers"] = orig_helpers
        else:
            sys.modules.pop("pokemon.utils.pokemon_helpers", None)

    assert poke.max_hp == 42


def test_battle_state_serialization_new_fields():
    """BattleState should persist ability_holder and pokemon_control."""

    state_cls = st_mod.BattleState
    state = state_cls()
    state.ability_holder = "poke-123"
    state.pokemon_control = {"poke-123": "1"}

    data = state.to_dict()
    assert data.get("ability_holder") == "poke-123"
    assert data.get("pokemon_control") == {"poke-123": "1"}

    restored = state_cls.from_dict(data)
    assert restored.ability_holder == "poke-123"
    assert restored.pokemon_control == {"poke-123": "1"}


def test_pokemon_control_restored_after_reload():
    room = DummyRoom()

    class StoredPoke:
        def __init__(self, uid):
            self.name = "Bulbasaur"
            self.level = 5
            self.moves = ["tackle"]
            self.data = {"ivs": {}, "evs": {}, "nature": "Hardy"}
            self.current_hp = 20
            self.unique_id = uid

    class StorageWithPoke(DummyStorage):
        def __init__(self, uid):
            self.poke = StoredPoke(uid)

        def get_party(self):
            return [self.poke]

    p1 = DummyPlayer(1, room)
    p1.storage = StorageWithPoke("uid1")
    p2 = DummyPlayer(2, room)
    p2.storage = StorageWithPoke("uid2")

    inst = BattleSession(p1, p2)
    inst.start_pvp()

    assert inst.state.pokemon_control == {"uid1": "1", "uid2": "2"}

    # clear ndb refs simulating reload
    p1.ndb.battle_instance = None
    p2.ndb.battle_instance = None
    room.ndb.battle_instances = {}

    orig_search = bi_mod.search_object
    bi_mod.search_object = lambda oid: [p1] if str(oid).lstrip("#") == "1" else ([p2] if str(oid).lstrip("#") == "2" else [])
    try:
        restored = BattleSession.restore(room, inst.battle_id)
    finally:
        bi_mod.search_object = orig_search

    assert restored.state.pokemon_control == {"uid1": "1", "uid2": "2"}

def test_multiple_battles_saved_in_room():
    room = DummyRoom()
    p1 = DummyPlayer(1, room)
    p2 = DummyPlayer(2, room)
    p3 = DummyPlayer(3, room)
    p4 = DummyPlayer(4, room)

    inst1 = BattleSession(p1, p2)
    inst1.start_pvp()

    inst2 = BattleSession(p3, p4)
    inst2.start_pvp()

    s1 = BattleDataWrapper(room, inst1.battle_id)
    s2 = BattleDataWrapper(room, inst2.battle_id)
    assert s1.get("data") is not None
    assert s2.get("data") is not None
    assert set(room.db.battles) == {inst1.battle_id, inst2.battle_id}


def test_multiple_hunts_saved_in_room():
    room = DummyRoom()
    p1 = DummyPlayer(1, room)
    p2 = DummyPlayer(2, room)

    inst1 = BattleSession(p1)
    inst1.start()

    inst2 = BattleSession(p2)
    inst2.start()

    s1 = BattleDataWrapper(room, inst1.battle_id)
    s2 = BattleDataWrapper(room, inst2.battle_id)
    assert s1.get("data") is not None
    assert s2.get("data") is not None
    assert set(room.db.battles) == {inst1.battle_id, inst2.battle_id}

def test_battle_segments_removed_on_end():
    room = DummyRoom()
    p1 = DummyPlayer(1, room)
    p2 = DummyPlayer(2, room)
    inst = BattleSession(p1, p2)
    inst.start_pvp()

    storage = BattleDataWrapper(room, inst.battle_id)
    assert storage.get("data") is not None
    assert storage.get("state") is not None
    assert storage.get("trainers") == {"teamA": [1], "teamB": [2]}
    assert storage.get("temp_pokemon_ids") == []

    inst.end()

    assert storage.get("data") is None
    assert storage.get("state") is None
    assert storage.get("trainers") is None
    assert storage.get("temp_pokemon_ids") is None
    assert inst.battle_id not in getattr(room.db, "battles", [])


def test_independent_storage_between_battles():
    room = DummyRoom()
    p1 = DummyPlayer(1, room)
    p2 = DummyPlayer(2, room)
    p3 = DummyPlayer(3, room)
    p4 = DummyPlayer(4, room)

    inst1 = BattleSession(p1, p2)
    inst1.start_pvp()
    inst2 = BattleSession(p3, p4)
    inst2.start_pvp()

    s1 = BattleDataWrapper(room, inst1.battle_id)
    s2 = BattleDataWrapper(room, inst2.battle_id)
    assert s1.get("data") is not None
    assert s2.get("data") is not None
    assert hasattr(room.db, f"battle_{inst1.battle_id}_data")
    assert hasattr(room.db, f"battle_{inst2.battle_id}_data")

    inst1.end()

    assert not hasattr(room.db, f"battle_{inst1.battle_id}_data")
    assert hasattr(room.db, f"battle_{inst2.battle_id}_data")

    inst2.end()

    assert not hasattr(room.db, f"battle_{inst2.battle_id}_data")
    assert not hasattr(room.db, f"battle_{inst2.battle_id}_state")
