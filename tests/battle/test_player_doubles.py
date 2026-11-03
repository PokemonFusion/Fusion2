"""Per-slot player actions, legal targets, persistence and stable doubles slots."""

from __future__ import annotations

import random
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pokemon.battle.active_slots import active_at, active_slots
from pokemon.battle.battledata import BattleData, Move, Pokemon, Team, TurnData
from pokemon.battle.engine import ActionType, Battle, BattleParticipant, BattleType
from pokemon.battle.logic import BattleLogic
from pokemon.battle.player_choices import PlayerChoices
from pokemon.battle.state import BattleState


@pytest.fixture
def session():
    """Use actual engine, position and state models with a memory-only transport."""
    messages = []
    player = SimpleNamespace(id=1, msg=messages.append)
    roster = [Pokemon(name, level=20, moves=[Move(move) for move in
              ("Tackle", "Water Gun", "Surf", "Helping Hand", "Swords Dance", "Growl")])
              for name in ("Squirtle", "Eevee", "Pikachu")]
    foe_roster = [Pokemon(name, level=20, moves=[Move("Tackle")]) for name in ("Vulpix", "Bulbasaur")]
    own = BattleParticipant("Player", roster, player=player, team="A", max_active=2)
    foe = BattleParticipant("Opponent", foe_roster, team="B", max_active=2)
    own.active, foe.active = roster[:2], foe_roster[:2]
    battle = Battle(BattleType.PVP, [own, foe], rng=random.Random(2))
    data = BattleData(Team("Player", roster), Team("Opponent", foe_roster))
    data.turndata = TurnData(data.teams, teamslots=2)
    state = BattleState.from_battle_data(data, ai_type="PVP")
    logic = BattleLogic(battle, data, state)
    return SimpleNamespace(battle=battle, data=data, state=state, logic=logic, storage=SimpleNamespace(set=Mock()),
                           captainA=player, messages=messages, maybe_run_turn=Mock(),
                           _compact_state_for_persist=lambda state: state)


def choices(session):
    """Construct a fresh command view for the fixture's normal player."""
    return PlayerChoices(session, session.captainA)


def test_two_independent_actions_and_duplicate_guard(session):
    """The second actor cannot overwrite the first actor's queued action."""
    choices(session).move("Water Gun", "B2", actor="A1")
    first = session.battle.participants[0].pending_action
    with pytest.raises(ValueError, match="already has an action"):
        choices(session).move("Tackle", "B1", actor="A1")
    choices(session).move("Tackle", "B1", actor="A2")
    assert session.battle.participants[0].pending_action[0] is first
    assert len(session.battle.participants[0].pending_action) == 2
    assert set(session.state.declare) == {"A1", "A2"}


def test_actor_and_target_ambiguity_does_not_mutate(session):
    """Missing or foreign actor/target tokens leave the queue unchanged."""
    for actor, target in ((None, "B1"), ("B1", "B2"), ("A1", None), ("A1", "B3"), ("A1", "A1")):
        with pytest.raises(ValueError):
            choices(session).move("Tackle", target, actor=actor)
    assert not session.state.declare
    assert session.battle.participants[0].pending_action is None


@pytest.mark.parametrize("remaining", (0, 2))
def test_owned_remaining_pp_controls_ordinary_choice(session, remaining):
    """Name-only runtime moves cannot refill exhausted saved active slots."""
    pokemon = session.battle.participants[0].active[0]
    pokemon.moves = [Move("Tackle")]
    pokemon.activemoveslot_set = [SimpleNamespace(move=SimpleNamespace(name="Tackle"), current_pp=remaining)]
    if remaining == 0:
        with pytest.raises(ValueError, match="cannot use that move"):
            choices(session).move("Tackle", "B1", actor="A1")
        assert session.battle.participants[0].pending_action is None
        assert not session.state.declare
        assert choices(session).legal_moves(pokemon)[0].move.name == "Struggle"
    else:
        choices(session).move("Tackle", "B1", actor="A1")
        assert session.battle.participants[0].pending_action.move.pp == remaining


def test_temporary_copied_slot_keeps_independent_pp(session):
    """A virtual copied move may match an exhausted owned move in another slot."""
    pokemon = session.battle.participants[0].active[0]
    pokemon.moves = [Move("Tackle")]
    pokemon.moves[0].pp = 5
    pokemon.tempvals["copy_state"] = {"original_slots": {"0": {"name": "Mimic", "pp": 9}}}
    pokemon.activemoveslot_set = [SimpleNamespace(move=SimpleNamespace(name="Tackle"), current_pp=0)]
    choices(session).move("Tackle", "B1", actor="A1")
    assert session.battle.participants[0].pending_action.move.pp == 5


def test_self_and_ally_targets_follow_metadata(session):
    """Self and ally moves do not silently select the first foe or the wrong ally."""
    choices(session).move("Helping Hand", actor="A1")
    action = session.battle.participants[0].pending_action
    assert action.target_pokemon is session.battle.participants[0].active[1]
    choices(session).move("Swords Dance", actor="A2")
    second = session.battle.participants[0].pending_action[1]
    assert second.target_pokemon is second.pokemon


