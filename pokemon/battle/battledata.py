"""Data structures and helpers for Pokemon battles.

This module is a simplified adaptation of an older battle engine.
It focuses on storing all data necessary to resume a battle at a
later time.  Each class implements `to_dict` and `from_dict`
methods used for JSON serialisation.  `BattleData` also provides
`save_to_file` and `load_from_file` helpers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

try:
    from pokemon.dex import POKEDEX  # type: ignore
except Exception:  # pragma: no cover - optional in tests
    POKEDEX = {}


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
        model_id: Optional[int] = None,
        base_stats=None,
    ):
        self.name = name
        self.level = level
        self.hp = hp
        self.max_hp = max_hp if max_hp is not None else hp
        self.status = status
        self.toxic_counter = toxic_counter
        self.moves = moves or []
        self.ability = ability
        self.model_id = model_id
        self.data = data or {}
        self.base_stats = base_stats
        if self.base_stats is None:
            species = (
                POKEDEX.get(name)
                or POKEDEX.get(name.lower())
                or POKEDEX.get(name.capitalize())
            )
            if species is not None:
                self.base_stats = getattr(species, "base_stats", None)
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

    def setStatus(self, status: str | int) -> None:
        self.status = status
        if status == "tox":
            self.toxic_counter = 1
        else:
            self.toxic_counter = 0

    def to_dict(self) -> Dict:
        """Return a minimal serialisable representation of this Pokémon."""

        info = {
            "current_hp": self.hp,
            "status": self.status,
            "boosts": self.boosts,
            "toxic_counter": self.toxic_counter,
            "tempvals": self.tempvals,
        }

        if self.model_id:
            info["model_id"] = self.model_id
            return info

        if self.ability is not None:
            info["ability"] = getattr(self.ability, "name", self.ability)
        if self.data:
            info["data"] = self.data
        info.update(
            {
                "name": self.name,
                "level": self.level,
                "max_hp": self.max_hp,
                "moves": [m.to_dict() for m in self.moves],
            }
        )

        return info

    @classmethod
    def from_dict(cls, data: Dict) -> "Pokemon":
        """Recreate a ``Pokemon`` from its minimal serialised form."""

        name = data.get("name", "Pikachu")
        level = data.get("level", 1)
        moves = [Move.from_dict(m) for m in data.get("moves", [])]
        max_hp = data.get("max_hp")
        model_id = data.get("model_id")
        ability = data.get("ability")
        extra_data = data.get("data")

        slots = None
        base_stats = None
        if model_id:
            try:
                from ..models import OwnedPokemon
            except Exception:  # pragma: no cover - DB not available in tests
                OwnedPokemon = None

            if OwnedPokemon:
                try:
                    poke = OwnedPokemon.objects.get(unique_id=model_id)
                    name = getattr(poke, "name", getattr(poke, "species", "Pikachu"))
                    level = getattr(poke, "level", 1)
                    ability = getattr(poke, "ability", ability)
                    extra_data = getattr(poke, "data", extra_data)
                    species_name = getattr(poke, "species", None)
                    if species_name:
                        base_stats = (
                            POKEDEX.get(species_name)
                            or POKEDEX.get(str(species_name).lower())
                            or POKEDEX.get(str(species_name).capitalize())
                        )
                        if base_stats is not None:
                            base_stats = getattr(base_stats, "base_stats", None)
                    if max_hp is None:
                        try:
                            from pokemon.utils.pokemon_helpers import get_max_hp

                            max_hp = get_max_hp(poke)
                        except Exception:
                            max_hp = getattr(poke, "current_hp", None)
                    if not moves:
                        slots = getattr(poke, "activemoveslot_set", None)
                        if slots is not None:
                            try:
                                iterable = slots.all().order_by("slot")
                            except Exception:
                                try:
                                    iterable = slots.order_by("slot")
                                except Exception:
                                    iterable = slots
                            move_names = [getattr(s.move, "name", "") for s in iterable][:4]
                        elif getattr(poke, "active_moveset", None):
                            move_names = [
                                s.move.name for s in poke.active_moveset.slots.order_by("slot")
                            ][:4]
                        else:
                            move_names = ["Tackle"]
                        moves = [Move(name=m) for m in move_names]
                except Exception:
                    pass

        if base_stats is None:
            base_stats = (
                POKEDEX.get(name)
                or POKEDEX.get(name.lower())
                or POKEDEX.get(name.capitalize())
            )
            if base_stats is not None:
                base_stats = getattr(base_stats, "base_stats", None)

        obj = cls(
            name=name,
            level=level,
            hp=data.get("current_hp", data.get("hp", 100)),
            max_hp=max_hp,
            status=data.get("status", 0),
            moves=moves,
            toxic_counter=data.get("toxic_counter", 0),
            ability=ability,
            data=extra_data,
            model_id=model_id,
        )
        if base_stats is not None:
            try:
                obj.base_stats = base_stats
            except Exception:
                pass
        if slots is not None:
            obj.activemoveslot_set = slots
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


@dataclass
class PositionData:
    """Container for a Pokémon and its declared action."""

    pokemon: Optional[Pokemon] = None
    turninit: TurnInit = field(default_factory=TurnInit)

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

    def declareItem(self, item: str) -> None:
        """Declare use of an item this turn."""
        self.turninit = TurnInit(item=item)

    def declareRun(self) -> None:
        """Declare attempting to flee this turn."""
        self.turninit = TurnInit(run=True)

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
        turninit = TurnInit.from_dict(data.get("turninit", {}))
        return cls(pokemon=poke, turninit=turninit)


@dataclass(init=False)
class Team:
    """Representation of a trainer's party."""

    trainer: str
    slot1: Optional[Pokemon] = None
    slot2: Optional[Pokemon] = None
    slot3: Optional[Pokemon] = None
    slot4: Optional[Pokemon] = None
    slot5: Optional[Pokemon] = None
    slot6: Optional[Pokemon] = None

    def __init__(self, trainer: str, pokemon_list: Optional[List[Pokemon]] = None) -> None:
        self.trainer = trainer
        pokemon_list = pokemon_list or []
        slots = [None] * 6
        for i, poke in enumerate(pokemon_list[:6]):
            slots[i] = poke
        (
            self.slot1,
            self.slot2,
            self.slot3,
            self.slot4,
            self.slot5,
            self.slot6,
        ) = slots

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
