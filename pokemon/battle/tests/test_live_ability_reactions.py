"""Actual hit, entry, and ally event regressions reproduced in local logins."""
import random

import pytest

from .helpers import build_battle, load_modules, make_stats
from .test_live_checkpoint_effect_consumers import quiet_log, stage
from .test_pending_action_effects import action


def ally(battle, name="Ally", ability="No Ability", hp=200):
    """Attach an independent live ally to the actual participant roster."""
    pokemon = load_modules()["Pokemon"](name, level=50, hp=hp, max_hp=200, ability=ability)
    pokemon.base_stats = make_stats()
    part = battle.participants[0]
    part.pokemons.append(pokemon)
    part.active.append(pokemon)
    pokemon.battle, pokemon.side = battle, part.side
    pokemon.ability_state = battle.init_effect_state(pokemon.ability, target=pokemon)
    return pokemon


@pytest.mark.parametrize("hp", [200, 100])
def test_tera_shell_reduces_full_hp_damage_without_making_neutral_hits_immune(hp):
    losses = []
    for ability in ("No Ability", "Tera Shell"):
        battle, user, target = build_battle(defender_ability=ability)
        target.species = target.base_species = "Terapagos-Terastal"
        target.hp = hp
        battle.rng = random.Random(1)
        battle.use_move(action(battle, user, target, "Water Gun"))
        losses.append(hp - target.hp)
    assert losses[0] > 0
    assert (0 < losses[1] < losses[0]) if hp == 200 else losses[1] == losses[0]


def test_mycelium_might_status_move_ignores_limber_but_not_innate_typing():
    battle, user, target = build_battle(attacker_ability="Mycelium Might", defender_ability="Limber")
    # Seed the real 90% accuracy roll; this test isolates ability/type immunity.
    battle.rng = random.Random(1)
    battle.use_move(action(battle, user, target, "Thunder Wave"))
    assert target.status == "par"
    battle, user, target = build_battle(attacker_ability="Mycelium Might", defender_ability="Limber", defender_types=["Electric"])
    battle.rng = random.Random(1)
    battle.use_move(action(battle, user, target, "Thunder Wave"))
    assert target.status != "par"


def test_rebound_reflects_an_eligible_status_only_during_its_entry_turn():
    battle, user, source = build_battle(attacker_ability="Rebound")
    battle.start_turn()
    battle.use_move(action(battle, source, user, "Growl"))
    assert stage(user, "atk", "attack") == 0 and stage(source, "atk", "attack") == -1
    battle.start_turn()
    battle.use_move(action(battle, source, user, "Growl"))
    assert stage(user, "atk", "attack") == -1


@pytest.mark.parametrize("ability", ["Plus", "Minus"])
def test_electric_pair_ability_uses_real_named_active_ally(ability):
    losses = []
    for own in ("No Ability", ability):
        battle, user, target = build_battle(attacker_ability=own)
        ally(battle, ability="Minus")
        battle.rng = random.Random(1)
        battle.use_move(action(battle, user, target, "Water Gun"))
        losses.append(target.max_hp - target.hp)
    assert losses[1] > losses[0] > 0


@pytest.mark.parametrize("ability", ["Receiver", "Power of Alchemy"])
def test_copy_ability_uses_a_real_fainted_ally_and_starts_the_new_effect(ability):
    battle, user, foe = build_battle(attacker_ability=ability)
    friend = ally(battle, ability="Water Absorb", hp=1)
    battle.rng = random.Random(1)
    battle.use_move(action(battle, foe, friend, "Tackle"))
    assert friend.hp == 0
    battle.run_faint()
    assert user.hasAbility("Water Absorb")


@pytest.mark.parametrize("hp,trigger", [(101, True), (50, False), (200, False)])
@pytest.mark.parametrize("ability", ["Emergency Exit", "Wimp Out"])
def test_exit_ability_requires_an_actual_surviving_half_hp_crossing(ability, hp, trigger):
    battle, user, source = build_battle(attacker_ability=ability)
    reserve = load_modules()["Pokemon"]("Reserve", hp=200, max_hp=200)
    battle.participants[0].pokemons.append(reserve)
    user.hp = hp
    battle.rng = random.Random(1)
    battle.use_move(action(battle, source, user, "Tackle"))
    assert bool(user.tempvals.get("switch_out")) is trigger


def test_moody_samples_two_distinct_combat_stats_without_accuracy_or_evasion(monkeypatch):
    from pokemon.dex.functions import abilities_funcs
    battle, user, _ = build_battle(attacker_ability="Moody")
    allowed = {"atk", "def", "spa", "spd", "spe"}
    def first(options):
        assert set(options) <= allowed
        return options[0]
    monkeypatch.setattr(abilities_funcs, "choice", first)
    abilities_funcs.Moody().onResidual(user)
    assert stage(user, "atk", "attack") == 2 and stage(user, "def", "defense") == -1


