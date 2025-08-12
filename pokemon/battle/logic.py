from __future__ import annotations

"""Simple container tying together battle engine objects and persistent state."""

from .battledata import BattleData
from .engine import Battle, BattleParticipant, BattleType
from .state import BattleState


class BattleLogic:
    """Live battle logic stored only in ``ndb``."""

    def __init__(self, battle, data, state):
        self.battle = battle
        self.data = data
        self.state = state
        battle.debug = getattr(state, "debug", False)

    def to_dict(self):
        return {
            "data": self.data.to_dict(),
            "state": self.state.to_dict(),
        }

    @classmethod
    def from_dict(cls, info):
        data = BattleData.from_dict(info.get("data", {}))
        state = BattleState.from_dict(info.get("state", {}))

        teamA = data.teams.get("A")
        teamB = data.teams.get("B")
        try:
            part_a = BattleParticipant(
                teamA.trainer,
                [p for p in teamA.returnlist() if p],
                is_ai=False,
                team="A",
            )
        except TypeError:
            part_a = BattleParticipant(
                teamA.trainer,
                [p for p in teamA.returnlist() if p],
                is_ai=False,
            )
        try:
            part_b = BattleParticipant(
                teamB.trainer,
                [p for p in teamB.returnlist() if p],
                team="B",
            )
        except TypeError:
            part_b = BattleParticipant(
                teamB.trainer,
                [p for p in teamB.returnlist() if p],
            )
        part_b.is_ai = state.ai_type != "Player"
        pos_a = data.turndata.teamPositions("A").get("A1")
        if pos_a and pos_a.pokemon:
            part_a.active = [pos_a.pokemon]
        pos_b = data.turndata.teamPositions("B").get("B1")
        if pos_b and pos_b.pokemon:
            part_b.active = [pos_b.pokemon]
        try:
            btype = BattleType[state.ai_type.upper()]
        except KeyError:
            btype = BattleType.WILD
        battle = Battle(btype, [part_a, part_b])
        battle.turn_count = data.battle.turn
        battle.debug = getattr(state, "debug", False)
        return cls(battle, data, state)
