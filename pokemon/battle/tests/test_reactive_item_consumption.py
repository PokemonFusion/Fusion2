"""Real reactive triggers, guarded consumption and recoverable item histories."""

import json
import random
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats

from .test_diagnosed_item_effects import attack, native_battle


ITEMS = {
    "Jaboca Berry": "Tackle", "Rowap Berry": "Water Gun",
    "Kee Berry": "Tackle", "Maranga Berry": "Water Gun",
    "Weakness Policy": "Payback", "Throat Spray": "Screech",
}
BERRIES = tuple(name for name in ITEMS if "Berry" in name)


@pytest.fixture(autouse=True)
def isolated_callback_randomness():
    """Seed legacy callback RNG locally and restore other suites' random state."""
    before = random.getstate()
    random.seed(853)
    yield
    random.setstate(before)


def scenario(item, *, foe_ability="Synchronize", ability="Synchronize"):
    """Use actual level-50 native stats and dex effects, never forced damage."""
    battle, holder, foe = native_battle("Mew", item, "Mew", ability=ability)
    data = SimpleNamespace(species="Mew", level=50, ivs=[0] * 6,
                           evs=[0] * 6, nature="Hardy")
    foe.level = 50
    foe.base_stats = type(holder.base_stats)(**get_stats(data))
    foe.stats = dict(holder.stats)
    foe.hp = foe.max_hp = get_max_hp(data)
    foe.ability = foe_ability
    battle.rng = random.Random(853)
    return battle, holder, foe


def trigger(battle, holder, foe, item, move=None):
    """Execute the real damaging or sound move through ordinary engine events."""
    move = move or ITEMS[item]
    if item == "Throat Spray":
        return attack(battle, holder, foe, move)
    return attack(battle, foe, holder, move)


def name(item):
    """Compare canonical item identity without depending on object instances."""
    return (getattr(item, "raw", {}) or {}).get("name") or getattr(item, "name", item) or ""


def stages(pokemon):
    """Ignore zero-key normalization while checking actual stage changes."""
    from pokemon.utils.boosts import STAT_KEY_MAP
    return {STAT_KEY_MAP.get(key, key): value for key, value in pokemon.boosts.items() if value}


@pytest.mark.parametrize("item", ITEMS)
def test_consumption_records_one_use_and_real_recycle_restores(item):
    "Record one consumed copy and restore it once through Recycle."
    battle, holder, foe = scenario(item)
    trigger(battle, holder, foe, item)
    assert holder.hp > 0 and foe.hp > 0
    assert name(holder.item) == name(getattr(holder, "held_item", "")) == ""
    assert name(holder.last_used_item) == item
    assert [name(value) for value in holder.side.used_items] == [item]
    attack(battle, holder, holder, "Recycle")
    assert name(holder.item) == item
    assert holder.last_used_item is None
    attack(battle, holder, holder, "Recycle")
    assert name(holder.item) == item
    assert holder.side.used_items == []
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item", BERRIES)
def test_unnerve_refuses_effect_and_consumption(item):
    """The opposing ability is a mechanics adapter, not a native learnset claim."""
    battle, holder, foe = scenario(item, foe_ability="Unnerve")
    old_hp, boosts = foe.hp, stages(holder)
    trigger(battle, holder, foe, item)
    assert name(holder.item) == item
    assert name(holder.last_used_item) == ""
    assert holder.side.used_items == []
    assert foe.hp == old_hp
    assert stages(holder) == boosts


@pytest.mark.parametrize("item", ITEMS)
def test_consumed_history_round_trips_before_recycle(item):
    "Retain named recovery references through the Pokemon checkpoint."
    from pokemon.battle.battledata import Pokemon

    battle, holder, foe = scenario(item)
    trigger(battle, holder, foe, item)
    restored = Pokemon.from_dict(holder.to_dict())
    assert name(restored.item) == ""
    assert name(restored.last_used_item) == item
    if item in BERRIES:
        assert name(restored.consumed_berry) == item
        assert name(restored.berry_consumed) == item


@pytest.mark.parametrize("item", ITEMS)
def test_use_item_veto_keeps_copy_and_effect(item):
    "A real UseItem veto keeps both the copy and its effect unspent."
    battle, holder, foe = scenario(item)
    old_hp, boosts = foe.hp, stages(holder)
    original = battle.runEvent

    def veto(event, *args, **kwargs):
        """Isolate the actual UseItem refusal without faking trigger success."""
        return False if event == "UseItem" else original(event, *args, **kwargs)

    with patch.object(battle, "runEvent", side_effect=veto):
        trigger(battle, holder, foe, item)
    assert name(holder.item) == item
    assert name(holder.last_used_item) == ""
    assert holder.side.used_items == []
    assert stages(holder) == boosts
    assert foe.hp == old_hp


