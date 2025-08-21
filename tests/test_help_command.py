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
    utils_mod.format_grid = lambda elements, width=78, sep="  ", line_prefix="", verbatim_elements=None: [
        " ".join(elements)
    ]
    utils_mod.pad = lambda text, width=78, fillchar="-": text
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
