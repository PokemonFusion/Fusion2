import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# stub evennia help base


class FakeBaseHelp:
	index_category_clr = ""
	index_type_separator_clr = ""
	index_topic_clr = ""
	subtopic_separator_char = "/"
	DEFAULT_HELP_CATEGORY = "General"
	clickable_topics = True

	default_cmd = {}
	default_db = {}
	default_file = {}

	def client_width(self):
		return 78

	def collect_topics(self, caller, mode="list"):
		return self.default_cmd, self.default_db, self.default_file

	def format_help_entry(self, topic="", help_text="", **kwargs):
		return f"{topic}:{help_text}"

	def msg_help(self, text, **kwargs):
		self.last_msg = text


class FakeHelpCategory:
	def __init__(self, key):
		self.key = key


# utility to load command module with stub


def load_cmd_module():
	path = os.path.join(ROOT, "commands", "player", "cmd_help.py")
	spec = importlib.util.spec_from_file_location("commands.player.cmd_help", path)
	mod = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = mod
	spec.loader.exec_module(mod)
	return mod


def setup_module():
	# replace evennia.commands.default.help with stub
	global orig_help_mod, orig_evennia
	orig_help_mod = sys.modules.get("evennia.commands.default.help")
	fake_mod = types.ModuleType("evennia.commands.default.help")
	fake_mod.CmdHelp = FakeBaseHelp
	fake_mod.DEFAULT_HELP_CATEGORY = "General"
	fake_mod.HelpCategory = FakeHelpCategory
	sys.modules["evennia.commands.default.help"] = fake_mod

	# minimal evennia.utils.utils implementation
	orig_evennia = sys.modules.get("evennia")
	evennia_mod = types.ModuleType("evennia")
	utils_pkg = types.ModuleType("evennia.utils")
	utils_mod = types.ModuleType("evennia.utils.utils")
	utils_mod.format_grid_calls = []
	utils_mod.pad_calls = []

	def format_grid(elements, width=78, sep="  ", line_prefix="", verbatim_elements=None):
		utils_mod.format_grid_calls.append(width)
		row = []
		rows = []
		row_len = 0
		for element in elements:
			element_len = len(element)
			next_len = row_len + len(sep) + element_len if row else element_len
			if row and next_len > width:
				rows.append(line_prefix + sep.join(row))
				row = [element]
				row_len = element_len
			else:
				row.append(element)
				row_len = next_len
		if row:
			rows.append(line_prefix + sep.join(row))
		return rows

	def pad(text, width=78, fillchar="-"):
		utils_mod.pad_calls.append(width)
		return text + fillchar * max(0, width - len(text))

	utils_mod.format_grid = format_grid
	utils_mod.pad = pad
	utils_pkg.utils = utils_mod
	evennia_mod.utils = utils_pkg
	sys.modules["evennia"] = evennia_mod
	sys.modules["evennia.utils"] = utils_pkg
	sys.modules["evennia.utils.utils"] = utils_mod


def teardown_module():
	if orig_help_mod is not None:
		sys.modules["evennia.commands.default.help"] = orig_help_mod
	else:
		sys.modules.pop("evennia.commands.default.help", None)

	if orig_evennia is not None:
		sys.modules["evennia"] = orig_evennia
	else:
		sys.modules.pop("evennia", None)
	sys.modules.pop("evennia.utils", None)
	sys.modules.pop("evennia.utils.utils", None)


def test_format_help_index_nested():
	cmd_mod = load_cmd_module()
	cmd = cmd_mod.CmdHelp()
	output = cmd.format_help_index(
		{
			"Pokemon/Battle": ["attack", "switch"],
			"Pokemon/Dex": ["pokedex"],
		},
		{},
	)
	assert "Pokemon" in output
	assert "Battle" in output
	assert "attack" in output


def test_collect_topics_category_path():
	cmd_mod = load_cmd_module()
	entry = types.SimpleNamespace(help_category="Pokemon/Battle")
	FakeBaseHelp.default_cmd = {"attack": entry}
	FakeBaseHelp.default_db = {}
	FakeBaseHelp.default_file = {}
	cmd = cmd_mod.CmdHelp()
	cmd_topics, _, _ = cmd.collect_topics(None)
	assert cmd_topics["attack"].category_path == ["Pokemon", "Battle"]


def test_help_subcategory_lookup():
	cmd_mod = load_cmd_module()
	entry = types.SimpleNamespace(help_category="Pokemon/Battle", entrytext="atk help")
	FakeBaseHelp.default_cmd = {"attack": entry}
	FakeBaseHelp.default_db = {}
	FakeBaseHelp.default_file = {}
	cmd = cmd_mod.CmdHelp()
	cmd.caller = object()
	cmd.args = "Pokemon/Battle"
	cmd.parse()
	cmd.func()
	assert "attack" in cmd.last_msg