@pytest.mark.parametrize("item", BERRIES)
@pytest.mark.parametrize("recovery", ("recycle", "harvest"))
def test_recovery_then_theft_cannot_duplicate_the_consumed_copy(item, recovery):
    """Successful recovery retires all aliases, retaining Belch eligibility."""
    battle, holder, foe = scenario(item, ability="Harvest" if recovery == "harvest" else "Synchronize")
    assert battle.eat_item(holder)
    if recovery == "recycle":
        attack(battle, holder, holder, "Recycle")
    else:
        from pokemon.dex.functions.abilities_funcs import Harvest
        with patch("pokemon.dex.functions.abilities_funcs.random", return_value=0.0):
            Harvest().onResidual(holder)
    assert name(holder.item) == item
    assert battle.steal_item(foe, holder)
    attack(battle, holder, holder, "Recycle")
    assert name(holder.item) == ""
    assert name(foe.item) == item
    assert name(holder.last_used_item) == name(holder.berry_consumed) == ""
    from pokemon.dex.functions.moves.damage_moves import Belch
    assert Belch().onDisableMove(holder) is False


@pytest.mark.parametrize("item", ITEMS)
@pytest.mark.parametrize("suppression", ("magicroom", "embargo", "klutz"))
def test_actual_suppression_moves_keep_copy_and_history_empty(item, suppression):
    "Actual suppression moves retain the inactive physical item."
    battle, holder, foe = scenario(item)
    if suppression == "klutz":
        foe.ability = "Klutz"  # Mechanics adapter; SQL uses a native Skill Swap source.
    attack(battle, foe, holder if suppression != "magicroom" else foe,
           {"magicroom": "Magic Room", "embargo": "Embargo", "klutz": "Skill Swap"}[suppression])
    trigger(battle, holder, foe, item)
    assert name(holder.item) == item
    assert not holder.last_used_item
    assert not holder.side.used_items


@pytest.mark.parametrize("item", ITEMS)
def test_wrong_category_or_nonsound_move_does_not_consume(item):
    "Non-triggering move data cannot spend the reactive copy."
    battle, holder, foe = scenario(item)
    move = ("Water Gun" if item in {"Jaboca Berry", "Kee Berry", "Weakness Policy"}
            else "Amnesia" if item == "Throat Spray" else "Tackle")
    trigger(battle, holder, foe, item, move)
    assert name(holder.item) == item and not holder.last_used_item


@pytest.mark.parametrize("item", ITEMS)
def test_actual_protect_prevents_trigger(item):
    "A genuine protected move cannot activate the held item."
    battle, holder, foe = scenario(item)
    protected = foe if item == "Throat Spray" else holder
    attack(battle, protected, protected, "Protect")
    trigger(battle, holder, foe, item)
    assert name(holder.item) == item and not holder.last_used_item


@pytest.mark.parametrize("item", ITEMS)
def test_faint_rules_keep_retaliation_exception_only(item):
    "Only retaliation berries permit consumption after a genuine KO."
    battle, holder, foe = scenario(item)
    holder.hp = 1  # Labelled depleted prerequisite; the actual attack causes the KO.
    if item == "Throat Spray":
        attack(battle, foe, holder, "Tackle")
    trigger(battle, holder, foe, item)
    assert holder.hp == 0
    consumed = item in {"Jaboca Berry", "Rowap Berry"}
    assert name(holder.item) == ("" if consumed else item)
    assert name(holder.last_used_item) == (item if consumed else "")


