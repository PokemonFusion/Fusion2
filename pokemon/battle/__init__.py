from .damage import DamageResult, damage_calc
from .battledata import BattleData, Team, Pokemon, TurnData, Field, Move
from .turnorder import calculateTurnorder
try:
    from .battleinstance import (
        BattleSession,
        generate_trainer_pokemon,
        generate_wild_pokemon,
        create_battle_pokemon,
    )
except Exception:  # pragma: no cover - allow partial imports during tests
    BattleSession = None
    generate_trainer_pokemon = generate_wild_pokemon = create_battle_pokemon = None
from .state import BattleState
try:
    from .engine import BattleType, BattleParticipant, Battle, BattleMove, Action, ActionType
except Exception:  # pragma: no cover - optional for lightweight test stubs
    BattleType = BattleParticipant = Battle = BattleMove = Action = ActionType = None
from .capture import attempt_capture
from .storage import BattleDataWrapper

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
]