@pytest.mark.parametrize("move,affected", (("Surf", {"A2", "B1", "B2"}), ("Growl", {"B1", "B2"})))
def test_spread_needs_no_target_and_announces_set(session, move, affected):
    """The queue announces the actual spread set with no irrelevant target prompt."""
    choices(session).move(move, actor="A1")
    message = session.messages[-1]
    assert all(label in message for label in affected)
    action = session.battle.participants[0].pending_action
    before = {name: pos.pokemon.hp for name, pos in session.data.turndata.positions.items()}
    session.battle.use_move(action)
    for name in affected:
        mon = session.data.turndata.positions[name].pokemon
        assert mon.hp < before[name] if move == "Surf" else mon.boosts["attack"] == -1
    if move == "Surf":
        assert action.pokemon.moves[2].pp == 14


def test_switch_reservation_and_exact_slot(session):
    """One reserve cannot be booked twice, and A2 switching preserves A1."""
    player = session.battle.participants[0]
    lead, second, reserve = player.pokemons
    choices(session).switch(3, actor="A2")
    with pytest.raises(ValueError, match="cannot switch"):
        choices(session).switch(3, actor="A1")
    action = player.pending_action
    assert action.action_type is ActionType.SWITCH
    session.battle.execute_actions([action])
    assert active_at(player, 0) is lead
    assert active_at(player, 1) is reserve
    assert second not in player.active


def test_gapped_party_switch_keeps_sibling_double_action(session):
    """Canonical slot six maps to reserve three without overwriting A1's move."""
    player = session.battle.participants[0]
    for index, pokemon in enumerate(player.pokemons):
        pokemon.model_id = f"owned:{index}"
    models = [SimpleNamespace(unique_id=str(index)) for index in range(3)]
    session.captainA.storage = SimpleNamespace(get_party_slots=lambda: [None, models[0], None, models[1], None, models[2]])
    with pytest.raises(ValueError, match="Invalid Pokémon slot"):
        choices(session).switch(3, actor="A2")
    assert not session.state.declare
    choices(session).move("Tackle", "B1", actor="A1")
    first = player.pending_action
    choices(session).switch(6, actor="A2")
    assert player.pending_action[0] is first
    assert player.pending_action[1].pokemon is player.pokemons[2]
    assert session.state.declare["A2"]["switch"] == 3


def test_fainting_preserves_surviving_slot_and_checkpoint(session):
    """A2 stays A2 when A1 faints, including when no reserve remains."""
    player = session.battle.participants[0]
    lead, second, reserve = player.pokemons
    active_slots(player)
    lead.hp = reserve.hp = 0
    session.battle.run_faint()
    assert active_at(player, 0) is None
    assert active_at(player, 1) is second
    session.data.turndata.positions["A1"].pokemon = None
    restored = BattleLogic.from_dict(session.logic.to_dict())
    assert active_at(restored.battle.participants[0], 0) is None
    assert active_at(restored.battle.participants[0], 1).name == second.name


def test_stale_menu_view_and_save_failure_leave_no_choice(session):
    """Expired views and failed saves cannot leave phantom actions in memory."""
    view = choices(session)
    session.battle.turn_count += 1
    with pytest.raises(ValueError, match="earlier turn"):
        view.move("Tackle", "B1", actor="A1")
    session.storage.set.side_effect = RuntimeError("storage unavailable")
    with pytest.raises(RuntimeError):
        choices(session).move("Tackle", "B1", actor="A1")
    assert not session.state.declare
    assert not session.data.turndata.positions["A1"].getAction()
    assert session.battle.participants[0].pending_action is None


def test_medicine_targets_the_selected_actor(session):
    """A2 medicine neither heals nor consumes an action for A1."""
    player = session.battle.participants[0]
    player.inventory = {"Potion": 1}
    lead, second = player.active
    lead.hp = second.hp = 1
    choices(session).item("Potion", actor="A2")
    action = player.pending_action
    session.battle.execute_actions([action])
    assert lead.hp == 1
    assert second.hp > 1
    assert not player.inventory


def test_late_invalidated_human_action_does_not_attack(session):
    """A forced-out battler's selected move cannot execute from the bench."""
    player = session.battle.participants[0]
    choices(session).move("Water Gun", "B1", actor="A1")
    actions = session.battle.select_actions()
    assert actions[0].player_selected
    session.battle.switch_pokemon(player, player.pokemons[2], slot=0)
    before = session.battle.participants[1].active[0].hp
    session.battle.execute_actions(actions)
    assert session.battle.participants[1].active[0].hp == before


@pytest.mark.parametrize("move", ("Howl", "Life Dew"))
def test_group_support_targets_each_active_ally_once(session, move):
    """Group support moves affect both living allies with one PP charge."""
    own = session.battle.participants[0]
    own.active[0].moves = [Move(move)]
    for mon in own.active:
        mon.hp = 1
    choices(session).move(move, actor="A1")
    session.battle.use_move(own.pending_action)
    for mon in own.active:
        if move == "Howl":
            assert mon.boosts["attack"] == 1
        else:
            assert mon.hp == 1 + mon.max_hp // 4