@pytest.mark.parametrize("item", BERRIES)
def test_cheek_pouch_runs_once_after_permitted_eating(item):
    "Permitted eating invokes one existing Cheek Pouch heal."
    plain, ordinary, attacker = scenario(item)
    battle, holder, foe = scenario(item, ability="Cheek Pouch")
    ordinary.hp = holder.hp = holder.max_hp // 2
    trigger(plain, ordinary, attacker, item)
    trigger(battle, holder, foe, item)
    assert ordinary.hp > 0
    assert holder.hp == min(holder.max_hp, ordinary.hp + holder.max_hp // 3)
    assert [name(value) for value in holder.side.used_items] == [item]


@pytest.mark.parametrize("item", BERRIES)
def test_suppressed_unnerve_does_not_block_permitted_berry(item):
    "Gastro Acid disables the opposing eating veto."
    battle, holder, foe = scenario(item, foe_ability="Unnerve")
    attack(battle, holder, foe, "Gastro Acid")
    assert getattr(foe, "ability_suppressed", False) or "gastroacid" in foe.volatiles
    trigger(battle, holder, foe, item)
    assert name(holder.item) == "" and name(holder.last_used_item) == item


@pytest.mark.parametrize("item", BERRIES)
def test_existing_belch_move_gate_and_damage_follow_consumption(item):
    """Qualify the existing DisableMove callback, not generic selection wiring."""
    from pokemon.dex.functions.moves.damage_moves import Belch

    battle, holder, foe = scenario(item)
    assert Belch().onDisableMove(holder) is True
    trigger(battle, holder, foe, item)
    assert Belch().onDisableMove(holder) is False
    after, _ = attack(battle, holder, foe, "Belch")
    assert after > 0


@pytest.mark.parametrize("item", ITEMS)
def test_history_and_side_ledger_are_primitive_and_restore_without_replay(item):
    "Primitive histories rebuild without replaying use or grants."
    from pokemon.battle.item_consumption import ItemUseHistory

    battle, holder, foe = scenario(item)
    trigger(battle, holder, foe, item)
    payload = json.loads(json.dumps(ItemUseHistory.freeze(holder)))
    sides = json.loads(json.dumps(ItemUseHistory.freeze_sides(battle)))
    rebuilt, copy, _ = scenario(item)
    rebuilt.set_item(copy, None)
    for _ in range(2):
        ItemUseHistory.restore(copy, payload)
        ItemUseHistory.restore_sides(rebuilt, sides)
        assert name(copy.item) == ""
        assert name(copy.last_used_item) == item
        assert [name(value) for value in copy.side.used_items] == [item]


@pytest.mark.parametrize("corruption", ("version", "missing", "unknown", "object", "ate_berry"))
def test_malformed_explicit_item_history_refuses_without_partial_restore(corruption):
    "Malformed explicit history cannot grant or partially restore items."
    from pokemon.battle.item_consumption import ItemUseHistory

    battle, holder, _ = scenario("Kee Berry")
    before = ItemUseHistory.freeze(holder)
    payload = dict(before)
    if corruption == "missing":
        payload.pop("last_used_item")
    elif corruption in {"unknown", "object"}:
        payload["last_used_item"] = "missing-no-such-item-921" if corruption == "unknown" else {}
    else:
        payload[corruption] = "bad"
    with pytest.raises(ValueError, match="history"):
        ItemUseHistory.restore(holder, payload)
    assert ItemUseHistory.freeze(holder) == before
    assert name(holder.item) == "Kee Berry"


def test_legacy_absent_history_grants_no_copy():
    "Legacy absent history never invents a recoverable copy."
    from pokemon.battle.battledata import Pokemon

    _, holder, _ = scenario("Kee Berry")
    payload = holder.to_dict()
    payload.pop("item_use_history")
    payload["item"] = None
    restored = Pokemon.from_dict(payload)
    assert not restored.item and not restored.last_used_item and not restored.consumed_berry


@pytest.mark.parametrize("item", tuple(ITEMS)[:-1])
def test_actual_substitute_hit_does_not_consume_defensive_item(item):
    "A real substitute intercepts the defensive trigger."
    battle, holder, foe = scenario(item)
    attack(battle, holder, holder, "Substitute")
    trigger(battle, holder, foe, item)
    assert name(holder.item) == item and not holder.last_used_item


@pytest.mark.parametrize("item", ITEMS)
def test_multiple_hit_or_sound_execution_records_one_use(item):
    "A repeated-hit or sound execution records one consumption."
    battle, holder, foe = scenario(item)
    move = ("Snarl" if item == "Throat Spray" else "Pin Missile" if item == "Weakness Policy"
            else "Water Shuriken" if item in {"Rowap Berry", "Maranga Berry"} else "Double Kick")
    trigger(battle, holder, foe, item, move)
    assert name(holder.item) == "" and name(holder.last_used_item) == item
    assert [name(value) for value in holder.side.used_items] == [item]


def test_fixed_super_effective_damage_does_not_consume_weakness_policy():
    "Fixed damage cannot activate Weakness Policy."
    battle, holder, foe = scenario("Weakness Policy")
    trigger(battle, holder, foe, "Weakness Policy", "Night Shade")
    assert name(holder.item) == "Weakness Policy" and not holder.last_used_item


@pytest.mark.parametrize("payload", ({"A": [None]}, {"C": []}, {"A": "Kee Berry"},
                                   {"A": [], "B": ["unknown-item-921"]}))
def test_invalid_side_history_never_partially_replaces_a_ledger(payload):
    "Corrupt side data refuses before replacing any ledger."
    from pokemon.battle.item_consumption import ItemUseHistory

    battle, holder, foe = scenario("Kee Berry")
    trigger(battle, holder, foe, "Kee Berry")
    before = ItemUseHistory.freeze_sides(battle)
    with pytest.raises(ValueError, match="history"):
        ItemUseHistory.restore_sides(battle, payload)
    assert ItemUseHistory.freeze_sides(battle) == before


@pytest.mark.parametrize("item", ITEMS)
def test_existing_pickup_recovery_retires_recycle_alias(item):
    """Qualify one-copy bookkeeping within the existing side-based Pickup route."""
    from pokemon.dex.functions.abilities_funcs import Pickup

    battle, holder, foe = scenario(item)
    trigger(battle, holder, foe, item)
    Pickup().onResidual(holder)
    assert name(holder.item) == item
    assert battle.steal_item(foe, holder)
    attack(battle, holder, holder, "Recycle")
    assert name(holder.item) == ""
    assert name(foe.item) == item


@pytest.mark.parametrize("item", ITEMS)
def test_recycle_retires_side_pickup_opportunity(item):
    "Returning a used copy retires its side recovery opportunity."
    battle, holder, foe = scenario(item)
    trigger(battle, holder, foe, item)
    attack(battle, holder, holder, "Recycle")
    assert name(holder.item) == item
    assert holder.side.used_items == []


@pytest.mark.parametrize("item,recovery", [(item, recovery) for item in ITEMS
                                         for recovery in ("recycle", "pickup")]
                         + [(item, "harvest") for item in BERRIES])
def test_failed_recovery_keeps_one_available_use(item, recovery):
    """A refused recipient write cannot retire history or grant another copy."""
    from pokemon.dex.functions.abilities_funcs import Harvest, Pickup

    battle, holder, foe = scenario(item)
    trigger(battle, holder, foe, item)
    with patch.object(battle, "set_item", return_value=False):
        if recovery == "recycle":
            attack(battle, holder, holder, "Recycle")
        elif recovery == "pickup":
            Pickup().onResidual(holder)
        else:
            with patch("pokemon.dex.functions.abilities_funcs.random", return_value=0.0):
                Harvest().onResidual(holder)
    assert name(holder.item) == ""
    assert name(holder.last_used_item) == item
    assert [name(value) for value in holder.side.used_items] == [item]


@pytest.mark.parametrize("item", ITEMS)
def test_one_after_use_notification_reaches_existing_unburden(item):
    """Unburden is a mechanics adapter; no native Mew ability claim is made."""
    battle, holder, foe = scenario(item, ability="Unburden")
    with patch.object(battle, "_notify_after_use_item", wraps=battle._notify_after_use_item) as notified:
        trigger(battle, holder, foe, item)
        trigger(battle, holder, foe, item)
    assert notified.call_count == 1
    assert holder.abilityState.get("unburden") is True


def test_ambiguous_pickup_owner_refuses_without_guessing_or_retiring_history():
    """A deliberately ambiguous recovery fixture grants no third-party copy."""
    from pokemon.dex.functions.abilities_funcs import Pickup

    battle, holder, foe = scenario("Kee Berry")
    trigger(battle, holder, foe, "Kee Berry")
    other = type(holder).from_dict(holder.to_dict())
    other.side = holder.side
    holder.side.pokemons.append(other)
    Pickup().onResidual(holder)
    assert name(holder.item) == ""
    assert name(holder.last_used_item) == "Kee Berry"
    assert [name(value) for value in holder.side.used_items] == ["Kee Berry"]


@pytest.mark.parametrize("berry", BERRIES)
@pytest.mark.parametrize("item", ("Weakness Policy", "Throat Spray"))
def test_later_nonberry_use_supersedes_berry_recovery_without_losing_eaten_flag(berry, item):
    """A later consumed non-berry cannot leave an older Harvest recovery slot."""
    from pokemon.dex.functions.abilities_funcs import Harvest
    from pokemon.dex.functions.moves.damage_moves import Belch

    battle, holder, foe = scenario(berry)
    trigger(battle, holder, foe, berry)
    assert battle.set_item(holder, item)  # Separate second physical-copy prerequisite.
    trigger(battle, holder, foe, item)
    assert name(holder.last_used_item) == item
    assert holder.consumed_berry is None and holder.berry_consumed is None
    assert Belch().onDisableMove(holder) is False
    with patch("pokemon.dex.functions.abilities_funcs.random", return_value=0.0):
        Harvest().onResidual(holder)
    assert name(holder.item) == ""
    attack(battle, holder, holder, "Recycle")
    assert name(holder.item) == item


def test_empty_item_reference_does_not_require_a_catalog():
    """An empty checkpoint slot must work in standalone Pokemon serializers."""
    from pokemon.battle.item_consumption import ItemUseHistory

    with patch.dict(sys.modules, {"pokemon.dex": SimpleNamespace()}):
        assert ItemUseHistory.item(None) is None
