import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# stubs similar to other tests
utils_stub = types.ModuleType("pokemon.battle.utils")
utils_stub.apply_boost = lambda *args, **kwargs: None
pkg_battle = types.ModuleType("pokemon.battle")
pkg_battle.__path__ = []
pkg_battle.utils = utils_stub
sys.modules["pokemon.battle"] = pkg_battle
sys.modules["pokemon.battle.utils"] = utils_stub

ent_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", ent_path)
ent_mod = importlib.util.module_from_spec(ent_spec)
sys.modules[ent_spec.name] = ent_mod
ent_spec.loader.exec_module(ent_mod)
Stats = ent_mod.Stats

pokemon_dex = types.ModuleType("pokemon.dex")
pokemon_dex.__path__ = []
pokemon_dex.entities = ent_mod
pokemon_dex.MOVEDEX = {}
pokemon_dex.Move = ent_mod.Move
pokemon_dex.Pokemon = ent_mod.Pokemon
sys.modules["pokemon.dex"] = pokemon_dex

# basic pokemon container
bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
bd_mod = importlib.util.module_from_spec(bd_spec)
sys.modules[bd_spec.name] = bd_mod
bd_spec.loader.exec_module(bd_mod)
Pokemon = bd_mod.Pokemon

moves_path = os.path.join(ROOT, "pokemon", "dex", "functions", "moves_funcs.py")
mv_spec = importlib.util.spec_from_file_location("pokemon.dex.functions.moves_funcs", moves_path)
mv_mod = importlib.util.module_from_spec(mv_spec)
sys.modules[mv_spec.name] = mv_mod
mv_spec.loader.exec_module(mv_mod)

# helper to create pokemon with stats
base = Stats(
	hp=100,
	attack=50,
	defense=50,
	special_attack=50,
	special_defense=50,
	speed=50,
)


def make_poke(**kwargs):
	p = Pokemon("Poke")
	p.base_stats = base
	p.num = 1
	p.types = ["Normal"]
	for k, v in kwargs.items():
		setattr(p, k, v)
	return p


