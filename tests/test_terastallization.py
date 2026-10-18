"""Tera rules through real choices, engine damage, AI and checkpoint rebuilds."""

import random
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pokemon.battle.battledata import BattleData, Move, Pokemon, Team, TurnData
from pokemon.battle.damage import damage_calc, stab_multiplier, type_effectiveness
from pokemon.battle.engine import (
    Action,
    ActionType,
    Battle,
    BattleMove,
    BattleParticipant,
    BattleType,
    _select_ai_action,
)
from pokemon.battle.logic import BattleLogic
from pokemon.battle.player_choices import PlayerChoices
from pokemon.battle.state import BattleState
from pokemon.battle.terastallization import TERA_TYPES, Terastallization, tera_power_floor
from pokemon.dex import MOVEDEX
from pokemon.dex.entities import Move as DamageMove
from pokemon.dex.entities import Stats
from pokemon.helpers.pokemon_helpers import get_max_hp
from pokemon.utils.boosts import apply_boost


def pokemon(name, tera_type="", moves=("Tackle", "Water Gun", "Tera Blast")):
    """Build an ordinary battler with canonical health and real move data."""
    mon = Pokemon(name, level=50, tera_type=tera_type, moves=[Move(move) for move in moves])
    mon.max_hp = get_max_hp(mon)
    mon.hp = mon.max_hp
    return mon


def damage_move(name):
    """Load the full move definition required by the damage pipeline."""
    from pokemon.battle._shared import _normalize_key, get_raw

    return DamageMove.from_dict(name, get_raw(MOVEDEX[_normalize_key(name)]))


@pytest.fixture
def session():
    """A doubles session boundary with actual battle state and captured transport."""
    messages = []
    player = SimpleNamespace(id=1, msg=messages.append)
    roster = [pokemon("Squirtle", "Stellar"), pokemon("Eevee", "Water"), pokemon("Pikachu")]
    foes = [pokemon("Vulpix"), pokemon("Bulbasaur")]
    own = BattleParticipant("Player", roster, player=player, team="A", max_active=2)
    foe = BattleParticipant("Opponent", foes, team="B", max_active=2)
    own.active, foe.active = roster[:2], foes
    battle = Battle(BattleType.PVP, [own, foe], rng=random.Random(5))
    data = BattleData(Team("Player", roster), Team("Opponent", foes))
    data.turndata = TurnData(data.teams, teamslots=2)
    state = BattleState.from_battle_data(data, ai_type="PVP")
    logic = BattleLogic(battle, data, state)
    return SimpleNamespace(battle=battle, data=data, state=state, logic=logic, captainA=player,
                           messages=messages, storage=SimpleNamespace(set=Mock()), maybe_run_turn=Mock(),
                           _compact_state_for_persist=lambda value: value)


def activate(session, slot="A1"):
    """Declare Tera and an attack using the real per-slot player choice boundary."""
    choices = PlayerChoices(session, session.captainA)
    choices.tera(actor=slot)
    choices.move("Water Gun", "B1", actor=slot)
    session.battle.lock_choices()
    return session.data.turndata.positions[slot].pokemon


def test_doubles_reservation_and_queued_timing(session):
    """A reservation spends no action; only its actor transforms when locked."""
    choice = PlayerChoices(session, session.captainA)
    choice.tera(actor="A2")
    assert not session.state.declare and not session.battle.tera_used
    assert session.state.tera_pending["A"]["type"] == "Water"
    with pytest.raises(ValueError, match="reserved"):
        choice.tera(actor="A1")
    choice.move("Water Gun", "B1", actor="A2")
    with pytest.raises(ValueError, match="already has an action"):
        choice.tera(actor="A2")
    session.battle.lock_choices()
    assert session.battle.participants[0].active[1].terastallized == "Water"
    assert session.battle.participants[0].active[0].terastallized is None
    with pytest.raises(ValueError, match="already used"):
        PlayerChoices(session, session.captainA).tera(actor="A1")


def test_cancel_and_save_failure_are_reversible(session):
    """Failed storage must not strand a reservation or use the side's allowance."""
    choice = PlayerChoices(session, session.captainA)
    session.storage.set.side_effect = RuntimeError("storage unavailable")
    with pytest.raises(RuntimeError):
        choice.tera(actor="A1")
    assert not session.battle.tera_pending and not session.state.tera_pending
    session.storage.set.side_effect = None
    choice.tera(actor="A1")
    choice.tera(actor="A1", cancel=True)
    assert not session.battle.tera_pending and not session.battle.tera_used
    choice.tera(actor="A2")


