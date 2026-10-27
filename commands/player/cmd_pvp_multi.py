"""Ordinary room-local four-trainer PvP lobby entry point."""

from evennia import Command

from pokemon.battle.multi_lobby import MultiLobby


class CmdPvpMulti(Command):
    """Play two trainers versus two trainers, each with one active Pokemon.

    Usage:
      +pvp/multi create
      +pvp/multi join <A2||B1||B2>
      +pvp/multi ready
      +pvp/multi unready
      +pvp/multi status
      +pvp/multi leave
      +pvp/multi start

    Four different player accounts join two teams and ready separately. The
    host starts after all four agree. Joining/changing teams or leaving clears
    readiness. Lobbies expire after ten minutes and acquire no movement locks.
    Every trainer keeps their own Pokemon/items. A five-minute action deadline
    and confirmed concession forfeit the affected team; both overdue teams draw.
    """

    key = '+pvp/multi'
    locks = 'cmd:all()'
    help_category = 'Pokemon/PvP'

    def func(self):
        """Dispatch only supported consent actions with actionable refusals."""
        action, _, argument = (self.args or 'status').strip().partition(' ')
        try:
            lobby = MultiLobby(self.caller)
            if action == 'create':
                result = lobby.create()
            elif action in {'join', 'team'}:
                result = lobby.join(argument.strip())
            elif action in {'ready', 'unready'}:
                result = lobby.ready(action == 'ready')
            elif action in {'leave', 'cancel'}:
                result = lobby.leave()
            elif action == 'start':
                session = lobby.start()
                result = f'Multi Battle #{session.battle_id} started.'
            elif action == 'status':
                result = lobby.status()
            else:
                raise ValueError('Use +pvp/multi create, join <slot>, ready, unready, status, leave or start.')
            self.caller.msg(result)
        except ValueError as error:
            self.caller.msg(str(error))