MOVES = [
	(
		mv_mod.Electroball().basePowerCallback,
		make_poke(
			base_stats=Stats(
				hp=100,
				attack=50,
				defense=50,
				special_attack=50,
				special_defense=50,
				speed=40,
			)
		),
		make_poke(
			base_stats=Stats(
				hp=100,
				attack=50,
				defense=50,
				special_attack=50,
				special_defense=50,
				speed=100,
			)
		),
		40,
	),
	(mv_mod.Eruption().basePowerCallback, make_poke(hp=50, max_hp=100), make_poke(), 75.0, {"power": 150}),
	(mv_mod.Firepledge().basePowerCallback, make_poke(), make_poke(), 150, {"sourceEffect": "waterpledge"}),
	(mv_mod.Heatcrash().basePowerCallback, make_poke(weightkg=100), make_poke(weightkg=10), 120),
	(mv_mod.Heavyslam().basePowerCallback, make_poke(weightkg=100), make_poke(weightkg=10), 120),
	(mv_mod.Hex().basePowerCallback, make_poke(), make_poke(status="brn"), 130, {"power": 65}),
	(mv_mod.Iceball().basePowerCallback, make_poke(defensecurl=True), make_poke(), 60, {"power": 30}),
	(mv_mod.Infernalparade().basePowerCallback, make_poke(), make_poke(status="brn"), 120, {"power": 60}),
	(
		mv_mod.Lastrespects().basePowerCallback,
		make_poke(party=[make_poke(hp=0), make_poke(hp=0), make_poke()]),
		make_poke(),
		150,
	),
	(mv_mod.Lowkick().basePowerCallback, make_poke(), make_poke(weightkg=120), 100),
	(mv_mod.Payback().basePowerCallback, make_poke(), make_poke(tempvals={"moved": True}), 100, {"power": 50}),
	(mv_mod.Pikapapow().basePowerCallback, make_poke(happiness=255), make_poke(), 102),
	(mv_mod.Powertrip().basePowerCallback, make_poke(boosts={"atk": 2}), make_poke(), 60, {"power": 20}),
	(mv_mod.Punishment().basePowerCallback, make_poke(), make_poke(boosts={"spa": 4}), 140),
	(mv_mod.Pursuit().basePowerCallback, make_poke(), make_poke(tempvals={"switching": True}), 80, {"power": 40}),
	(mv_mod.Ragefist().basePowerCallback, make_poke(times_attacked=3), make_poke(), 200),
	(mv_mod.Return().basePowerCallback, make_poke(happiness=255), make_poke(), 102),
	(mv_mod.Revenge().basePowerCallback, make_poke(tempvals={"took_damage": True}), make_poke(), 120, {"power": 60}),
	(mv_mod.Reversal().basePowerCallback, make_poke(hp=10, max_hp=100), make_poke(), 150),
	(
		mv_mod.Risingvoltage().basePowerCallback,
		make_poke(terrain="electricterrain"),
		make_poke(grounded=True),
		140,
		{"power": 70},
	),
	(mv_mod.Rollout().basePowerCallback, make_poke(tempvals={"rollout_hits": 2}), make_poke(), 120, {"power": 30}),
	(mv_mod.Round().basePowerCallback, make_poke(), make_poke(), 120, {"power": 60, "sourceEffect": "round"}),
	(mv_mod.Smellingsalts().basePowerCallback, make_poke(), make_poke(status="par"), 140, {"power": 70}),
	(mv_mod.Spitup().basePowerCallback, make_poke(stockpile_layers=3), make_poke(), 300),
	(mv_mod.Stompingtantrum().basePowerCallback, make_poke(move_failed=True), make_poke(), 150, {"power": 75}),
	(mv_mod.Storedpower().basePowerCallback, make_poke(boosts={"atk": 2, "def": 1}), make_poke(), 80, {"power": 20}),
	(mv_mod.Temperflare().basePowerCallback, make_poke(move_failed=True), make_poke(), 150, {"power": 75}),
	(mv_mod.Terablast().basePowerCallback, make_poke(terastallized="Stellar"), make_poke(), 100, {"power": 80}),
	(mv_mod.Tripleaxel().basePowerCallback, make_poke(), make_poke(), 60, {"hit": 3}),
	(mv_mod.Triplekick().basePowerCallback, make_poke(), make_poke(), 20, {"hit": 2}),
	(mv_mod.Trumpcard().basePowerCallback, make_poke(), make_poke(), 80, {"pp": 1}),
	(mv_mod.Veeveevolley().basePowerCallback, make_poke(happiness=255), make_poke(), 102),
	(mv_mod.Wakeupslap().basePowerCallback, make_poke(), make_poke(status="slp"), 140, {"power": 70}),
	(
		mv_mod.Waterpledge().basePowerCallback,
		make_poke(),
		make_poke(),
		150,
		{"power": 80, "sourceEffect": "firepledge"},
	),
	(
		mv_mod.Watershuriken().basePowerCallback,
		make_poke(species="Greninja-Ash", ability="battlebond"),
		make_poke(),
		20,
		{"power": 15},
	),
	(mv_mod.Waterspout().basePowerCallback, make_poke(hp=50, max_hp=100), make_poke(), 75.0, {"power": 150}),
	(mv_mod.Wringout().basePowerCallback, make_poke(), make_poke(hp=50, max_hp=100), 60),
]


def test_base_power_callbacks():
	for entry in MOVES:
		if len(entry) == 5:
			cb, user, target, expected, extra = entry
		else:
			cb, user, target, expected = entry
			extra = {}
		move = types.SimpleNamespace(
			power=extra.get("power", expected),
			pp=extra.get("pp"),
			hit=extra.get("hit"),
			sourceEffect=extra.get("sourceEffect"),
		)
		res = cb(user, target, move)
		assert int(res) == int(expected), f"{cb.__qualname__} {res} != {expected}"


# cleanup

del sys.modules["pokemon.dex"]
