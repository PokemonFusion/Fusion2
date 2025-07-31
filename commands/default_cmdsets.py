"""
Command sets

All commands in the game must be grouped in a cmdset.  A given command
can be part of any number of cmdsets and cmdsets can be added/removed
and merged onto entities at runtime.

To create new commands to populate the cmdset, see
`commands/command.py`.

This module wraps the default command sets of Evennia; overloads them
to add/remove commands from the default lineup. You can create your
own cmdsets by inheriting from them or directly from `evennia.CmdSet`.

"""

from evennia import default_cmds
from commands.cmd_help import CmdHelp
from commands.cmd_debugpy import CmdDebugPy
from commands.cmd_examine import CmdExamine
from bboard.commands import (
    CmdBBList,
    CmdBBRead,
    CmdBBPost,
    CmdBBDelete,
    CmdBBSet,
    CmdBBNew,
    CmdBBEdit,
    CmdBBMove,
    CmdBBPurge,
    CmdBBLock,
)
from commands.pokedex import (
    CmdPokedexSearch,
    CmdPokedexAll,
    CmdMovedexSearch,
    CmdMovesetSearch,
    CmdPokedexNumber,
    CmdStarterList,
)

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
    CmdSpoof,
)
from commands.cmd_hunt import CmdHunt, CmdLeaveHunt, CmdCustomHunt
from commands.cmd_watchbattle import CmdWatchBattle, CmdUnwatchBattle
from commands.cmd_watch import CmdWatch, CmdUnwatch
from commands.cmd_adminbattle import (
    CmdAbortBattle,
    CmdRestoreBattle,
    CmdBattleInfo,
    CmdRetryTurn,
)
from commands.cmd_battle import (
    CmdBattleAttack,
    CmdBattleSwitch,
    CmdBattleItem,
    CmdBattleFlee,
)
from commands.cmd_store import CmdStore
from commands.cmd_pokestore import CmdPokestore
from commands.cmd_movesets import CmdMovesets
from commands.cmd_pvp import (
    CmdPvpHelp,
    CmdPvpList,
    CmdPvpCreate,
    CmdPvpJoin,
    CmdPvpAbort,
    CmdPvpStart,
)
from commands.cmd_spawns import CmdSpawns
from commands.cmd_chargen import CmdChargen
from commands.cmd_roomwizard import CmdRoomWizard
from commands.cmd_editroom import CmdEditRoom
from commands.cmd_validate import CmdValidate
from commands.cmd_givepokemon import CmdGivePokemon
from commands.cmd_adminpokemon import (
    CmdListPokemon,
    CmdRemovePokemon,
    CmdPokemonInfo,
)
from commands.cmd_gitpull import CmdGitPull
from commands.cmd_logusage import CmdLogUsage, CmdMarkVerified
from commands.cmd_account import CmdCharCreate, CmdAlts, CmdTradePokemon
from commands.cmd_glance import CmdGlance
from commands.cmd_sheet import CmdSheet, CmdSheetPokemon
from commands.cmdmapmove import CmdMapMove
from commands.cmdstartmap import CmdStartMap
from commands.cmd_roleplay import CmdGOIC, CmdGOOOC, CmdOOC

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `AccountCmdSet` when an Account puppets a Character.
    """

    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        self.remove("help")
        self.remove("@examine")
        self.add(CmdHelp())
        self.add(CmdDebugPy)
        self.add(CmdExamine())
        #
        # any commands you add below will overload the default ones.
        #
        # Bulletin board commands
        self.add(CmdBBList())
        self.add(CmdBBRead())
        self.add(CmdBBPost())
        self.add(CmdBBDelete())
        self.add(CmdBBSet())
        self.add(CmdBBNew())
        self.add(CmdBBEdit())
        self.add(CmdBBMove())
        self.add(CmdBBPurge())
        self.add(CmdBBLock())

        # Basic roleplay command
        self.add(CmdSpoof())
        self.add(CmdGlance())
        self.add(CmdOOC())

        # Add Pokémon commands
        self.add(CmdShowPokemonOnUser())
        self.add(CmdShowPokemonInStorage())
        self.add(CmdAddPokemonToUser())
        self.add(CmdAddPokemonToStorage())
        self.add(CmdGetPokemonDetails())
        self.add(CmdUseMove())
        self.add(CmdChooseStarter())
        self.add(CmdDepositPokemon())
        self.add(CmdWithdrawPokemon())
        self.add(CmdShowBox())
        self.add(CmdSetHoldItem())
        self.add(CmdSheet())
        self.add(CmdSheetPokemon())
        self.add(CmdChargenInfo())
        self.add(CmdInventory())
        self.add(CmdAddItem())
        self.add(CmdGiveItem())
        self.add(CmdUseItem())
        self.add(CmdStore())
        self.add(CmdPokestore())
        self.add(CmdEvolvePokemon())
        self.add(CmdExpShare())
        self.add(CmdHeal())
        self.add(CmdTeachMove())
        self.add(CmdLearn())
        self.add(CmdChooseMoveset())
        self.add(CmdMovesets())
        self.add(CmdAdminHeal())
        self.add(CmdTradePokemon())
        self.add(CmdHunt())
        self.add(CmdCustomHunt())
        self.add(CmdLeaveHunt())
        self.add(CmdWatchBattle())
        self.add(CmdUnwatchBattle())
        self.add(CmdWatch())
        self.add(CmdUnwatch())
        self.add(CmdAbortBattle())
        self.add(CmdRestoreBattle())
        self.add(CmdBattleInfo())
        self.add(CmdRetryTurn())
        self.add(CmdBattleAttack())
        self.add(CmdBattleSwitch())
        self.add(CmdBattleItem())
        self.add(CmdBattleFlee())
        self.add(CmdSpawns())
        self.add(CmdGivePokemon())
        self.add(CmdListPokemon())
        self.add(CmdRemovePokemon())
        self.add(CmdPokemonInfo())
        self.add(CmdGitPull())
        # PVP commands
        self.add(CmdPvpHelp())
        self.add(CmdPvpList())
        self.add(CmdPvpCreate())
        self.add(CmdPvpJoin())
        self.add(CmdPvpAbort())
        self.add(CmdPvpStart())
        self.add(CmdPokedexSearch())
        self.add(CmdPokedexAll())
        self.add(CmdMovedexSearch())
        self.add(CmdMovesetSearch())
        self.add(CmdPokedexNumber())
        self.add(CmdStarterList())
        self.add(CmdChargen())
        self.add(CmdRoomWizard())
        self.add(CmdEditRoom())
        self.add(CmdValidate())
        self.add(CmdMapMove())
        self.add(CmdStartMap())
        self.add(CmdLogUsage())
        self.add(CmdMarkVerified())


class AccountCmdSet(default_cmds.AccountCmdSet):
    """
    This is the cmdset available to the Account at all times. It is
    combined with the `CharacterCmdSet` when the Account puppets a
    Character. It holds game-account-specific commands, channel
    commands, etc.
    """

    key = "DefaultAccount"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        self.remove("help")
        self.remove("@examine")
        self.add(CmdHelp())
        self.add(CmdExamine())
        #
        # any commands you add below will overload the default ones.
        #
        # replace default ic/ooc commands
        for cmdname in ("ic", "puppet", "ooc", "unpuppet"):
            self.remove(cmdname)
        self.add(CmdGOIC())
        self.add(CmdGOOOC())
        self.add(CmdCharCreate())
        self.add(CmdAlts())


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    """
    Command set available to the Session before being logged in.  This
    holds commands like creating a new account, logging in, etc.
    """

    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        self.remove("help")
        self.add(CmdHelp())
        #
        # any commands you add below will overload the default ones.
        #


class SessionCmdSet(default_cmds.SessionCmdSet):
    """
    This cmdset is made available on Session level once logged in. It
    is empty by default.
    """

    key = "DefaultSession"

    def at_cmdset_creation(self):
        """
        This is the only method defined in a cmdset, called during
        its creation. It should populate the set with command instances.

        As and example we just add the empty base `Command` object.
        It prints some info.
        """
        super().at_cmdset_creation()
        self.remove("help")
        self.add(CmdHelp())
        #
        # any commands you add below will overload the default ones.
        #

