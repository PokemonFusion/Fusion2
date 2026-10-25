"""Native Memory/Drive protection through actual item-removal consumers."""

from types import SimpleNamespace

import pytest

from pokemon.battle.effect_context import EffectContext

from .test_diagnosed_item_effects import attack, native_battle
from .test_plate_theft_identity import held, pair


MEMORIES = tuple(kind + " Memory" for kind in (
    "Bug", "Dark", "Dragon", "Electric", "Fairy", "Fighting", "Fire", "Flying",
    "Ghost", "Grass", "Ground", "Ice", "Poison", "Psychic", "Rock", "Steel", "Water",
))
DRIVES = ("Burn Drive", "Chill Drive", "Douse Drive", "Shock Drive")
PROFILES = tuple((item, "Silvally", "RKS System") for item in MEMORIES) + tuple(
    (item, "Genesect", "Download") for item in DRIVES
)


@pytest.mark.parametrize("item,native,ability", PROFILES)
@pytest.mark.parametrize("name", ("Buddy", "exact", "prefix"))
def test_foreign_holder_names_never_block_thief(item, native, ability, name):
    """Matched Mew holders lose exactly one real item regardless of nickname."""
    nickname = native if name == "exact" else native + "-Imposter" if name == "prefix" else name
    battle, target, thief = pair(item, nickname=nickname)
    damage, _ = attack(battle, thief, target, "Thief")
    assert 0 < damage < target.max_hp
    assert not held(target) and held(thief) == EffectContext.key(item)
    assert str(target.species) == "Mew"
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item,native,ability", PROFILES)
@pytest.mark.parametrize("name", ("exact", "prefix"))
def test_foreign_source_nicknames_do_not_block_thief(item, native, ability, name):
    """A foreign source uses the same native query as the physical holder."""
    battle, target, thief = pair(item)
    thief.name = native + ("-Imposter" if name == "prefix" else "")
    damage, _ = attack(battle, thief, target, "Thief")
    assert 0 < damage < target.max_hp
    assert not held(target) and held(thief) == EffectContext.key(item)


@pytest.mark.parametrize("item,native,ability", PROFILES)
@pytest.mark.parametrize("role", ("holder", "source"))
@pytest.mark.parametrize("renamed", (False, True))
def test_native_holder_and_source_retain_protection(item, native, ability, role, renamed):
    """Policy adapters assign Thief to sources; this is not a learnset claim."""
    battle, target, thief = pair(
        item, holder=native if role == "holder" else "Mew",
        source=native if role == "source" else "Mew", ability=ability,
        nickname="Buddy" if renamed else native,
    )
    thief.name = "Buddy" if renamed else native
    damage, _ = attack(battle, thief, target, "Thief")
    assert 0 < damage < target.max_hp
    assert held(target) == EffectContext.key(item) and not held(thief)
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item,native,ability", PROFILES)
def test_native_protection_does_not_depend_on_ability(item, native, ability):
    """Missing RKS System cannot grant a form, but native removal rules survive."""
    battle, target, thief = pair(item, holder=native, ability="No Ability")
    attack(battle, thief, target, "Thief")
    assert held(target) == EffectContext.key(item) and not held(thief)
    if native == "Silvally":
        assert str(target.species) == "Silvally"


@pytest.mark.parametrize("item,native,ability", PROFILES)
def test_other_native_family_has_no_protection(item, native, ability):
    """Silvally and Genesect cannot protect each other's item family."""
    other = "Genesect" if native == "Silvally" else "Silvally"
    battle, target, thief = pair(item, holder=other, nickname=native)
    attack(battle, thief, target, "Thief")
    assert not held(target) and held(thief) == EffectContext.key(item)


@pytest.mark.parametrize("item,native,ability", PROFILES)
def test_existing_native_forms_and_typed_moves_remain_available(item, native, ability):
    """All twenty-one genuine item forms still execute their existing typed move."""
    from pokemon.dex import ITEMDEX
    from pokemon.names import resolve_dex_entry

    entry = resolve_dex_entry(ITEMDEX, item)
    battle, holder, target = native_battle(native, item=item, ability=ability)
    holder.name = "Buddy"
    assert str(holder.species) == entry.raw["forcedForme"]
    move = "Multi-Attack" if native == "Silvally" else "Techno Blast"
    damage, action_move = attack(battle, holder, target, move)
    assert damage > 0
    assert action_move.type == entry.raw["onMemory" if native == "Silvally" else "onDrive"]
    assert held(holder) == EffectContext.key(item)
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item,native,ability", (PROFILES[6], PROFILES[17]))
@pytest.mark.parametrize("suppression", ("magicroom", "embargo", "klutz"))
@pytest.mark.parametrize("native_holder", (False, True))
@pytest.mark.parametrize("move", ("Thief", "Knock Off", "Trick", "Switcheroo"))
def test_shared_suppressed_removal_path_uses_native_identity(item, native, ability, suppression, native_holder, move):
    """Reuse #855's physical TakeItem exception while other effects stay suppressed."""
    battle, target, thief = pair(item, holder=native if native_holder else "Mew",
                                nickname="Buddy" if native_holder else native, ability=ability)
    if suppression == "magicroom":
        battle.add_pseudo_weather("magicroom", source=thief)
    elif suppression == "embargo":
        battle.apply_volatile_status(target, "embargo", source=thief)
    else:
        target.ability = "Klutz"  # Explicit adapter, not a native ability route.
    assert EffectContext.item(target) is None
    attack(battle, thief, target, move)
    assert bool(held(target)) is native_holder
    assert bool(held(thief)) is (not native_holder and move != "Knock Off")


@pytest.mark.parametrize("item,native,ability", (PROFILES[6], PROFILES[17]))
@pytest.mark.parametrize("native_holder", (False, True))
def test_genuine_transform_preserves_base_identity(item, native, ability, native_holder):
    """A copied native appearance cannot grant protection to foreign base Mew."""
    battle, target, thief = pair(item, holder=native if native_holder else "Mew",
                                source="Mew" if native_holder else native, ability=ability)
    attack(battle, target, thief, "Transform")
    assert target.transformed
    target.name = "Buddy" if native_holder else native
    # Third-party source identity adapter isolates the transformed holder rule.
    thief.base_species, thief.species = "Mew", "Mew"
    attack(battle, thief, target, "Thief")
    assert bool(held(target)) is native_holder
    assert bool(held(thief)) is not native_holder


@pytest.mark.parametrize("item,native,ability", PROFILES)
def test_known_native_type_forms_and_malformed_adapters(item, native, ability):
    """Known families protect either role; unknown names alone never protect."""
    from pokemon.dex import ITEMDEX
    from pokemon.names import resolve_dex_entry

    entry = resolve_dex_entry(ITEMDEX, item)
    form = SimpleNamespace(base_species=entry.raw["forcedForme"], name="Buddy")
    foreign = SimpleNamespace(base_species="Mew", species="Mew", name=native)
    assert entry.call("onTakeItem", item=entry, pokemon=form, source=foreign) is False
    assert entry.call("onTakeItem", item=entry, pokemon=foreign, source=form) is False
    for value in (SimpleNamespace(name=native), SimpleNamespace(base_species=native + "-Fake", name=native)):
        assert entry.call("onTakeItem", item=entry, pokemon=value, source=None) is True