def test_help_command_topic_uses_get_help():
	cmd_mod = load_cmd_module()

	class Entry:
		key = "who"
		help_category = "General"
		aliases = []

		def get_help(self, caller, cmdset):
			assert cmdset == "cmdset"
			return "who help text"

	entry = Entry()
	FakeBaseHelp.default_cmd = {"who": entry}
	FakeBaseHelp.default_db = {}
	FakeBaseHelp.default_file = {}
	cmd = cmd_mod.CmdHelp()
	cmd.caller = object()
	cmd.cmdset = "cmdset"
	cmd.args = "who"
	cmd.parse()
	cmd.func()
	assert "who help text" in cmd.last_msg


def test_help_command_alias_lookup_uses_command_aliases():
	cmd_mod = load_cmd_module()

	class Entry:
		key = "goooc"
		help_category = "General"
		aliases = ["gooc"]
		_keyaliases = ("goooc", "gooc")

		def get_help(self, caller, cmdset):
			return "out-of-character help"

	entry = Entry()
	FakeBaseHelp.default_cmd = {"goooc": entry}
	FakeBaseHelp.default_db = {}
	FakeBaseHelp.default_file = {}
	cmd = cmd_mod.CmdHelp()
	cmd.caller = object()
	cmd.cmdset = object()
	cmd.args = "gooc"
	cmd.parse()
	cmd.func()
	assert "out-of-character help" in cmd.last_msg


def test_help_entry_alias_lookup():
	cmd_mod = load_cmd_module()
	entry = types.SimpleNamespace(
		key="evennia",
		help_category="General",
		aliases=["ev"],
		entrytext="file help text",
	)
	FakeBaseHelp.default_cmd = {}
	FakeBaseHelp.default_db = {}
	FakeBaseHelp.default_file = {"evennia": entry}
	cmd = cmd_mod.CmdHelp()
	cmd.caller = object()
	cmd.args = "ev"
	cmd.parse()
	cmd.func()
	assert "file help text" in cmd.last_msg


def test_help_category_lists_subgroups():
	cmd_mod = load_cmd_module()
	entry1 = types.SimpleNamespace(help_category="Pokemon/Battle", entrytext="atk")
	entry2 = types.SimpleNamespace(help_category="Pokemon/Dex", entrytext="dex")
	FakeBaseHelp.default_cmd = {"attack": entry1, "pokedex": entry2}
	FakeBaseHelp.default_db = {}
	FakeBaseHelp.default_file = {}
	cmd = cmd_mod.CmdHelp()
	cmd.caller = object()
	cmd.args = "Pokemon"
	cmd.parse()
	cmd.func()
	output = cmd.last_msg
	assert "Battle" in output
	assert "Dex" in output
	assert "attack" not in output
	assert "pokedex" not in output


def test_help_index_width_is_capped_for_wide_clients():
	cmd_mod = load_cmd_module()
	utils_mod = sys.modules["evennia.utils.utils"]
	utils_mod.format_grid_calls.clear()
	utils_mod.pad_calls.clear()

	class WideHelp(cmd_mod.CmdHelp):
		def client_width(self):
			return 180

	cmd = WideHelp()
	output = cmd.format_help_index(
		{
			"Pokemon": [
				"+battlewatch",
				"+battle/watch",
				"+expshare",
				"+heal",
				"+hunt",
				"+learn",
				"+leave",
				"+move",
				"+moveset",
				"+pokestore",
				"+sheet/pokemon",
				"+showbattle",
			],
		},
		{},
		click_topics=False,
	)
	lines = output.splitlines()
	assert max(len(line) for line in lines) <= cmd_mod.HELP_INDEX_WIDTH
	assert "Commands" + "-" * (cmd_mod.HELP_INDEX_WIDTH - len("Commands")) in output
	assert any(width == cmd_mod.HELP_INDEX_WIDTH for width in utils_mod.pad_calls)
	assert all(width <= cmd_mod.HELP_INDEX_WIDTH for width in utils_mod.format_grid_calls)
	assert "+sheet/pokemon" in output
	assert len(lines) > 3


def test_help_entry_width_is_capped_for_wide_clients():
	cmd_mod = load_cmd_module()

	class WideHelp(cmd_mod.CmdHelp):
		def client_width(self):
			return 180

	cmd = WideHelp()
	output = cmd.format_help_entry(topic="+hunt", help_text="Attempt to encounter a wild Pokemon.")
	separator = "|C" + "-" * cmd_mod.HELP_INDEX_WIDTH + "|n"
	assert output.splitlines()[0] == separator
	assert output.splitlines()[-1] == separator
	assert "|C" + "-" * (cmd_mod.HELP_INDEX_WIDTH + 1) not in output
