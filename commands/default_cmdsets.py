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
from paxboards.commands import add_board_commands
from commands.pokedex import (
    CmdPokedexSearch,
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
    CmdChooseStarter,
    CmdDepositPokemon,
    CmdWithdrawPokemon,
    CmdShowBox,
)
from commands.cmd_hunt import CmdHunt, CmdLeaveHunt
from commands.cmd_watchbattle import CmdWatchBattle, CmdUnwatchBattle
from commands.cmd_battle import (
    CmdBattleAttack,
    CmdBattleSwitch,
    CmdBattleItem,
)
from commands.cmd_spawns import CmdSpawns
from commands.cmd_chargen import CmdChargen
from commands.cmd_roomwizard import CmdRoomWizard

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
        #
        # any commands you add below will overload the default ones.
        #
        add_board_commands(self)

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
        self.add(CmdHunt())
        self.add(CmdLeaveHunt())
        self.add(CmdWatchBattle())
        self.add(CmdUnwatchBattle())
        self.add(CmdBattleAttack())
        self.add(CmdBattleSwitch())
        self.add(CmdBattleItem())
        self.add(CmdSpawns())
        self.add(CmdPokedexSearch())
        self.add(CmdMovedexSearch())
        self.add(CmdMovesetSearch())
        self.add(CmdPokedexNumber())
        self.add(CmdStarterList())
        self.add(CmdChargen())
        self.add(CmdRoomWizard())


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
        #
        # any commands you add below will overload the default ones.
        #


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
        #
        # any commands you add below will overload the default ones.
        #
