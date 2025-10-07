"""CmdSet containing the core Pokémon gameplay commands."""

from django.conf import settings
from evennia import CmdSet

from commands.debug.command import (
	CmdAddPokemonToStorage,
	CmdAddPokemonToUser,
	CmdAdminHeal,
	CmdChooseStarter,
	CmdExpShare,
	CmdGetPokemonDetails,
	CmdHeal,
	CmdShowPokemonInStorage,
	CmdShowPokemonOnUser,
	CmdUseMove,
)
from commands.player.cmd_account import CmdTradePokemon
from commands.player.cmd_hunt import CmdCustomHunt, CmdHunt, CmdLeaveHunt
from commands.player.cmd_inventory import (
	CmdAddItem,
	CmdGiveItem,
	CmdInventory,
	CmdUseItem,
)
from commands.player.cmd_learn_evolve import (
	CmdChooseMoveset,
	CmdEvolvePokemon,
	CmdLearn,
	CmdTeachMove,
)
from commands.player.cmd_movesets import CmdMovesets
from commands.player.cmd_party import (
        CmdChargenInfo,
        CmdDepositPokemon,
        CmdSetHoldItem,
        CmdShowBox,
        CmdWithdrawPokemon,
)
from commands.player.cmd_sheet import CmdSheet, CmdSheetPokemon
from commands.player.cmd_vendor import CmdVend


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
                        CmdVend,
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
