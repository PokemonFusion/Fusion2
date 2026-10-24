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
from commands.player.cmd_market import CmdMarket
from commands.player.cmd_daycare import CmdDaycare
from commands.player.cmd_breed import CmdBreed
from commands.player.cmd_berry import CmdBerry
from commands.player.cmd_alpha import CmdAlphaLearnMove, CmdAlphaPokemon, alpha_test_commands_enabled
from commands.player.cmd_fusion import (
	CmdFusionFight,
	CmdFusionForms,
	CmdFusionOrder,
	CmdPermFuse,
	CmdTempFuse,
	CmdUnfuse,
)
from commands.player.cmd_gym import CmdGym
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
from commands.player.cmd_nickname import CmdCaptureNickname
from commands.player.cmd_necrozma import CmdNecrozma
from commands.player.cmd_party import (
	CmdChargenInfo,
	CmdDepositPokemon,
	CmdSetHoldItem,
	CmdShowBox,
	CmdSwapPokemon,
	CmdWithdrawPokemon,
)
from commands.player.cmd_sheet import CmdSheet, CmdSheetPokemon
from commands.player.cmd_trainer_xp import CmdTrainerXP
from commands.player.cmd_vendor import CmdVend
from pokemon.adventures.commands import CmdAdventure


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
			CmdSwapPokemon,
			CmdShowBox,
			CmdSetHoldItem,
			CmdSheet,
			CmdSheetPokemon,
			CmdCaptureNickname,
			CmdTrainerXP,
			CmdChargenInfo,
			CmdInventory,
			CmdAddItem,
			CmdGiveItem,
			CmdUseItem,
			CmdBerry,
			CmdNecrozma,
			CmdTempFuse,
			CmdPermFuse,
			CmdUnfuse,
			CmdFusionForms,
			CmdFusionOrder,
			CmdFusionFight,
			CmdGym,
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
			CmdMarket,
			CmdDaycare,
			CmdBreed,
			CmdAdventure,
			CmdHunt,
			CmdLeaveHunt,
		]
		if settings.DEV_MODE:
			cmds.append(CmdCustomHunt)
		if alpha_test_commands_enabled():
			cmds.extend([CmdAlphaPokemon, CmdAlphaLearnMove])
		for cmd in cmds:
			self.add(cmd())
