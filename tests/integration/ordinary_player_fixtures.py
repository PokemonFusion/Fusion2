"""Real standalone Evennia facilities and tagged disposable player fixtures."""

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4


class OrdinaryPlayerFixtures:
    """Bind actual APIs without constructing services, opening ports or game DBs."""

    def __init__(self, tag):
        """Use only the caller's already-guarded test schema and explicit fixture tag."""
        self.tag = tag
        self.patches = []

    def __enter__(self):
        """Initialize only real command, model, session, create and search facades."""
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet
        base = patch.multiple(evennia, Command=Command, CmdSet=CmdSet)
        base.start()
        self.patches.append(base)
        from evennia.commands.default.cmdset_account import AccountCmdSet
        from evennia.commands.default.cmdset_character import CharacterCmdSet
        from evennia.commands.default.cmdset_session import SessionCmdSet
        from evennia.commands.default.cmdset_unloggedin import UnloggedinCmdSet
        from evennia.commands.default.muxcommand import MuxCommand
        from evennia.server.sessionhandler import ServerSessionHandler
        from evennia.objects.objects import DefaultObject, DefaultCharacter, DefaultRoom, DefaultExit
        from evennia.accounts.accounts import DefaultAccount, DefaultGuest
        from evennia.comms.comms import DefaultChannel
        from evennia.scripts.scripts import DefaultScript
        from evennia.scripts.models import ScriptDB
        from evennia.objects.models import ObjectDB
        from evennia.accounts.models import AccountDB
        from evennia.comms.models import ChannelDB, Msg
        from evennia.utils import create, search
        from evennia.commands import cmdhandler
        self.sessions = ServerSessionHandler()
        api = patch.multiple(evennia, Command=Command, CmdSet=CmdSet,
            DefaultObject=DefaultObject, DefaultCharacter=DefaultCharacter, DefaultRoom=DefaultRoom,
            DefaultExit=DefaultExit, DefaultScript=DefaultScript, DefaultAccount=DefaultAccount,
            DefaultGuest=DefaultGuest, DefaultChannel=DefaultChannel, ScriptDB=ScriptDB,
            ObjectDB=ObjectDB, AccountDB=AccountDB, ChannelDB=ChannelDB, Msg=Msg,
            SESSION_HANDLER=self.sessions, search_object=search.search_object,
            search_account=search.search_account, search_script=search.search_script,
            search_channel=search.search_channel, create_object=create.create_object,
            create_account=create.create_account, create_script=create.create_script,
            create_message=create.create_message, create_channel=create.create_channel,
            default_cmds=SimpleNamespace(CharacterCmdSet=CharacterCmdSet, AccountCmdSet=AccountCmdSet,
                SessionCmdSet=SessionCmdSet, UnloggedinCmdSet=UnloggedinCmdSet, MuxCommand=MuxCommand),
            syscmdkeys=SimpleNamespace(**{key: getattr(cmdhandler, key) for key in
                ('CMD_NOINPUT', 'CMD_NOMATCH', 'CMD_MULTIMATCH', 'CMD_LOGINSTART')}))
        api.start()
        self.patches.append(api)
        return self

    def __exit__(self, *error):
        """Restore only the child process's patched API facades."""
        for item in reversed(self.patches):
            item.stop()

    def character(self, *, account=None, staff=False):
        """Create independent ordinary characters; optional staff is a separate fixture."""
        from evennia.accounts.models import AccountDB
        from evennia.objects.models import ObjectDB
        from pokemon.models.trainer import Trainer
        from pokemon.models.storage import UserStorage
        if account is None:
            account = AccountDB.objects.create(username=self.tag[:12] + uuid4().hex[:12],
                db_typeclass_path='typeclasses.accounts.Account')
        permission = 'Admin' if staff else 'Player'
        if staff:
            account.permissions.add('Admin')
        account.permissions.add('Player')
        player = ObjectDB.objects.create(db_key=('Staff ' if staff else 'Player ') + uuid4().hex[:10],
            db_typeclass_path='pokemon.user.User', db_account=account)
        player.permissions.add(permission)
        player.tags.add(self.tag)
        account.characters.add(player)
        Trainer.objects.get_or_create(user=player, defaults={'trainer_number': Trainer.objects.count() + 1})
        UserStorage.objects.get_or_create(user=player)
        return player
