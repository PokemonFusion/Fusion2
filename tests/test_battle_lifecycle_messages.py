"""Regression tests for human-readable battle lifecycle messages."""

from __future__ import annotations

import types

from pokemon.battle.battledata import Pokemon
from pokemon.battle.engine import (
        Action,
        ActionType,
        Battle,
        BattleMove,
        BattleParticipant,
        BattleType,
)
from pokemon.data.text import DEFAULT_TEXT


def _replace_trainer(template: str, first: str, second: str | None = None) -> str:
        """Replace sequential ``[TRAINER]`` placeholders in ``template``."""

        result = template.replace("[TRAINER]", first, 1)
        if "[TRAINER]" in result:
                result = result.replace("[TRAINER]", second or first, 1)
        return result


def test_start_battle_logs_opening_and_switch_messages() -> None:
        pikachu = Pokemon("Pikachu", level=5)
        eevee = Pokemon("Eevee", level=5)
        p1 = BattleParticipant("Ash", [pikachu], is_ai=False)
        p2 = BattleParticipant("Gary", [eevee], is_ai=False)
        battle = Battle(BattleType.TRAINER, [p1, p2])
        logs: list[str] = []
        battle.log_action = logs.append

        battle.start_battle()

        start_msg = _replace_trainer(DEFAULT_TEXT["default"]["startBattle"], "Ash", "Gary")
        assert start_msg in logs

        switch_msg_ash = (
                DEFAULT_TEXT["default"]["switchIn"].replace("[TRAINER]", "Ash").replace("[FULLNAME]", "Pikachu")
        )
        switch_msg_gary = (
                DEFAULT_TEXT["default"]["switchIn"].replace("[TRAINER]", "Gary").replace("[FULLNAME]", "Eevee")
        )
        assert switch_msg_ash in logs
        assert switch_msg_gary in logs


def test_switch_pokemon_logs_out_and_in_messages() -> None:
        alpha = Pokemon("Alpha", level=5)
        beta = Pokemon("Beta", level=5)
        opponent = Pokemon("Gamma", level=5)
        participant = BattleParticipant("Trainer", [alpha, beta], is_ai=False)
        foe = BattleParticipant("Opponent", [opponent], is_ai=False)
        battle = Battle(BattleType.TRAINER, [participant, foe])
        logs: list[str] = []
        battle.log_action = logs.append

        battle.start_battle()
        logs.clear()

        battle.switch_pokemon(participant, beta)

        out_msg = (
                DEFAULT_TEXT["default"]["switchOut"].replace("[TRAINER]", "Trainer").replace("[NICKNAME]", "Alpha")
        )
        in_msg = (
                DEFAULT_TEXT["default"]["switchIn"].replace("[TRAINER]", "Trainer").replace("[FULLNAME]", "Beta")
        )
        assert out_msg in logs
        assert in_msg in logs


def test_move_logging_includes_move_ability_and_item_templates() -> None:
        user = Pokemon("User", level=5)
        target = Pokemon("Target", level=5)
        noop = lambda *_, **__: None  # noqa: E731 - simple stub callback
        user.ability = types.SimpleNamespace(name="Overgrow", call=noop, raw={})
        user.item = types.SimpleNamespace(name="Oran Berry", call=noop, raw={})
        part1 = BattleParticipant("P1", [user], is_ai=False)
        part2 = BattleParticipant("P2", [target], is_ai=False)
        part1.active = [user]
        part2.active = [target]
        battle = Battle(BattleType.WILD, [part1, part2])
        logs: list[str] = []
        battle.log_action = logs.append

        move = BattleMove("Tackle", power=40, accuracy=True, raw={"category": "Physical", "target": "normal"})
        action = Action(part1, ActionType.MOVE, part2, move, priority=0, pokemon=user)

        battle.use_move(action)

        move_msg = (
                DEFAULT_TEXT["default"]["move"].replace("[POKEMON]", "User").replace("[MOVE]", "Tackle")
        )
        ability_msg = (
                DEFAULT_TEXT["default"]["abilityActivation"].replace("[POKEMON]", "User").replace("[ABILITY]", "Overgrow")
        )
        item_msg = (
                DEFAULT_TEXT["default"]["activateItem"].replace("[POKEMON]", "User").replace("[ITEM]", "Oran Berry")
        )
        assert move_msg in logs
        assert ability_msg in logs
        assert item_msg in logs


def test_check_win_conditions_logs_victory_message() -> None:
        winner_pokemon = Pokemon("Hero", level=5)
        loser_pokemon = Pokemon("Villain", level=5)
        winner = BattleParticipant("Champion", [winner_pokemon], is_ai=False)
        loser = BattleParticipant("Rival", [loser_pokemon], is_ai=False)
        battle = Battle(BattleType.TRAINER, [winner, loser])
        logs: list[str] = []
        battle.log_action = logs.append

        loser.has_lost = True

        result = battle.check_win_conditions()

        win_msg = DEFAULT_TEXT["default"]["winBattle"].replace("[TRAINER]", "Champion")
        assert result is winner
        assert win_msg in logs
