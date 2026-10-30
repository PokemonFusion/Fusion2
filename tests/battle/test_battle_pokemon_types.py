import importlib
import sys
import types
from unittest import mock

from pokemon.battle import damage as damage_mod
from pokemon.battle.battledata import Pokemon
from utils.safe_import import safe_import


def test_basic_pokemon_has_types():
	mon = Pokemon("Bulbasaur", level=5)
	assert mon.types == ["Grass", "Poison"]


def test_from_dict_populates_types():
        mon = Pokemon.from_dict({"name": "Charmander", "level": 5})
        assert mon.types == ["Fire"]


def test_types_and_stab_from_packaged_pokedex_when_module_missing():
        module_name = "pokemon.battle.battledata"
        for mod in [name for name in list(sys.modules) if name.startswith("pokemon.dex")]:
                sys.modules.pop(mod)
        sys.modules.pop(module_name, None)

        original_safe_import = safe_import

        def _safe_import_with_missing_dex(name: str):
                if name == "pokemon.dex":
                        raise ModuleNotFoundError
                return original_safe_import(name)

        with mock.patch("utils.safe_import.safe_import", side_effect=_safe_import_with_missing_dex):
                        battledata = importlib.import_module(module_name)
                        charmander = battledata.Pokemon("Charmander", level=50)
                        bulbasaur = battledata.Pokemon("Bulbasaur", level=50)

                        assert charmander.types == ["Fire"]
                        assert bulbasaur.types == ["Grass", "Poison"]

                        move = types.SimpleNamespace(type="Fire")
                        assert damage_mod.stab_multiplier(charmander, move) == 1.5

                        chart = damage_mod.TYPE_CHART.setdefault("Fire", {})
                        prior = chart.get("Grass")
                        chart["Grass"] = 1
                        try:
                                assert damage_mod.type_effectiveness(bulbasaur, move) == 2.0
                        finally:
                                if prior is None:
                                        chart.pop("Grass")
                                else:
                                        chart["Grass"] = prior

        sys.modules.pop(module_name, None)
        for mod in [name for name in list(sys.modules) if name.startswith("pokemon.dex")]:
                sys.modules.pop(mod)
        importlib.import_module("pokemon.dex")
        importlib.import_module(module_name)
