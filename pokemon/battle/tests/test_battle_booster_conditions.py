"""Critical damage and source-aware timed Mist through actual battle consumers."""

import random
from types import SimpleNamespace

import pytest

from pokemon.battle.battle_boosters import BattleBoosters
from pokemon.battle.damage import damage_calc
from pokemon.utils.boosts import apply_boost
from .helpers import build_battle
from .test_boost_switch_pp_event_flow import _reserve_copy
from .test_pending_action_effects import action


class FixedRoll(random.Random):
    """Pin the critical boundary while retaining ordinary damage calculation."""

    def __init__(self, value):
        super().__init__(17)
        self.value = value

    def random(self):
        return self.value


@pytest.mark.parametrize("value,critical", [(0.25, True), (0.75, False)])
def test_dire_hit_focus_energy_adds_exactly_two_at_the_critical_consumer(value, critical):
    """A real critical outcome distinguishes two stages from accidental double-counting."""
    battle, user, foe = build_battle()
    assert BattleBoosters.apply_effect(battle, "Dire Hit", user)
    state = user.volatiles["focusenergy"]
    assert state["source"] is user and state["target"] is user
    assert state["sourceEffect"] == "item:direhit"
    assert battle.runEvent("ModifyCritRatio", user, foe, None, 0) == 2
    selected = action(battle, user, foe, "Tackle")
    result = damage_calc(user, foe, selected.move, battle=battle, rng=FixedRoll(value))
    assert result.debug["critical"] == [critical]
    assert result.debug["damage"][0] > 0
    assert not BattleBoosters.useful("Dire Hit", user)
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("ability", [None, "Battle Armor", "Shell Armor"])
def test_focus_combines_with_held_bonus_and_real_critical_prevention(ability):
    """An extra critical stage guarantees crits until a real prevention ability blocks them."""
    battle, user, foe = build_battle(defender_ability=ability)
    user.item = "Scope Lens"
    BattleBoosters.apply_effect(battle, "Dire Hit", user)
    selected = action(battle, user, foe, "Tackle")
    result = damage_calc(user, foe, selected.move, battle=battle, rng=FixedRoll(0.99))
    assert result.debug["critical"] == [ability is None]
    assert result.debug["damage"][0] > 0


def test_focus_ordinary_switch_and_faint_clear_the_real_volatile():
    """Normal switching and faint cleanup do not leave a critical boost behind."""
    battle, user, foe = build_battle()
    reserve = _reserve_copy(user)
    battle.participants[0].pokemons.append(reserve)
    reserve.side, reserve.battle = user.side, battle
    BattleBoosters.apply_effect(battle, "Dire Hit", user)
    battle.switch_pokemon(battle.participants[0], reserve)
    assert "focusenergy" not in user.volatiles and "focusenergy" not in reserve.volatiles
    BattleBoosters.apply_effect(battle, "Dire Hit", reserve)
    reserve.hp = 0
    battle.on_faint(reserve)
    assert "focusenergy" not in reserve.volatiles


def test_focus_deliberate_normal_baton_pass_preserves_one_bound_recipient_state():
    """The supported normal Baton Pass path transfers Focus Energy without retaining it on the bench."""
    battle, user, foe = build_battle()
    reserve = _reserve_copy(user)
    battle.participants[0].pokemons.append(reserve)
    reserve.side, reserve.battle = user.side, battle
    BattleBoosters.apply_effect(battle, "Dire Hit", user)
    battle.use_move(action(battle, user, user, "Baton Pass"))
    battle.run_switch()
    assert battle.participants[0].active[0] is reserve
    assert "focusenergy" not in user.volatiles
    assert reserve.volatiles["focusenergy"]["target"] is reserve
    assert reserve.volatiles["focusenergy"]["source"] is user
    assert battle.runEvent("ModifyCritRatio", reserve, foe, None, 0) == 2