@pytest.mark.parametrize("invalid", ("ambiguous", "enemy", "fainted", "context", "ended", "type", "special", "stale"))
def test_invalid_declarations_leave_state_unchanged(session, invalid):
    """Reject wrong controllers, unsupported forms and expired command views."""
    choice = PlayerChoices(session, session.captainA)
    mon = session.battle.participants[0].active[0]
    actor = "A1"
    if invalid == "ambiguous":
        actor = None
    elif invalid == "enemy":
        actor = "B1"
    elif invalid == "fainted":
        mon.hp = 0
    elif invalid == "context":
        session.battle.type = BattleType.SCRIPTED
    elif invalid == "ended":
        session.battle.battle_over = True
    elif invalid == "type":
        mon.tera_type = "Mystery"
    elif invalid == "special":
        mon.species = "Terapagos"
    else:
        session.battle.turn_count += 1
    with pytest.raises(ValueError):
        choice.tera(actor=actor)
    assert not session.battle.tera_pending and not session.battle.tera_used
    session.storage.set.assert_not_called()


def test_pending_survives_checkpoint_before_move(session):
    """Disconnecting before +attack retains the reservation without consuming it."""
    PlayerChoices(session, session.captainA).tera(actor="A2")
    restored = BattleLogic.from_dict(session.logic.to_dict())
    assert restored.battle.tera_pending == session.battle.tera_pending
    assert not restored.battle.tera_used


@pytest.mark.parametrize("species", ("Meganium", "Yanmega"))
def test_ordinary_species_with_mega_in_name_can_terastallize(session, species):
    """Species names are not evidence of an incompatible Mega forme."""
    mon = session.battle.participants[0].active[0]
    mon.species = species
    assert Terastallization.validate(session.battle, session.battle.participants[0], mon) == "Stellar"


@pytest.mark.parametrize("species", (
    "Charizard-Mega-X", "charizardmegay", "Groudon-Primal", "kyogreprimal",
    "Ogerpon-Wellspring", "Terapagos-Stellar",
))
def test_special_formes_remain_ineligible(session, species):
    """Canonical dex identifiers and display forme names remain unsupported."""
    mon = session.battle.participants[0].active[0]
    mon.species = species
    with pytest.raises(ValueError, match="form or transformation"):
        Terastallization.validate(session.battle, session.battle.participants[0], mon)


@pytest.mark.parametrize("tera_type", TERA_TYPES)
def test_all_nineteen_types_rebuild_with_used_side(session, tera_type):
    """Every supported type survives the real roster/position checkpoint path."""
    mon = session.battle.participants[0].active[0]
    ordinary = list(mon.types)
    mon.tera_type = tera_type
    activate(session)
    restored = BattleLogic.from_dict(session.logic.to_dict())
    rebuilt = restored.battle.participants[0].active[0]
    assert rebuilt.terastallized == tera_type
    assert rebuilt.types == (ordinary if tera_type == "Stellar" else [tera_type])
    assert rebuilt.tera_original_types == ordinary and restored.battle.tera_used == {"A"}
    assert not restored.battle.tera_pending


def test_typing_stab_and_adaptability(session):
    """Tera retains original STAB, adds its type, and doubles a matching original."""
    mon = session.battle.participants[0].active[0]
    mon.tera_type = "Fire"
    activate(session)
    assert mon.types == ["Fire"]
    assert stab_multiplier(mon, BattleMove("Water Gun", type="Water")) == 1.5
    assert stab_multiplier(mon, BattleMove("Ember", type="Fire")) == 1.5
    assert type_effectiveness(mon, BattleMove("Water Gun", type="Water")) == 2
    mon.ability = SimpleNamespace(raw={"onModifySTAB": "Adaptability.onModifySTAB"})
    assert stab_multiplier(mon, BattleMove("Ember", type="Fire")) == 2
    assert stab_multiplier(mon, BattleMove("Water Gun", type="Water")) == 1.5
    mon.terastallized = "Water"
    mon._types = ["Water"]
    assert stab_multiplier(mon, BattleMove("Water Gun", type="Water")) == 2.25


