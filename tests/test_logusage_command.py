import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
	path = os.path.join(ROOT, "commands", "debug", "cmd_logusage.py")
	spec = importlib.util.spec_from_file_location("commands.debug.cmd_logusage", path)
	mod = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = mod
	spec.loader.exec_module(mod)
	return mod


def test_logusage_records_message(tmp_path):
	orig_evennia = sys.modules.get("evennia")
	fake_evennia = types.ModuleType("evennia")
	fake_evennia.Command = type("Command", (), {})
	sys.modules["evennia"] = fake_evennia

	cmd_mod = load_cmd_module()

	logs = []

	class DummyLogger:
		def info(self, msg):
			logs.append(msg)

	def fake_setup(path):
		return DummyLogger()

	cmd_mod.setup_daily_usage_log = fake_setup
	cmd_mod.LOG_DIR = tmp_path

	class DummyCaller:
		def __init__(self):
			self.msgs = []

		def msg(self, text):
			self.msgs.append(text)

	cmd = cmd_mod.CmdLogUsage()
	cmd.caller = DummyCaller()
	cmd.args = "tackle=intimidate"
	cmd.parse()
	cmd.func()

	if orig_evennia is not None:
		sys.modules["evennia"] = orig_evennia
	else:
		sys.modules.pop("evennia", None)

	assert logs and "tackle" in logs[0] and "intimidate" in logs[0]
	assert cmd.caller.msgs and "logged" in cmd.caller.msgs[0].lower()


def test_markverified_creates_file(tmp_path):
	orig_evennia = sys.modules.get("evennia")
	fake_evennia = types.ModuleType("evennia")
	fake_evennia.Command = type("Command", (), {})
	sys.modules["evennia"] = fake_evennia

	cmd_mod = load_cmd_module()
	cmd_mod.LOG_DIR = tmp_path

	class DummyCaller:
		def __init__(self):
			self.msgs = []

		def msg(self, text):
			self.msgs.append(text)

	cmd = cmd_mod.CmdMarkVerified()
	cmd.caller = DummyCaller()
	cmd.args = "move tackle"
	cmd.parse()
	cmd.func()

	if orig_evennia is not None:
		sys.modules["evennia"] = orig_evennia
	else:
		sys.modules.pop("evennia", None)

	data_path = tmp_path / "verified_usage.json"
	assert data_path.exists()
	data = data_path.read_text()
	assert "tackle" in data
	assert cmd.caller.msgs and "marked" in cmd.caller.msgs[0].lower()
