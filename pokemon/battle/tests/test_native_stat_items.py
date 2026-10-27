"""Native identity and genuine effect regressions for the nine #853 items."""

from types import SimpleNamespace

import pytest

from .test_diagnosed_item_effects import attack, native_battle


STAT_CASES = (
    ("Light Ball", "Pikachu", "ModifyAtk", "atk"),
    ("Light Ball", "Pikachu", "ModifySpA", "spa"),
    ("Thick Club", "Cubone", "ModifyAtk", "atk"),
    ("Deep Sea Scale", "Clamperl", "ModifySpD", "spd"),
    ("Deep Sea Tooth", "Clamperl", "ModifySpA", "spa"),
    ("Metal Powder", "Ditto", "ModifyDef", "def"),
    ("Quick Powder", "Ditto", "ModifySpe", "spe"),
)
CRITICAL_CASES = (("Lucky Punch", "Chansey"), ("Stick", "Farfetch'd"), ("Leek", "Sirfetch'd"))


@pytest.mark.parametrize("item,species,event,stat", STAT_CASES)
@pytest.mark.parametrize("renamed", (False, True))
def test_native_stat_bonus_survives_a_nickname(item, species, event, stat, renamed):
    """Only a real native identity controls the exact twofold stat effect."""
    battle, holder, foe = native_battle(species, item=item)
    if renamed:
        holder.name = "Buddy"
    base = holder.stats[stat]
    assert battle.runEvent(event, holder, foe, None, base) == base * 2
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item,species,event,stat", STAT_CASES)
@pytest.mark.parametrize("suffix", ("", "-Imposter"))
def test_foreign_nickname_cannot_gain_a_stat_bonus(item, species, event, stat, suffix):
    """Exact and prefix-like display names cannot change a foreign holder."""
    battle, holder, foe = native_battle("Mew", item=item)
    holder.name = species + suffix
    base = holder.stats[stat]
    assert battle.runEvent(event, holder, foe, None, base) == base
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item,species", CRITICAL_CASES)
def test_only_the_native_species_gets_the_critical_bonus(item, species):
    """Renamed natives gain two stages; a foreign nickname grants none."""
    battle, holder, foe = native_battle(species, item=item)
    holder.name = "Buddy"
    assert battle.runEvent("ModifyCritRatio", holder, foe, None, 0) == 2
    battle, holder, foe = native_battle("Mew", item=item)
    holder.name = species
    assert battle.runEvent("ModifyCritRatio", holder, foe, None, 0) == 0


@pytest.mark.parametrize(
    "item,species",
    (
        ("Light Ball", "Pikachu-Cosplay"),
        ("Light Ball", "Pikachu-Starter"),
        ("Thick Club", "Marowak-Alola"),
        ("Thick Club", "Marowak-Alola-Totem"),
        ("Stick", "Farfetch'd-Galar"),
        ("Leek", "Farfetch'd-Galar"),
    ),
)
def test_canonical_regional_and_special_forms_remain_eligible(item, species):
    """Dex base-species identity supports real forms without prefix matching."""
    battle, holder, foe = native_battle(species, item=item)
    holder.name = "Buddy"
    event = "ModifyCritRatio" if item in {"Stick", "Leek"} else "ModifyAtk"
    value = 0 if event == "ModifyCritRatio" else holder.stats["atk"]
    expected = 2 if event == "ModifyCritRatio" else value * 2
    assert battle.runEvent(event, holder, foe, None, value) == expected


def test_stick_does_not_gain_leeks_sirfetchd_extension():
    """The two critical items deliberately have different native allowlists."""
    battle, holder, foe = native_battle("Sirfetch'd", item="Stick")
    assert battle.runEvent("ModifyCritRatio", holder, foe, None, 0) == 0


@pytest.mark.parametrize("item,species,event,stat", STAT_CASES)
@pytest.mark.parametrize("suppression", ("magicroom", "embargo", "klutz"))
def test_stat_bonuses_still_obey_effective_item_suppression(
    item, species, event, stat, suppression
):
    """Identity fixes cannot bypass the ordinary effective-item boundary."""
    battle, holder, foe = native_battle(species, item=item)
    holder.name = "Buddy"
    if suppression == "magicroom":
        battle.field.pseudo_weather["magicroom"] = {"duration": 5}
    elif suppression == "embargo":
        holder.volatiles["embargo"] = {"duration": 5}
    else:
        holder.ability = "Klutz"
    base = holder.stats[stat]
    assert battle.runEvent(event, holder, foe, None, base) == base
    assert holder.item is not None


