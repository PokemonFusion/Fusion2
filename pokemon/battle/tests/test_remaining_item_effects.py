"""Normal-resolution regressions for the remaining October item diagnoses."""

import pytest

from pokemon.battle.effect_context import EffectContext

from .test_diagnosed_item_effects import attack, native_battle


@pytest.mark.parametrize("item", ["Choice Band", "Choice Specs", "Choice Scarf"])
def test_choice_item_allows_locked_move_and_rejects_other_move(item):
    from pokemon.battle.engine import BattleMove

    battle, holder, foe = native_battle(item=item)
    attack(battle, holder, foe, "Tackle")
    assert not battle._is_move_disabled(holder, BattleMove(name="Tackle"))
    assert battle._is_move_disabled(holder, BattleMove(name="Water Gun"))
    assert attack(battle, holder, foe, "Tackle")[0] > 0
    holder.item_suppressed = True
    assert not battle._is_move_disabled(holder, BattleMove(name="Water Gun"))
    holder.item_suppressed = False
    assert battle._is_move_disabled(holder, BattleMove(name="Water Gun"))


def test_assault_vest_disables_native_status_candidate_only():
    from pokemon.battle.engine import BattleMove

    battle, holder, _ = native_battle(item="Assault Vest")
    assert battle._is_move_disabled(holder, BattleMove(name="Growl"))
    assert not battle._is_move_disabled(holder, BattleMove(name="Tackle"))
    holder.item_suppressed = True
    assert not battle._is_move_disabled(holder, BattleMove(name="Growl"))


@pytest.mark.parametrize(
    "ability,move,foe",
    [
        ("Magic Guard", "Tackle", "Wailord"),
        ("Sheer Force", "Thunderbolt", "Wailord"),
        ("No Ability", "Tackle", "Gengar"),
    ],
)
def test_life_orb_recoil_requires_damage_and_obeys_recoil_exceptions(ability, move, foe):
    battle, holder, target = native_battle(item="Life Orb", ability=ability, foe=foe)
    before = holder.hp
    attack(battle, holder, target, move)
    assert holder.hp == before


def test_life_orb_recoils_once_on_successful_damage():
    battle, holder, foe = native_battle(item="Life Orb")
    before = holder.hp
    assert attack(battle, holder, foe, "Tackle")[0] > 0
    assert holder.hp == before - holder.max_hp // 10


def test_punching_glove_removes_contact_before_helmet_reaction():
    from pokemon.dex import ITEMDEX
    from pokemon.names import resolve_dex_entry

    battle, holder, foe = native_battle(item="Punching Glove")
    battle.set_item(foe, resolve_dex_entry(ITEMDEX, "Rocky Helmet"))
    before = holder.hp
    assert attack(battle, holder, foe, "Mach Punch")[0] > 0
    assert holder.hp == before


@pytest.mark.parametrize("seed", range(8))
def test_loaded_dice_uses_four_or_five_hits(seed):
    battle, holder, foe = native_battle(item="Loaded Dice", ability="No Guard")
    battle.rng.seed(seed)
    messages = []
    battle.log_action = messages.append
    _, move = attack(battle, holder, foe, "Fury Swipes")
    assert tuple(move.multihit) == (4, 5)
    assert any(f"hit {count} times" in line for line in messages for count in (4, 5))


@pytest.mark.parametrize("item", ["", "Terrain Extender"])
@pytest.mark.parametrize(
    "terrain", ["electricterrain", "grassyterrain", "mistyterrain", "psychicterrain"]
)
def test_terrain_expires_at_its_actual_duration(item, terrain):
    battle, holder, _ = native_battle(item=item)
    battle.setTerrain(terrain, source=holder)
    duration = 8 if item else 5
    for _ in range(duration - 1):
        battle.residual()
        assert battle.field.terrain == terrain
    battle.residual()
    assert not battle.field.terrain
    assert terrain not in battle.field.pseudo_weather


def test_power_herb_skips_charge_and_consumes_through_native_service():
    battle, holder, foe = native_battle(item="Power Herb")
    damage, _ = attack(battle, holder, foe, "Solar Beam")
    assert damage > 0 and holder.item is None
    assert "solarbeam" not in holder.volatiles


