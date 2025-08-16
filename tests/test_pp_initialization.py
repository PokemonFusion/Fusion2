"""Tests for PP initialisation and moveset healing behaviour."""

import ast
import os
import sys
import textwrap
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def _load_heal_func():
    """Extract the ``heal`` method from the model for isolated testing."""
    models_path = os.path.join(ROOT, "pokemon", "models", "core.py")
    source = open(models_path).read()
    module = ast.parse(source)
    heal_code = None
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == "OwnedPokemon":
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef) and sub.name == "heal":
                    heal_code = ast.get_source_segment(source, sub)
                    break
    if heal_code is None:
        raise RuntimeError("heal method not found")
    ns = {}
    exec(textwrap.dedent(heal_code), ns)
    return ns["heal"]


heal_func = _load_heal_func()


def _load_apply_ms_func():
    """Extract ``apply_active_moveset`` for testing."""
    models_path = os.path.join(ROOT, "pokemon", "models", "core.py")
    source = open(models_path).read()
    module = ast.parse(source)
    apply_code = None
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == "OwnedPokemon":
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef) and sub.name == "apply_active_moveset":
                    apply_code = ast.get_source_segment(source, sub)
                    break
    if apply_code is None:
        raise RuntimeError("apply_active_moveset not found")
    ns = {}
    exec(textwrap.dedent(apply_code), ns)
    return ns["apply_active_moveset"]


apply_ms_func = _load_apply_ms_func()


def setup_modules():
    """Provide minimal stubs required for ``heal``."""
    orig_evennia = sys.modules.get("evennia")
    orig_helpers = sys.modules.get("helpers.pokemon_helpers")
    orig_dex = sys.modules.get("pokemon.dex")

    evennia = types.ModuleType("evennia")
    sys.modules["evennia"] = evennia

    helpers_mod = types.ModuleType("helpers.pokemon_helpers")
    helpers_mod.get_max_hp = lambda poke: 50
    sys.modules["helpers.pokemon_helpers"] = helpers_mod

    dex_mod = types.ModuleType("pokemon.dex")
    dex_mod.MOVEDEX = {}
    sys.modules["pokemon.dex"] = dex_mod

    return orig_evennia, orig_helpers, orig_dex


def restore_modules(orig_evennia, orig_helpers, orig_dex):
    if orig_evennia is not None:
        sys.modules["evennia"] = orig_evennia
    else:
        sys.modules.pop("evennia", None)

    if orig_helpers is not None:
        sys.modules["helpers.pokemon_helpers"] = orig_helpers
    else:
        sys.modules.pop("helpers.pokemon_helpers", None)

    if orig_dex is not None:
        sys.modules["pokemon.dex"] = orig_dex
    else:
        sys.modules.pop("pokemon.dex", None)


class SlotManager(list):
    def all(self):
        return self

    def bulk_update(self, objs, fields):
        pass


class FakeSlot:
    def __init__(self, move_name):
        self.move = types.SimpleNamespace(name=move_name)
        self.current_pp = None


class FakePokemon:
    heal = heal_func

    def __init__(self, move_name):
        self.current_hp = 0
        self.status = ""
        self.pp_boosts = []
        self.activemoveslot_set = SlotManager([FakeSlot(move_name)])

    def save(self):
        pass


def test_heal_populates_normalised_pp():
    orig_evennia, orig_helpers, orig_dex = setup_modules()
    try:
        sys.modules["pokemon.dex"].MOVEDEX["fireblast"] = {"pp": 5}
        mon = FakePokemon("Fire Blast")
        mon.heal()
        assert mon.activemoveslot_set[0].current_pp == 5
    finally:
        restore_modules(orig_evennia, orig_helpers, orig_dex)


def test_apply_active_moveset_invokes_heal(monkeypatch):
    mod = types.ModuleType("pokemon.services.move_management")
    called = {}

    def fake_apply(poke):
        called["done"] = True

    mod.apply_active_moveset = fake_apply
    services_pkg = types.ModuleType("pokemon.services")
    services_pkg.move_management = mod
    monkeypatch.setitem(sys.modules, "pokemon.services", services_pkg)
    monkeypatch.setitem(sys.modules, "pokemon.services.move_management", mod)

    class Poke:
        apply_active_moveset = apply_ms_func

        def __init__(self):
            self.healed = False

        def heal(self):
            self.healed = True

    p = Poke()
    p.apply_active_moveset()

    assert called.get("done") is True
    assert p.healed is True

