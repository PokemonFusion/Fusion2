"""Behavioral regressions for effects reproduced with ordinary local logins."""

import logging
import random
from types import SimpleNamespace

import pytest

from .helpers import build_battle, load_modules
from .test_live_move_state_persistence import Slots
from .test_pending_action_effects import action


@pytest.fixture(autouse=True)
def quiet_offline_log():
    """Keep these simulations out of the real local battle transcript."""
    logger = logging.getLogger("battle")
    previous = logger.disabled
    logger.disabled = True
    yield
    logger.disabled = previous


def calculated(pokemon, species="Mew", level=50):
    """Use actual species, training and level through the canonical helpers."""
    from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats

    pokemon.name = pokemon.species = pokemon.base_species = species
    pokemon.level = level
    pokemon.ivs, pokemon.evs, pokemon.nature = [0] * 6, [0] * 6, "Hardy"
    pokemon.base_stats = load_modules()["Stats"](**get_stats(pokemon))
    pokemon.max_hp = pokemon.hp = get_max_hp(pokemon)
    pokemon.types = list(pokemon._lookup_species_entry(species).raw["types"])
    return pokemon


def fixture(species="Mew", foe="Wailord"):
    """Build a real callback-enabled battle with calculated native stats."""
    battle, user, target = build_battle(attacker_ability="No Guard")
    calculated(user, species)
    calculated(target, foe, 100)
    return battle, user, target


def use(battle, user, target, name, *, seed=0):
    """Use the same named action and PP/effect dispatch as the game engine."""
    battle.rng = random.Random(seed)
    battle.use_move(action(battle, user, target, name))
    assert not getattr(battle, "_callback_failures", [])


def stage(pokemon, name):
    """Read stages regardless of the canonical short/long serialized aliases."""
    from pokemon.utils.boosts import STAT_KEY_MAP
    return pokemon.boosts.get(STAT_KEY_MAP.get(name, name), pokemon.boosts.get(name, 0))


@pytest.mark.parametrize("name", ["Aromatherapy", "Heal Bell"])
def test_team_cure_reaches_a_benched_member_without_curing_the_enemy(name):
    battle, user, target = fixture()
    bench = calculated(load_modules()["Pokemon"]("Eevee"), "Eevee")
    battle.participants[0].pokemons.append(bench)
    bench.battle = battle
    user.setStatus("psn")
    bench.setStatus("par")
    target.setStatus("brn")
    use(battle, user, user, name)
    assert not user.status and not bench.status and target.status == "brn"


def test_doodle_copies_to_the_living_active_ally():
    battle, user, target = fixture()
    ally = calculated(load_modules()["Pokemon"]("Eevee"), "Eevee")
    ally.battle = battle
    battle.participants[0].pokemons.append(ally)
    battle.participants[0].active.append(ally)
    target.ability = battle._resolve_ability("Overgrow") if hasattr(battle, "_resolve_ability") else "Overgrow"
    use(battle, user, target, "Doodle")
    from pokemon.battle.effect_context import EffectContext
    assert EffectContext.key(user.ability) == EffectContext.key(ally.ability) == "overgrow"


def test_natural_gift_spends_its_berry_and_cannot_reuse_it():
    battle, user, target = fixture()
    user.item = battle._coerce_item("Cheri Berry")
    use(battle, user, target, "Natural Gift")
    assert not user.item and target.hp < target.max_hp
    hp = target.hp
    use(battle, user, target, "Natural Gift")
    assert target.hp == hp


@pytest.mark.parametrize("name", ["Power Trick", "Power Shift"])
def test_stat_swap_changes_the_damage_stats_and_roundtrips(name):
    from pokemon.battle.utils import get_modified_stat
    battle, user, _ = fixture("Shuckle")
    old = {stat: get_modified_stat(user, stat) for stat in ("attack", "defense")}
    use(battle, user, user, name)
    restored = load_modules()["Pokemon"].from_dict(user.to_dict())
    for pokemon in (user, restored):
        assert get_modified_stat(pokemon, "attack") == old["defense"]
        assert get_modified_stat(pokemon, "defense") == old["attack"]
    use(battle, user, user, name)
    assert get_modified_stat(user, "attack") == old["attack"]
    assert get_modified_stat(user, "defense") == old["defense"]


@pytest.mark.parametrize("consume", ["Swallow", "Spit Up"])
def test_stockpile_layers_and_actual_boosts_survive_checkpoint_then_are_consumed(consume):
    battle, user, target = fixture()
    user.hp = user.max_hp // 4
    use(battle, user, user, "Stockpile")
    restored = load_modules()["Pokemon"].from_dict(user.to_dict())
    restored.battle = battle
    battle.participants[0].pokemons[0] = restored
    battle.participants[0].active[0] = restored
    use(battle, restored, restored, "Stockpile")
    assert stage(restored, "def") == stage(restored, "spd") == 2
    before = restored.hp
    use(battle, restored, restored if consume == "Swallow" else target, consume)
    assert stage(restored, "def") == stage(restored, "spd") == 0
    assert "stockpile" not in restored.volatiles
    if consume == "Swallow":
        assert restored.hp == before + restored.max_hp // 2
    else:
        assert target.hp < target.max_hp


