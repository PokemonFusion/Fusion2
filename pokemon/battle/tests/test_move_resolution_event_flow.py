"""Tests for move-resolution events in use_move/apply_damage."""

from __future__ import annotations

from .helpers import build_battle, load_modules, physical_move


class _RedirectAbility:
    def __init__(self):
        self.redirect_to = None

    def call(self, func: str, *args, **kwargs):
        if func == "onAnyRedirectTarget":
            return self.redirect_to
        return None


def _add_follow_me_volatile(pokemon):
    pokemon.volatiles["followme"] = {"id": "followme"}


class _InvulnerableAbility:
    def call(self, func: str, *args, **kwargs):
        if func == "onInvulnerability":
            return True
        return None


class _SourceReduceDamageAbility:
    def call(self, func: str, *args, **kwargs):
        if func == "onSourceModifyDamage":
            return max(1, int(args[0] / 2))
        return None


def _battle_action(actor, action_type, **kwargs):
    modules = load_modules()
    Action = __import__("pokemon.battle.actions", fromlist=["Action"]).Action
    return Action(actor=actor, action_type=action_type, **kwargs)


def test_redirect_target_event_changes_damage_recipient():
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    battle, attacker, defender = build_battle()
    redirector = modules["Pokemon"]("Redirector", hp=200, max_hp=200)
    redirector.base_stats = attacker.base_stats
    redirector.types = ["Normal"]
    redirector.boosts = dict(attacker.boosts)
    redirector.tempvals = {}
    redirector.volatiles = {}
    redirect_ability = _RedirectAbility()
    redirect_ability.redirect_to = redirector
    redirector.ability = redirect_ability
    redirector.side = battle.participants[1].side
    redirector.battle = battle
    battle.participants[1].pokemons.append(redirector)
    battle.participants[1].active.append(redirector)

    move = BattleMove(
        name="Tackle",
        power=50,
        accuracy=100,
        type="Normal",
        raw={"category": "Physical", "basePower": 50, "accuracy": 100},
    )
    move.key = "tackle"
    action = _battle_action(
        battle.participants[0],
        ActionType.MOVE,
        target=battle.participants[1],
        move=move,
        pokemon=attacker,
    )
    start_defender_hp = defender.hp
    start_redirector_hp = redirector.hp

    battle.use_move(action)

    assert defender.hp == start_defender_hp
    assert redirector.hp < start_redirector_hp


def test_foe_redirect_target_volatile_redirects_to_partner():
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    battle, attacker, defender = build_battle()
    redirector = modules["Pokemon"]("Redirector", hp=200, max_hp=200)
    redirector.base_stats = attacker.base_stats
    redirector.types = ["Normal"]
    redirector.boosts = dict(attacker.boosts)
    redirector.tempvals = {}
    redirector.volatiles = {}
    _add_follow_me_volatile(redirector)
    redirector.side = battle.participants[1].side
    redirector.battle = battle
    battle.participants[1].pokemons.append(redirector)
    battle.participants[1].active.append(redirector)

    move = BattleMove(
        name="Tackle",
        power=50,
        accuracy=100,
        type="Normal",
        raw={"category": "Physical", "basePower": 50, "accuracy": 100},
    )
    move.key = "tackle"
    action = _battle_action(
        battle.participants[0],
        ActionType.MOVE,
        target=battle.participants[1],
        move=move,
        pokemon=attacker,
    )
    start_defender_hp = defender.hp
    start_redirector_hp = redirector.hp

    battle.use_move(action)

    assert defender.hp == start_defender_hp
    assert redirector.hp < start_redirector_hp


def test_invulnerability_event_blocks_move_execution():
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    battle, attacker, defender = build_battle(defender_ability=_InvulnerableAbility())
    move = BattleMove(
        name="Tackle",
        power=50,
        accuracy=100,
        type="Normal",
        raw={"category": "Physical", "basePower": 50, "accuracy": 100},
    )
    move.key = "tackle"
    action = _battle_action(
        battle.participants[0],
        ActionType.MOVE,
        target=battle.participants[1],
        move=move,
        pokemon=attacker,
    )
    start_hp = defender.hp

    battle.use_move(action)

    assert defender.hp == start_hp


def test_modify_damage_event_runs_source_damage_modifier():
    modules = load_modules()
    damage_mod = __import__("pokemon.battle.damage", fromlist=["apply_damage"])
    battle, attacker, defender = build_battle(attacker_ability=_SourceReduceDamageAbility())
    move = physical_move(name="Tackle", power=70)

    baseline_battle, baseline_attacker, baseline_defender = build_battle()
    baseline_move = physical_move(name="Tackle", power=70)
    baseline = damage_mod.apply_damage(
        baseline_attacker,
        baseline_defender,
        baseline_move,
        battle=baseline_battle,
        update_hp=False,
    )
    modified = damage_mod.apply_damage(
        attacker,
        defender,
        move,
        battle=battle,
        update_hp=False,
    )

    assert sum(modified.debug["damage"]) < sum(baseline.debug["damage"])
