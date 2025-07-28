import os
import sys
import types
import importlib.util


def load_magnetrise():
    """Dynamically load the Magnetrise move with minimal stubs."""
    utils_stub = types.ModuleType("pokemon.battle.utils")
    utils_stub.apply_boost = lambda *a, **k: None
    utils_stub.get_modified_stat = lambda *_: 0

    pkg_battle = types.ModuleType("pokemon.battle")
    pkg_battle.__path__ = []
    pkg_battle.utils = utils_stub

    pkg_root = types.ModuleType("pokemon")
    pkg_root.__path__ = []
    pkg_root.battle = pkg_battle

    data_stub = types.ModuleType("pokemon.data")
    data_stub.__path__ = []
    data_stub.TYPE_CHART = {}

    sys.modules.update({
        "pokemon": pkg_root,
        "pokemon.battle": pkg_battle,
        "pokemon.battle.utils": utils_stub,
        "pokemon.data": data_stub,
    })

    path = os.path.join(os.path.dirname(__file__), "..", "pokemon", "dex", "functions", "moves_funcs.py")
    spec = importlib.util.spec_from_file_location("moves_funcs", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Magnetrise


def cleanup():
    """Remove stubbed modules from ``sys.modules``."""
    for name in [
        "pokemon",
        "pokemon.battle",
        "pokemon.battle.utils",
        "pokemon.data",
    ]:
        sys.modules.pop(name, None)


class DummyPokemon:
    """Simple Pokémon stub lacking a volatiles attribute."""
    pass


def test_magnetrise_ontry_without_volatiles():
    Magnetrise = load_magnetrise()
    move = Magnetrise()
    user = DummyPokemon()
    try:
        assert move.onTry(user) is True
    finally:
        cleanup()
