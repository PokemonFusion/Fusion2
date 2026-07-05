import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


IMPORTS = {
    "commands.debug.command": [
        "CmdAddPokemonToStorage",
        "CmdAddPokemonToUser",
        "CmdAdminHeal",
        "CmdChooseStarter",
        "CmdExpShare",
        "CmdGetPokemonDetails",
        "CmdHeal",
        "CmdShowPokemonInStorage",
        "CmdShowPokemonOnUser",
        "CmdUseMove",
    ],
    "commands.player.cmd_account": ["CmdTradePokemon"],
    "commands.player.cmd_fusion": [
        "CmdFusionFight",
        "CmdFusionForms",
        "CmdFusionOrder",
        "CmdPermFuse",
        "CmdTempFuse",
        "CmdUnfuse",
    ],
    "commands.player.cmd_hunt": ["CmdCustomHunt", "CmdHunt", "CmdLeaveHunt"],
    "commands.player.cmd_inventory": ["CmdAddItem", "CmdGiveItem", "CmdInventory", "CmdUseItem"],
    "commands.player.cmd_learn_evolve": [
        "CmdChooseMoveset",
        "CmdEvolvePokemon",
        "CmdLearn",
        "CmdTeachMove",
    ],
    "commands.player.cmd_movesets": ["CmdMovesets"],
    "commands.player.cmd_party": [
        "CmdChargenInfo",
        "CmdDepositPokemon",
        "CmdSetHoldItem",
        "CmdShowBox",
        "CmdSwapPokemon",
        "CmdWithdrawPokemon",
    ],
    "commands.player.cmd_sheet": ["CmdSheet", "CmdSheetPokemon"],
    "commands.player.cmd_trainer_xp": ["CmdTrainerXP"],
    "commands.player.cmd_vendor": ["CmdVend"],
    "pokemon.adventures.commands": ["CmdAdventure"],
}


def command_class(key):
    return type("FakeCommand", (), {"key": key})


def load_pokemon_core(alpha_enabled):
    patched = {
        "django": sys.modules.get("django"),
        "django.conf": sys.modules.get("django.conf"),
        "evennia": sys.modules.get("evennia"),
        "commands.player.cmd_alpha": sys.modules.get("commands.player.cmd_alpha"),
        **{name: sys.modules.get(name) for name in IMPORTS},
    }
    try:
        fake_django = types.ModuleType("django")
        fake_conf = types.ModuleType("django.conf")
        fake_conf.settings = types.SimpleNamespace(DEV_MODE=False)
        fake_django.conf = fake_conf
        sys.modules["django"] = fake_django
        sys.modules["django.conf"] = fake_conf

        class FakeCmdSet:
            def __init__(self):
                self.added = []

            def add(self, command):
                self.added.append(command)

        fake_evennia = types.ModuleType("evennia")
        fake_evennia.CmdSet = FakeCmdSet
        sys.modules["evennia"] = fake_evennia

        fake_alpha = types.ModuleType("commands.player.cmd_alpha")
        fake_alpha.CmdAlphaPokemon = command_class("+alphapokemon")
        fake_alpha.CmdAlphaLearnMove = command_class("+alphalearn")
        fake_alpha.alpha_test_commands_enabled = lambda caller=None: alpha_enabled
        sys.modules["commands.player.cmd_alpha"] = fake_alpha

        for module_name, class_names in IMPORTS.items():
            module = types.ModuleType(module_name)
            for class_name in class_names:
                setattr(module, class_name, command_class(class_name))
            sys.modules[module_name] = module

        path = os.path.join(ROOT, "commands", "cmdsets", "pokemon_core.py")
        spec = importlib.util.spec_from_file_location("commands.cmdsets.pokemon_core", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod
    finally:
        for name, module in patched.items():
            if module is not None:
                sys.modules[name] = module
            else:
                sys.modules.pop(name, None)


def test_pokemon_core_cmdset_hides_alpha_commands_when_gate_disabled():
    mod = load_pokemon_core(alpha_enabled=False)

    cmdset = mod.PokemonCoreCmdSet()
    cmdset.at_cmdset_creation()

    keys = [command.key for command in cmdset.added]
    assert "+alphapokemon" not in keys
    assert "+alphalearn" not in keys


def test_pokemon_core_cmdset_registers_alpha_commands_when_gate_enabled():
    mod = load_pokemon_core(alpha_enabled=True)

    cmdset = mod.PokemonCoreCmdSet()
    cmdset.at_cmdset_creation()

    keys = [command.key for command in cmdset.added]
    assert "+alphapokemon" in keys
    assert "+alphalearn" in keys
