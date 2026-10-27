"""Four independent controllers over two shared battle sides and stable positions."""

from collections.abc import Mapping, MutableSequence

from .engine import BattleSide

POSITIONS = ('A1', 'A2', 'B1', 'B2')
SIDE_FIELDS = ('conditions', 'hazards', 'screens', 'volatiles', 'used_items', 'slot_conditions')


class TeamSide(BattleSide):
    """Share effects while each participant retains its own active/reserve lists."""

    def __init__(self, team, controllers):
        """Bind aggregate read views independently of legacy side assignments."""
        self.team, self.controllers = team, controllers
        super().__init__()

    @property
    def active(self):
        """Return living field occupants in physical position order."""
        return [mon for part in sorted(self.controllers, key=lambda part: part.field_position)
                for mon in part.active if mon.hp > 0]

    @active.setter
    def active(self, value):
        """Participant compatibility writes cannot replace a teammate's roster."""
        pass

    @property
    def pokemons(self):
        """Expose team members for side effects without transferring control."""
        return [mon for part in self.controllers for mon in part.pokemons]

    @pokemons.setter
    def pokemons(self, value):
        """Keep the per-controller rosters authoritative under legacy setters."""
        pass


def bind_sides(battle):
    """Attach one effect state per team without sharing controller rosters."""
    battle.sides = []
    battle.multi = True
    for team in ('A', 'B'):
        members = [part for part in battle.participants if part.team == team]
        side = TeamSide(team, members)
        for part in members:
            part.side = side
            for mon in part.pokemons:
                mon.side = side
        battle.sides.append(side)


