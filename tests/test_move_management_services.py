import sys
import types
import ast
import os
import textwrap


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _load_heal_func():
	"""Extract ``OwnedPokemon.heal`` for isolated behavior tests."""

	models_path = os.path.join(ROOT, "pokemon", "models", "core.py")
	source = open(models_path).read()
	module = ast.parse(source)
	for node in module.body:
		if isinstance(node, ast.ClassDef) and node.name == "OwnedPokemon":
			for sub in node.body:
				if isinstance(sub, ast.FunctionDef) and sub.name == "heal":
					ns = {}
					exec(textwrap.dedent(ast.get_source_segment(source, sub)), ns)
					return ns["heal"]
	raise RuntimeError("heal method not found")


heal_func = _load_heal_func()


def test_learn_level_up_moves_invokes_learn_move(monkeypatch):
	calls = []

	ml_mod = types.ModuleType("pokemon.utils.move_learning")

	def fake_get_moves(poke):
		return ["tackle", "growl"], {}

	def fake_learn_move(poke, name, caller=None, prompt=False):
		calls.append((poke, name, caller, prompt))

	ml_mod.get_learnable_levelup_moves = fake_get_moves
	ml_mod.learn_move = fake_learn_move
	monkeypatch.setitem(sys.modules, "pokemon.utils.move_learning", ml_mod)

	from pokemon.services.move_management import learn_level_up_moves

	poke = object()
	learn_level_up_moves(poke, caller="ash", prompt=True)

	assert calls == [(poke, "tackle", "ash", True), (poke, "growl", "ash", True)]


def test_apply_active_moveset_populates_slots(monkeypatch):
	dex_mod = types.ModuleType("pokemon.dex")
	dex_mod.MOVEDEX = {"tackle": {"pp": 35}, "growl": {"pp": 40}}
	monkeypatch.setitem(sys.modules, "pokemon.dex", dex_mod)
	engine_mod = types.ModuleType("pokemon.battle.engine")
	engine_mod._normalize_key = lambda v: str(v).lower().replace(" ", "")
	monkeypatch.setitem(sys.modules, "pokemon.battle.engine", engine_mod)

	tackle = types.SimpleNamespace(name="tackle")
	growl = types.SimpleNamespace(name="growl")

	class Slot:
		def __init__(self, move, slot):
			self.move = move
			self.slot = slot

	class SlotManager(list):
		def order_by(self, field):
			return sorted(self, key=lambda s: s.slot)

	class Moveset:
		def __init__(self):
			self.slots = SlotManager()

	class Boost:
		def __init__(self, move, bonus_pp):
			self.move = move
			self.bonus_pp = bonus_pp

	class BoostManager(list):
		def all(self):
			return self

	class ActiveSlotManager(list):
		def all(self):
			return self

		def delete(self):
			self.clear()

		def create(self, move, slot, current_pp=None):
			obj = types.SimpleNamespace(move=move, slot=slot, current_pp=current_pp)
			self.append(obj)
			return obj

	ms = Moveset()
	ms.slots.append(Slot(tackle, 1))
	ms.slots.append(Slot(growl, 2))

	pokemon = types.SimpleNamespace(
		active_moveset=ms,
		activemoveslot_set=ActiveSlotManager(),
		pp_boosts=BoostManager([Boost(tackle, 5)]),
		save=lambda: None,
	)

	from pokemon.services.move_management import apply_active_moveset

	apply_active_moveset(pokemon)

	assert [(s.move.name, s.slot, s.current_pp) for s in pokemon.activemoveslot_set] == [
		("tackle", 1, 40),
		("growl", 2, 40),
	]


