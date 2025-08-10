from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set

from .battledata import BattleData, Pokemon, Team


@dataclass
class BattleState:
    """Representation of an ongoing battle."""

    ai_type: str = "Wild"
    ability_holder: Optional[str] = None
    first_ability: Optional[str] = None
    first_turn_taken: bool = False
    how_many: int = 1
    teams: Dict[str, List[int]] = field(default_factory=lambda: {"A": [], "B": []})
    movesets: Dict[int, Dict[str, str]] = field(default_factory=dict)
    positions: Dict[str, int] = field(default_factory=dict)
    declare: Dict[str, Dict[str, str]] = field(default_factory=dict)
    recycle: Dict[str, str] = field(default_factory=dict)
    expshare: Dict[str, str] = field(default_factory=dict)
    roomweather: str = "clear"
    watchers: Set[int] = field(default_factory=set)
    tier: int = 1
    turn: int = 1
    xp: bool = True
    txp: bool = True
    four_moves: bool = False
    pokemon_control: Dict[str, str] = field(default_factory=dict)
    debug: bool = False

    def to_dict(self) -> Dict:
        """Return a serialisable representation of this state."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "BattleState":
        """Recreate state from stored data."""
        return cls(**data)

    @classmethod
    def from_battle_data(cls, data: BattleData, ai_type: str = "Wild") -> "BattleState":
        """Create a serialisable state from ``BattleData``."""

        state = cls(ai_type=ai_type)

        id_map: Dict[Pokemon, int] = {}
        counter = 1

        for team_key, team in data.teams.items():
            for poke in team.returnlist():
                if not poke:
                    continue
                pid = counter
                counter += 1
                id_map[poke] = pid
                state.teams.setdefault(team_key, []).append(pid)
                state.movesets[pid] = {
                    chr(ord("A") + idx): mv.name
                    for idx, mv in enumerate(poke.moves[:4])
                }

        for pos, pdata in data.turndata.positions.items():
            if pdata.pokemon:
                state.positions[pos] = id_map.get(pdata.pokemon, 0)
            if pdata.turninit.attack:
                state.declare[pos] = {
                    "move": pdata.turninit.attack.move,
                    "target": pdata.turninit.attack.target,
                }
            elif pdata.turninit.switch is not None:
                state.declare[pos] = {"switch": pdata.turninit.switch}
            elif pdata.turninit.item:
                state.declare[pos] = {"item": pdata.turninit.item}
            elif pdata.turninit.run:
                state.declare[pos] = {"run": "1"}

        return state
