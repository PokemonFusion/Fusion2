import sys
import types


def setup_env(monkeypatch):
    class DummyQuery(list):
        def first(self):
            return self[0] if self else None

        def update(self, **kwargs):
            for obj in self:
                for k, v in kwargs.items():
                    setattr(obj, k, v)

    class OwnedPokemon:
        objects = None  # placeholder

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
            self.unique_id = kwargs.get("unique_id", str(id(self)))
            self.species = kwargs.get("species", "")
            self.level = kwargs.get("level", 1)
            self.current_hp = kwargs.get("current_hp", 0)
            self.friendship = kwargs.get("friendship", 0)
            self.held_item = kwargs.get("held_item", "")
            self.evs = kwargs.get("evs", {}) or {}
            self.total_exp = kwargs.get("total_exp", 0)
            self.status = kwargs.get("status", "")

        def save(self):
            pass

    class OwnedManager:
        def __init__(self):
            self.store = {}

        def create(self, **kwargs):
            obj = OwnedPokemon(**kwargs)
            self.store[obj.unique_id] = obj
            return obj

        def filter(self, **kwargs):
            res = [obj for obj in self.store.values() if all(getattr(obj, k) == v for k, v in kwargs.items())]
            return DummyQuery(res)

    OwnedPokemon.objects = OwnedManager()

    class ActiveMoveslot:
        objects = None

        def __init__(self, pokemon, move, slot, current_pp=None):
            self.pokemon = pokemon
            self.move = move
            self.slot = slot
            self.current_pp = current_pp

        def save(self):
            pass

    class ActiveManager:
        def __init__(self):
            self.store = []

        def create(self, **kwargs):
            obj = ActiveMoveslot(**kwargs)
            self.store.append(obj)
            return obj

        def filter(self, **kwargs):
            res = [obj for obj in self.store if all(getattr(obj, k) == v for k, v in kwargs.items())]
            return DummyQuery(res)

    ActiveMoveslot.objects = ActiveManager()

    class Moveset:
        objects = None

        def __init__(self, pokemon, index):
            self.pokemon = pokemon
            self.index = index

        def save(self):
            pass

    class MovesetManager:
        def __init__(self):
            self.store = []

        def create(self, **kwargs):
            obj = Moveset(**kwargs)
            self.store.append(obj)
            return obj

    Moveset.objects = MovesetManager()

    class MovesetSlot:
        objects = None

        def __init__(self, moveset, move, slot):
            self.moveset = moveset
            self.move = move
            self.slot = slot

        def save(self):
            pass

    class MovesetSlotManager:
        def __init__(self):
            self.store = []

        def create(self, **kwargs):
            obj = MovesetSlot(**kwargs)
            self.store.append(obj)
            return obj

    MovesetSlot.objects = MovesetSlotManager()

    class Move:
        objects = None

        def __init__(self, name):
            self.name = name

    class MoveManager:
        def __init__(self):
            self.store = {}

        def get_or_create(self, name):
            obj = self.store.get(name)
            if obj is None:
                obj = Move(name)
                self.store[name] = obj
                return obj, True
            return obj, False

    Move.objects = MoveManager()

    fake_core = types.ModuleType("pokemon.models.core")
    fake_core.OwnedPokemon = OwnedPokemon
    monkeypatch.setitem(sys.modules, "pokemon.models.core", fake_core)

    fake_moves = types.ModuleType("pokemon.models.moves")
    fake_moves.ActiveMoveslot = ActiveMoveslot
    fake_moves.Moveset = Moveset
    fake_moves.MovesetSlot = MovesetSlot
    fake_moves.Move = Move
    monkeypatch.setitem(sys.modules, "pokemon.models.moves", fake_moves)

    fake_trainer = types.ModuleType("pokemon.models.trainer")
    class Trainer:
        pass
    fake_trainer.Trainer = Trainer
    monkeypatch.setitem(sys.modules, "pokemon.models.trainer", fake_trainer)

    fake_stats = types.ModuleType("pokemon.models.stats")

    def award_experience_to_party(player, amount, ev_gains=None):
        mons = player.storage.active_pokemon.all()
        if not mons:
            return
        mon = mons[0]
        mon.total_exp += amount
        if ev_gains:
            for k, v in ev_gains.items():
                mon.evs[k] = mon.evs.get(k, 0) + v

    def add_experience(mon, amount):
        mon.total_exp += amount

    def add_evs(mon, gains):
        for k, v in gains.items():
            mon.evs[k] = mon.evs.get(k, 0) + v

    def apply_item_ev_mod(mon, gains):
        return gains

    fake_stats.award_experience_to_party = award_experience_to_party
    fake_stats.add_experience = add_experience
    fake_stats.add_evs = add_evs
    fake_stats.apply_item_ev_mod = apply_item_ev_mod
    monkeypatch.setitem(sys.modules, "pokemon.models.stats", fake_stats)

    class DummyAtomic:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyTransaction:
        def atomic(self):
            return DummyAtomic()

    fake_db = types.ModuleType("django.db")
    fake_db.transaction = DummyTransaction()
    monkeypatch.setitem(sys.modules, "django.db", fake_db)

    monkeypatch.delitem(sys.modules, "services.battle.commit_adapter", raising=False)

    return OwnedPokemon, ActiveMoveslot, Move


