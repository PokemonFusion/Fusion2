"""Native identity and participant roles for seven special held items."""

from types import SimpleNamespace

import pytest

from pokemon.battle.effect_context import EffectContext
from pokemon.battle.item_identity import HeldItemIdentity
from pokemon.dex import ITEMDEX
from pokemon.names import resolve_dex_entry

from .test_diagnosed_item_effects import attack, native_battle
from .test_forced_item_form_eligibility import identity
from .test_plate_theft_identity import held, pair


PROFILES = (
    ("Adamant Crystal", "Dialga", "Dialga-Origin", "Pressure"),
    ("Griseous Core", "Giratina", "Giratina-Origin", "Pressure"),
    ("Lustrous Globe", "Palkia", "Palkia-Origin", "Pressure"),
    ("Blue Orb", "Kyogre", "Kyogre-Primal", "Drizzle"),
    ("Red Orb", "Groudon", "Groudon-Primal", "Drought"),
    ("Rusted Sword", "Zacian", "Zacian-Crowned", "Intrepid Sword"),
    ("Rusted Shield", "Zamazenta", "Zamazenta-Crowned", "Dauntless Shield"),
)


@pytest.mark.parametrize("item,native,form,ability", PROFILES)
@pytest.mark.parametrize("role", ("holder", "source"))
@pytest.mark.parametrize("nickname", ("Buddy", "exact", "prefix"))
def test_foreign_nicknames_cannot_protect_either_role(item, native, form, ability, role, nickname):
    """Matched real damage must transfer the item regardless of display name."""
    battle, target, thief = pair(item)
    mon = target if role == "holder" else thief
    mon.name = native if nickname == "exact" else native + "-Imposter" if nickname == "prefix" else nickname
    damage, _ = attack(battle, thief, target, "Thief")
    assert 0 < damage < target.max_hp
    assert not held(target) and held(thief) == EffectContext.key(item)
    assert str(target.species) == str(thief.species) == "Mew"
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item,native,form,ability", PROFILES)
@pytest.mark.parametrize("role", ("holder", "source"))
@pytest.mark.parametrize("active", (False, True))
@pytest.mark.parametrize("ability_present", (False, True))
def test_base_and_active_native_roles_are_precise(item, native, form, ability, role, active, ability_present):
    """Primal Orbs protect only the holder; neither policy requires an ability.

    These source-role Thief assignments are offline policy adapters, not claims
    that these native species learn Thief. Base-state adapters hold the real
    dex item without invoking automatic battle-entry form activation.
    """
    species = form if active else native
    battle, target, thief = pair("", holder=species if role == "holder" else "Mew",
                                 source=species if role == "source" else "Mew")
    target.item = resolve_dex_entry(ITEMDEX, item)
    native_mon = target if role == "holder" else thief
    native_mon.ability = ability if ability_present else "No Ability"
    native_mon.name = "Buddy"
    damage, _ = attack(battle, thief, target, "Thief")
    assert 0 < damage < target.max_hp
    protected = role == "holder" or item not in {"Blue Orb", "Red Orb"}
    assert bool(held(target)) is protected
    assert bool(held(thief)) is not protected
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item,native,form,ability", PROFILES)
@pytest.mark.parametrize("move", ("Thief", "Knock Off", "Trick", "Switcheroo"))
@pytest.mark.parametrize("suppression", ("none", "magicroom", "embargo", "klutz"))
@pytest.mark.parametrize("native_holder", (False, True))
def test_actual_removal_preserves_physical_native_rules(item, native, form, ability, move, suppression, native_holder):
    """Protection survives suppression; a foreign name never grants it."""
    battle, target, thief = pair(item, holder=native if native_holder else "Mew",
                                ability=ability if native_holder else "Synchronize",
                                nickname="Buddy" if native_holder else native)
    if suppression == "magicroom":
        battle.add_pseudo_weather("magicroom", source=thief)
    elif suppression == "embargo":
        battle.apply_volatile_status(target, "embargo", source=thief)
    elif suppression == "klutz":
        target.ability = "Klutz"  # Explicit offline suppression adapter.
    if suppression != "none":
        assert EffectContext.item(target) is None
    damage, _ = attack(battle, thief, target, move)
    if move in {"Thief", "Knock Off"}:
        assert damage > 0
    assert bool(held(target)) is native_holder
    assert bool(held(thief)) is (not native_holder and move != "Knock Off")
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item,native,form,ability", PROFILES)
def test_known_forms_unknown_adapters_and_cross_family(item, native, form, ability):
    """Resolve only known native identities; itemUser and names are insufficient."""
    entry = resolve_dex_entry(ITEMDEX, item)
    for species in (native, form):
        holder = SimpleNamespace(base_species=species, name="Buddy")
        assert entry.call("onTakeItem", item=entry, pokemon=holder) is False
        foreign = SimpleNamespace(base_species="Mew", name=native)
        expected = item in {"Blue Orb", "Red Orb"}
        assert entry.call("onTakeItem", item=entry, pokemon=foreign, source=holder) is expected
    for malformed in (SimpleNamespace(name=native), SimpleNamespace(base_species=native + "-Fake", name=native),
                      SimpleNamespace(base_species="Ditto", species=form, name=native, transformed=True)):
        assert entry.call("onTakeItem", item=entry, pokemon=malformed) is True
    for other in PROFILES:
        if other[1] != native:
            assert entry.call("onTakeItem", item=entry,
                              pokemon=SimpleNamespace(base_species=other[1], name=native)) is True


@pytest.mark.parametrize("item,native,form,ability", PROFILES)
@pytest.mark.parametrize("kind", ("native", "foreign", "copied"))
def test_safe_form_entry_and_reversion(item, native, form, ability, kind):
    """Retain genuine form entry and reject nicknames or incompatible copies."""
    battle, holder, _ = native_battle(native if kind == "native" else "Mew", ability=ability)
    holder.name = native if kind == "foreign" else "Buddy"
    if kind == "copied":
        holder.species, holder.transformed = native, True
    before = identity(holder)
    assert battle.set_item(holder, resolve_dex_entry(ITEMDEX, item))
    battle.on_enter_battle(holder)
    if kind == "native":
        assert str(holder.species) == form
        assert HeldItemIdentity.matches(holder, native, family=True)
        battle.set_item(holder, None)
        # Existing clear-item policy reverts forms whose dex has changesFrom.
        from pokemon.dex import POKEDEX
        if resolve_dex_entry(POKEDEX, form).raw.get("changesFrom"):
            assert str(holder.species) == native
    else:
        assert identity(holder) == before
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item,native,form,ability", PROFILES)
@pytest.mark.parametrize("native_holder", (False, True))
def test_transform_uses_original_native_identity(item, native, form, ability, native_holder):
    """Copied appearance cannot grant protection; real native identity persists."""
    battle, target, thief = pair(item, holder=native if native_holder else "Mew",
                                source="Mew" if native_holder else native, ability=ability)
    attack(battle, target, thief, "Transform")  # Native Transform is an offline adapter.
    assert target.transformed
    target.name = "Buddy" if native_holder else native
    thief.base_species, thief.species = "Mew", "Mew"
    attack(battle, thief, target, "Thief")
    assert bool(held(target)) is native_holder
    assert bool(held(thief)) is not native_holder