def test_autotomize_weight_reduction_stacks_and_survives_checkpoint():
    from pokemon.battle.effect_context import EffectContext
    battle, user, _ = fixture("Bronzong")
    before = EffectContext.weight(user)
    use(battle, user, user, "Autotomize")
    assert EffectContext.weight(user) == pytest.approx(before - 100)
    restored = load_modules()["Pokemon"].from_dict(user.to_dict())
    assert EffectContext.weight(restored) == pytest.approx(before - 100)
    use(battle, user, user, "Autotomize")
    assert EffectContext.weight(user) == .1


@pytest.mark.parametrize("name,relation", [("Electro Ball", "greater"), ("Gyro Ball", "less")])
def test_speed_power_responds_to_real_agility_stages(name, relation):
    battle, user, target = fixture(foe="Mew")
    calculated(target, "Mew", 50)
    use(battle, user, target, name)
    before = target.max_hp - target.hp
    target.hp = target.max_hp
    use(battle, user, user, "Agility")
    use(battle, user, target, name)
    after = target.max_hp - target.hp
    assert after > before if relation == "greater" else after < before


@pytest.mark.parametrize("friendship", [0, 255])
def test_owned_friendship_reaches_the_battle_and_its_checkpoint(friendship):
    from pokemon.helpers.pokemon_helpers import get_max_hp
    from utils.pokemon_utils import build_battle_pokemon_from_model
    model = SimpleNamespace(species="Mew", name="Mew", level=50, moves=["Return"],
                            ivs=[0] * 6, evs=[0] * 6, nature="Hardy", friendship=friendship,
                            gender="N", ability="No Guard", held_item="")
    model.current_hp = get_max_hp(model)
    pokemon = build_battle_pokemon_from_model(model)
    assert pokemon.happiness == friendship
    restored = load_modules()["Pokemon"].from_dict(pokemon.to_dict())
    assert restored.happiness == friendship


@pytest.mark.parametrize("name,target_species,attack", [("Foresight", "Gengar", "Tackle"),
    ("Odor Sleuth", "Gengar", "Tackle"), ("Miracle Eye", "Umbreon", "Confusion")])
def test_identification_bypasses_its_specific_type_immunity(name, target_species, attack):
    battle, user, target = fixture(foe=target_species)
    use(battle, user, target, attack)
    assert target.hp == target.max_hp
    use(battle, user, target, name)
    use(battle, user, target, attack)
    assert target.hp < target.max_hp


