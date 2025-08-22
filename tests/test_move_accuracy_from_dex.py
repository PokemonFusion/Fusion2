import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from pokemon.battle.battledata import Pokemon
from pokemon.battle.engine import (
	Action,
	ActionType,
	Battle,
	BattleMove,
	BattleParticipant,
	BattleType,
)
from pokemon.dex import MOVEDEX
from pokemon.dex.entities import Move


def test_accuracy_overridden_from_dex():
	"""Moves should hydrate accuracy from the Pokédex when used."""
	MOVEDEX["thunder"] = Move(
		name="Thunder",
		num=0,
		type="Electric",
		category="Special",
		power=110,
		accuracy=70,
		pp=10,
		raw={},
	)
	try:
		user = Pokemon("User")
		target = Pokemon("Target")
		move = BattleMove("Thunder", pp=5)
		# Avoid damage calculation during the test
		move.onHit = lambda *args, **kwargs: None
		p1 = BattleParticipant("P1", [user])
		p2 = BattleParticipant("P2", [target])
		p1.active = [user]
		p2.active = [target]
		action = Action(p1, ActionType.MOVE, p2, move, move.priority)
		battle = Battle(BattleType.WILD, [p1, p2])
		battle.use_move(action)
		assert action.move.accuracy == 70
	finally:
		MOVEDEX.pop("thunder", None)
