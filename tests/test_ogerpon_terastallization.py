"""Native Ogerpon masks, committed Tera, signature attacks and restoration."""

import copy
import random

import pytest

from pokemon.battle.battledata import Move, Pokemon
from pokemon.battle.engine import Action, ActionType, Battle, BattleMove, BattleParticipant, BattleType
from pokemon.battle.terastallization import Terastallization
from pokemon.dex.entities import Stats
from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats
from tests.test_terapagos_terastallization import battler


FORMS = (
    ("Ogerpon", "Defiant", "", "Grass", "Teal", "spe"),
    ("Ogerpon-Wellspring", "Water Absorb", "Wellspring Mask", "Water", "Wellspring", "spd"),
    ("Ogerpon-Hearthflame", "Mold Breaker", "Hearthflame Mask", "Fire", "Hearthflame", "atk"),
    ("Ogerpon-Cornerstone", "Sturdy", "Cornerstone Mask", "Rock", "Cornerstone", "def"),
)


def encounter(form, *, item=None, ability=None):
    """Build real calculated actors and initialize ordinary entry callbacks."""
    species, native_ability, mask, _, _, _ = form
    user = battler(species, ability or native_ability, moves=("Ivy Cudgel", "Splash", "Tackle"), tera_type="Stellar")
    foe = battler("Wailord", "No Ability", moves=("Splash",))
    reserve = battler("Eevee", "No Ability", moves=("Splash",))
    a, b = BattleParticipant("QA", [user, reserve], team="A"), BattleParticipant("Foe", [foe], team="B")
    a.active, b.active = [user], [foe]
    battle = Battle(BattleType.PVP, [a, b], rng=random.Random(19))
    battle.tera_used, battle.tera_pending = set(), {}
    user.item = battle._coerce_item(mask if item is None else item)
    battle.start_turn()
    return battle, user, foe


def stage(user, stat):
    """Read the engine's supported long or short boost key."""
    aliases = {"atk": "attack", "def": "defense", "spe": "speed", "spd": "special_defense"}
    return user.boosts.get(stat, user.boosts.get(aliases[stat], 0))


def commit(battle, user):
    """Use the real declaration/commit boundary rather than a form callback."""
    owner = battle.participant_for(user)
    chosen = Terastallization.reserve(battle, owner, user)
    assert Terastallization.activate(battle, owner, user, chosen)
    return chosen


@pytest.mark.parametrize("form", FORMS, ids=[row[4] for row in FORMS])
def test_native_mask_fixes_tera_type_and_boosts_once_only_after_commit(form):
    battle, user, _ = encounter(form)
    species, ability, _, typ, aspect, stat = form
    maximum, stats = user.max_hp, get_stats(user)
    user.hp -= 17
    assert stage(user, stat) == 0
    assert Terastallization.reserve(battle, battle.participants[0], user) == typ
    assert user.species == species and stage(user, stat) == 0 and not battle.tera_used
    assert Terastallization.activate(battle, battle.participants[0], user, typ)
    assert user.species == f"Ogerpon-{aspect}-Tera" and user.types == [typ]
    assert user.hasAbility(f"Embody Aspect ({aspect})") and user.terastallized == typ
    assert user.max_hp == maximum == get_max_hp(user) and user.hp == maximum - 17
    assert get_stats(user) == stats and stage(user, stat) == 1
    full = {"atk": "attack", "def": "defense", "spe": "speed", "spd": "special_defense"}[stat]
    assert user.getStat(stat) == stats[full] * 3 // 2
    battle.runEvent("AfterTerastallization", user)
    battle.start_turn()
    assert stage(user, stat) == 1 and battle.tera_used == {"A"}
    with pytest.raises(ValueError, match="already Terastallized"):
        Terastallization.reserve(battle, battle.participants[0], user)


