"""Regressions for failures reproduced by the logged-in item-effect sweep."""

from types import SimpleNamespace

import pytest

from .test_diagnosed_item_effects import attack, native_battle


@pytest.mark.parametrize("item,amount", [("Berry", 10), ("Gold Berry", 30)])
@pytest.mark.parametrize("blocked", [False, True])
def test_legacy_healing_berries_activate_at_half_hp_with_eating_gates(item, amount, blocked):
    battle, holder, foe = native_battle(item=item, hp_fraction=0.2)
    if blocked:
        foe.ability = "Unnerve"
    before = holder.hp
    battle.residual()
    assert holder.hp == before + (0 if blocked else amount)
    assert (holder.item is not None) is blocked
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item", ["Bitter Berry", "Miracle Berry"])
@pytest.mark.parametrize("blocked", [False, True])
def test_legacy_confusion_berries_use_volatile_confusion_and_normal_gates(item, blocked):
    battle, holder, foe = native_battle(item=item)
    if blocked:
        foe.ability = "Unnerve"
    attack(battle, foe, holder, "Confuse Ray")
    assert ("confusion" in holder.volatiles) is blocked
    assert (holder.item is not None) is blocked


def test_ice_berry_cures_burn_rather_than_freeze():
    battle, holder, _ = native_battle(item="Ice Berry")
    holder.status = "brn"
    battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
    assert not holder.status and holder.item is None


@pytest.mark.parametrize("current", [0, 4, 35])
def test_mystery_berry_reads_authoritative_pp_without_uncached_move_attributes(current):
    battle, holder, _ = native_battle(item="Mystery Berry")
    slot = SimpleNamespace(
        move=SimpleNamespace(name="Tackle"),
        current_pp=current,
        max_pp=56,
        save=lambda **kwargs: None,
    )
    holder.activemoveslot_set = SimpleNamespace(all=lambda: [slot])
    holder.moves = [SimpleNamespace(name="Tackle")]
    battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
    assert slot.current_pp == (5 if current == 0 else current)
    assert (holder.item is None) is (current == 0)
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize(
    "item,weather",
    [
        ("Damp Rock", "raindance"),
        ("Heat Rock", "sunnyday"),
        ("Smooth Rock", "sandstorm"),
        ("Icy Rock", "snow"),
        ("Icy Rock", "hail"),
    ],
)
@pytest.mark.parametrize("suppressed", [False, True])
def test_native_weather_rocks_extend_weather_only_while_effective(item, weather, suppressed):
    battle, holder, _ = native_battle(item=item, ability="Klutz" if suppressed else "No Ability")
    assert battle.setWeather(weather, source=holder)
    assert battle.field.pseudo_weather[weather]["duration"] == (5 if suppressed else 8)


@pytest.mark.parametrize("suppressed", [False, True])
@pytest.mark.parametrize(
    "terrain", ["electricterrain", "grassyterrain", "mistyterrain", "psychicterrain"]
)
def test_native_terrain_extender_uses_effective_item(suppressed, terrain):
    battle, holder, _ = native_battle(
        item="Terrain Extender", ability="Klutz" if suppressed else "No Ability"
    )
    assert battle.setTerrain(terrain, source=holder)
    assert battle.field.pseudo_weather[terrain]["duration"] == (5 if suppressed else 8)


@pytest.mark.parametrize("suppressed", [False, True])
@pytest.mark.parametrize(
    "move,effect",
    [("Reflect", "reflect"), ("Light Screen", "lightscreen"), ("Aurora Veil", "auroraveil")],
)
def test_native_light_clay_extends_reflect_only_while_effective(suppressed, move, effect):
    battle, holder, foe = native_battle(
        item="Light Clay", ability="Klutz" if suppressed else "No Ability"
    )
    if move == "Aurora Veil":
        battle.setWeather("snow", source=holder)
    attack(battle, holder, foe, move)
    side = battle.participant_for(holder).side
    assert side.conditions[effect]["duration"] == (5 if suppressed else 8)


def test_shell_bell_heals_actual_substitute_damage_once():
    battle, holder, foe = native_battle(item="Shell Bell", hp_fraction=0.5)
    attack(battle, foe, holder, "Substitute")
    before_sub = foe.volatiles["substitute"]["hp"]
    before = holder.hp
    attack(battle, holder, foe, "Tackle")
    after_sub = foe.volatiles.get("substitute", {}).get("hp", 0)
    actual = before_sub - after_sub
    assert actual > 0
    assert holder.hp == before + max(1, actual // 8)
    assert not getattr(battle, "_callback_failures", [])


def test_normal_gem_boosts_substitute_damage_without_stat_stages():
    values = []
    for item in ["", "Normal Gem"]:
        battle, holder, foe = native_battle(item=item)
        attack(battle, foe, holder, "Substitute")
        before = foe.volatiles["substitute"]["hp"]
        attack(battle, holder, foe, "Tackle")
        values.append(before - foe.volatiles.get("substitute", {}).get("hp", 0))
        assert not any(holder.boosts.values())
    assert values[-1] > values[0]


@pytest.mark.parametrize("native", [False, True])
def test_power_anklet_adds_to_existing_speed_yield_without_alias_loss_or_double_bonus(native):
    from pokemon.dex import ITEMDEX
    from pokemon.models.stats import apply_item_ev_mod
    from pokemon.names import resolve_dex_entry

    item = resolve_dex_entry(ITEMDEX, "Power Anklet") if native else "Power Anklet"
    mon = SimpleNamespace(item=item, held_item=item)
    assert apply_item_ev_mod(mon, {"spe": 1}) == {"speed": 9}


def test_native_lucky_egg_applies_its_exp_bonus_once():
    from pokemon.dex import ITEMDEX
    from pokemon.models.stats import apply_item_exp_mod
    from pokemon.names import resolve_dex_entry

    item = resolve_dex_entry(ITEMDEX, "Lucky Egg")
    assert apply_item_exp_mod(SimpleNamespace(item=item), 100) == 150


def test_zoom_lens_checks_the_targets_remaining_action():
    from pokemon.battle.accuracy import MoveAccuracy
    from pokemon.battle.action_queue import ActionQueue
    from pokemon.battle.actions import Action, ActionType
    from pokemon.battle.engine import BattleMove

    battle, holder, foe = native_battle(item="Zoom Lens")
    action = Action(
        battle.participant_for(foe), ActionType.MOVE, pokemon=foe, move=BattleMove(name="Splash")
    )
    battle.queue = ActionQueue([action])
    move = BattleMove(name="Rock Throw")
    assert MoveAccuracy.modified(holder, foe, move, battle, base=90) == 90
    battle.queue.pop_next()
    assert MoveAccuracy.modified(holder, foe, move, battle, base=90) == 108


def test_light_clay_does_not_extend_safeguard():
    battle, holder, foe = native_battle(item="Light Clay")
    attack(battle, holder, foe, "Safeguard")
    assert battle.participant_for(holder).side.conditions["safeguard"]["duration"] == 5
