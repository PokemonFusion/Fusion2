import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _class_attrs(path, class_name):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            attrs = {"doc": ast.get_docstring(node) or ""}
            for stmt in node.body:
                if not isinstance(stmt, ast.Assign):
                    continue
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id in {"key", "aliases", "help_category"}:
                        attrs[target.id] = ast.literal_eval(stmt.value)
            return attrs
    raise AssertionError(f"{class_name} not found in {path}")


def test_preferred_player_command_names_keep_legacy_aliases():
    expected = {
        ("commands/player/cmd_sheet.py", "CmdSheetPokemon"): (
            "+party",
            {"+sheet/pokemon", "+sheet/pkmn"},
        ),
        ("commands/player/cmd_party.py", "CmdShowBox"): (
            "+box",
            {"showbox", "+showbox"},
        ),
        ("commands/player/cmd_party.py", "CmdDepositPokemon"): (
            "+box/deposit",
            {"deposit", "+deposit"},
        ),
        ("commands/player/cmd_party.py", "CmdWithdrawPokemon"): (
            "+box/withdraw",
            {"withdraw", "+withdraw"},
        ),
        ("commands/player/cmd_party.py", "CmdSwapPokemon"): (
            "+box/swap",
            {"swap", "+swap", "pokemonswap", "boxswap"},
        ),
        ("commands/player/cmd_pokestore.py", "CmdPokestore"): (
            "+storage",
            {"+pokestore", "pokestore"},
        ),
        ("commands/player/cmd_learn_evolve.py", "CmdTeachMove"): (
            "+teach",
            {"+move"},
        ),
        ("commands/player/cmd_learn_evolve.py", "CmdChooseMoveset"): (
            "+moves/use",
            {"+moveset"},
        ),
        ("commands/player/cmd_learn_evolve.py", "CmdEvolvePokemon"): (
            "+evolve",
            {"evolve"},
        ),
        ("commands/player/cmd_inventory.py", "CmdUseItem"): (
            "+use",
            {"+useitem"},
        ),
        ("commands/player/cmd_pokedex.py", "CmdPokedexSearch"): (
            "+dex",
            {"pokedex", "poke"},
        ),
        ("commands/player/cmd_pokedex.py", "CmdMovedexSearch"): (
            "+movedex",
            {"movedex", "+mdex", "mdex", "move"},
        ),
        ("commands/player/cmd_pokedex.py", "CmdMovesetSearch"): (
            "+learnset",
            {"moveset", "learnset", "movelist"},
        ),
        ("commands/player/cmd_pokedex.py", "CmdStarterList"): (
            "+starters",
            {"starterlist", "starters"},
        ),
        ("commands/debug/command.py", "CmdChooseStarter"): (
            "+starter",
            {"choosestarter"},
        ),
        ("commands/debug/command.py", "CmdGetPokemonDetails"): (
            "+pokemon",
            {"getpokemondetails"},
        ),
        ("commands/player/cmd_showbattle.py", "CmdShowBattle"): (
            "+battleui",
            {"+showbattle", "+battleview"},
        ),
        ("commands/player/cmd_battleuistyle.py", "CmdBattleUiStyle"): (
            "+battleui/style",
            {"+battleuistyle", "+buistyle"},
        ),
        ("commands/player/cmd_effects.py", "CmdEffects"): (
            "+status",
            {"+effects", "+bstate"},
        ),
        ("commands/player/cmd_watchbattle.py", "CmdWatchBattle"): (
            "+watch/battle",
            {"+battlewatch"},
        ),
        ("commands/player/cmd_watchbattle.py", "CmdBattleList"): (
            "+battles",
            {"+battlelist"},
        ),
        ("commands/player/cmdstartmap.py", "CmdStartMap"): (
            "+map/start",
            {"@startmap"},
        ),
        ("commands/player/cmd_map_move.py", "CmdMapMove"): (
            "+map/move",
            {"@mapmove"},
        ),
    }

    for (path, class_name), (key, aliases) in expected.items():
        attrs = _class_attrs(path, class_name)
        assert attrs["key"] == key
        assert aliases <= set(attrs.get("aliases", []))


def test_updated_player_help_docstrings_have_examples_or_notes():
    commands = [
        ("commands/player/cmd_party.py", "CmdDepositPokemon"),
        ("commands/player/cmd_party.py", "CmdWithdrawPokemon"),
        ("commands/player/cmd_party.py", "CmdSwapPokemon"),
        ("commands/player/cmd_party.py", "CmdShowBox"),
        ("commands/player/cmd_pokedex.py", "CmdPokedexSearch"),
        ("commands/player/cmd_pokedex.py", "CmdMovedexSearch"),
        ("commands/player/cmd_pokedex.py", "CmdMovesetSearch"),
        ("commands/player/cmd_learn_evolve.py", "CmdTeachMove"),
        ("commands/player/cmd_learn_evolve.py", "CmdChooseMoveset"),
        ("commands/player/cmd_learn_evolve.py", "CmdEvolvePokemon"),
        ("commands/player/cmd_inventory.py", "CmdUseItem"),
        ("commands/player/cmd_showbattle.py", "CmdShowBattle"),
        ("commands/player/cmd_effects.py", "CmdEffects"),
    ]

    for path, class_name in commands:
        doc = _class_attrs(path, class_name)["doc"]
        assert "Usage:" in doc
        assert "Examples:" in doc
        assert "Notes:" in doc


def test_guide_teaches_preferred_command_names():
    text = (ROOT / "world/help_entries.py").read_text(encoding="utf-8")

    for command in (
        "+starter",
        "+party <slot>",
        "+box/deposit <pokemon_id> [box]",
        "+storage",
        "+teach <slot>=<move>",
        "+moves/use <slot>=<set>",
        "+learnset <pokemon>",
        "+watch/battle <battle id>",
        "+status list",
    ):
        assert command in text

    for legacy in (
        "+starter <pokemon>",
        "choosestarter <pokemon>",
        "\ndeposit <pokemon_id> [box]",
        "+move <slot>=<move>",
        "\nmovesets              Manage",
        "\nmovedex <move>",
        "+effects list",
    ):
        assert legacy not in text
