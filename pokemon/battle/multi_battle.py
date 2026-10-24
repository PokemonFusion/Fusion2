"""Build and finish the bounded four-controller PvP format on BattleSession."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .multi_state import POSITIONS, bind_sides

ACTION_SECONDS = 300


def field_text(session):
    """Show four controllers, physical slots, public HP/status and missing inputs."""
    from datetime import datetime
    lines = [f'Multi Battle #{session.battle_id} — four independent trainers']
    for part in sorted(session.battle.participants, key=lambda part: part.field_position):
        mon = next(iter(part.active), None)
        if mon is None or mon.hp <= 0:
            detail = 'empty (no remaining battlers)' if part.has_lost else 'empty'
        else:
            hp = max(0, round(mon.hp / max(1, mon.max_hp) * 100))
            detail = f'{mon.name}, {hp}% HP, {getattr(mon, "status", None) or "OK"}'
            if getattr(mon, 'terastallized', None):
                detail += f', Tera {mon.terastallized}'
            if getattr(mon, 'mega_evolved', False):
                detail += f', Mega {mon.species}'
        lines.append(f'{part.field_position}: {part.name} — {detail}')
    missing = session._missing_action_positions()
    seconds = max(0, int((datetime.fromisoformat(session.state.multi['deadline']) - timezone.now()).total_seconds()))
    lines.append('Waiting on: ' + (', '.join(missing) or 'no missing choices') + f'. Deadline in {seconds // 60}m {seconds % 60}s.')
    for team in ('A', 'B'):
        used = [label for key, label in (('tera', 'Tera'), ('mega', 'Mega'), ('z', 'Z'))
                if team in getattr(session.battle, key + '_used', set())]
        if used:
            lines.append(f'Team {team} mechanics spent: ' + ', '.join(used) + '.')
    return '\n'.join(lines)


def start(session, players):
    """Assemble one active per controller; publish prompts only after commit."""
    from .battledata import BattleData, Team, TurnData, PositionData
    from .engine import Battle, BattleParticipant, BattleType
    from .logic import BattleLogic
    from .state import BattleState
    from .handler import battle_handler
    from pokemon.services.battle_rewards import BufferedMessages

    session.teamA = [players[label] for label in ('A1', 'A2')]
    session.teamB = [players[label] for label in ('B1', 'B2')]
    session.trainers = session.teamA + session.teamB
    parts = []
    for label in POSITIONS:
        player = players[label]
        session._register_trainer(player)
        roster = session._prepare_player_party(player)
        if not roster or not any(mon.hp > 0 for mon in roster):
            raise ValueError(f'{player.key} needs a conscious eligible Pokemon.')
        part = BattleParticipant(player.key, roster, player=player, max_active=1, team=label[0])
        part.controller_id, part.field_position = str(player.pk), label
        part.active = next(([mon] for mon in roster if mon.hp > 0), [])
        part._active_slots = {0: part.active[0]}
        parts.append(part)
    battle = Battle(BattleType.PVP, parts, rng=session.rng)
    bind_sides(battle)
    data = BattleData(*[Team(' / '.join(part.name for part in parts if part.team == team),
        [mon for part in parts if part.team == team for mon in part.pokemons]) for team in ('A', 'B')])
    data.turndata = TurnData(data.teams, teamslots=2)
    data.turndata.positions = {part.field_position: PositionData(part.active[0]) for part in parts}
    data.battle.how_many = 2
    state = BattleState.from_battle_data(data, ai_type='PVP')
    state.multi = {'version': 1, 'deadline': (timezone.now() + timedelta(seconds=ACTION_SECONDS)).isoformat(), 'deadline_turn': 0}
    state.pokemon_control = {str(mon.model_id): part.controller_id for part in parts for mon in part.pokemons}
    session.logic = BattleLogic(battle, data, state)
    session._bind_reward_delivery()
    messages = BufferedMessages(session)
    battle.log_action = messages.msg
    battle.start_turn()
    marker = getattr(battle, 'mark_initial_prompt', None)
    if marker:
        marker()
    session._sync_active_battle_state()
    session.logic.sync_runtime_state()
    session.storage.set('trainers', {'teamA': [player.pk for player in session.teamA],
                                     'teamB': [player.pk for player in session.teamB]})
    session.storage.set('data', data.to_dict())
    session.storage.set('state', session._compact_state_for_persist(state.to_dict()))
    for part in parts:
        part.player.team = part.pokemons
        part.player.active_pokemon = part.active[0]
    def announce():
        """Committed launch becomes visible to all four ordinary controllers."""
        battle.log_action = session.notify
        battle_handler.register(session)
        for player in session.trainers:
            session.add_watcher(player)
        messages.publish()
        session.msg(f'Multi Battle #{session.battle_id} started: two trainers per team. Each controls only their own Pokemon/items. '
                    'A five-minute action deadline applies; +concede yes forfeits your team.')
        session.prompt_next_turn()
    transaction.on_commit(announce, robust=True)
    return session


def reset_deadline(session):
    """Start a new deadline only after a successful turn, never on reconnect."""
    if session.state.multi and session.state.multi.get('deadline_turn') != session.battle.turn_count:
        session.state.multi['deadline'] = (timezone.now() + timedelta(seconds=ACTION_SECONDS)).isoformat()
        session.state.multi['deadline_turn'] = session.battle.turn_count


def outcomes(session, winner=None, *, reason='completed'):
    """Retain four immutable receipts using existing no-prize/no-XP PvP policy."""
    from evennia.objects.models import ObjectDB
    from pokemon.services.battle_rewards import BattleRewards
    if not session.state.multi:
        return
    delivery = BattleRewards(session.state.reward_id)
    with transaction.atomic():
        ObjectDB.objects.select_for_update().get(pk=session.room.pk)
        list(ObjectDB.objects.select_for_update().filter(pk__in=[player.pk for player in session.trainers]).order_by('pk'))
        result = session.state.multi.get('result')
        if result is None:
            result = {'winner': getattr(winner, 'team', None), 'reason': reason,
                      'controllers': sorted(part.controller_id for part in session.battle.participants)}
            session.state.multi['result'] = result
        keys = []
        for part in session.battle.participants:
            outcome = 'draw' if result['winner'] is None else 'win' if part.team == result['winner'] else 'loss'
            keys.append((part.player, delivery.record(part.player, 'multi-result',
                {'outcome': outcome, 'team': part.team, 'result': result, 'pokemon': [], 'txp': 0, 'money': 0})))
        session.logic.sync_runtime_state()
        session.storage.set('state', session._compact_state_for_persist(session.state.to_dict()))
    for player, key in keys:
        delivery.claim(player, key, caller=session)
    session._battle_result_handled = True


def forfeit(session, teams, *, reason):
    """A living controller may forfeit their team; both overdue teams draw."""
    if not session.state.multi or session.battle.battle_over:
        raise ValueError('That Multi Battle has already ended.')
    from evennia.objects.models import ObjectDB
    with transaction.atomic():
        ObjectDB.objects.select_for_update().get(pk=session.room.pk)
        for part in session.battle.participants:
            if part.team in teams:
                part.has_lost = True
        winner = session.battle.check_victory()
        session.state.multi.setdefault('result', {'winner': getattr(winner, 'team', None), 'reason': reason,
            'controllers': sorted(part.controller_id for part in session.battle.participants)})
        session.state.battle_over = True
        session.logic.sync_runtime_state()
        session.storage.set('state', session._compact_state_for_persist(session.state.to_dict()))
    outcomes(session, winner, reason=reason)
    session.msg('Multi Battle ended: ' + reason + '. ' + ('Draw.' if winner is None else f'Team {winner.team} wins.'))
    session.end()


def check_timeout(session, *, now=None):
    """End absent-controller waits without partner takeover or reconnect resets."""
    from datetime import datetime
    if not session.state.multi or session.state.multi.get('result'):
        return False
    now = now or timezone.now()
    deadline = datetime.fromisoformat(session.state.multi['deadline'])
    if deadline > now:
        return False
    missing = session._missing_action_positions()
    teams = {label[0] for label in missing}
    if teams:
        forfeit(session, teams, reason='action deadline expired for ' + ', '.join(missing))
        return True
    session.maybe_run_turn(notify_waiting=False)
    return False