@pytest.mark.parametrize("normal_move", [False, True])
def test_bag_and_ordinary_mist_block_real_growl_and_expire_in_five_residuals(normal_move):
    """The shared Mist repair protects and expires for both producers."""
    battle, user, foe = build_battle()
    if normal_move:
        battle.use_move(action(battle, user, user, "Mist"))
    else:
        assert BattleBoosters.apply_effect(battle, "Guard Spec.", user)
    assert user.side.conditions["mist"]["duration"] == 5
    assert not BattleBoosters.useful("Guard Spec.", user)
    battle.use_move(action(battle, foe, user, "Growl"))
    assert user.boosts.get("attack", 0) == 0
    for remaining in (4, 3, 2, 1):
        battle.residual()
        assert user.side.conditions["mist"]["duration"] == remaining
    battle.residual()
    assert "mist" not in user.side.conditions and "mist" not in user.side.screens
    battle.use_move(action(battle, foe, user, "Growl"))
    assert user.boosts["attack"] == -1
    assert not getattr(battle, "_callback_failures", [])


def test_mist_blocks_real_intimidate_entry_but_keeps_self_debuffs_and_positive_changes():
    """Only the opposing negative part is filtered with actual source/effect context."""
    battle, user, foe = build_battle()
    BattleBoosters.apply_effect(battle, "Guard Spec.", user)
    reserve = _reserve_copy(foe, ability="Intimidate")
    reserve.side, reserve.battle = foe.side, battle
    battle.participants[1].pokemons.append(reserve)
    battle.switch_pokemon(battle.participants[1], reserve)
    assert user.boosts.get("attack", 0) == 0
    effect = SimpleNamespace(effectType="Move", name="Mixed source fixture")
    apply_boost(user, {"atk": -1, "def": 1}, source=reserve, effect=effect)
    assert user.boosts.get("attack", 0) == 0 and user.boosts["defense"] == 1
    apply_boost(user, {"atk": -2}, source=user, effect=effect)
    assert user.boosts["attack"] == -2
    apply_boost(user, {"atk": 2}, source=reserve, effect=effect)
    assert user.boosts["attack"] == 0
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("ability,result", [("Simple", 0), ("Contrary", 1)])
def test_mist_filters_after_normal_ability_modification(ability, result):
    """Contrary's beneficial reversal survives, while Simple's amplified enemy drop is blocked."""
    battle, user, foe = build_battle(attacker_ability=ability)
    BattleBoosters.apply_effect(battle, "Guard Spec.", user)
    battle.use_move(action(battle, foe, user, "Growl"))
    assert user.boosts.get("attack", 0) == result


def test_infiltrator_move_bypasses_mist_and_haze_clear_smog_still_reset():
    """Move infiltration and direct resets retain their reviewed ordinary outcomes."""
    battle, user, foe = build_battle(defender_ability="Infiltrator")
    BattleBoosters.apply_effect(battle, "Guard Spec.", user)
    battle.use_move(action(battle, foe, user, "Growl"))
    assert user.boosts["attack"] == -1
    user.boosts["attack"] = 4
    battle.use_move(action(battle, foe, user, "Clear Smog"))
    assert user.boosts["attack"] == 0
    user.boosts["attack"] = 4
    battle.use_move(action(battle, foe, foe, "Haze"))
    assert user.boosts["attack"] == 0


def test_side_mist_survives_user_switch_faint_and_clears_at_end():
    """The five-turn condition belongs to the side, including its source after a switch."""
    battle, user, foe = build_battle()
    reserve = _reserve_copy(user)
    reserve.side, reserve.battle = user.side, battle
    battle.participants[0].pokemons.append(reserve)
    BattleBoosters.apply_effect(battle, "Guard Spec.", user)
    state = user.side.conditions["mist"]
    battle.switch_pokemon(battle.participants[0], reserve)
    assert reserve.side.conditions["mist"] == state
    reserve.hp = 0
    battle.on_faint(reserve)
    assert user.side.conditions["mist"] == state
    BattleBoosters.cleanup(battle)
    assert "mist" not in user.side.conditions and "mist" not in user.side.screens