def test_commit_updates(monkeypatch):
    OwnedPokemon, ActiveMoveslot, Move = setup_env(monkeypatch)
    from services.battle.commit_adapter import CommitAdapter

    move, _ = Move.objects.get_or_create("Tackle")
    mon = OwnedPokemon.objects.create(species="Pikachu", level=5, current_hp=20, evs={})
    ActiveMoveslot.objects.create(pokemon=mon, move=move, slot=1, current_pp=10)

    class DummyManager:
        def __init__(self, mons):
            self._mons = mons

        def all(self):
            return list(self._mons)

    class DummyStorage:
        def __init__(self, mons):
            self.active_pokemon = DummyManager(mons)

    class DummyTrainer:
        def __init__(self):
            self.money = 0
            self.badges = []

        def add_money(self, amt):
            self.money += amt

        def add_badge(self, b):
            self.badges.append(b)

    char = types.SimpleNamespace(
        db=types.SimpleNamespace(exp_share=False, battle_lock="lock"),
        storage=DummyStorage([mon]),
        trainer=DummyTrainer(),
    )

    spec = {
        "character": char,
        "party": [
            {
                "unique_id": mon.unique_id,
                "current_hp": 5,
                "status": "brn",
                "moves": [{"slot": 1, "current_pp": 7}],
                "friendship": 99,
                "held_item": "berry",
            }
        ],
        "exp": 100,
        "evs": {"attack": 2},
        "money": 50,
        "badges": ["Boulder"],
    }

    CommitAdapter.apply([spec])

    assert mon.current_hp == 5
    assert mon.friendship == 99
    assert mon.held_item == "berry"
    assert getattr(mon, "status") == "brn"
    slot = ActiveMoveslot.objects.filter(pokemon=mon, slot=1).first()
    assert slot.current_pp == 7
    assert mon.total_exp == 100
    assert mon.evs.get("attack") == 2
    assert char.trainer.money == 50
    assert "Boulder" in char.trainer.badges
    assert not hasattr(char.db, "battle_lock")


def test_commit_capture(monkeypatch):
    OwnedPokemon, ActiveMoveslot, Move = setup_env(monkeypatch)
    from services.battle.commit_adapter import CommitAdapter

    char = types.SimpleNamespace(
        db=types.SimpleNamespace(exp_share=False, battle_lock="abc"),
        storage=types.SimpleNamespace(active_pokemon=types.SimpleNamespace(all=lambda: [])),
        trainer=None,
    )

    capture = {
        "species": "Bulbasaur",
        "level": 5,
        "current_hp": 12,
        "moves": [{"name": "Tackle", "current_pp": 35}],
        "ivs": [1, 1, 1, 1, 1, 1],
        "evs": [0, 0, 0, 0, 0, 0],
    }

    CommitAdapter.apply([{ "character": char, "party": [], "capture": capture }])

    bulba = [o for o in OwnedPokemon.objects.store.values() if o.species == "Bulbasaur"][0]
    slot = ActiveMoveslot.objects.filter(pokemon=bulba, slot=1).first()
    assert slot.current_pp == 35
    assert bulba.level == 5
    assert not hasattr(char.db, "battle_lock")
