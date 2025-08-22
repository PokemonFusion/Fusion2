from .ai import AIMoveSelector
from .battledata import BattleData, Field, Move, Pokemon, Team, TurnData
from .damage import DamageResult, damage_calc
from .turnorder import calculateTurnorder

try:
	from .battleinstance import (
		BattleSession,
		create_battle_pokemon,
		generate_trainer_pokemon,
		generate_wild_pokemon,
	)
except Exception:  # pragma: no cover - allow partial imports during tests
	BattleSession = None
	generate_trainer_pokemon = generate_wild_pokemon = create_battle_pokemon = None
from .state import BattleState

try:
	from .engine import Action, ActionType, Battle, BattleMove, BattleParticipant, BattleType
except Exception:  # pragma: no cover - optional for lightweight test stubs
	BattleType = BattleParticipant = Battle = BattleMove = Action = ActionType = None
from . import capture as capture_mod
from .messaging import MessagingMixin
from .setup import build_initial_state, create_participants, persist_initial_state
from .storage import BattleDataWrapper


def attempt_capture(*args, **kwargs):
        """Proxy to :func:`pokemon.battle.capture.attempt_capture` for convenience."""
        return capture_mod.attempt_capture(*args, **kwargs)

__all__ = [
	"DamageResult",
	"damage_calc",
	"BattleData",
	"Team",
	"Pokemon",
	"TurnData",
	"Field",
	"Move",
	"calculateTurnorder",
	"AIMoveSelector",
	"BattleSession",
	"generate_trainer_pokemon",
	"generate_wild_pokemon",
	"create_battle_pokemon",
	"BattleType",
	"BattleParticipant",
	"Battle",
	"BattleMove",
	"Action",
	"ActionType",
	"BattleState",
	"attempt_capture",
	"BattleDataWrapper",
	"create_participants",
	"build_initial_state",
	"persist_initial_state",
	"MessagingMixin",
]
