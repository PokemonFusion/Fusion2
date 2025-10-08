import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
        """Load the pokedex command module with a stubbed evennia."""

        path = os.path.join(ROOT, "commands", "player", "cmd_pokedex.py")
        spec = importlib.util.spec_from_file_location("commands.player.cmd_pokedex", path)
        module = importlib.util.module_from_spec(spec)
        original = sys.modules.get(spec.name)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module, spec.name, original


class DummyCaller:
        def __init__(self):
                self.msgs = []

        def msg(self, text):
                self.msgs.append(text)


def setup_environment():
        """Prepare fake dependencies and load the command module."""

        orig_evennia = sys.modules.get("evennia")
        fake_evennia = types.ModuleType("evennia")
        fake_evennia.Command = type("Command", (), {})
        sys.modules["evennia"] = fake_evennia

        module, module_name, original_module = load_cmd_module()
        middleware = sys.modules["pokemon.middleware"]

        orig_itemdex = middleware.itemdex
        orig_items_text = middleware.ITEMS_TEXT

        middleware.itemdex = {
                "Testorb": {
                        "name": "Test Orb",
                        "gen": 5,
                        "fling": {"basePower": 60},
                        "itemUser": ["Testmon"],
                }
        }
        middleware.ITEMS_TEXT = {
                "testorb": {
                        "name": "Test Orb",
                        "shortDesc": "Boosts Testmon's moves by 20%.",
                }
        }
        middleware._build_item_lookup()

        return (
                module,
                middleware,
                orig_evennia,
                module_name,
                original_module,
                orig_itemdex,
                orig_items_text,
        )


def teardown_environment(
        orig_evennia,
        module_name,
        original_module,
        middleware,
        orig_itemdex,
        orig_items_text,
):
        """Restore modules replaced during setup."""

        middleware.itemdex = orig_itemdex
        middleware.ITEMS_TEXT = orig_items_text
        middleware._build_item_lookup()

        if orig_evennia is not None:
                sys.modules["evennia"] = orig_evennia
        else:
                sys.modules.pop("evennia", None)

        if original_module is not None:
                sys.modules[module_name] = original_module
        else:
                sys.modules.pop(module_name, None)


def test_itemdex_command_displays_item_details():
        (
                module,
                middleware,
                orig_evennia,
                module_name,
                original_module,
                orig_itemdex,
                orig_items_text,
        ) = setup_environment()

        try:
                caller = DummyCaller()
                cmd = module.CmdItemdexSearch()
                cmd.caller = caller
                cmd.args = "Test Orb"
                cmd.func()

                assert caller.msgs, "Command did not respond."
                output = caller.msgs[-1]
                assert "Test Orb" in output
                assert "Boosts Testmon's moves by 20%." in output
                assert "Fling Power: 60" in output
        finally:
                teardown_environment(
                        orig_evennia,
                        module_name,
                        original_module,
                        middleware,
                        orig_itemdex,
                        orig_items_text,
                )


def test_itemdex_command_handles_missing_item():
        (
                module,
                middleware,
                orig_evennia,
                module_name,
                original_module,
                orig_itemdex,
                orig_items_text,
        ) = setup_environment()

        try:
                caller = DummyCaller()
                cmd = module.CmdItemdexSearch()
                cmd.caller = caller
                cmd.args = "Unknown Item"
                cmd.func()

                assert caller.msgs[-1] == "No item found with that name."
        finally:
                teardown_environment(
                        orig_evennia,
                        module_name,
                        original_module,
                        middleware,
                        orig_itemdex,
                        orig_items_text,
                )