def _freeze(value):
    """Keep side references primitive rather than pickling controller graphs."""
    from ._shared import snapshot_battle_value
    if isinstance(value, TeamSide):
        return {'__pf2_multi_side__': value.team}
    if isinstance(value, Mapping):
        return {key: _freeze(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_freeze(item) for item in value]
    return snapshot_battle_value(value)


def _restore(value, pokemon, field, sides):
    """Rebind shared sides and ordinary Pokemon/move/field references."""
    from ._shared import restore_battle_value
    if isinstance(value, Mapping):
        if set(value) == {'__pf2_multi_side__'}:
            return sides[value['__pf2_multi_side__']]
        if any(str(key).startswith('__pf2_') for key in value):
            return restore_battle_value(value, pokemon, field=field)
        return {key: _restore(item, pokemon, field, sides) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_restore(item, pokemon, field, sides) for item in value]
    return value


def freeze(logic):
    """Checkpoint all controllers and both shared effect states exactly once."""
    from .battledata import Team
    from .logic import _participant_identifier
    battle, data, state = logic.battle, logic.data, logic.state
    if not state.multi:
        return
    controllers = {}
    for part in battle.participants:
        identity = part.controller_id
        controllers[identity] = {'trainer': int(identity), 'name': part.name,
            'team': part.team, 'position': part.field_position,
            'roster': [_participant_identifier(mon) for mon in part.pokemons]}
    state.multi['controllers'] = controllers
    for team in ('A', 'B'):
        members = [part for part in battle.participants if part.team == team]
        data.teams[team] = Team(' / '.join(part.name for part in members),
                               [mon for part in members for mon in part.pokemons])
    state.participants = {part.controller_id: [_participant_identifier(mon) for mon in part.participating_pokemon]
                          for part in battle.participants}
    state.flee_attempts = {part.controller_id: int(getattr(part, 'flee_attempts', 0)) for part in battle.participants}
    state.multi['sides'] = {side.team: {name: _freeze(getattr(side, name)) for name in SIDE_FIELDS} for side in battle.sides}


def rebuild(logic_class, data, state):
    """Restore exact saved controllers; never guess by team order or nickname."""
    from .engine import Battle, BattleParticipant, BattleType
    from .logic import _participant_identifier
    info = state.multi
    if not isinstance(info, Mapping) or type(info.get('version')) is not int or info.get('version') != 1:
        raise ValueError('Unsupported Multi Battle checkpoint.')
    saved = info.get('controllers')
    if not isinstance(saved, Mapping) or len(saved) != 4:
        raise ValueError('Multi Battle requires four saved controllers.')
    all_mons = [mon for team in data.teams.values() for mon in team.returnlist() if mon]
    by_ref = {_participant_identifier(mon): mon for mon in all_mons}
    if len(by_ref) != len(all_mons):
        raise ValueError('Multi Battle has duplicate Pokemon identities.')
    parts, claimed, labels = [], set(), set()
    positions = data.turndata.positions
    if set(positions) != set(POSITIONS):
        raise ValueError('Multi Battle is missing its four saved physical positions.')
    for identity, binding in sorted(saved.items()):
        trainer = binding.get('trainer')
        label, team, refs = binding.get('position'), binding.get('team'), binding.get('roster')
        if (type(trainer) is not int or trainer <= 0 or str(trainer) != identity
                or label not in POSITIONS or label in labels or team != label[0]
                or not isinstance(refs, (list, tuple, MutableSequence)) or not refs or any(ref not in by_ref or ref in claimed for ref in refs)
                or len(refs) != len(set(refs))
                or any(str(state.pokemon_control.get(ref)) != identity for ref in refs)):
            raise ValueError('Invalid saved Multi controller/roster/position mapping.')
        roster = [by_ref[ref] for ref in refs]
        part = BattleParticipant(binding['name'], roster, team=team, max_active=1)
        part.controller_id, part.field_position = identity, label
        old = getattr(positions.get(label), 'pokemon', None)
        active_ref = _participant_identifier(old) if old else None
        if active_ref and active_ref not in refs:
            raise ValueError('Saved Multi field occupant belongs to another controller.')
        active = by_ref.get(active_ref)
        conscious = [mon for mon in roster if mon.hp > 0]
        if active is not None and active.hp <= 0:
            active = None
        if active is None and conscious:
            raise ValueError('Saved Multi controller is missing a living active member.')
        part.active = [active] if active else []
        part._active_slots = {0: active} if active else {}
        part.has_lost = not conscious
        positions[label].pokemon = active
        claimed.update(refs)
        labels.add(label)
        parts.append(part)
    if labels != set(POSITIONS) or claimed != set(by_ref):
        raise ValueError('Multi checkpoint contains unassigned controllers or Pokemon.')
    battle = Battle(BattleType.PVP, parts)
    bind_sides(battle)
    sides = {side.team: side for side in battle.sides}
    for part in parts:
        for mon in part.pokemons:
            for attr in ('tempvals', 'volatiles', 'ability_state', 'item_state', 'last_move'):
                setattr(mon, attr, _restore(getattr(mon, attr, None), by_ref, data.field, sides))
    for attr in ('weather_state', 'terrain_state', 'pseudo_weather'):
        setattr(data.field, attr, _restore(getattr(data.field, attr), by_ref, data.field, sides))
    for team, side in sides.items():
        saved_side = info.get('sides', {}).get(team, {})
        for attr in SIDE_FIELDS:
            if attr in saved_side:
                value = _restore(saved_side[attr], by_ref, data.field, sides)
                if attr == 'slot_conditions':
                    value = {int(slot): states for slot, states in value.items()}
                setattr(side, attr, value)
        side.sideConditions = side.conditions
    battle.field = data.field
    for name in ('weather', 'terrain'):
        effect = getattr(data.field, name, None)
        setattr(data.field, name + '_handler', battle._lookup_effect(effect) if effect else None)
    battle.weather_state, battle.turn_count = data.field.weather_state, data.battle.turn
    logic = logic_class(battle, data, state)
    for part in parts:
        saved_refs = state.participants.get(part.controller_id, [])
        part.participating_pokemon, part._participant_cache = [], set()
        for mon in part.pokemons:
            if _participant_identifier(mon) in saved_refs:
                part.record_participation(mon)
    return logic


def attach_players(session):
    """Attach exact persistent characters independently of saved participant order."""
    from utils.character_reads import persistent_character, existing_trainer
    players = {str(player.pk): player for player in session.teamA + session.teamB}
    for part in session.battle.participants:
        if not getattr(part, 'controller_id', None):
            raise ValueError('Multi participant is missing its controller identity.')
        player = players.get(part.controller_id)
        if player is None or not persistent_character(player):
            raise ValueError('Multi Battle is missing a saved character controller.')
        trainer = existing_trainer(player)
        if trainer is None:
            raise ValueError('Multi controller is missing its existing trainer data.')
        part.player, part.trainer = player, trainer
        player.team, player.active_pokemon = part.pokemons, part.active[0] if part.active else None
    session.trainers = list(players.values())
