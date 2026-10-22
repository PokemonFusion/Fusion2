import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
	path = os.path.join(ROOT, "commands", "player", "cmd_inventory.py")
	spec = importlib.util.spec_from_file_location("commands.player.cmd_inventory", path)
	mod = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = mod
	spec.loader.exec_module(mod)
	return mod


class FakeMove:
	objects = types.SimpleNamespace(filter=lambda **kw: [FakeMove("tackle")])

	def __init__(self, name):
		self.name = name


class FakePokemon:
	def __init__(self):
		self.name = "Pika"
		self.species = "Pikachu"
		self.level = 5
		self.total_exp = 125
		self.saved = False


class DummyTrainer:
	def __init__(self, counter, has_item=True):
		self.counter = counter
		self.has_item_result = has_item

	def has_item(self, name, amount=1):
		return self.has_item_result

	def remove_item(self, name):
		self.counter[0] += 1
		return True


class DummyCaller:
	def __init__(self, poke, counter, has_item=True):
		self.poke = poke
		self.msgs = []
		self.ndb = types.SimpleNamespace()
		self.trainer = DummyTrainer(counter, has_item=has_item)

	def get_active_pokemon_by_slot(self, slot):
		return self.poke if slot == 1 else None

	def msg(self, text):
		self.msgs.append(text)


def setup_modules(remove_counter):
	orig_evennia = sys.modules.get("evennia")
	fake_evennia = types.ModuleType("evennia")
	fake_evennia.Command = type("Command", (), {})
	sys.modules["evennia"] = fake_evennia

	orig_core = sys.modules.get("pokemon.models.core")
	orig_moves = sys.modules.get("pokemon.models.moves")
	orig_trainer = sys.modules.get("pokemon.models.trainer")
	fake_core = types.ModuleType("pokemon.models.core")
	fake_core.OwnedPokemon = FakePokemon
	fake_moves = types.ModuleType("pokemon.models.moves")
	fake_moves.Move = FakeMove
	fake_trainer = types.ModuleType("pokemon.models.trainer")
	fake_trainer.InventoryEntry = type("InventoryEntry", (), {})
	sys.modules["pokemon.models.core"] = fake_core
	sys.modules["pokemon.models.moves"] = fake_moves
	sys.modules["pokemon.models.trainer"] = fake_trainer

	orig_inv = sys.modules.get("utils.inventory")
	fake_inv = types.ModuleType("utils.inventory")
	fake_inv.add_item = lambda *a, **k: None

	def rem(owner, name):
		remove_counter[0] += 1
		return True

	fake_inv.remove_item = rem
	sys.modules["utils.inventory"] = fake_inv

	orig_dex = sys.modules.get("pokemon.dex")
	fake_dex = types.ModuleType("pokemon.dex")
	fake_dex.ITEMDEX = {"ppup": {}, "ppmax": {}}
	fake_dex.MOVEDEX = {"tackle": {"pp": 10}}
	sys.modules["pokemon.dex"] = fake_dex

	return orig_evennia, orig_core, orig_moves, orig_trainer, orig_inv, orig_dex


def restore_modules(orig_evennia, orig_core, orig_moves, orig_trainer, orig_inv, orig_dex):
	if orig_evennia is not None:
		sys.modules["evennia"] = orig_evennia
	else:
		sys.modules.pop("evennia", None)
	if orig_core is not None:
		sys.modules["pokemon.models.core"] = orig_core
	else:
		sys.modules.pop("pokemon.models.core", None)
	if orig_moves is not None:
		sys.modules["pokemon.models.moves"] = orig_moves
	else:
		sys.modules.pop("pokemon.models.moves", None)
	if orig_trainer is not None:
		sys.modules["pokemon.models.trainer"] = orig_trainer
	else:
		sys.modules.pop("pokemon.models.trainer", None)
	if orig_inv is not None:
		sys.modules["utils.inventory"] = orig_inv
	else:
		sys.modules.pop("utils.inventory", None)
	if orig_dex is not None:
		sys.modules["pokemon.dex"] = orig_dex
	else:
		sys.modules.pop("pokemon.dex", None)


