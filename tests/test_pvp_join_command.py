import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
	path = os.path.join(ROOT, "commands", "player", "cmd_pvp.py")
	spec = importlib.util.spec_from_file_location("commands.player.cmd_pvp", path)
	mod = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = mod
	spec.loader.exec_module(mod)
	return mod


def test_pvpjoin_incorrect_password():
	orig_evennia = sys.modules.get("evennia")
	fake_evennia = types.ModuleType("evennia")
	fake_evennia.Command = type("Command", (), {})
	utils_mod = types.ModuleType("evennia.utils")
	utils_utils = types.ModuleType("evennia.utils.utils")
	utils_utils.inherits_from = lambda obj, parent: isinstance(obj, parent)
	utils_mod.utils = utils_utils
	fake_evennia.utils = utils_mod
	sys.modules["evennia"] = fake_evennia
	sys.modules["evennia.utils"] = utils_mod
	sys.modules["evennia.utils.utils"] = utils_utils

	cmd_mod = load_cmd_module()

	class DummyCaller:
		def __init__(self):
			self.msgs = []
			self.location = object()
			self.id = 2
			self.key = "Bob"

		def msg(self, text):
			self.msgs.append(text)

	req = types.SimpleNamespace(
		host_key="Alice",
		password="secret",
		opponent_id=None,
		is_joinable=lambda: True,
		get_host=lambda: None,
	)

	def fake_find_request(location, host_name):
		return req

	orig_find = cmd_mod.find_request
	cmd_mod.find_request = fake_find_request

	cmd = cmd_mod.CmdPvpJoin()
	cmd.caller = DummyCaller()
	cmd.args = "Alice wrong"
	cmd.func()

	if orig_evennia is not None:
		sys.modules["evennia"] = orig_evennia
	else:
		sys.modules.pop("evennia", None)
	sys.modules.pop("evennia.utils", None)
	sys.modules.pop("evennia.utils.utils", None)
	cmd_mod.find_request = orig_find

	assert cmd.caller.msgs and "incorrect" in cmd.caller.msgs[-1].lower()


def test_pvpjoin_notifies_host():
	orig_evennia = sys.modules.get("evennia")
	fake_evennia = types.ModuleType("evennia")
	fake_evennia.Command = type("Command", (), {})
	utils_mod = types.ModuleType("evennia.utils")
	utils_utils = types.ModuleType("evennia.utils.utils")
	utils_utils.inherits_from = lambda obj, parent: isinstance(obj, parent)
	utils_mod.utils = utils_utils
	fake_evennia.utils = utils_mod
	sys.modules["evennia"] = fake_evennia
	sys.modules["evennia.utils"] = utils_mod
	sys.modules["evennia.utils.utils"] = utils_utils

	cmd_mod = load_cmd_module()

	class DummyCaller:
		def __init__(self):
			self.msgs = []
			self.location = object()
			self.id = 2
			self.key = "Bob"

		def msg(self, text):
			self.msgs.append(text)

	host = types.SimpleNamespace(msgs=[], msg=lambda t: host.msgs.append(t))

	req = types.SimpleNamespace(
		host_key="Alice",
		password=None,
		opponent_id=None,
		is_joinable=lambda: True,
		get_host=lambda: host,
	)

	def fake_find_request(location, host_name):
		return req

	orig_find = cmd_mod.find_request
	cmd_mod.find_request = fake_find_request

	cmd = cmd_mod.CmdPvpJoin()
	cmd.caller = DummyCaller()
	cmd.args = "Alice"
	cmd.func()

	if orig_evennia is not None:
		sys.modules["evennia"] = orig_evennia
	else:
		sys.modules.pop("evennia", None)
	sys.modules.pop("evennia.utils", None)
	sys.modules.pop("evennia.utils.utils", None)
	cmd_mod.find_request = orig_find

	assert host.msgs and "joined" in host.msgs[-1].lower()


