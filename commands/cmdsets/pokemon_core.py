"""CmdSet containing the core Pokémon gameplay commands."""

from evennia import CmdSet
from commands.command import (
    CmdShowPokemonOnUser,
    CmdShowPokemonInStorage,
    CmdAddPokemonToUser,
    CmdAddPokemonToStorage,
    CmdGetPokemonDetails,
    CmdUseMove,
    CmdInventory,
    CmdAddItem,
    CmdGiveItem,
    CmdUseItem,
    CmdEvolvePokemon,
    CmdExpShare,
    CmdHeal,
    CmdTeachMove,
    CmdLearn,
    CmdChooseMoveset,
    CmdAdminHeal,
    CmdChooseStarter,
    CmdDepositPokemon,
    CmdWithdrawPokemon,
    CmdShowBox,
    CmdSetHoldItem,
    CmdChargenInfo,
    CmdHunt,
    CmdLeaveHunt,
    CmdCustomHunt,
)
from commands.cmd_sheet import CmdSheet, CmdSheetPokemon
from commands.cmd_movesets import CmdMovesets
from commands.cmd_account import CmdTradePokemon


class PokemonCoreCmdSet(CmdSet):
    """CmdSet bundling core Pokémon related commands."""

    key = "PokemonCoreCmdSet"

    def at_cmdset_creation(self):
        """Populate the cmdset."""
        for cmd in (
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
            CmdCustomHunt,
        ):
            self.add(cmd())
