"""Tests for boost, switch, PP, and faint event routing."""

from __future__ import annotations

from pokemon.utils.boosts import apply_boost

from .helpers import build_battle, load_modules, physical_move


class _BoostAbility:
    def __init__(self):
        self.after_each = 0
        self.after = 0

    def call(self, func: str, *args, **kwargs):
        if func == "onChangeBoost":
            boost = args[0]
            boost["atk"] = boost.get("atk", 0) + 1
        elif func == "onTryBoost":
            return args[0]
        elif func == "onAfterEachBoost":
            self.after_each += 1
        elif func == "onAfterBoost":
            self.after += 1
        return None


class _BlockSwitchAbility:
    def call(self, func: str, *args, **kwargs):
        if func == "onBeforeSwitchOut":
            return False
        return None


class _SwitchInAbility:
    def __init__(self):
        self.calls = 0

    def call(self, func: str, *args, **kwargs):
        if func == "onBeforeSwitchIn":
            self.calls += 1
        return None


class _SwitchOutAbility:
    def __init__(self):
        self.calls = 0

    def call(self, func: str, *args, **kwargs):
        if func == "onSwitchOut":
            self.calls += 1
        return None


class _AllySwitchInAbility:
    def __init__(self):
        self.calls = 0

    def call(self, func: str, *args, **kwargs):
        if func == "onAllySwitchIn":
            self.calls += 1
        return None


class _DeductPPAbility:
    def call(self, func: str, *args, **kwargs):
        if func == "onDeductPP":
            return 2
        return None


class _AnyFaintAbility:
    def __init__(self):
        self.calls = 0

    def call(self, func: str, *args, **kwargs):
        if func == "onAnyFaint":
            self.calls += 1
        return None


def _reserve_copy(template, *, ability=None):
    reserve = type(template)("Reserve", level=50, hp=200, max_hp=200)
    reserve.base_stats = template.base_stats
    reserve.types = ["Normal"]
    reserve.boosts = dict(template.boosts)
    reserve.tempvals = {}
    reserve.volatiles = {}
    reserve.ability = ability
    return reserve


def test_apply_boost_runs_showdown_style_boost_events():
    battle, attacker, _ = build_battle()
    attacker.ability = _BoostAbility()

    apply_boost(attacker, {"atk": 1}, source=attacker, effect="move:howl")

    assert attacker.boosts["attack"] == 2
    assert attacker.ability.after_each == 1
    assert attacker.ability.after == 1


def test_switch_pokemon_honors_before_switch_out_gate():
    battle, attacker, _ = build_battle(attacker_ability=_BlockSwitchAbility())
    participant = battle.participants[0]
    reserve = _reserve_copy(attacker)
    reserve.side = participant.side
    reserve.battle = battle
    participant.pokemons.append(reserve)

    battle.switch_pokemon(participant, reserve)

    assert participant.active[0] is attacker


def test_switch_pokemon_runs_before_switch_in_event():
    battle, attacker, _ = build_battle()
    participant = battle.participants[0]
    switch_in = _SwitchInAbility()
    reserve = _reserve_copy(attacker, ability=switch_in)
    reserve.side = participant.side
    reserve.battle = battle
    participant.pokemons.append(reserve)

    battle.switch_pokemon(participant, reserve)

    assert participant.active[0] is reserve
    assert switch_in.calls == 1


def test_switch_pokemon_runs_switch_out_event_for_leaving_pokemon():
    battle, attacker, _ = build_battle(attacker_ability=_SwitchOutAbility())
    participant = battle.participants[0]
    reserve = _reserve_copy(attacker)
    reserve.side = participant.side
    reserve.battle = battle
    participant.pokemons.append(reserve)

    battle.switch_pokemon(participant, reserve)

    assert attacker.ability.calls == 1


def test_switch_in_emits_ally_switch_in_for_partner_holders():
    modules = load_modules()
    Pokemon = modules["Pokemon"]
    Battle = modules["Battle"]
    BattleParticipant = modules["BattleParticipant"]
    BattleType = modules["BattleType"]

    lead = Pokemon("Lead", level=50, hp=200, max_hp=200)
    partner = Pokemon("Partner", level=50, hp=200, max_hp=200, ability=_AllySwitchInAbility())
    reserve = Pokemon("Reserve", level=50, hp=200, max_hp=200)
    foe = Pokemon("Foe", level=50, hp=200, max_hp=200)

    for mon in (lead, partner, reserve, foe):
        mon.types = ["Normal"]
        mon.boosts = {
            "attack": 0,
            "defense": 0,
            "special_attack": 0,
            "special_defense": 0,
            "speed": 0,
            "accuracy": 0,
            "evasion": 0,
        }

    part1 = BattleParticipant("P1", [lead, partner, reserve])
    part2 = BattleParticipant("P2", [foe])
    part1.max_active = 2
    part2.max_active = 1
    part1.active = [lead, partner]
    part2.active = [foe]

    battle = Battle(BattleType.WILD, [part1, part2])
    for mon in (lead, partner, reserve, foe):
        mon.battle = battle
    reserve.side = part1.side
    reserve.battle = battle

    battle.switch_pokemon(part1, reserve, slot=0)

    assert partner.ability.calls == 1


def test_deduct_pp_uses_deduct_pp_event_result():
    battle, attacker, _ = build_battle(attacker_ability=_DeductPPAbility())
    move = physical_move(name="Tackle", power=40)
    move.pp = 5
    attacker.moves = [move]

    battle.deduct_pp(attacker, move)

    assert move.pp == 3


def test_on_any_faint_runs_for_other_active_abilities():
    battle, attacker, defender = build_battle()
    watcher = _AnyFaintAbility()
    defender.ability = watcher
    attacker.hp = 0

    battle.run_faint()

    assert attacker.is_fainted is True
    assert watcher.calls == 1
