"""Data structures and helpers for Pokemon battles.

This module is a simplified adaptation of an older battle engine.
It focuses on storing all data necessary to resume a battle at a
later time.  Each class implements `to_dict` and `from_dict`
methods used for JSON serialisation.  `BattleData` also provides
`save_to_file` and `load_from_file` helpers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class Move:
    """Minimal representation of a Pokemon move."""

    name: str
    priority: int = 0

    def to_dict(self) -> Dict:
        return {"name": self.name, "priority": self.priority}

    @classmethod
    def from_dict(cls, data: Dict) -> "Move":
        return cls(name=data["name"], priority=data.get("priority", 0))


class Pokemon:
    """Very small Pokemon container used for battles."""

    def __init__(
        self,
        name: str,
        level: int = 1,
        hp: int = 100,
        max_hp: Optional[int] = None,
        status: int = 0,
        moves: Optional[List[Move]] = None,
        toxic_counter: int = 0,
        ability=None,
        data: Optional[Dict] = None,
    ):
        self.name = name
        self.level = level
        self.hp = hp
        self.max_hp = max_hp if max_hp is not None else hp
        self.status = status
        self.toxic_counter = toxic_counter
        self.moves = moves or []
        self.ability = ability
        self.data = data or {}
        self.tempvals: Dict[str, int] = {}
        self.boosts: Dict[str, int] = {
            "atk": 0,
            "def": 0,
            "spa": 0,
            "spd": 0,
            "spe": 0,
            "accuracy": 0,
            "evasion": 0,
        }

    def getName(self) -> str:
        return self.name

    def setStatus(self, status: int) -> None:
        self.status = status
        if status == "tox":
            self.toxic_counter = 1
        else:
            self.toxic_counter = 0

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "level": self.level,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "status": self.status,
            "moves": [m.to_dict() for m in self.moves],
            "tempvals": self.tempvals,
            "boosts": self.boosts,
            "toxic_counter": self.toxic_counter,
            "ability": getattr(self.ability, "name", self.ability),
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Pokemon":
        obj = cls(
            name=data["name"],
            level=data.get("level", 1),
            hp=data.get("hp", 100),
            max_hp=data.get("max_hp"),
            status=data.get("status", 0),
            moves=[Move.from_dict(m) for m in data.get("moves", [])],
            toxic_counter=data.get("toxic_counter", 0),
            ability=data.get("ability"),
            data=data.get("data"),
        )
        obj.tempvals = data.get("tempvals", {})
        obj.boosts = data.get(
            "boosts",
            {
                "atk": 0,
                "def": 0,
                "spa": 0,
                "spd": 0,
                "spe": 0,
                "accuracy": 0,
                "evasion": 0,
            },
        )
        return obj


class DeclareAttack:
    def __init__(self, target: str, move: Move):
        self.target = target
        self.move = move

    def __repr__(self):
        return f"{self.move.name} -> {self.target}"

    def to_dict(self) -> Dict:
        return {"target": self.target, "move": self.move.to_dict()}

    @classmethod
    def from_dict(cls, data: Dict) -> "DeclareAttack":
        return cls(target=data["target"], move=Move.from_dict(data["move"]))


class TurnInit:
    def __init__(self, switch=None, attack: Optional[DeclareAttack] = None,
                 item=None, run=None, recharge=None):
        self.switch = switch
        self.attack = attack
        self.item = item
        self.run = run
        self.recharge = recharge

    def getTarget(self) -> Optional[str]:
        if self.attack is None:
            return None
        return self.attack.target

    def to_dict(self) -> Dict:
        return {
            "switch": self.switch,
            "attack": self.attack.to_dict() if self.attack else None,
            "item": self.item,
            "run": self.run,
            "recharge": self.recharge,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TurnInit":
        attack = None
        if data.get("attack"):
            attack = DeclareAttack.from_dict(data["attack"])
        return cls(
            switch=data.get("switch"),
            attack=attack,
            item=data.get("item"),
            run=data.get("run"),
            recharge=data.get("recharge"),
        )


class PositionData:
    def __init__(self, pokedata: Optional[Pokemon] = None):
        self.pokemon = pokedata
        self.turninit = TurnInit()

    def getTarget(self) -> Optional[str]:
        return self.turninit.getTarget()

    def getAction(self) -> Optional[Move]:
        if self.turninit.attack:
            return self.turninit.attack.move
        return None

    def declareAttack(self, target: str, move: Move) -> None:
        self.turninit = TurnInit(attack=DeclareAttack(target, move))

    def declareSwitch(self, slotswitch) -> None:
        self.turninit = TurnInit(switch=slotswitch)

    def removeDeclare(self) -> None:
        self.turninit = TurnInit()

    def to_dict(self) -> Dict:
        return {
            "pokemon": self.pokemon.to_dict() if self.pokemon else None,
            "turninit": self.turninit.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "PositionData":
        poke = Pokemon.from_dict(data["pokemon"]) if data.get("pokemon") else None
        obj = cls(pokedata=poke)
        obj.turninit = TurnInit.from_dict(data.get("turninit", {}))
        return obj


class Team:
    def __init__(self, trainer: str, pokemon_list: Optional[List[Pokemon]] = None):
        self.trainer = trainer
        pokemon_list = pokemon_list or []
        slots = [None] * 6
        for i, poke in enumerate(pokemon_list[:6]):
            slots[i] = poke
        (self.slot1, self.slot2, self.slot3,
         self.slot4, self.slot5, self.slot6) = slots

    def returnlist(self) -> List[Optional[Pokemon]]:
        return [self.slot1, self.slot2, self.slot3,
                self.slot4, self.slot5, self.slot6]

    def returndict(self) -> Dict[int, Optional[Pokemon]]:
        return {
            1: self.slot1,
            2: self.slot2,
            3: self.slot3,
            4: self.slot4,
            5: self.slot5,
            6: self.slot6,
        }

    def to_dict(self) -> Dict:
        return {
            "trainer": self.trainer,
            "pokemon": [p.to_dict() if p else None for p in self.returnlist()],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Team":
        plist = [Pokemon.from_dict(p) if p else None for p in data.get("pokemon", [])]
        return cls(trainer=data.get("trainer"), pokemon_list=plist)


class Field:
    def __init__(self):
        self.payday: Dict[str, int] = {}
        # Track ongoing field effects such as Trick Room or Echoed Voice
        self.pseudo_weather: Dict[str, Dict] = {}
        # Track standard weather and terrain conditions
        self.weather: Optional[str] = None
        self.weather_state: Dict[str, Any] = {}
        self.terrain: Optional[str] = None
        self.terrain_state: Dict[str, Any] = {}

    # ------------------------------
    # Pseudo weather helpers
    # ------------------------------
    def add_pseudo_weather(self, name: str, effect: Dict, *, moves_funcs=None) -> None:
        """Add a pseudo weather condition to the field."""
        moves_funcs = moves_funcs or {}
        current = self.pseudo_weather.get(name)
        if current is None:
            self.pseudo_weather[name] = effect.copy()
            cb = effect.get("onFieldStart")
        else:
            cb = effect.get("onFieldRestart")
        if isinstance(cb, str) and moves_funcs:
            try:
                cls_name, func_name = cb.split(".", 1)
                cls = getattr(moves_funcs, cls_name, None)
                if cls:
                    cb = getattr(cls(), func_name, None)
            except Exception:
                cb = None
        if callable(cb):
            cb(self.pseudo_weather[name])

    def get_pseudo_weather(self, name: str) -> Optional[Dict]:
        return self.pseudo_weather.get(name)

    def remove_pseudo_weather(self, name: str) -> None:
        if name in self.pseudo_weather:
            del self.pseudo_weather[name]

    def to_dict(self) -> Dict:
        return {
            "payday": self.payday,
            "weather": self.weather,
            "weather_state": self.weather_state,
            "terrain": self.terrain,
            "terrain_state": self.terrain_state,
            "pseudo_weather": self.pseudo_weather,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Field":
        obj = cls()
        obj.payday = data.get("payday", {})
        obj.weather = data.get("weather")
        obj.weather_state = data.get("weather_state", {})
        obj.terrain = data.get("terrain")
        obj.terrain_state = data.get("terrain_state", {})
        obj.pseudo_weather = data.get("pseudo_weather", {})
        return obj


class Battle:
    def __init__(self, battletype: int = 1):
        self.turn = 1
        self.battletype = battletype
        # Field represents global effects active on the battlefield
        self.field = Field()

    def incrementTurn(self) -> None:
        self.turn += 1

    def to_dict(self) -> Dict:
        return {"turn": self.turn, "battletype": self.battletype}

    @classmethod
    def from_dict(cls, data: Dict) -> "Battle":
        obj = cls(battletype=data.get("battletype", 1))
        obj.turn = data.get("turn", 1)
        return obj


class TurnData:
    def __init__(self, teams: Optional[Dict[str, Team]] = None, teamslots: int = 1):
        self.positions: Dict[str, PositionData] = {}
        teams = teams or {}

        def populate(teamname: str, team: Team) -> None:
            count = 0
            for poke in team.returnlist():
                if count >= teamslots:
                    return
                posname = f"{teamname}{count + 1}"
                if poke and poke.hp > 0:
                    self.positions[posname] = PositionData(poke)
                    count += 1
                    continue
            while count < teamslots:
                posname = f"{teamname}{count + 1}"
                self.positions[posname] = PositionData()
                count += 1

        for name, team in teams.items():
            populate(name, team)

    def teamPositions(self, team: str) -> Dict[str, PositionData]:
        return {k: v for k, v in self.positions.items() if k.startswith(team)}

    def to_dict(self) -> Dict:
        return {pos: data.to_dict() for pos, data in self.positions.items()}

    @classmethod
    def from_dict(cls, data: Dict) -> "TurnData":
        obj = cls(teams={})
        obj.positions = {pos: PositionData.from_dict(d) for pos, d in data.items()}
        return obj


class BattleData:
    def __init__(self, team_a: Team, team_b: Team):
        self.teams: Dict[str, Team] = {"A": team_a, "B": team_b}
        self.battle = Battle()
        self.turndata = TurnData(self.teams)
        self.field = Field()

    def paydayPayout(self) -> int:
        payout = 0
        for team in self.teams.values():
            for poke in team.returnlist():
                if not poke:
                    continue
                if hasattr(poke, "payday"):
                    payout += poke.level * poke.payday * 5
                    del poke.payday
        return payout

    def to_dict(self) -> Dict:
        return {
            "teams": {k: v.to_dict() for k, v in self.teams.items()},
            "battle": self.battle.to_dict(),
            "turndata": self.turndata.to_dict(),
            "field": self.field.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "BattleData":
        team_a = Team.from_dict(data["teams"]["A"])
        team_b = Team.from_dict(data["teams"]["B"])
        obj = cls(team_a, team_b)
        obj.battle = Battle.from_dict(data.get("battle", {}))
        obj.turndata = TurnData.from_dict(data.get("turndata", {}))
        obj.field = Field.from_dict(data.get("field", {}))
        return obj

    def save_to_file(self, filename: str) -> None:
        with open(filename, "w") as f:
            json.dump(self.to_dict(), f)

    @staticmethod
    def load_from_file(filename: str) -> "BattleData":
        with open(filename) as f:
            data = json.load(f)
        return BattleData.from_dict(data)
