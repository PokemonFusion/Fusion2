"""Incense power must respect effective held state in normal move dispatch."""

import random

import pytest


PROFILES = [("Odd Incense", "Psychic"), ("Rock Incense", "Power Gem"),
            ("Rose Incense", "Energy Ball"), ("Sea Incense", "Surf"), ("Wave Incense", "Surf")]


def damage(item, move_name, suppression, *, ability="Synchronize", species="Mew", weather=None):
    """Use real dex effects, calculated stats and an ordinary engine move action."""
    from .helpers import load_modules, battle_move

    modules = load_modules()
    from pokemon.battle.actions import Action, ActionType
    from pokemon.dex import ITEMDEX, MOVEDEX
    from pokemon.battle.effect_context import EffectContext
    from pokemon.helpers.pokemon_helpers import get_max_hp
    from pokemon.names import resolve_dex_entry

    Pokemon, Battle = modules["Pokemon"], modules["Battle"]
    participant = modules["BattleParticipant"]
    user = Pokemon(species, level=50, ivs=[0] * 6, evs=[0] * 6, ability=ability)
    target = Pokemon("Mew", level=50, ivs=[31] * 6, evs=[0] * 6, ability="Synchronize")
    for mon in (user, target):
        mon.hp = mon.max_hp = get_max_hp(mon)
    left, right = participant("left", [user]), participant("right", [target])
    left.active, right.active = [user], [target]
    battle = Battle(modules["BattleType"].PVP, [left, right], rng=random.Random(771))
    user.battle = target.battle = battle
    user.item = resolve_dex_entry(ITEMDEX, item) if item else None
    assert user.item is not None if item else user.item is None
    original = user.item
    if weather:
        battle.setWeather(weather, source=user)
    if suppression == "magic":
        battle.add_pseudo_weather("magicroom", source=user)
    elif suppression == "embargo":
        battle.apply_volatile_status(user, "embargo", source=target)
    elif suppression == "explicit":
        user.item_suppressed = True
    entry = resolve_dex_entry(MOVEDEX, move_name)
    move = battle_move(entry.name, power=entry.power, move_type=entry.type,
                       category=entry.category, accuracy=entry.accuracy, raw=entry.raw)
    user.moves = [move]
    hp = target.hp
    battle.use_move(Action(left, ActionType.MOVE, right, move=move, pokemon=user))
    assert user.item is original
    assert EffectContext.item(user) is (None if suppression else original)
    return hp - target.hp


@pytest.mark.parametrize("item,move", PROFILES)
@pytest.mark.parametrize("suppression", (None, "magic", "embargo", "explicit"))
def test_incense_matching_power_obeys_effective_held_state(item, move, suppression):
    """Suppressed copies equal the unheld control; active copies add useful damage."""
    baseline = damage(None, move, suppression)
    actual = damage(item, move, suppression)
    assert baseline > 0
    if suppression:
        assert actual == baseline
    else:
        assert actual > baseline


@pytest.mark.parametrize("weather", (None, "sandstorm"))
def test_native_sand_force_and_rock_incense_compose(weather):
    """Both no-op and active ability power results must keep the item modifier."""
    options = {"ability": "Sand Force", "species": "Gigalith", "weather": weather}
    assert damage("Rock Incense", "Power Gem", None, **options) > damage(None, "Power Gem", None, **options)
