import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

class FakeQS(list):
    def order_by(self, field):
        return self
    def first(self):
        return self[0] if self else None
    def all(self):
        return self

class FakeManager:
    def __init__(self):
        self.data = []
    def create(self, **kw):
        obj = FakeOwnedPokemon(**kw)
        self.data.append(obj)
        return obj
    def filter(self, **kw):
        res = []
        for obj in self.data:
            ok = True
            for k, v in kw.items():
                if getattr(obj, k, None) != v:
                    ok = False
                    break
            if ok:
                res.append(obj)
        return FakeQS(res)

class FakeOwnedPokemon:
    objects = FakeManager()
    def __init__(self, species, level=5, ai_trainer=None, is_template=False, current_hp=30):
        self.species = species
        self.level = level
        self.ai_trainer = ai_trainer
        self.is_template = is_template
        self.current_hp = current_hp
        self.unique_id = f"uid{len(FakeOwnedPokemon.objects.data)}"
        self.activemoveslot_set = FakeQS([types.SimpleNamespace(move=types.SimpleNamespace(name="tackle"), slot=1)])
        self.learned_moves = types.SimpleNamespace(all=lambda: [])
        self.ability = None
        self.ivs = [0, 0, 0, 0, 0, 0]
        self.evs = [0, 0, 0, 0, 0, 0]
        self.nature = "Hardy"

    @property
    def computed_level(self):
        return self.level


def load_utils():
    path = os.path.join(ROOT, "utils", "pokemon_utils.py")
    spec = importlib.util.spec_from_file_location("utils.pokemon_utils", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod

class DummyBattleData(types.SimpleNamespace):
    pass

# stub battledata
battledata = types.ModuleType("pokemon.battle.battledata")
class Move:
    def __init__(self, name):
        self.name = name
class Pokemon:
    def __init__(
        self,
        name,
        level=1,
        hp=10,
        max_hp=10,
        moves=None,
        ability=None,
        ivs=None,
        evs=None,
        nature="Hardy",
        model_id=None,
        species=None,
    ):
        self.name = name
        self.species = species or name
        self.level = level
        self.hp = hp
        self.max_hp = max_hp
        self.moves = moves or []
        self.ability = ability
        self.ivs = ivs or [0, 0, 0, 0, 0, 0]
        self.evs = evs or [0, 0, 0, 0, 0, 0]
        self.nature = nature
        self.model_id = model_id
battledata.Move = Move
battledata.Pokemon = Pokemon

def setup_module(module):
    module.prev_bd = sys.modules.get("pokemon.battle.battledata")
    module.prev_bi = sys.modules.get("pokemon.battle.battleinstance")
    module.prev_models = sys.modules.get("pokemon.models")
    sys.modules["pokemon.battle.battledata"] = battledata

    battleinstance = types.ModuleType("pokemon.battle.battleinstance")
    battleinstance._calc_stats_from_model = lambda p: {"hp": 30}
    battleinstance.create_battle_pokemon = lambda name, level, trainer=None, is_wild=False: Pokemon(name, level)
    module.battleinstance = battleinstance
    sys.modules["pokemon.battle.battleinstance"] = battleinstance

    models_mod = types.ModuleType("pokemon.models")
    models_mod.OwnedPokemon = FakeOwnedPokemon
    module.models_mod = models_mod
    sys.modules["pokemon.models"] = models_mod

    module.mod = load_utils()
    module.mod.clone_pokemon = lambda p, for_ai=True: p


def teardown_module(module):
    for name, old in [
        ("pokemon.battle.battledata", module.prev_bd),
        ("pokemon.battle.battleinstance", module.prev_bi),
        ("pokemon.models", module.prev_models),
    ]:
        if old is not None:
            sys.modules[name] = old
        else:
            sys.modules.pop(name, None)


def test_spawn_npc_pokemon_from_template():
    trainer = object()
    tmpl = FakeOwnedPokemon.objects.create(species="Pikachu", level=5, ai_trainer=trainer, is_template=True)
    p = mod.spawn_npc_pokemon(trainer)
    assert p.name == "Pikachu"
    assert p.model_id == tmpl.unique_id


def test_spawn_npc_pokemon_generated_fallback():
    trainer = object()
    p = mod.spawn_npc_pokemon(trainer)
    assert p.name == "Charmander"
