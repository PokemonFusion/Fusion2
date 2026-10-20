"""Native battle regressions for the issue-linked item effect failures."""

import random
from types import SimpleNamespace

import pytest

from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats

from .helpers import battle_move, load_modules


def native_battle(name="Mew", item="", foe="Wailord", *, hp_fraction=1, ability="No Ability"):
    """Construct native species/stats and real dex items without invented flags."""
    modules = load_modules()
    from pokemon.dex import ITEMDEX, POKEDEX
    from pokemon.battle.effect_context import EffectContext
    from pokemon.names import resolve_dex_entry

    mons = []
    for species, level in ((name, 50), (foe, 100)):
        data = SimpleNamespace(
            species=species, level=level, ivs=[0] * 6, evs=[0] * 6, nature="Hardy"
        )
        stats = get_stats(data)
        mon = modules["Pokemon"](species, level=level, hp=get_max_hp(data), max_hp=get_max_hp(data))
        mon.base_stats = modules["Stats"](**stats)
        mon.stats = {
            "hp": stats["hp"],
            **{
                short: stats[long]
                for short, long in (
                    ("atk", "attack"),
                    ("def", "defense"),
                    ("spa", "special_attack"),
                    ("spd", "special_defense"),
                    ("spe", "speed"),
                )
            },
        }
        entry = resolve_dex_entry(POKEDEX, species)
        mon.types = list(entry.raw["types"])
        mon.ability = ability if not mons else "No Ability"
        mons.append(mon)
    parts = [modules["BattleParticipant"]("P" + str(i), [mon]) for i, mon in enumerate(mons)]
    for part, mon in zip(parts, mons):
        part.active = [mon]
    battle = modules["Battle"](modules["BattleType"].WILD, parts)
    battle.rng = random.Random(4)
    for mon in mons:
        mon.battle = battle
    mons[0].hp = max(1, int(mons[0].max_hp * hp_fraction))
    if item:
        battle.set_item(mons[0], resolve_dex_entry(ITEMDEX, item))
    return battle, *mons


def attack(battle, source, target, name):
    """Route genuine move data through prevention, damage and item events."""
    from pokemon.battle.actions import Action, ActionType

    action = Action(
        battle.participant_for(source),
        ActionType.MOVE,
        battle.participant_for(target),
        move=load_modules()["BattleMove"](name=name),
        pokemon=source,
    )
    old = target.hp
    battle.use_move(action)
    return old - target.hp, action.move