def _pp_boundary(monkeypatch, error=None):
	"""Only test command routing here; real PP/SQL effects have PG coverage."""
	from pokemon.services.field_pp import FieldPPCapacityUse

	calls = []

	def use(service, item, target, *, move=None):
		"""Capture the target handoff and simulate a prompt at the boundary."""
		calls.append((item, target, move))
		service.caller.ndb.pending_pp_item = {"item": item, "pokemon_id": "stable-id"}
		service.caller.msg("Choose a move")

	def confirm(service, pending, selection):
		"""Capture confirmation routing without implementing any PP math."""
		calls.append((pending["item"], pending["pokemon_id"], selection))
		if error:
			raise ValueError(error)
		return True

	monkeypatch.setattr(FieldPPCapacityUse, "use", use)
	monkeypatch.setattr(FieldPPCapacityUse, "confirm", confirm)
	monkeypatch.setattr(FieldPPCapacityUse, "notify_success", lambda *args: None)
	return calls


def test_ppup_flow(monkeypatch):
	"""Delegate initial target and exact confirmation text to the field service."""
	remove_counter = [0]
	origs = setup_modules(remove_counter)
	cmd_mod = load_cmd_module()
	restore_modules(*origs)
	calls = _pp_boundary(monkeypatch)
	caller = DummyCaller(FakePokemon(), remove_counter)
	cmd = cmd_mod.CmdUseItem()
	cmd.caller, cmd.args = caller, "ppup=1"
	cmd.func()
	cmd.args = "3"
	cmd.func()
	assert calls == [("ppup", "1", None), ("ppup", "stable-id", "3")]
	assert remove_counter[0] == 0


def test_ppup_compatibility_target_first_flow(monkeypatch):
	"""The legacy target-first spelling reaches the same safe route."""
	remove_counter = [0]
	origs = setup_modules(remove_counter)
	cmd_mod = load_cmd_module()
	restore_modules(*origs)
	calls = _pp_boundary(monkeypatch)
	caller = DummyCaller(FakePokemon(), remove_counter)
	cmd = cmd_mod.CmdUseItem()
	cmd.caller, cmd.args = caller, "1=ppup"
	cmd.func()
	assert calls == [("ppup", "1", None)]


def test_ppup_at_max(monkeypatch):
	"""A service rejection is reported without a command-side debit or effect."""
	remove_counter = [0]
	origs = setup_modules(remove_counter)
	cmd_mod = load_cmd_module()
	restore_modules(*origs)
	_pp_boundary(monkeypatch, "That move already has maximum PP.")
	caller = DummyCaller(FakePokemon(), remove_counter)
	cmd = cmd_mod.CmdUseItem()
	cmd.caller, cmd.args = caller, "PP Up=1"
	cmd.func()
	cmd.args = "1"
	cmd.func()
	assert remove_counter[0] == 0
	assert "already has maximum" in caller.msgs[-1]


def _rare_candy_boundary(monkeypatch, error=None):
	"""Capture command delegation; real effects belong to PostgreSQL coverage."""
	from pokemon.services.field_progression import FieldRareCandyUse

	calls = []

	def use(service, item, target, *, move=None):
		"""Represent the shared service outcome without faking its effect."""
		calls.append((item, target, move))
		if error:
			raise ValueError(error)
		return True

	monkeypatch.setattr(FieldRareCandyUse, "use", use)
	monkeypatch.setattr(FieldRareCandyUse, "success_message", lambda *args: "Pika grew to level 6.")
	monkeypatch.setattr(FieldRareCandyUse, "notify_success", lambda service, *args: service.caller.msg("Pika grew to level 6."))
	return calls


def test_rare_candy_delegates_name_to_field_boundary(monkeypatch):
	remove_counter = [0]
	origs = setup_modules(remove_counter)
	cmd_mod = load_cmd_module()
	restore_modules(*origs)
	calls = _rare_candy_boundary(monkeypatch)

	poke = FakePokemon()
	caller = DummyCaller(poke, remove_counter)

	cmd = cmd_mod.CmdUseItem()
	cmd.caller = caller
	cmd.args = "Rare Candy=Pikachu"
	cmd.func()

	assert calls == [("rarecandy", "Pikachu", None)]
	assert remove_counter[0] == 0
	assert any("grew to level 6" in msg for msg in caller.msgs)


def test_rare_candy_compatibility_target_first_flow(monkeypatch):
	remove_counter = [0]
	origs = setup_modules(remove_counter)
	cmd_mod = load_cmd_module()
	restore_modules(*origs)
	calls = _rare_candy_boundary(monkeypatch)

	poke = FakePokemon()
	caller = DummyCaller(poke, remove_counter)

	cmd = cmd_mod.CmdUseItem()
	cmd.caller = caller
	cmd.args = "1=Rare Candy"
	cmd.func()

	assert calls == [("rarecandy", "1", None)]
	assert remove_counter[0] == 0
	assert any("grew to level 6" in msg for msg in caller.msgs)