@pytest.mark.parametrize("form", FORMS, ids=[row[4] for row in FORMS])
@pytest.mark.parametrize("tera", [False, True])
def test_ivy_cudgel_uses_native_form_before_and_after_tera(form, tera):
    from pokemon import dex
    from pokemon.names import resolve_dex_entry

    battle, user, foe = encounter(form)
    raw = copy.deepcopy(resolve_dex_entry(dex.MOVEDEX, "Ivy Cudgel").raw)
    if tera:
        commit(battle, user)
    move = BattleMove("Ivy Cudgel")
    before = foe.hp
    battle.use_move(Action(battle.participants[0], ActionType.MOVE, battle.participants[1],
                           move=move, pokemon=user, target_pokemon=foe))
    assert move.type == form[3] and foe.hp < before
    assert resolve_dex_entry(dex.MOVEDEX, "Ivy Cudgel").raw == raw
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("form", FORMS[1:], ids=[row[4] for row in FORMS[1:]])
def test_mask_boosts_all_damaging_types_by_native_identity_even_with_a_nickname(form):
    battle, user, foe = encounter(form)
    user.name = "QA nickname"
    mask = user.item
    for name in ("Tackle", "Ivy Cudgel"):
        assert mask.call("onBasePower", 100, user=user, target=foe, move=BattleMove(name)) == 120
    assert battle.take_item(user, source=foe) is None
    assert user.item is mask


@pytest.mark.parametrize("form", FORMS[1:], ids=[row[4] for row in FORMS[1:]])
def test_base_ogerpon_mask_entry_is_runtime_only_and_preserves_health(form):
    battle, user, _ = encounter(FORMS[0], item=form[2])
    assert user.species == form[0] and user.hasAbility(form[1])
    assert user.types == ["Grass", form[3]] and not user.terastallized
    assert user.base_species == "Ogerpon" and user.max_hp == get_max_hp(user)
    commit(battle, user)
    battle.restore_transforms()
    assert user.species == "Ogerpon" and user.types == ["Grass"] and user.hasAbility("Defiant")


@pytest.mark.parametrize("old,new", [(1, 2), (2, 3), (3, 1)])
def test_a_different_mask_selects_its_ordinary_form_then_restores_the_original(old, new):
    battle, user, _ = encounter(FORMS[old], item=FORMS[new][2])
    assert user.species == FORMS[new][0] and user.hasAbility(FORMS[new][1])
    assert user.base_species == FORMS[old][0]
    user.hp -= 9
    assert commit(battle, user) == FORMS[new][3]
    battle.restore_transforms()
    assert user.species == FORMS[old][0] and user.hasAbility(FORMS[old][1])
    assert user.types == ["Grass", FORMS[old][3]] and user.max_hp - user.hp == 9


@pytest.mark.parametrize("form", FORMS, ids=[row[4] for row in FORMS])
def test_checkpoint_switch_reentry_and_final_restoration_preserve_owned_identity(form):
    battle, user, _ = encounter(form)
    user.hp -= 11
    commit(battle, user)
    saved = user.to_dict()
    restored = Pokemon.from_dict(saved)
    assert restored.species == user.species and restored.terastallized == form[3]
    assert restored.hp == user.hp and restored.base_species == form[0]
    owner = battle.participants[0]
    owner.pokemons[0] = owner.active[0] = restored
    battle.switch_pokemon(owner, owner.pokemons[1])
    battle.run_after_switch()
    battle.switch_pokemon(owner, restored)
    assert restored.species == f"Ogerpon-{form[4]}-Tera" and restored.terastallized == form[3]
    assert stage(restored, form[5]) == 1
    assert battle.tera_used == {"A"}
    battle.restore_transforms()
    assert restored.species == form[0] and restored.types == (["Grass"] if not form[2] else ["Grass", form[3]])
    assert restored.hasAbility(form[1]) and restored.max_hp - restored.hp == 11
    assert not restored.terastallized and not restored.tempvals.get("native_form")


@pytest.mark.parametrize("form", FORMS[1:], ids=[row[4] for row in FORMS[1:]])
def test_missing_required_mask_cannot_commit_native_tera(form):
    battle, user, _ = encounter(form, item="")
    with pytest.raises(ValueError):
        Terastallization.reserve(battle, battle.participants[0], user)
    assert not user.terastallized and not battle.tera_used and not battle.tera_pending