def test_shell_bell_heals_actual_damage_once_and_status_does_not_reuse_it():
    battle, holder, foe = native_battle(item="Shell Bell", hp_fraction=0.5)
    before = holder.hp
    damage, _ = attack(battle, holder, foe, "Tackle")
    assert damage > 0
    assert holder.hp == min(holder.max_hp, before + max(1, damage // 8))
    current = holder.hp
    attack(battle, holder, foe, "Splash")
    assert holder.hp == current
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize(
    "species,eligible",
    [("Bulbasaur", True), ("Ivysaur", True), ("Venusaur", False), ("Mew", False)],
)
def test_eviolite_uses_native_evolution_data(species, eligible):
    from pokemon.battle.item_effects import HeldItemRules

    battle, holder, foe = native_battle(species, "Eviolite")
    assert HeldItemRules.can_evolve(holder) is eligible
    base = holder.stats["def"]
    assert battle.runEvent("ModifyDef", holder, None, None, base) == (
        int(base * 1.5) if eligible else base
    )


GEM_MOVES = {
    "Normal": "Tackle",
    "Fire": "Ember",
    "Water": "Water Gun",
    "Electric": "Thunder Shock",
    "Grass": "Vine Whip",
    "Ice": "Ice Beam",
    "Fighting": "Karate Chop",
    "Poison": "Acid",
    "Ground": "Mud-Slap",
    "Flying": "Gust",
    "Psychic": "Confusion",
    "Bug": "Struggle Bug",
    "Rock": "Rock Throw",
    "Ghost": "Lick",
    "Dragon": "Dragon Breath",
    "Dark": "Snarl",
    "Steel": "Bullet Punch",
    "Fairy": "Dazzling Gleam",
}


@pytest.mark.parametrize("move_type", GEM_MOVES)
def test_each_gem_boosts_one_matching_attack_without_stat_stages(move_type):
    name = GEM_MOVES[move_type]
    control, plain, target = native_battle(ability="No Guard")
    baseline, _ = attack(control, plain, target, name)
    battle, holder, foe = native_battle(item=move_type + " Gem", ability="No Guard")
    damage, _ = attack(battle, holder, foe, name)
    assert damage > baseline
    assert holder.item is None
    assert all(not stage for stage in holder.boosts.values())
    battle.rng = random.Random(4)
    second, _ = attack(battle, holder, foe, name)
    assert second == baseline


@pytest.mark.parametrize("move", ["Splash", "Water Gun"])
def test_normal_gem_does_not_trigger_for_status_or_nonmatching_move(move):
    battle, holder, foe = native_battle(item="Normal Gem", ability="No Guard")
    attack(battle, holder, foe, move)
    assert holder.item is not None
    assert all(not stage for stage in holder.boosts.values())


def test_chilan_handles_neutral_normal_and_respects_unnerve():
    plain, unheld, attacker = native_battle()
    baseline, _ = attack(plain, attacker, unheld, "Tackle")
    battle, holder, attacker = native_battle(item="Chilan Berry")
    damage, _ = attack(battle, attacker, holder, "Tackle")
    assert damage == baseline // 2
    assert holder.item is None
    battle, holder, attacker = native_battle(item="Chilan Berry")
    attacker.ability = "Unnerve"
    damage, _ = attack(battle, attacker, holder, "Tackle")
    assert damage == baseline
    assert holder.item is not None


def test_leppa_uses_authoritative_depleted_slot_and_updates_runtime_cache():
    from pokemon.battle.item_effects import HeldItemRules

    saved = []
    slot = SimpleNamespace(
        move=SimpleNamespace(name="Tackle"),
        current_pp=0,
        max_pp=56,
        save=lambda **kw: saved.append(kw),
    )
    move = SimpleNamespace(name="Tackle", pp=None)
    battle, holder, _ = native_battle()
    holder.activemoveslot_set = SimpleNamespace(all=lambda: [slot])
    holder.moves = [move]
    assert HeldItemRules.berry_pp(holder)
    assert HeldItemRules.berry_pp(holder, restore=True) == 10
    assert slot.current_pp == move.pp == 10
    assert saved == [{"update_fields": ["current_pp"]}]
    assert not HeldItemRules.berry_pp(holder)


def test_pads_prevent_helmet_contact_damage():
    from pokemon.dex import ITEMDEX
    from pokemon.names import resolve_dex_entry

    battle, holder, foe = native_battle(item="Protective Pads")
    battle.set_item(foe, resolve_dex_entry(ITEMDEX, "Rocky Helmet"))
    before = holder.hp
    damage, _ = attack(battle, holder, foe, "Tackle")
    assert damage > 0 and holder.hp == before


def test_suppressed_pads_do_not_prevent_helmet_damage():
    from pokemon.dex import ITEMDEX
    from pokemon.names import resolve_dex_entry

    battle, holder, foe = native_battle(item="Protective Pads", ability="Klutz")
    battle.set_item(foe, resolve_dex_entry(ITEMDEX, "Rocky Helmet"))
    before = holder.hp
    damage, _ = attack(battle, holder, foe, "Tackle")
    assert damage > 0 and holder.hp == before - holder.max_hp // 6


@pytest.mark.parametrize("blocked", [False, True])
def test_lum_confusion_cure_respects_eating_gates(blocked):
    battle, holder, foe = native_battle(item="Lum Berry")
    if blocked:
        foe.ability = "Unnerve"
    battle.apply_volatile_status(holder, "confusion", source=foe, effect="Confuse Ray")
    battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
    assert ("confusion" in holder.volatiles) is blocked
    assert (holder.item is not None) is blocked


@pytest.mark.parametrize(
    "item,nature",
    [
        ("Figy Berry", "Modest"),
        ("Wiki Berry", "Adamant"),
        ("Mago Berry", "Brave"),
        ("Aguav Berry", "Naughty"),
        ("Iapapa Berry", "Lonely"),
    ],
)
@pytest.mark.parametrize("own_tempo", [False, True])
def test_flavor_berries_respect_nature_and_confusion_immunity(item, nature, own_tempo):
    battle, holder, foe = native_battle(
        item=item, hp_fraction=0.2, ability="Own Tempo" if own_tempo else "No Ability"
    )
    holder.nature = nature
    before = holder.hp
    battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
    assert holder.hp == min(holder.max_hp, before + holder.max_hp // 3)
    assert holder.item is None
    assert ("confusion" in holder.volatiles) is (not own_tempo)


@pytest.mark.parametrize("suppressed", [False, True])
def test_boots_block_native_hazard_switch_unless_suppressed(suppressed):
    from pokemon.dex import ITEMDEX
    from pokemon.names import resolve_dex_entry

    battle, holder, foe = native_battle()
    other, incoming, _ = native_battle("Charizard", ability="Klutz" if suppressed else "No Ability")
    incoming.battle = battle
    part = battle.participant_for(holder)
    part.pokemons.append(incoming)
    battle.set_item(incoming, resolve_dex_entry(ITEMDEX, "Heavy-Duty Boots"))
    attack(battle, foe, holder, "Stealth Rock")
    before = incoming.hp
    battle.perform_switch_action(part, incoming, slot=0)
    assert incoming.hp == (before - incoming.max_hp // 2 if suppressed else before)


def test_micle_threshold_consumption_and_accuracy_volatile():
    from pokemon.battle.accuracy import MoveAccuracy

    battle, holder, foe = native_battle(item="Micle Berry", hp_fraction=0.2)
    battle.residual()
    assert holder.item is None
    assert "micleberry" in holder.volatiles
    move = load_modules()["BattleMove"](name="Thunder")
    assert MoveAccuracy.modified(holder, foe, move, battle, base=70) == 84
    assert "micleberry" not in holder.volatiles


def test_consumed_held_item_is_synced_to_owned_model(monkeypatch):
    import pokemon.battle.battleinstance as sessions
    import uuid

    ident = uuid.uuid4()
    saved = []
    mon = SimpleNamespace(
        unique_id=ident,
        current_hp=30,
        held_item="Oran Berry",
        status="",
        sleep_turns=0,
        get_max_hp=lambda: 100,
        save=lambda **kw: saved.append(kw),
    )
    player = SimpleNamespace(storage=object())
    runtime = SimpleNamespace(model_id="owned:" + str(ident), hp=40, status=0, item=None)
    session = SimpleNamespace(
        battle=SimpleNamespace(participants=[SimpleNamespace(player=player, pokemons=[runtime])])
    )
    monkeypatch.setattr(sessions, "get_battle_party_with_fusion", lambda p: [mon])
    sessions.BattleSession._sync_player_pokemon_state(session, strict=True)
    assert mon.held_item == "" and mon.current_hp == 40
    assert "held_item" in saved[-1]["update_fields"]


def test_shell_bell_uses_actual_overkill_damage():
    battle, holder, foe = native_battle(item="Shell Bell", hp_fraction=0.5)
    foe.hp = 1
    before = holder.hp
    damage, _ = attack(battle, holder, foe, "Tackle")
    assert damage == 1 and holder.hp == before + 1


def test_consumed_update_handler_cannot_eat_a_replacement_item():
    from pokemon.dex import ITEMDEX
    from pokemon.names import resolve_dex_entry

    battle, holder, _ = native_battle(item="Oran Berry", hp_fraction=0.2)
    battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
    assert holder.item is None
    battle.set_item(holder, resolve_dex_entry(ITEMDEX, "Life Orb"))
    holder.hp = holder.max_hp // 5
    battle.register_handlers(holder)
    battle.register_handlers(holder)
    battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
    assert holder.item is not None and holder.item.raw["name"] == "Life Orb"


def test_magic_room_suppresses_registered_berry_update_handler():
    battle, holder, foe = native_battle(item="Oran Berry", hp_fraction=0.2)
    before = holder.hp
    attack(battle, foe, holder, "Magic Room")
    battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
    assert holder.hp == before and holder.item is not None


def test_lum_cures_confuse_ray_before_the_next_action():
    battle, holder, foe = native_battle(item="Lum Berry")
    foe.ability = "No Guard"
    attack(battle, foe, holder, "Confuse Ray")
    assert "confusion" not in holder.volatiles
    assert holder.item is None
