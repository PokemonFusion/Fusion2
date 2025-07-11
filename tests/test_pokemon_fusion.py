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
    def __init__(self, result, parent_a, parent_b):
        self.result = result
        self.parent_a = parent_a
        self.parent_b = parent_b

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
    a = DummyPK("a")
    b = DummyPK("b")
    result = DummyPK("c")
    fusion_mod.record_fusion(result, a, b)
    pa, pb = fusion_mod.get_fusion_parents(result)
    assert pa is a and pb is b


def teardown_module(module):
    if orig_models is not None:
        sys.modules["pokemon.models"] = orig_models
    else:
        sys.modules.pop("pokemon.models", None)
