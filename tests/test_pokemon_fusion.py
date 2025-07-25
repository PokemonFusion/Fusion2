import types
import sys
import importlib

# Set up fake models
class FakeManager:
    def __init__(self):
        self.store = {}
        self.counter = 1
    def create(self, **kwargs):
        obj = FakePokemonFusion(**kwargs)
        self.store[obj.result.unique_id] = obj
        return obj
    def get_or_create(self, defaults=None, **kwargs):
        trainer = kwargs.get("trainer")
        pokemon = kwargs.get("pokemon")
        permanent = (defaults or {}).get("permanent", False)
        for obj in self.store.values():
            if obj.trainer is trainer and obj.pokemon is pokemon:
                return obj, False
        data = defaults or {}
        obj = FakePokemonFusion(result=data.get("result"), trainer=trainer, pokemon=pokemon, permanent=permanent)
        self.store[obj.result.unique_id] = obj
        return obj, True
    def filter(self, **kwargs):
        result = kwargs.get("result")
        key = getattr(result, "unique_id", None)
        items = [v for v in self.store.values() if v.result.unique_id == key] if key else list(self.store.values())
        class _QS(list):
            def first(self_inner):
                return self_inner[0] if self_inner else None
        return _QS(items)

class FakePokemonFusion:
    objects = FakeManager()

    def __init__(self, result, trainer, pokemon, permanent=False):
        self.result = result
        self.trainer = trainer
        self.pokemon = pokemon
        self.permanent = permanent

orig_models = sys.modules.get("pokemon.models")
models_mod = types.ModuleType("pokemon.models")
if orig_models:
    for attr in dir(orig_models):
        setattr(models_mod, attr, getattr(orig_models, attr))
models_mod.PokemonFusion = FakePokemonFusion
sys.modules["pokemon.models"] = models_mod

fusion_mod = importlib.import_module("utils.fusion")

class DummyPK:
    def __init__(self, uid):
        self.unique_id = uid


def test_record_and_get_parents():
    FakePokemonFusion.objects.store.clear()
    trainer = DummyPK("t")
    pokemon = DummyPK("p")
    result = DummyPK("c")
    fusion_mod.record_fusion(result, trainer, pokemon)
    pa, pb = fusion_mod.get_fusion_parents(result)
    assert pa is trainer and pb is pokemon


def test_no_duplicate_when_reused():
    FakePokemonFusion.objects.store.clear()
    trainer = DummyPK("t")
    pokemon = DummyPK("p")
    result1 = DummyPK("c")
    fusion_mod.record_fusion(result1, trainer, pokemon)
    result2 = DummyPK("d")
    fusion_mod.record_fusion(result2, trainer, pokemon)
    entries = list(FakePokemonFusion.objects.store.values())
    assert len(entries) == 1
    entry = entries[0]
    assert entry.trainer is trainer and entry.pokemon is pokemon
    assert entry.result is result1


def test_permanent_flag():
    FakePokemonFusion.objects.store.clear()
    trainer = DummyPK("t")
    pokemon = DummyPK("p")
    result = DummyPK("c")
    fusion_mod.record_fusion(result, trainer, pokemon, permanent=True)
    entry = list(FakePokemonFusion.objects.store.values())[0]
    assert entry.permanent is True


def teardown_module(module):
    if orig_models is not None:
        sys.modules["pokemon.models"] = orig_models
    else:
        sys.modules.pop("pokemon.models", None)
