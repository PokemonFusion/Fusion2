"""Toxic Chain must affect the damaged foe through the real source-hit event."""

import random

import pytest

from .helpers import build_battle, load_modules


def strike(monkeypatch, *, name="Tackle", chance=0, ability="No Ability", item="", status=None,
           suppressed=False, magic_room=False, substitute=False, incoming=False, types=("Normal",)):
    """Qualify a real hit; fixed chance is confined to this unit process."""
    from pokemon.battle.actions import Action, ActionType
    from pokemon.dex.functions import abilities_funcs

    monkeypatch.setattr(abilities_funcs, "random", lambda: chance)
    battle, holder, foe = build_battle(
        attacker_ability="Toxic Chain", defender_ability=ability,
        attacker_types=["Poison", "Fighting"], defender_types=list(types),
    )
    battle.rng = random.Random(0)
    foe.ability_suppressed = suppressed
    if item:
        assert battle.set_item(foe, item)
    foe.status = status
    if magic_room:
        battle.field.pseudo_weather["magicroom"] = {"duration": 5}
    if substitute:
        foe.volatiles["substitute"] = {"hp": 50}
    user, target = (foe, holder) if incoming else (holder, foe)
    action = Action(battle.participant_for(user), ActionType.MOVE,
                    battle.participant_for(target), load_modules()["BattleMove"](name), pokemon=user)
    battle.use_move(action)
    assert not getattr(battle, "_callback_failures", [])
    return holder, foe


@pytest.mark.parametrize("name", ["Tackle", "Water Gun"])
def test_toxic_chain_poisons_the_hit_foe_for_contact_and_noncontact(monkeypatch, name):
    holder, foe = strike(monkeypatch, name=name)
    assert foe.hp < foe.max_hp
    assert foe.status == "tox"
    assert not holder.status


def test_toxic_chain_respects_failed_chance_roll(monkeypatch):
    holder, foe = strike(monkeypatch, chance=.9)
    assert foe.hp < foe.max_hp and not foe.status and not holder.status


def test_toxic_chain_preserves_existing_status(monkeypatch):
    _, foe = strike(monkeypatch, status="par")
    assert foe.status == "par"


@pytest.mark.parametrize("types", [("Poison",), ("Steel",)])
def test_toxic_chain_preserves_native_poison_immunities(monkeypatch, types):
    _, foe = strike(monkeypatch, types=types)
    assert foe.hp < foe.max_hp and not foe.status


@pytest.mark.parametrize("ability,item", [("Shield Dust", ""), ("No Ability", "Covert Cloak")])
def test_toxic_chain_respects_its_special_prevention_rules(monkeypatch, ability, item):
    _, foe = strike(monkeypatch, ability=ability, item=item)
    assert foe.hp < foe.max_hp and not foe.status


def test_toxic_chain_does_not_use_suppressed_shield_dust(monkeypatch):
    _, foe = strike(monkeypatch, ability="Shield Dust", suppressed=True)
    assert foe.status == "tox"


@pytest.mark.parametrize("ability,magic_room", [("Klutz", False), ("No Ability", True)])
def test_toxic_chain_does_not_use_inactive_covert_cloak(monkeypatch, ability, magic_room):
    _, foe = strike(monkeypatch, ability=ability, item="Covert Cloak", magic_room=magic_room)
    assert foe.status == "tox"


def test_toxic_chain_does_not_poison_through_substitute(monkeypatch):
    _, foe = strike(monkeypatch, substitute=True)
    assert not foe.status and foe.hp == foe.max_hp


def test_toxic_chain_does_not_turn_status_moves_into_toxic_poison(monkeypatch):
    _, foe = strike(monkeypatch, name="Growl")
    assert not foe.status


def test_toxic_chain_does_not_poison_the_holder_or_an_incoming_attacker(monkeypatch):
    holder, foe = strike(monkeypatch, incoming=True)
    assert holder.hp < holder.max_hp
    assert not holder.status and not foe.status