@pytest.mark.parametrize("item,species", CRITICAL_CASES)
def test_critical_items_remain_suppressed_in_magic_room(item, species):
    """The repaired critical callbacks do not bypass Magic Room."""
    battle, holder, foe = native_battle(species, item=item)
    battle.field.pseudo_weather["magicroom"] = {"duration": 5}
    assert battle.runEvent("ModifyCritRatio", holder, foe, None, 0) == 0


@pytest.mark.parametrize("item,species,event,stat", STAT_CASES)
def test_real_transform_preserves_native_policy_and_disables_ditto_powders(
    item, species, event, stat
):
    """Most items follow base identity; powders require untransformed Ditto."""
    battle, holder, foe = native_battle(species, item=item, foe="Mew")
    attack(battle, holder, foe, "Transform")
    assert holder.transformed and str(holder.base_species) == species
    assert str(holder.species) == "Mew"
    value = 100
    assert battle.runEvent(event, holder, foe, None, value) == (
        value if species == "Ditto" else value * 2
    )


@pytest.mark.parametrize("item,species,event,stat", STAT_CASES)
def test_foreign_transform_into_a_native_species_cannot_gain_its_bonus(item, species, event, stat):
    """A copied current appearance never overwrites the original base identity."""
    battle, holder, foe = native_battle("Mew", item=item, foe=species)
    attack(battle, holder, foe, "Transform")
    assert holder.transformed and str(holder.base_species) == "Mew"
    assert str(holder.species) == species
    assert battle.runEvent(event, holder, foe, None, 100) == 100


@pytest.mark.parametrize("item,species", CRITICAL_CASES)
def test_critical_items_follow_native_identity_through_transform(item, species):
    """Native critical bonuses survive copying; foreign copied natives get none."""
    battle, holder, foe = native_battle(species, item=item, foe="Mew")
    attack(battle, holder, foe, "Transform")
    assert holder.transformed
    assert battle.runEvent("ModifyCritRatio", holder, foe, None, 0) == 2
    battle, holder, foe = native_battle("Mew", item=item, foe=species)
    attack(battle, holder, foe, "Transform")
    assert holder.transformed
    assert battle.runEvent("ModifyCritRatio", holder, foe, None, 0) == 0


@pytest.mark.parametrize("item", ("Light Ball", "Thick Club"))
def test_nickname_fix_reaches_actual_damage(item):
    """Native nicknames retain damage while foreign nicknames cannot boost it."""
    species = "Pikachu" if item == "Light Ball" else "Cubone"
    native_damage = []
    for nickname in (species, "Buddy"):
        battle, holder, foe = native_battle(species, item=item)
        holder.name = nickname
        native_damage.append(attack(battle, holder, foe, "Tackle")[0])
    assert native_damage[0] == native_damage[1] > 0
    foreign_damage = []
    for nickname in ("Mew", species):
        battle, holder, foe = native_battle("Mew", item=item)
        holder.name = nickname
        foreign_damage.append(attack(battle, holder, foe, "Tackle")[0])
    assert foreign_damage[0] == foreign_damage[1] > 0


def test_identity_helper_rejects_names_unknown_species_and_inconsistent_powders():
    """Adapters may supply real species, but never invent identity from a name."""
    from pokemon.battle.item_identity import HeldItemIdentity

    assert not HeldItemIdentity.matches(SimpleNamespace(name="Pikachu"), "Pikachu", family=True)
    assert not HeldItemIdentity.matches(
        SimpleNamespace(base_species="Pikachu-Fake", species="Pikachu"), "Pikachu", family=True
    )
    assert HeldItemIdentity.matches(SimpleNamespace(species="Pikachu"), "Pikachu", family=True)
    assert not HeldItemIdentity.matches(
        SimpleNamespace(species="Pikachu", transformed=True), "Pikachu", family=True
    )
    assert not HeldItemIdentity.matches(
        SimpleNamespace(base_species="Mew", species="Ditto"), "Ditto", untransformed=True
    )
    assert not HeldItemIdentity.matches(
        SimpleNamespace(base_species="Ditto", species="Mew"), "Ditto", untransformed=True
    )