def test_apply_active_moveset_handles_missing_slots_all(monkeypatch):
	dex_mod = types.ModuleType("pokemon.dex")
	dex_mod.MOVEDEX = {"tackle": {"pp": 35}}
	monkeypatch.setitem(sys.modules, "pokemon.dex", dex_mod)
	engine_mod = types.ModuleType("pokemon.battle.engine")
	engine_mod._normalize_key = lambda v: str(v).lower().replace(" ", "")
	monkeypatch.setitem(sys.modules, "pokemon.battle.engine", engine_mod)

	class Slot:
		def __init__(self, move, slot):
			self.move = move
			self.slot = slot

	class SlotsWithoutAll(list):
		def order_by(self, field):
			return sorted(self, key=lambda s: s.slot)

	class Moveset:
		def __init__(self):
			self.slots = SlotsWithoutAll()

	class ActiveSlotManager(list):
		def all(self):
			return self

		def delete(self):
			self.clear()

		def create(self, move, slot, current_pp=None):
			self.append(types.SimpleNamespace(move=move, slot=slot, current_pp=current_pp))

	ms = Moveset()
	ms.slots.append(Slot(types.SimpleNamespace(name="tackle"), 2))
	ms.slots.append(Slot(types.SimpleNamespace(name="tackle"), 1))
	pokemon = types.SimpleNamespace(active_moveset=ms, activemoveslot_set=ActiveSlotManager(), save=lambda: None)

	from pokemon.services.move_management import apply_active_moveset

	apply_active_moveset(pokemon)

	assert [slot.slot for slot in pokemon.activemoveslot_set] == [1, 2]


def test_heal_and_apply_active_moveset_match_pp_results(monkeypatch):
	dex_mod = types.ModuleType("pokemon.dex")
	dex_mod.MOVEDEX = {"fireblast": {"pp": 5}, "growl": {"pp": 40}}
	monkeypatch.setitem(sys.modules, "pokemon.dex", dex_mod)

	helpers_mod = types.ModuleType("pokemon.helpers.pokemon_helpers")
	helpers_mod.get_max_hp = lambda _poke: 88
	monkeypatch.setitem(sys.modules, "pokemon.helpers.pokemon_helpers", helpers_mod)

	fire_blast = types.SimpleNamespace(name="Fire Blast")
	growl = types.SimpleNamespace(name="Growl")

	class Slot:
		def __init__(self, move, slot):
			self.move = move
			self.slot = slot

	class SlotManager(list):
		def all(self):
			return self

		def order_by(self, field):
			return sorted(self, key=lambda s: s.slot)

	class Moveset:
		def __init__(self):
			self.slots = SlotManager([Slot(fire_blast, 1), Slot(growl, 2)])

	class Boost:
		def __init__(self, move, bonus_pp):
			self.move = move
			self.bonus_pp = bonus_pp

	class BoostManager(list):
		def all(self):
			return self

	class ActiveSlotManager(list):
		def all(self):
			return self

		def delete(self):
			self.clear()

		def create(self, move, slot, current_pp=None):
			obj = types.SimpleNamespace(move=move, slot=slot, current_pp=current_pp, save=lambda: None)
			self.append(obj)
			return obj

		def bulk_update(self, objs, fields):
			return None

	apply_target = types.SimpleNamespace(
		active_moveset=Moveset(),
		activemoveslot_set=ActiveSlotManager(),
		pp_boosts=BoostManager([Boost(types.SimpleNamespace(name="fire-blast"), 3)]),
		save=lambda: None,
	)

	from pokemon.services.move_management import apply_active_moveset

	apply_active_moveset(apply_target)
	pp_from_apply = [s.current_pp for s in apply_target.activemoveslot_set]

	heal_target = types.SimpleNamespace(
		current_hp=1,
		status="poisoned",
		activemoveslot_set=ActiveSlotManager(
			[
				types.SimpleNamespace(move=fire_blast, slot=1, current_pp=0, save=lambda: None),
				types.SimpleNamespace(move=growl, slot=2, current_pp=0, save=lambda: None),
			]
		),
		pp_boosts=BoostManager([Boost(types.SimpleNamespace(name="fire-blast"), 3)]),
		save=lambda: None,
	)
	heal_func(heal_target)

	assert [s.current_pp for s in heal_target.activemoveslot_set] == pp_from_apply == [8, 40]