@pytest.mark.parametrize(
    "item,move,foe", [("Normal Gem", "Tackle", "Gengar"), ("Fire Gem", "Inferno", "Wailord")]
)
def test_gem_retained_when_attack_is_immune_or_misses(item, move, foe):
    battle, holder, target = native_battle(item=item, foe=foe)
    battle.rng.seed(2)  # Inferno's genuine accuracy miss; no forced-hit override.
    damage, _ = attack(battle, holder, target, move)
    assert damage == 0
    assert EffectContext.key(holder.item) == EffectContext.key(item)
    assert not target.status


def test_air_balloon_blocks_ground_and_pops_only_on_damaging_hit():
    battle, holder, foe = native_battle(item="Air Balloon")
    assert attack(battle, foe, holder, "Earthquake")[0] == 0
    assert holder.item is not None
    assert attack(battle, foe, holder, "Tackle")[0] > 0
    assert holder.item is None


def test_safety_goggles_blocks_spore_without_suppressing_user_action():
    battle, holder, foe = native_battle(item="Safety Goggles")
    attack(battle, foe, holder, "Spore")
    assert not holder.status
    holder.item_suppressed = True
    attack(battle, foe, holder, "Spore")
    assert holder.status == "slp"


def test_room_service_affects_holder_not_trick_room_setter():
    battle, holder, foe = native_battle(item="Room Service")
    attack(battle, foe, holder, "Trick Room")
    assert holder.boosts.get("speed", 0) == -1
    assert foe.boosts.get("speed", 0) == 0
    assert holder.item is None


def test_float_stone_uses_native_species_weight_and_suppression():
    battle, holder, _ = native_battle(name="Wailmer", item="Float Stone")
    assert EffectContext.weight(holder) == 65
    holder.item_suppressed = True
    assert EffectContext.weight(holder) == 130


def test_enigma_heals_after_super_effective_damage_and_respects_unnerve():
    for ability in ["No Ability", "Unnerve"]:
        battle, holder, foe = native_battle(item="Enigma Berry")
        foe.ability = ability
        before = holder.hp
        _, move = attack(battle, foe, holder, "Lick")
        damage = move.total_damage
        assert damage > 0
        assert holder.hp == min(
            holder.max_hp, before - damage + (holder.max_hp // 4 if ability == "No Ability" else 0)
        )
        assert (holder.item is None) is (ability == "No Ability")


def test_mirror_herb_copies_foes_self_boost_only_once():
    battle, holder, foe = native_battle(item="Mirror Herb")
    attack(battle, foe, holder, "Swords Dance")
    assert holder.boosts["attack"] == foe.boosts["attack"] == 2
    assert holder.item is None
    attack(battle, foe, holder, "Swords Dance")
    assert holder.boosts["attack"] == 2


def test_metronome_repeated_move_boost_caps_and_resets_on_new_move():
    battle, holder, foe = native_battle(item="Metronome")
    amounts = []
    for _ in range(8):
        battle.rng.seed(4)
        foe.hp = foe.max_hp
        amounts.append(attack(battle, holder, foe, "Tackle")[0])
    assert amounts[0] < amounts[1] < amounts[5]
    assert amounts[5] == amounts[6] == amounts[7]
    attack(battle, holder, foe, "Splash")
    assert holder.volatiles["metronome"]["num_consecutive"] == 0


@pytest.mark.parametrize(
    "item,species,expected",
    [
        ("Blue Orb", "Kyogre", "Kyogre-Primal"),
        ("Red Orb", "Groudon", "Groudon-Primal"),
        ("Rusted Sword", "Zacian", "Zacian-Crowned"),
        ("Rusted Shield", "Zamazenta", "Zamazenta-Crowned"),
    ],
)
def test_native_item_forms_activate_only_for_eligible_species(item, species, expected):
    ability = {
        "Kyogre": "Drizzle",
        "Groudon": "Drought",
        "Zacian": "Intrepid Sword",
        "Zamazenta": "Dauntless Shield",
    }[species]
    battle, holder, _ = native_battle(name=species, item=item, ability=ability)
    battle.on_enter_battle(holder)
    assert holder.species == expected
    if species == "Zacian":
        assert holder.boosts["attack"] == 1
    elif species == "Zamazenta":
        assert holder.boosts["defense"] == 1
    battle, other, _ = native_battle(item=item)
    battle.on_enter_battle(other)
    assert other.species == "Mew"


@pytest.mark.parametrize(
    "species,ability", [("Flutter Mane", "Protosynthesis"), ("Iron Bundle", "Quark Drive")]
)
def test_booster_energy_activates_real_native_highest_stat(species, ability):
    from pokemon.battle.stat_activation import HighestStatActivation

    battle, holder, _ = native_battle(name=species, item="Booster Energy", ability=ability)
    controller = HighestStatActivation(EffectContext.key(ability))
    state = controller.state(holder)
    assert state["active"] and state["from_booster"]
    assert holder.item is None
    assert controller.modify(100, holder, state["stat"]) == (150 if state["stat"] == "spe" else 130)


@pytest.mark.parametrize("suppressed", [False, True])
def test_binding_band_and_grip_claw_use_source_item_at_application(suppressed):
    for item in ["Binding Band", "Grip Claw"]:
        battle, holder, foe = native_battle(
            item=item, ability="Klutz" if suppressed else "No Guard"
        )
        attack(battle, holder, foe, "Bind")
        state = foe.volatiles["partiallytrapped"]
        assert state["turns"] == (7 if item == "Grip Claw" and not suppressed else 5)
        before = foe.hp
        battle.residual()
        assert before - foe.hp == foe.max_hp // (
            6 if item == "Binding Band" and not suppressed else 8
        )
        battle.on_switch_out(holder)
        battle.participant_for(holder).active = []
        battle.residual()
        assert "partiallytrapped" not in foe.volatiles