@pytest.mark.parametrize("invalid", ["transformed", "foreign", "prebuilt", "fainted"])
def test_ineligible_native_holders_cannot_consume_the_side(invalid):
    battle, user, _ = encounter(FORMS[0])
    if invalid == "transformed":
        user.transformed = True
    elif invalid == "foreign":
        user.base_species = "Mew"
    elif invalid == "prebuilt":
        user.species = "Ogerpon-Teal-Tera"
    else:
        user.hp = 0
    with pytest.raises(ValueError):
        Terastallization.reserve(battle, battle.participants[0], user)
    assert not user.terastallized and not battle.tera_used


def test_failed_commit_and_non_native_embody_assignment_cannot_grant_a_boost():
    battle, user, _ = encounter(FORMS[0])
    typ = Terastallization.reserve(battle, battle.participants[0], user)
    user.hp = 0
    assert not Terastallization.activate(battle, battle.participants[0], user, typ)
    assert user.species == "Ogerpon" and not user.terastallized and not battle.tera_used
    user = battler("Mew", "Embody Aspect (Teal)", moves=("Splash",))
    other = battler("Wailord", "No Ability", moves=("Splash",))
    a, b = BattleParticipant("A", [user], team="A"), BattleParticipant("B", [other], team="B")
    a.active, b.active = [user], [other]
    plain = Battle(BattleType.PVP, [a, b])
    plain.start_turn()
    assert stage(user, "spe") == 0


@pytest.mark.parametrize("form", FORMS, ids=[row[4] for row in FORMS])
def test_suppression_blocks_the_boost_but_not_native_typing(form):
    battle, user, _ = encounter(form)
    user.ability_suppressed = True
    commit(battle, user)
    assert user.types == [form[3]] and user.terastallized == form[3]
    assert stage(user, form[5]) == 0


@pytest.mark.parametrize("mask", [row[2] for row in FORMS[1:]])
def test_a_mask_on_an_unrelated_species_never_changes_it_into_ogerpon(mask):
    battle, user, _ = encounter(FORMS[0])
    user.species = user.base_species = "Mew"
    user.item = battle._coerce_item(mask)
    battle._apply_item_forme_effects(user)
    assert user.species == "Mew"
    assert user.item.call("onBasePower", 100, user=user, move=BattleMove("Tackle")) == 100


def test_ordinary_switch_clears_boosts_and_baton_pass_preserves_them_until_transfer():
    battle, user, _ = encounter(FORMS[0])
    user.species = user.base_species = "Mew"
    user.boosts = {"atk": 3, "def": -1}
    battle.switch_pokemon(battle.participants[0], battle.participants[0].pokemons[1])
    assert not user.boosts
    user.boosts = {"atk": 3}
    user.tempvals["baton_pass"] = True
    battle.on_switch_out(user)
    assert stage(user, "atk") == 3


@pytest.mark.parametrize("form", FORMS, ids=[row[4] for row in FORMS])
def test_catalog_embody_cases_use_an_actual_native_tera_command(form):
    from tools.live_dex_cases import catalog

    case = next(case for case in catalog() if case.kind == "ability" and case.subject == f"Embody Aspect ({form[4]})")
    assert case.a[0].species == form[0] and case.a[0].ability == form[1] and case.a[0].item == form[2]
    assert case.entry_ability == form[1]
    assert case.turns[0][0] == ("a", "+tera")
    assert {row["type"] for row in case.assertions} >= {"boosts", "types", "ability", "active_species"}


@pytest.mark.parametrize("short,full", [("atk", "attack"), ("def", "defense"),
                                      ("spa", "special_attack"), ("spd", "special_defense"), ("spe", "speed")])
def test_stat_getter_accepts_both_boost_aliases_without_changing_unboosted_values(short, full):
    _, user, _ = encounter(FORMS[0])
    base = get_stats(user)[full]
    for alias in (short, full):
        user.boosts = {alias: -2}
        assert user.getStat(short) == user.getStat(full) == base // 2
        assert user.getStat(short, True) == base
