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
from commands.cmd_roleplay import CmdGOIC, CmdGOOOC
from commands.cmd_account import CmdCharCreate, CmdAlts
from commands.cmd_testmenu import CmdTestMenu

# grouped cmdsets
from commands.cmdsets.bboard import BulletinBoardCmdSet
from commands.cmdsets.roleplay import RoleplayCmdSet
from commands.cmdsets.ui import UiCmdSet
from commands.cmdsets.pokemon_core import PokemonCoreCmdSet
from commands.cmdsets.battle import BattleCmdSet
from commands.cmdsets.battle_admin import BattleAdminCmdSet
from commands.cmdsets.pokedex import PokedexCmdSet
from commands.cmdsets.pvp import PvpCmdSet
from commands.cmdsets.world_build import WorldBuildCmdSet
from commands.cmdsets.economy_map import EconomyMapCmdSet
from commands.cmdsets.admin_misc import AdminMiscCmdSet


from commands.cmd_toggle_test import CmdToggleTest

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `AccountCmdSet` when an Account puppets a Character.
    """

    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """Populate the cmdset."""
        super().at_cmdset_creation()
        self.remove("help")
        self.remove("@examine")
        self.add(CmdHelp())
        self.add(CmdExamine())
        self.add(CmdDebugPy)

        # Attach grouped command sets
        self.add(BulletinBoardCmdSet())
        self.add(RoleplayCmdSet())
        self.add(UiCmdSet())
        self.add(PokemonCoreCmdSet())
        self.add(BattleCmdSet())
        self.add(BattleAdminCmdSet())
        self.add(PokedexCmdSet())
        self.add(PvpCmdSet())
        self.add(WorldBuildCmdSet())
        self.add(EconomyMapCmdSet())
        self.add(AdminMiscCmdSet())

        # Developer toggle for test cmdset
        self.add(CmdToggleTest())
        
        # Test commands
        self.add(CmdTestMenu())


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