def test_ring_target_removes_type_immunity_only_while_effective():
    for suppressed in [False, True]:
        battle, holder, foe = native_battle(name="Gengar", item="Ring Target")
        holder.item_suppressed = suppressed
        damage, _ = attack(battle, foe, holder, "Tackle")
        assert (damage > 0) is not suppressed


def test_blunder_policy_needs_accuracy_miss_and_does_not_consume_on_immunity():
    battle, holder, foe = native_battle(item="Blunder Policy")
    battle.rng.seed(2)
    assert attack(battle, holder, foe, "Dynamic Punch")[0] == 0
    assert holder.boosts["speed"] == 2 and holder.item is None
    assert "confusion" not in foe.volatiles
    battle, holder, foe = native_battle(item="Blunder Policy", foe="Gengar")
    assert attack(battle, holder, foe, "Tackle")[0] == 0
    assert holder.item is not None and holder.boosts["speed"] == 0


def test_suppressed_gem_and_protected_target_do_not_consume():
    battle, holder, foe = native_battle(item="Normal Gem")
    attack(battle, foe, holder, "Protect")
    assert attack(battle, holder, foe, "Tackle")[0] == 0
    assert holder.item is not None

    foe.volatiles.clear()
    holder.item_suppressed = True
    attack(battle, holder, foe, "Tackle")
    assert holder.item is not None


@pytest.mark.parametrize("item", ["Eject Button", "Red Card", "Eject Pack"])
def test_switching_item_uses_native_replacement_queue(item):
    from pokemon.battle.battledata import Pokemon

    battle, holder, foe = native_battle(item=item)
    recipient = foe if item == "Red Card" else holder
    participant = battle.participant_for(recipient)
    reserve = Pokemon("Eevee", hp=100, max_hp=100)
    participant.pokemons.append(reserve)
    reserve.battle = battle
    attack(battle, foe, holder, "Growl" if item == "Eject Pack" else "Tackle")
    assert holder.item is None
    assert recipient.tempvals["switch_out"]
    battle.run_switch()
    assert participant.active == [reserve]


