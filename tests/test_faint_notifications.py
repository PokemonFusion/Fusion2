import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from pokemon.battle.battledata import Pokemon
from pokemon.battle.engine import Battle, BattleType
from pokemon.battle.participants import BattleParticipant
from pokemon.data.text import DEFAULT_TEXT


class RecordingBattle(Battle):
        """Battle subclass capturing log output for assertions."""

        def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.logged = []

        def log_action(self, message: str) -> None:
                self.logged.append(message)


def test_run_faint_announces_faint_message():
        fainted = Pokemon("Target", level=50, hp=0, max_hp=100)
        survivor = Pokemon("Ally", level=50, hp=100, max_hp=100)

        participants = [
                BattleParticipant("Player", [survivor]),
                BattleParticipant("Opponent", [fainted]),
        ]

        battle = RecordingBattle(BattleType.TRAINER, participants)

        for part in battle.participants:
                if part.pokemons:
                        part.active.append(part.pokemons[0])

        battle.run_faint()

        expected = DEFAULT_TEXT["default"]["faint"].replace("[POKEMON]", fainted.name)
        assert expected in battle.logged