def test_pvpjoin_prompts_for_password():
	orig_evennia = sys.modules.get("evennia")
	fake_evennia = types.ModuleType("evennia")
	fake_evennia.Command = type("Command", (), {})
	utils_mod = types.ModuleType("evennia.utils")
	evmenu_mod = types.ModuleType("evennia.utils.evmenu")

	def fake_get_input(caller, prompt, callback, session=None, *a, **kw):
		caller.prompt = prompt
		caller.cb = callback

	evmenu_mod.get_input = fake_get_input
	utils_mod.evmenu = evmenu_mod
	utils_utils = types.ModuleType("evennia.utils.utils")
	utils_utils.inherits_from = lambda obj, parent: isinstance(obj, parent)
	utils_mod.utils = utils_utils
	fake_evennia.utils = utils_mod
	sys.modules["evennia"] = fake_evennia
	sys.modules["evennia.utils"] = utils_mod
	sys.modules["evennia.utils.evmenu"] = evmenu_mod
	sys.modules["evennia.utils.utils"] = utils_utils

	cmd_mod = load_cmd_module()

	class DummyCaller:
		def __init__(self):
			self.msgs = []
			self.location = object()
			self.id = 3
			self.key = "Eve"

		def msg(self, text):
			self.msgs.append(text)

	req = types.SimpleNamespace(
		host_key="Alice",
		password="secret",
		opponent_id=None,
		is_joinable=lambda: True,
		get_host=lambda: None,
	)

	def fake_find_request(location, host_name):
		return req

	orig_find = cmd_mod.find_request
	cmd_mod.find_request = fake_find_request

	caller = DummyCaller()
	cmd = cmd_mod.CmdPvpJoin()
	cmd.caller = caller
	cmd.args = "Alice"
	cmd.func()

	assert hasattr(caller, "prompt") and "password" in caller.prompt.lower()
	cb = caller.cb
	assert cb is not None
	cb(caller, "", "secret")

	if orig_evennia is not None:
		sys.modules["evennia"] = orig_evennia
	else:
		sys.modules.pop("evennia", None)
	sys.modules.pop("evennia.utils.evmenu", None)
	sys.modules.pop("evennia.utils", None)
	sys.modules.pop("evennia.utils.utils", None)
	cmd_mod.find_request = orig_find

	assert req.opponent_id == caller.id
	assert caller.msgs and "join" in caller.msgs[-1].lower()


def test_pvpjoin_cannot_join_self():
	orig_evennia = sys.modules.get("evennia")
	fake_evennia = types.ModuleType("evennia")
	fake_evennia.Command = type("Command", (), {})
	utils_mod = types.ModuleType("evennia.utils")
	utils_utils = types.ModuleType("evennia.utils.utils")
	utils_utils.inherits_from = lambda obj, parent: isinstance(obj, parent)
	utils_mod.utils = utils_utils
	fake_evennia.utils = utils_mod
	sys.modules["evennia"] = fake_evennia
	sys.modules["evennia.utils"] = utils_mod
	sys.modules["evennia.utils.utils"] = utils_utils

	cmd_mod = load_cmd_module()

	class DummyCaller:
		def __init__(self):
			self.msgs = []
			self.location = object()
			self.id = 1
			self.key = "Alice"

		def msg(self, text):
			self.msgs.append(text)

	req = types.SimpleNamespace(
		host_key="Alice",
		host_id=1,
		password=None,
		opponent_id=None,
		is_joinable=lambda: True,
		get_host=lambda: None,
	)

	def fake_find_request(location, host_name):
		return req

	orig_find = cmd_mod.find_request
	cmd_mod.find_request = fake_find_request

	cmd = cmd_mod.CmdPvpJoin()
	caller = DummyCaller()
	cmd.caller = caller
	cmd.args = "Alice"
	cmd.func()

	if orig_evennia is not None:
		sys.modules["evennia"] = orig_evennia
	else:
		sys.modules.pop("evennia", None)
	sys.modules.pop("evennia.utils", None)
	sys.modules.pop("evennia.utils.utils", None)
	cmd_mod.find_request = orig_find

	assert caller.msgs and "own" in caller.msgs[-1].lower()
	assert req.opponent_id is None