def test_stellar_preview_damage_and_spent_types_rebuild(session):
    """AI previews consume nothing; real hits consume one type and persist it."""
    mon = activate(session)
    foe = session.battle.participants[1].active[0]
    move = damage_move("Water Gun")
    assert stab_multiplier(mon, move) == 2
    assert stab_multiplier(mon, move) == 2
    assert not mon.stellar_boosted_types
    first = damage_calc(mon, foe, move, rng=random.Random(8))
    assert first.debug["stab"] == [2]
    assert mon.stellar_boosted_types == ["Water"]
    second = damage_calc(mon, foe, move, rng=random.Random(8))
    assert second.debug["stab"] == [1.5]
    rebuilt = BattleLogic.from_dict(session.logic.to_dict()).battle.participants[0].active[0]
    assert rebuilt.stellar_boosted_types == ["Water"]
    assert stab_multiplier(rebuilt, damage_move("Water Gun")) == 1.5
    assert stab_multiplier(rebuilt, damage_move("Tackle")) == 4915 / 4096


def test_stellar_one_boost_covers_multihit_and_next_use_is_unboosted(session):
    """One use shares its multiplier across hits, including the non-STAB boost."""
    mon = activate(session)
    foe = session.battle.participants[1].active[0]
    move = damage_move("Fury Swipes")
    move.raw = {**move.raw, "multihit": 3}
    first = damage_calc(mon, foe, move, rng=random.Random(1))
    assert first.debug["stab"] == [4915 / 4096] * 3
    assert damage_calc(mon, foe, move, rng=random.Random(1)).debug["stab"] == [1] * 3


@pytest.mark.parametrize("type_,priority,multihit,base,callback,expected", (
    ("Water", 0, None, 40, None, 60), ("Water", 1, None, 40, None, 40),
    ("Water", 0, 2, 40, None, 40), ("Water", 0, None, 0, True, 40),
    ("Fire", 0, None, 40, None, 40),
))
def test_power_floor_exceptions(session, type_, priority, multihit, base, callback, expected):
    """Matching weak attacks gain 60 power without boosting priority/variable moves."""
    session.battle.participants[0].active[0].tera_type = "Water"
    mon = activate(session)
    move = BattleMove("test", type=type_, raw={"priority": priority, "multihit": multihit,
                                             "basePower": base, "basePowerCallback": callback})
    assert tera_power_floor(mon, move, 40) == expected


@pytest.mark.parametrize("move_type", ("Water", "Fire"))
def test_stellar_weak_move_floor_expires_with_its_type_boost(session, move_type):
    """Native and non-native types get 60 power only while their boost is unused."""
    mon = activate(session)
    move = BattleMove("test", type=move_type, raw={"basePower": 40})
    assert tera_power_floor(mon, move, 40) == 60
    assert mon.stellar_boosted_types == []
    mon.stellar_boosted_types.append(move_type)
    assert tera_power_floor(mon, move, 40) == 40
    move._stellar_boosts = {move_type.lower(): True}
    assert tera_power_floor(mon, move, 40) == 40


def test_stellar_spread_power_floor_reads_spent_type_for_each_target(session):
    """Twister's first target consumes its floor; later damage stays at 40 power."""
    from unittest.mock import patch

    from pokemon.battle import damage

    mon = activate(session)
    own, foe = session.battle.participants
    mon.moves.append(Move("Twister"))
    action = Action(own, ActionType.MOVE, foe, move=BattleMove("Twister"), pokemon=mon, target_pokemon=foe.active[0])
    original, powers = damage.base_damage, []

    def record(level, power, *args, **kwargs):
        """Observe power in real damage calculations without replacing the damage."""
        powers.append(power)
        return original(level, power, *args, **kwargs)

    with patch.object(damage, "base_damage", side_effect=record):
        session.battle.use_move(action)
        assert powers == [60, 40]
        powers.clear()
        for member in foe.active:
            member.hp = member.max_hp
        session.battle.use_move(action)
        assert powers == [40, 40]
    assert mon.stellar_boosted_types == ["Dragon"]


def test_tera_blast_stellar_category_effectiveness_and_drop(session):
    """The live move uses boosted offensive stats, Stellar power and its stat cost."""
    mon = activate(session)
    mon.base_stats = Stats(attack=70, special_attack=100, defense=50, special_defense=50, speed=50)
    apply_boost(mon, {"atk": 2})
    foe = session.battle.participants[1].active[0]
    move = BattleMove("Tera Blast")
    session.battle.use_move(Action(session.battle.participants[0], ActionType.MOVE,
                                   session.battle.participants[1], move=move, pokemon=mon, target_pokemon=foe))
    assert move.type == "Stellar" and move.power == 100 and move.raw["category"] == "Physical"
    assert mon.boosts["attack"] == 1 and mon.boosts["special_attack"] == -1
    assert type_effectiveness(foe, move) == 1
    foe.terastallized = "Fire"
    assert type_effectiveness(foe, move) == 2