def test_rare_candy_requires_target_slot():
	remove_counter = [0]
	origs = setup_modules(remove_counter)
	cmd_mod = load_cmd_module()
	restore_modules(*origs)

	caller = DummyCaller(FakePokemon(), remove_counter)
	cmd = cmd_mod.CmdUseItem()
	cmd.caller = caller
	cmd.args = "Rare Candy"
	cmd.func()

	assert remove_counter[0] == 0
	assert "Usage: +use Rare Candy=<party slot" in caller.msgs[-1]


def test_rare_candy_does_not_apply_without_inventory(monkeypatch):
	remove_counter = [0]
	origs = setup_modules(remove_counter)
	cmd_mod = load_cmd_module()
	restore_modules(*origs)
	_rare_candy_boundary(monkeypatch, "You don't have any of that item to use.")

	poke = FakePokemon()
	caller = DummyCaller(poke, remove_counter, has_item=False)
	cmd = cmd_mod.CmdUseItem()
	cmd.caller = caller
	cmd.args = "Rare Candy=Pikachu"
	cmd.func()

	assert remove_counter[0] == 0
	assert poke.level == 5
	assert caller.msgs[-1] == "You don't have any of that item to use."


def test_unimplemented_field_item_does_not_consume_inventory():
	remove_counter = [0]
	origs = setup_modules(remove_counter)
	cmd_mod = load_cmd_module()
	restore_modules(*origs)

	caller = DummyCaller(FakePokemon(), remove_counter)
	cmd = cmd_mod.CmdUseItem()
	cmd.caller = caller
	cmd.args = "Leftovers=Pikachu"
	cmd.func()

	assert remove_counter[0] == 0
	assert "Leftovers is not usable outside battle yet." in caller.msgs[-1]
	assert "+heal at a Pokemon Center" in caller.msgs[-1]
	assert "+item <item> during battle" in caller.msgs[-1]


def test_pp_up_without_target_explains_supported_usage():
	"""A supported field item needs a target, rather than claiming it is unavailable."""
	remove_counter = [0]
	origs = setup_modules(remove_counter)
	cmd_mod = load_cmd_module()
	restore_modules(*origs)
	caller = DummyCaller(FakePokemon(), remove_counter)
	cmd = cmd_mod.CmdUseItem()
	cmd.caller, cmd.args = caller, "PP Up"
	cmd.func()
	assert remove_counter[0] == 0
	assert caller.msgs[-1] == "Usage: +use PP Up=<party slot or Pokemon name>"


def test_use_item_invalid_item_name_fails_before_target_lookup():
	remove_counter = [0]
	origs = setup_modules(remove_counter)
	cmd_mod = load_cmd_module()
	restore_modules(*origs)

	caller = DummyCaller(FakePokemon(), remove_counter)
	cmd = cmd_mod.CmdUseItem()
	cmd.caller = caller
	cmd.args = "Not An Item=Pikachu"
	cmd.func()

	assert remove_counter[0] == 0
	assert "No such item 'Not An Item' exists." in caller.msgs[-1]


def test_use_item_invalid_target_fails_before_item_removal(monkeypatch):
	remove_counter = [0]
	origs = setup_modules(remove_counter)
	cmd_mod = load_cmd_module()
	restore_modules(*origs)
	_rare_candy_boundary(monkeypatch, "Choose an owned party Pokemon by slot, name or full ID, or your current Fusion.")

	caller = DummyCaller(FakePokemon(), remove_counter)
	cmd = cmd_mod.CmdUseItem()
	cmd.caller = caller
	cmd.args = "Rare Candy=Missingno"
	cmd.func()

	assert remove_counter[0] == 0
	assert "Choose an owned party Pokemon" in caller.msgs[-1]


def test_use_item_ambiguous_two_item_names_fails():
	remove_counter = [0]
	origs = setup_modules(remove_counter)
	cmd_mod = load_cmd_module()
	restore_modules(*origs)

	caller = DummyCaller(FakePokemon(), remove_counter)
	cmd = cmd_mod.CmdUseItem()
	cmd.caller = caller
	cmd.args = "Potion=Rare Candy"
	cmd.func()

	assert remove_counter[0] == 0
	assert "Ambiguous item use" in caller.msgs[-1]
	assert "use its party slot" in caller.msgs[-1]