@pytest.mark.parametrize("ability,signal,expected", [("Anticipation", "anticipated", True),
                                                      ("Forewarn", "forewarn", "Hyper Beam"), ("Frisk", "frisked", "Leftovers")])
def test_entry_information_resolves_minimal_moves_and_reaches_the_player(ability, signal, expected):
    battle, user, foe = build_battle(attacker_ability=ability, attacker_types=["Water", "Ground"])
    foe.moves = [load_modules()["Move"](name) for name in ("Splash", "Energy Ball", "Hyper Beam")]
    foe.item = battle._coerce_item("Leftovers")
    messages = []
    battle.log_action = messages.append
    battle.start_turn()
    value = getattr(user, signal, None)
    if signal == "frisked":
        assert expected in [getattr(item, "name", item) for item in value or []]
    else:
        assert value == expected
    word = "shudder" if signal == "anticipated" else ability.lower()
    assert any(word in message.lower() for message in messages)


def test_battle_bond_native_greninja_boosts_once_after_its_actual_knockout():
    battle, user, foe = build_battle(attacker_ability="Battle Bond")
    user.species = user.base_species = "Greninja"
    battle.participants[1].pokemons.append(load_modules()["Pokemon"]("Reserve", hp=200, max_hp=200))
    foe.hp = 1
    battle.rng = random.Random(1)
    battle.use_move(action(battle, user, foe, "Water Gun"))
    battle.run_faint()
    assert all(stage(user, short, long) == 1 for short, long in (("atk", "attack"), ("spa", "special_attack"), ("spe", "speed")))


@pytest.mark.parametrize("move,hits", [("Tackle", True), ("Water Gun", False)])
def test_unseen_fist_only_bypasses_protect_for_contact_moves(move, hits):
    battle, user, target = build_battle(attacker_ability="Unseen Fist")
    battle.use_move(action(battle, target, target, "Protect"))
    battle.rng = random.Random(1)
    battle.use_move(action(battle, user, target, move))
    assert (target.hp < target.max_hp) is hits
    assert "protect" in target.volatiles


@pytest.mark.parametrize("ability,bypasses", [("No Ability", False), ("Propeller Tail", True), ("Stalwart", True)])
def test_target_tracking_ability_is_prepared_before_follow_me_redirects(ability, bypasses):
    battle, user, target = build_battle(attacker_ability=ability)
    redirector = load_modules()["Pokemon"]("Clefairy", level=50, hp=200, max_hp=200)
    redirector.base_stats = make_stats()
    part = battle.participants[1]
    part.pokemons.append(redirector)
    part.active.append(redirector)
    redirector.battle, redirector.side = battle, part.side
    battle.use_move(action(battle, redirector, redirector, "Follow Me"))
    battle.rng = random.Random(1)
    battle.use_move(action(battle, user, target, "Water Gun"))
    assert (target.hp < target.max_hp) is bypasses
    assert (redirector.hp < redirector.max_hp) is not bypasses


def test_mold_breaker_does_not_suppress_rough_skin_contact_retaliation():
    battle, user, target = build_battle(attacker_ability="Mold Breaker", defender_ability="Rough Skin")
    battle.rng = random.Random(1)
    battle.use_move(action(battle, user, target, "Tackle"))
    assert user.hp < user.max_hp and target.hp < target.max_hp


def test_cursed_body_uses_the_actual_hit_move_and_canonical_disable_state(monkeypatch):
    from pokemon.dex.functions import abilities_funcs
    battle, user, target = build_battle(defender_ability="Cursed Body")
    monkeypatch.setattr(abilities_funcs, "random", lambda: 0)
    battle.rng = random.Random(1)
    battle.use_move(action(battle, user, target, "Tackle"))
    assert "disable" in user.volatiles
    assert battle._is_move_disabled(user, action(battle, user, target, "Tackle").move)
    assert not battle._is_move_disabled(user, action(battle, user, target, "Water Gun").move)


def test_serene_grace_doubles_raw_single_secondary_without_editing_the_shared_dex():
    import copy
    from pokemon import dex
    from pokemon.names import resolve_dex_entry
    baseline = copy.deepcopy(resolve_dex_entry(dex.MOVEDEX, "Charge Beam").raw)
    qualified = False
    for seed in range(8):
        observed = []
        for ability in ("No Ability", "Serene Grace"):
            battle, user, target = build_battle(attacker_ability=ability)
            battle.rng = random.Random(seed)
            battle.use_move(action(battle, user, target, "Charge Beam"))
            observed.append((target.hp < target.max_hp, stage(user, "spa", "special_attack")))
        qualified |= observed == [(True, 0), (True, 1)]
    assert qualified, "A matched qualifying hit must expose the changed 70-to-100 percent secondary."
    assert resolve_dex_entry(dex.MOVEDEX, "Charge Beam").raw == baseline