def test_endure_survives_a_lethal_attack_but_not_indirect_damage():
    from pokemon.battle.indirect_damage import apply_indirect_damage
    battle, user, target = fixture()
    user.hp = max(2, user.max_hp // 10)
    use(battle, user, user, "Endure")
    use(battle, target, user, "Tackle")
    assert user.hp == 1
    apply_indirect_damage(user, 1, battle=battle)
    assert user.hp == 0


def test_imprison_blocks_shared_moves_and_allows_the_unshared_choice():
    battle, user, target = fixture()
    user.moves = [load_modules()["Move"](name) for name in ("Imprison", "Tackle")]
    target.moves = [load_modules()["Move"](name) for name in ("Tackle", "Water Gun")]
    use(battle, user, user, "Imprison")
    assert battle._is_move_disabled(target, load_modules()["BattleMove"]("Tackle"))
    assert not battle._is_move_disabled(target, load_modules()["BattleMove"]("Water Gun"))


@pytest.mark.parametrize("remaining", [5, 1])
def test_trump_card_passes_remaining_pp_to_the_damage_callback(remaining):
    battle, user, target = fixture()
    slots = user.activemoveslot_set = Slots(remaining)
    slots.slot.move.name = "Trump Card"
    user.moves = [load_modules()["Move"]("Trump Card")]
    use(battle, user, target, "Trump Card")
    assert slots.slot.current_pp == remaining - 1
    expected_power = 200 if remaining == 1 else 40
    assert user.last_move.power == expected_power


def test_embargo_stops_leftovers_without_removing_the_held_item():
    battle, user, target = fixture()
    target.item = battle._coerce_item("Leftovers")
    target.hp //= 2
    initial = target.hp
    use(battle, user, target, "Embargo")
    battle.residual()
    assert target.hp == initial and target.item


def test_defog_clears_both_hazards_target_screens_and_terrain():
    battle, user, target = fixture()
    a, b = (participant.side for participant in battle.participants)
    for side in (a, b):
        side.set_hazard("spikes")
        side.add_side_condition("reflect", {"duration": 5})
    battle.setTerrain("Electric Terrain")
    use(battle, user, target, "Defog")
    assert all("spikes" not in side.conditions for side in (a, b))
    assert "reflect" in a.conditions and "reflect" not in b.conditions
    assert not battle.field.terrain


def test_tidy_up_clears_both_substitutes_and_canonical_hazard_maps():
    battle, user, target = fixture()
    for side in (participant.side for participant in battle.participants):
        side.set_hazard("spikes")
    use(battle, user, user, "Substitute")
    use(battle, target, target, "Substitute")
    use(battle, user, user, "Tidy Up")
    assert all("substitute" not in pokemon.volatiles for pokemon in (user, target))
    assert all(not participant.side.hazards and "spikes" not in participant.side.conditions for participant in battle.participants)
    assert stage(user, "atk") == stage(user, "spe") == 1


@pytest.mark.parametrize("name,status,stat,delta", [
    ("Baneful Bunker", "psn", None, 0), ("Burning Bulwark", "brn", None, 0),
    ("King's Shield", None, "atk", -1), ("Obstruct", None, "def", -2),
    ("Silk Trap", None, "spe", -1), ("Spiky Shield", None, None, 0)])
def test_contact_shields_block_damage_and_retaliate_against_the_attacker(name, status, stat, delta):
    battle, user, target = fixture()
    use(battle, user, user, name)
    assert not user.status and user.hp == user.max_hp
    use(battle, target, user, "Tackle")
    assert user.hp == user.max_hp
    if status:
        assert target.status == status
    if stat:
        assert stage(target, stat) == delta
    if name == "Spiky Shield":
        assert target.hp == target.max_hp - target.max_hp // 8


@pytest.mark.parametrize("protection", ["noncontact", "pads", "longreach"])
def test_shield_does_not_retaliate_when_contact_is_absent_or_avoided(protection):
    battle, user, target = fixture()
    if protection == "pads":
        target.item = battle._coerce_item("Protective Pads")
    if protection == "longreach":
        target.ability = "Long Reach"
    use(battle, user, user, "Baneful Bunker")
    use(battle, target, user, "Water Gun" if protection == "noncontact" else "Tackle")
    assert user.hp == user.max_hp and not target.status


@pytest.mark.parametrize("name", ["Lock-On", "Mind Reader"])
def test_lock_matches_one_target_survives_checkpoint_and_expires_without_bypassing_protect(name):
    from pokemon.battle.accuracy import MoveAccuracy
    from pokemon.dex.functions.moves.damage_moves import Lockon
    battle, user, target = fixture()
    other = calculated(load_modules()["Pokemon"]("Eevee"), "Eevee")
    use(battle, user, target, name)
    restored = load_modules()["Pokemon"].from_dict(user.to_dict())
    assert MoveAccuracy.locked_on(restored, target)
    assert not MoveAccuracy.locked_on(restored, other)
    use(battle, target, target, "Protect")
    use(battle, user, target, "Zap Cannon")
    assert target.hp == target.max_hp
    Lockon().onResidual(restored, battle)
    assert MoveAccuracy.locked_on(restored, target)
    Lockon().onResidual(restored, battle)
    assert not MoveAccuracy.locked_on(restored, target)


def test_grudge_drains_the_knockout_moves_owned_and_cached_pp():
    battle, user, target = fixture()
    user.hp = 1
    slots = target.activemoveslot_set = Slots(10)
    cached = load_modules()["Move"]("Tackle")
    cached.pp = 10
    target.moves = [cached]
    use(battle, user, user, "Grudge")
    use(battle, target, user, "Tackle")
    assert user.hp == 0
    battle.run_faint()
    assert slots.slot.current_pp == cached.pp == target.last_move.pp == 0


def test_beat_up_includes_healthy_bench_and_excludes_fainted_or_statused_members():
    battle, user, target = fixture()
    damages = []
    for index in range(4):
        if index:
            bench = calculated(load_modules()["Pokemon"]("Eevee"), "Eevee")
            bench.battle = battle
            if index == 2:
                bench.hp = 0
            elif index == 3:
                bench.setStatus("par")
            battle.participants[0].pokemons.append(bench)
        target.hp = target.max_hp
        use(battle, user, target, "Beat Up")
        damages.append(target.max_hp - target.hp)
    assert damages[1] > damages[0] and damages[1:] == [damages[1]] * 3


def test_helping_hand_boosts_only_the_ally_and_ends_at_the_turn_boundary():
    battle, user, target = fixture()
    ally = calculated(load_modules()["Pokemon"]("Eevee"), "Eevee")
    ally.battle = battle
    battle.participants[0].pokemons.append(ally)
    battle.participants[0].active.append(ally)
    use(battle, ally, target, "Tackle")
    before = target.max_hp - target.hp
    target.hp = target.max_hp
    use(battle, user, ally, "Helping Hand")
    use(battle, ally, target, "Tackle")
    assert target.max_hp - target.hp > before
    assert "helpinghand" not in user.volatiles
    battle.residual()
    assert "helpinghand" not in ally.volatiles


def test_powder_cancels_fire_with_indirect_damage_but_allows_a_nonfire_move():
    battle, user, target = fixture()
    use(battle, user, target, "Powder")
    use(battle, target, user, "Ember")
    assert target.hp == target.max_hp - target.max_hp // 4 and user.hp == user.max_hp
    use(battle, target, user, "Water Gun")
    assert user.hp < user.max_hp
