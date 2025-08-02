import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_modules():
    """Load ability and item modules with real battle utils."""
    utils_path = os.path.join(ROOT, "pokemon", "battle", "utils.py")
    utils_spec = importlib.util.spec_from_file_location(
        "pokemon.battle.utils", utils_path
    )
    utils_mod = importlib.util.module_from_spec(utils_spec)
    utils_spec.loader.exec_module(utils_mod)

    pkg_battle = types.ModuleType("pokemon.battle")
    pkg_battle.__path__ = []
    pkg_battle.utils = utils_mod
    sys.modules["pokemon.battle.utils"] = utils_mod
    sys.modules["pokemon.battle"] = pkg_battle

    moves_path = os.path.join(ROOT, "pokemon", "dex", "functions", "moves_funcs.py")
    mv_spec = importlib.util.spec_from_file_location(
        "pokemon.dex.functions.moves_funcs", moves_path
    )
    moves_mod = importlib.util.module_from_spec(mv_spec)
    sys.modules[mv_spec.name] = moves_mod
    mv_spec.loader.exec_module(moves_mod)

    ab_path = os.path.join(ROOT, "pokemon", "dex", "functions", "abilities_funcs.py")
    ab_spec = importlib.util.spec_from_file_location(
        "pokemon.dex.functions.abilities_funcs", ab_path
    )
    ab_mod = importlib.util.module_from_spec(ab_spec)
    sys.modules[ab_spec.name] = ab_mod
    ab_spec.loader.exec_module(ab_mod)

    it_path = os.path.join(ROOT, "pokemon", "dex", "functions", "items_funcs.py")
    it_spec = importlib.util.spec_from_file_location(
        "pokemon.dex.functions.items_funcs", it_path
    )
    it_mod = importlib.util.module_from_spec(it_spec)
    sys.modules[it_spec.name] = it_mod
    it_spec.loader.exec_module(it_mod)

    modules = {
        "pokemon.battle": pkg_battle,
        "pokemon.battle.utils": utils_mod,
        "pokemon.dex.functions.moves_funcs": moves_mod,
        "pokemon.dex.functions.abilities_funcs": ab_mod,
        "pokemon.dex.functions.items_funcs": it_mod,
    }
    return ab_mod, it_mod, modules.keys()


def cleanup(mod_names):
    for name in mod_names:
        sys.modules.pop(name, None)


class DummyMove:
    def __init__(self, type_=None, category="Physical", flags=None):
        self.type = type_
        self.category = category
        self.flags = flags or {}


class DummyMon:
    def __init__(self, hp=100, max_hp=100):
        self.hp = hp
        self.max_hp = max_hp
        self.boosts = {
            "attack": 0,
            "defense": 0,
            "special_attack": 0,
            "special_defense": 0,
            "speed": 0,
            "accuracy": 0,
            "evasion": 0,
        }
        self.item = None
        self.abilityState = {}
        self.volatiles = {}
        self.tempvals = {}
        self.status = 0
        self.immune = None
        self.side = types.SimpleNamespace(conditions={})
        self._foes = []

    def foes(self):
        return self._foes

    def setStatus(self, status):
        self.status = status


def test_intimidate_lowers_attack():
    ab_mod, _, mods = load_modules()
    try:
        user = DummyMon()
        foe = DummyMon()
        user._foes = [foe]
        ab_mod.Intimidate().onStart(pokemon=user)
        assert foe.boosts["attack"] == -1
    finally:
        cleanup(mods)


def test_flash_fire_activation_and_boost():
    ab_mod, _, mods = load_modules()
    try:
        mon = DummyMon()
        move = DummyMove(type_="Fire")
        ff = ab_mod.Flashfire()
        ff.onTryHit(target=mon, source=DummyMon(), move=move)
        assert mon.abilityState.get("flashfire") is True
        assert mon.immune == "Flash Fire"
        assert ff.onModifyAtk(100, attacker=mon, defender=None, move=move) == 150
        assert ff.onModifySpA(100, attacker=mon, defender=None, move=move) == 150
        ff.onEnd(pokemon=mon)
        assert mon.abilityState.get("flashfire") is False
    finally:
        cleanup(mods)


def test_focus_sash_survival():
    _, it_mod, mods = load_modules()
    try:
        mon = DummyMon()
        mon.item = "Focussash"
        fs = it_mod.Focussash()
        dmg = fs.onDamage(200, target=mon, source=DummyMon(), effect=None)
        mon.hp -= dmg
        assert mon.hp == 1
        assert mon.item is None
    finally:
        cleanup(mods)


def test_life_orb_damage_and_recoil():
    _, it_mod, mods = load_modules()
    try:
        mon = DummyMon()
        move = DummyMove(category="Physical")
        lo = it_mod.Lifeorb()
        boosted = lo.onModifyDamage(100, source=mon, target=DummyMon(), move=move)
        assert boosted == 130
        lo.onAfterMoveSecondarySelf(source=mon, target=DummyMon(), move=move)
        assert mon.hp == 90
    finally:
        cleanup(mods)