def test_shell_bell_aggregates_native_spread_damage_before_one_heal():
    from pokemon.battle.battledata import Pokemon

    battle, holder, foe = native_battle(item="Shell Bell", hp_fraction=0.5)
    ally = Pokemon("Wailord", hp=500, max_hp=500)
    extra = Pokemon("Wailord", hp=500, max_hp=500)
    for part, mon in [(battle.participant_for(holder), ally), (battle.participant_for(foe), extra)]:
        part.max_active = 2
        part.pokemons.append(mon)
        part.active.append(mon)
        mon.side, mon.battle = part.side, battle
    before = holder.hp
    _, move = attack(battle, holder, foe, "Surf")
    assert ally.hp < 500 and extra.hp < 500
    assert holder.hp == before + max(1, move.total_damage // 8)


def test_custap_priority_survives_berry_consumption_for_one_action():
    from pokemon.battle.actions import Action, ActionType
    from pokemon.battle.engine import BattleMove

    battle, holder, foe = native_battle(
        name="Snorlax", item="Custap Berry", foe="Squirtle", hp_fraction=0.2
    )
    assert holder.item is not None
    actions = [
        Action(
            battle.participant_for(mon),
            ActionType.MOVE,
            battle.participant_for(other),
            move=BattleMove(name="Tackle"),
            pokemon=mon,
        )
        for mon, other in [(holder, foe), (foe, holder)]
    ]
    ordered = battle.order_actions(actions)
    assert ordered[0].pokemon is holder
    assert holder.item is None and "custap" not in holder.volatiles


@pytest.mark.parametrize(
    "item,move,expected",
    [
        ("King's Rock", "Tackle", True),
        ("Razor Fang", "Tackle", True),
        ("King's Rock", "Splash", False),
    ],
)
def test_flinch_item_installs_secondary_on_eligible_native_move(item, move, expected):
    battle, holder, foe = native_battle(item=item)
    _, used = attack(battle, holder, foe, move)
    assert (
        any(s.get("volatileStatus") == "flinch" for s in getattr(used, "secondaries", []))
        is expected
    )


@pytest.mark.parametrize("suppressed", [False, True])
def test_umbrella_suppresses_only_holders_sun_rain_ability_weather(suppressed):
    battle, holder, foe = native_battle(item="Utility Umbrella", ability="Chlorophyll")
    holder.item_suppressed = suppressed
    battle.setWeather("sunnyday", source=foe)
    assert holder.effective_weather() == ("sunnyday" if suppressed else "")
    assert foe.effective_weather() == "sunnyday"
    assert battle.runEvent("ModifySpe", holder, None, None, 100) == (200 if suppressed else 100)
    battle.setWeather("sandstorm", source=foe)
    assert holder.effective_weather() == "sandstorm"


@pytest.mark.parametrize("move", ["Thunder", "Hurricane"])
def test_umbrella_target_removes_rain_accuracy_guarantee(move):
    battle, holder, foe = native_battle(item="Utility Umbrella")
    battle.setWeather("raindance", source=foe)
    _, used = attack(battle, foe, holder, move)
    assert used.accuracy == 70
    holder.item_suppressed = True
    _, used = attack(battle, foe, holder, move)
    assert used.accuracy is True


def test_power_herb_is_retained_when_sun_already_skips_solar_charge():
    battle, holder, foe = native_battle(item="Power Herb")
    battle.setWeather("sunnyday", source=holder)
    assert attack(battle, holder, foe, "Solar Beam")[0] > 0
    assert holder.item is not None


def test_enigma_cannot_revive_a_knocked_out_holder():
    battle, holder, foe = native_battle(item="Enigma Berry", hp_fraction=0.1)
    attack(battle, foe, holder, "Shadow Ball")
    assert holder.hp == 0 and holder.item is not None


@pytest.mark.parametrize(
    "item,species,signature",
    [("Rusted Sword", "Zacian", "Behemoth Blade"), ("Rusted Shield", "Zamazenta", "Behemoth Bash")],
)
def test_crowned_signature_spends_iron_head_pp_and_survives_checkpoint(item, species, signature):
    from types import SimpleNamespace
    from pokemon.battle.battledata import Pokemon

    battle, holder, foe = native_battle(name=species, item=item)
    holder.moves = [
        SimpleNamespace(name="Iron Head", pp=4, to_dict=lambda: {"name": "Iron Head", "pp": 4})
    ]
    battle.on_enter_battle(holder)
    _, used = attack(battle, holder, foe, "Iron Head")
    assert used.name == signature
    assert holder.moves[0].name == "Iron Head" and holder.moves[0].pp == 3
    rebuilt = Pokemon.from_dict(holder.to_dict())
    assert rebuilt.species == holder.species and rebuilt.types == holder.types
    assert rebuilt.base_stats.attack == holder.base_stats.attack


def test_metronome_checkpoint_preserves_count_and_removal_resets_next_use():
    from pokemon.battle.battledata import Pokemon

    battle, holder, foe = native_battle(item="Metronome")
    attack(battle, holder, foe, "Tackle")
    attack(battle, holder, foe, "Tackle")
    rebuilt = Pokemon.from_dict(holder.to_dict())
    assert rebuilt.volatiles["metronome"]["num_consecutive"] == 1
    battle.remove_item(holder)
    attack(battle, holder, foe, "Tackle")
    assert "metronome" not in holder.volatiles


@pytest.mark.parametrize("foe,qualifies", [("Wailord", True), ("Snorlax", False)])
def test_bitter_malice_guaranteed_secondary_requires_a_nonimmune_hit(foe, qualifies):
    battle, holder, target = native_battle(foe=foe)
    damage, _ = attack(battle, holder, target, "Bitter Malice")
    assert (damage > 0) is qualifies
    assert target.boosts["attack"] == (-1 if qualifies else 0)


@pytest.mark.parametrize(
    "species,ability,field",
    [
        ("Iron Bundle", "Quark Drive", "electricterrain"),
        ("Flutter Mane", "Protosynthesis", "sunnyday"),
    ],
)
@pytest.mark.parametrize("booster", [False, True])
def test_field_expiration_ends_native_boost_or_consumes_waiting_booster(
    species, ability, field, booster
):
    from pokemon.battle.stat_activation import HighestStatActivation

    battle, holder, foe = native_battle(name=species, ability=ability)
    battle.on_enter_battle(holder)
    setter = battle.setTerrain if field == "electricterrain" else battle.setWeather
    setter(field, source=foe)
    controller = HighestStatActivation(EffectContext.key(ability))
    if booster:
        battle.set_item(holder, battle._coerce_item("Booster Energy"))
        assert holder.item is not None
    for _ in range(4):
        battle.residual()
        assert controller.state(holder)["active"]
    battle.residual()
    assert not battle.field.terrain and not battle.field.weather
    state = controller.state(holder)
    assert bool(state.get("active")) is booster
    if booster:
        assert state["from_booster"] and holder.item is None


def test_adrenaline_orb_uses_real_intimidate_entry_context():
    battle, holder, foe = native_battle(item="Adrenaline Orb")
    foe.ability = "Intimidate"
    battle.on_enter_battle(holder)
    battle.on_enter_battle(foe)
    assert holder.boosts["attack"] == -1
    assert holder.boosts["speed"] == 1 and holder.item is None


def test_adrenaline_orb_does_not_activate_from_an_ordinary_stat_drop():
    battle, holder, foe = native_battle(item="Adrenaline Orb")
    attack(battle, foe, holder, "Growl")
    assert holder.boosts["attack"] == -1
    assert holder.boosts["speed"] == 0 and holder.item is not None


def test_intimidate_context_retains_inner_focus_immunity():
    battle, holder, foe = native_battle(ability="Inner Focus")
    foe.ability = "Intimidate"
    battle.on_enter_battle(holder)
    battle.on_enter_battle(foe)
    assert holder.boosts["attack"] == 0


def test_destiny_knot_reflects_native_opposite_gender_attract_once():
    battle, holder, foe = native_battle(name="Eevee", item="Destiny Knot", foe="Slowpoke")
    holder.gender, foe.gender = "F", "M"
    attack(battle, foe, holder, "Attract")
    assert "attract" in holder.volatiles and "attract" in foe.volatiles
    assert holder.item is not None
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("weather,move", [("raindance", "Water Gun"), ("sunnyday", "Ember")])
def test_umbrella_reduces_incoming_weather_boost_only_while_effective(weather, move):
    amounts = []
    for held, suppressed in [("", False), ("Utility Umbrella", False), ("Utility Umbrella", True)]:
        battle, holder, foe = native_battle(item=held)
        holder.item_suppressed = suppressed
        battle.setWeather(weather, source=foe)
        amounts.append(attack(battle, foe, holder, move)[0])
    assert 0 < amounts[1] < amounts[0] == amounts[2]