def test_fixed_typing_switch_and_cleanup(session):
    """Type-changing callbacks and switching do not erase Tera; ending restores it."""
    mon = activate(session, "A2")
    assert not mon.setType("Ghost")
    mon.types = ["Ghost"]
    mon.types.append("Grass")
    assert mon.types == ["Water"]
    session.battle.on_switch_out(mon)
    session.battle.on_enter_battle(mon)
    assert mon.terastallized == "Water" and mon.types == ["Water"]
    session.battle.restore_transforms()
    assert mon.types == ["Normal"] and mon.terastallized is None
    assert not mon.stellar_boosted_types and mon.tera_type == "Water"


def test_ai_opt_in_and_one_side_reservation(session):
    """Only the explicit profile reserves Tera, and siblings cannot claim it twice."""
    own = session.battle.participants[0]
    own.is_ai = True
    mon = own.active[0]
    mon.moves = [Move("Water Gun")]
    _select_ai_action(own, mon, session.battle)
    assert not session.battle.tera_pending
    own.ai_profile = "trainer_tera"
    action = _select_ai_action(own, mon, session.battle)
    assert session.battle.tera_pending["A"]["type"] == "Stellar"
    assert not Terastallization.propose_ai(session.battle, own, action, SimpleNamespace(tera_policy="matching_attack"))
    Terastallization.lock(session.battle, [action])
    assert session.battle.tera_used == {"A"}


@pytest.mark.parametrize("fainted", (False, True))
def test_nonmove_or_fainted_reservation_is_not_consumed(session, fainted):
    """A cancelled move cannot leave a used side or a delayed transformation."""
    choices = PlayerChoices(session, session.captainA)
    choices.tera(actor="A1")
    if fainted:
        choices.move("Water Gun", "B1", actor="A1")
        session.battle.participants[0].active[0].hp = 0
    else:
        choices.switch(3, actor="A1")
    session.battle.lock_choices()
    assert not session.battle.tera_used and not session.battle.tera_pending


def test_stellar_spread_has_same_boost_on_every_target(session):
    """All Surf targets share one use's boost; a second use receives regular STAB."""
    mon = activate(session)
    own, foe = session.battle.participants
    mon.moves.append(Move("Surf"))
    seen = []
    from pokemon.battle import damage
    original = damage.stab_multiplier

    def record(attacker, move, **kwargs):
        """Observe real damage calculation without substituting its result."""
        value = original(attacker, move, **kwargs)
        seen.append(value)
        return value

    from unittest.mock import patch

    action = Action(own, ActionType.MOVE, foe, move=BattleMove("Surf"), pokemon=mon, target_pokemon=foe.active[0])
    with patch.object(damage, "stab_multiplier", side_effect=record):
        session.battle.use_move(action)
    assert seen == [2] * 3
    seen.clear()
    for part in (own, foe):
        for member in part.active:
            member.hp = member.max_hp
    with patch.object(damage, "stab_multiplier", side_effect=record):
        session.battle.use_move(action)
    assert seen == [1.5] * 3


def test_stellar_tera_blast_pays_cost_on_substitute(session):
    """A successful hit on a substitute still pays Stellar Tera Blast's cost."""
    mon = activate(session)
    own, foe = session.battle.participants
    target = foe.active[0]
    target.volatiles["substitute"] = {"hp": 20}
    hp = target.hp
    session.battle.use_move(Action(own, ActionType.MOVE, foe, move=BattleMove("Tera Blast"),
                                   pokemon=mon, target_pokemon=target))
    assert target.hp == hp
    assert mon.boosts["attack"] == mon.boosts["special_attack"] == -1


def test_duplicate_ephemeral_identity_still_targets_reserved_slot(session):
    """Two identical runtime battlers remain distinguishable by field slot."""
    own = session.battle.participants[0]
    own.pokemons[1].name = own.pokemons[0].name
    own.pokemons[1].level = own.pokemons[0].level
    own.pokemons[1].max_hp = own.pokemons[0].max_hp
    mon = activate(session, "A2")
    assert mon.terastallized == "Water" and own.active[0].terastallized is None


def test_transform_after_tera_cannot_restore_tera_typing_at_battle_end(session):
    """Transform's backup of a Tera type must not outlive Tera cleanup."""
    mon = activate(session, "A2")
    own, foe = session.battle.participants
    session.battle.use_move(Action(own, ActionType.MOVE, foe, move=BattleMove("Transform"),
                                   pokemon=mon, target_pokemon=foe.active[0]))
    assert mon.transformed and mon.types == ["Water"]
    session.battle.restore_transforms()
    assert mon.species == "Eevee" and mon.types == ["Normal"]
    assert mon.terastallized is None and not mon.transformed
