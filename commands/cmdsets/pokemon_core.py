"""CmdSet containing the core Pokémon gameplay commands."""

from django.conf import settings
from evennia import CmdSet
from commands.debug.command import (
    CmdShowPokemonOnUser,
    CmdShowPokemonInStorage,
    CmdAddPokemonToUser,
    CmdAddPokemonToStorage,
    CmdGetPokemonDetails,
    CmdUseMove,
    CmdExpShare,
    CmdHeal,
    CmdAdminHeal,
    CmdChooseStarter,
)
from commands.player.cmd_inventory import (
    CmdInventory,
    CmdAddItem,
    CmdGiveItem,
    CmdUseItem,
)
from commands.player.cmd_party import (
    CmdDepositPokemon,
    CmdWithdrawPokemon,
    CmdShowBox,
    CmdSetHoldItem,
    CmdChargenInfo,
)
from commands.player.cmd_learn_evolve import (
    CmdTeachMove,
    CmdLearn,
    CmdEvolvePokemon,
    CmdChooseMoveset,
)
from commands.player.cmd_hunt import CmdHunt, CmdLeaveHunt, CmdCustomHunt
from commands.player.cmd_sheet import CmdSheet, CmdSheetPokemon
from commands.player.cmd_movesets import CmdMovesets
from commands.player.cmd_account import CmdTradePokemon


class PokemonCoreCmdSet(CmdSet):
    """CmdSet bundling core Pokémon related commands."""

    key = "PokemonCoreCmdSet"

    def at_cmdset_creation(self):
        """Populate the cmdset."""
        cmds = [
            CmdShowPokemonOnUser,
            CmdShowPokemonInStorage,
            CmdAddPokemonToUser,
            CmdAddPokemonToStorage,
            CmdGetPokemonDetails,
            CmdUseMove,
            CmdChooseStarter,
            CmdDepositPokemon,
            CmdWithdrawPokemon,
            CmdShowBox,
            CmdSetHoldItem,
            CmdSheet,
            CmdSheetPokemon,
            CmdChargenInfo,
            CmdInventory,
            CmdAddItem,
            CmdGiveItem,
            CmdUseItem,
            CmdMovesets,
            CmdEvolvePokemon,
            CmdExpShare,
            CmdHeal,
            CmdTeachMove,
            CmdLearn,
            CmdChooseMoveset,
            CmdAdminHeal,
            CmdTradePokemon,
            CmdHunt,
            CmdLeaveHunt,
        ]
        if settings.DEV_MODE:
            cmds.append(CmdCustomHunt)
        for cmd in cmds:
            self.add(cmd())
