"""Tests for expanded scoped-holder event routing."""

from __future__ import annotations

from .helpers import build_battle, load_modules


class _SideAfterSetStatusHandler:
    def __init__(self):
        self.calls = 0

    def onAfterSetStatus(self, target, source, effect, **kwargs):
        self.calls += 1
        return True


class _FieldTryHealHandler:
    def __init__(self):
        self.calls = 0

    def onTryHeal(self, amount, target, source, effect, **kwargs):
        self.calls += 1
        return False


class _AllyFaintVolatileHandler:
    def __init__(self):
        self.calls = 0

    def onAllyFaint(self, target, source, effect, **kwargs):
        self.calls += 1
        return None


def test_targeted_events_reach_side_condition_handlers():
    battle, attacker, defender = build_battle()
    handler = _SideAfterSetStatusHandler()
    defender_side = battle.participants[1].side
    defender_side.conditions["watchstatus"] = {"id": "watchstatus"}

    battle._lookup_effect = lambda name: handler if name == "watchstatus" else None

    assert battle.apply_status_condition(defender, "brn", source=attacker, effect="test")
    assert handler.calls == 1


def test_targeted_events_reach_field_effect_handlers():
    battle, attacker, _ = build_battle()
    handler = _FieldTryHealHandler()
    battle.field.pseudo_weather["healwatch"] = {"id": "healwatch"}
    battle._lookup_effect = lambda name: handler if name == "healwatch" else None
    attacker.hp = 100

    healed = battle.heal(attacker, 40, source=attacker, effect="test")

    assert healed == 0
    assert handler.calls == 1


def test_ally_volatiles_receive_faint_events():
    modules = load_modules()
    Pokemon = modules["Pokemon"]
    Battle = modules["Battle"]
    BattleParticipant = modules["BattleParticipant"]
    BattleType = modules["BattleType"]

    lead = Pokemon("Lead", level=50, hp=0, max_hp=200)
    partner = Pokemon("Partner", level=50, hp=200, max_hp=200)
    foe = Pokemon("Foe", level=50, hp=200, max_hp=200)

    for mon in (lead, partner, foe):
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

    partner.volatiles["watchallyfaint"] = {"id": "watchallyfaint"}
    handler = _AllyFaintVolatileHandler()

    import pokemon.dex.functions.moves_funcs as moves_funcs

    original = moves_funcs.VOLATILE_HANDLERS.get("watchallyfaint")
    moves_funcs.VOLATILE_HANDLERS["watchallyfaint"] = handler
    try:
        part1 = BattleParticipant("P1", [lead, partner])
        part2 = BattleParticipant("P2", [foe])
        part1.active = [lead, partner]
        part2.active = [foe]
        battle = Battle(BattleType.WILD, [part1, part2])
        lead.battle = battle
        partner.battle = battle
        foe.battle = battle

        battle.on_faint(lead)

        assert handler.calls == 1
    finally:
        if original is None:
            moves_funcs.VOLATILE_HANDLERS.pop("watchallyfaint", None)
        else:
            moves_funcs.VOLATILE_HANDLERS["watchallyfaint"] = original
