from dataclasses import dataclass, field
from pathlib import Path
import json
import importlib.util
import sys
import csv
import re
from typing import Any, Dict, Optional, List

BASE_PATH = Path(__file__).resolve().parents[2]

@dataclass
class Ability:
    name: str
    num: int
    rating: Optional[float] = None
    is_nonstandard: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]):
        return cls(
            name=name,
            num=data.get("num", 0),
            rating=data.get("rating"),
            is_nonstandard=data.get("isNonstandard"),
            raw=data,
        )

    def call(self, func: str, *args, **kwargs):
        """Call a stored ability callback if it exists."""
        cb = self.raw.get(func)
        if callable(cb):
            return cb(*args, **kwargs)
        return None

@dataclass
class Move:
    name: str
    num: int
    type: Optional[str] = None
    category: Optional[str] = None
    power: Any = None
    accuracy: Any = None
    pp: Any = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]):
        return cls(
            name=name,
            num=data.get("num", 0),
            type=data.get("type"),
            category=data.get("category"),
            power=data.get("basePower"),
            accuracy=data.get("accuracy"),
            pp=data.get("pp"),
            raw=data,
        )


@dataclass
class Item:
    name: str
    num: int
    spritenum: Optional[int] = None
    desc: Optional[str] = None
    id: Optional[str] = None
    gen: Optional[int] = None
    mega_evolves: Optional[str] = None
    mega_stone: Optional[str] = None
    item_user: List[str] = field(default_factory=list)
    on_take_item: Any = None
    forced_forme: Optional[str] = None
    price: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]):
        return cls(
            name=name,
            num=data.get("num", 0),
            spritenum=data.get("spritenum"),
            desc=data.get("desc"),
            id=data.get("id"),
            gen=data.get("gen"),
            mega_evolves=data.get("megaEvolves"),
            mega_stone=data.get("megaStone"),
            item_user=data.get("itemUser", []),
            on_take_item=data.get("onTakeItem"),
            forced_forme=data.get("forcedForme"),
            price=data.get("price"),
            raw=data,
        )

    def call(self, func: str, *args, **kwargs):
        """Call a stored item callback if it exists."""
        cb = self.raw.get(func)
        if callable(cb):
            return cb(*args, **kwargs)
        return None


@dataclass
class Condition:
    name: str
    effect_type: Optional[str] = None
    duration: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]):
        return cls(
            name=name,
            effect_type=data.get("effectType"),
            duration=data.get("duration"),
            raw=data,
        )

    def call(self, func: str, *args, **kwargs):
        cb = self.raw.get(func)
        if callable(cb):
            return cb(*args, **kwargs)
        return None


@dataclass
class Stats:
    hp: int = 0
    atk: int = 0
    def_: int = 0
    spa: int = 0
    spd: int = 0
    spe: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            hp=data.get("hp", 0),
            atk=data.get("atk", 0),
            def_=data.get("def", 0),
            spa=data.get("spa", 0),
            spd=data.get("spd", 0),
            spe=data.get("spe", 0),
        )


@dataclass
class GenderRatio:
    M: float = 0.0
    F: float = 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(M=data.get("M", 0), F=data.get("F", 0))

@dataclass
class Pokemon:
    name: str
    num: int
    types: List[str] = field(default_factory=list)
    gender_ratio: Optional[GenderRatio] = None
    gender: Optional[str] = None
    base_stats: Stats = field(default_factory=Stats)
    abilities: Dict[str, Ability] = field(default_factory=dict)
    heightm: float = 0.0
    weightkg: float = 0.0
    color: Optional[str] = None
    prevo: Optional[str] = None
    evo_level: Optional[int] = None
    evos: List[str] = field(default_factory=list)
    egg_groups: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)
    is_baby: bool = False

    @classmethod
    def from_dict(
        cls,
        name: str,
        data: Dict[str, Any],
        abilitydex: Optional[Dict[str, Ability]] = None,
    ):
        abilitydex = abilitydex or {}

        base_stats = Stats.from_dict(data.get("baseStats", {}))
        gender_ratio = None
        if "genderRatio" in data:
            gender_ratio = GenderRatio.from_dict(data["genderRatio"])
        gender = data.get("gender")
        abilities: Dict[str, Ability] = {}
        for slot, ability_name in data.get("abilities", {}).items():
            lookup = abilitydex.get(ability_name.lower())
            if lookup:
                abilities[slot] = lookup
            else:
                abilities[slot] = Ability(name=ability_name, num=0, raw={})

        base = data.get("baseSpecies", name)
        from .baby_species import BABY_SPECIES
        is_baby = base in BABY_SPECIES

        return cls(
            name=name,
            num=data.get("num", 0),
            types=data.get("types", []),
            gender_ratio=gender_ratio,
            gender=gender,
            base_stats=base_stats,
            abilities=abilities,
            heightm=data.get("heightm", 0.0),
            weightkg=data.get("weightkg", 0.0),
            color=data.get("color"),
            prevo=data.get("prevo"),
            evo_level=data.get("evoLevel"),
            evos=data.get("evos", []),
            egg_groups=data.get("eggGroups", []),
            raw=data,
            is_baby=is_baby,
        )


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


def load_pokedex(
    path: Path, abilitydex: Optional[Dict[str, Ability]] = None
) -> Dict[str, Pokemon]:
    """Load pokemon data from a Python or JSON file."""
    if path.suffix == ".py":
        # support nested paths like pokemon/dex/pokedex.py
        rel_parts = path.with_suffix("").parts
        try:
            idx = rel_parts.index("pokemon")
            module_parts = rel_parts[idx:]
        except ValueError:
            module_parts = ["pokemon", "dex", path.stem]
        module_name = ".".join(module_parts)
        spec = importlib.util.spec_from_file_location(module_name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)
        data = getattr(mod, "pokedex")
    else:
        data = _load_json(path)
    return {
        name: Pokemon.from_dict(details.get("name", name), details, abilitydex)
        for name, details in data.items()
    }


def load_movedex(path: Path) -> Dict[str, Move]:
    """Load move data from a Python or JSON file."""
    if path.suffix == ".py":
        # support nested paths like pokemon/dex/abilities/abilitiesdex.py
        rel_parts = path.with_suffix("").parts
        try:
            idx = rel_parts.index("pokemon")
            module_parts = rel_parts[idx:]
        except ValueError:
            module_parts = ["pokemon", "dex", path.stem]
        module_name = ".".join(module_parts)
        spec = importlib.util.spec_from_file_location(module_name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)
        data = getattr(mod, "py_dict")
    else:
        data = _load_json(path)
    # Store entries keyed by lowercase names for case-insensitive lookup
    return {name.lower(): Move.from_dict(name, details) for name, details in data.items()}


def load_abilitydex(path: Path) -> Dict[str, Ability]:
    """Load ability data from a Python or JSON file."""
    if path.suffix == ".py":
        rel_parts = path.with_suffix("").parts
        try:
            idx = rel_parts.index("pokemon")
            module_parts = rel_parts[idx:]
        except ValueError:
            module_parts = ["pokemon", "dex", path.stem]
        module_name = ".".join(module_parts)
        spec = importlib.util.spec_from_file_location(module_name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)
        data = getattr(mod, "py_dict")
    else:
        data = _load_json(path)
    return {name: Ability.from_dict(name, details) for name, details in data.items()}


def load_itemdex(path: Path) -> Dict[str, Item]:
    """Load item data from a Python or JSON file."""
    if path.suffix == ".py":
        rel_parts = path.with_suffix("").parts
        try:
            idx = rel_parts.index("pokemon")
            module_parts = rel_parts[idx:]
        except ValueError:
            module_parts = ["pokemon", "dex", path.stem]
        module_name = ".".join(module_parts)
        spec = importlib.util.spec_from_file_location(module_name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)
        data = getattr(mod, "py_dict")
    else:
        data = _load_json(path)

    items = {name: Item.from_dict(name, details) for name, details in data.items()}

    price_path = BASE_PATH / "pokemon" / "data" / "item_prices.csv"
    if price_path.exists():
        with open(price_path) as f:
            reader = csv.DictReader(f)
            price_map = {}
            for row in reader:
                key = re.sub(r"\W+", "", row.get("identifier", "")).lower()
                cost = row.get("cost")
                if cost:
                    price_map[key] = int(cost)
        for item in items.values():
            key = re.sub(r"\W+", "", item.name).lower()
            if key in price_map:
                item.price = price_map[key]

    return items


def load_conditiondex(path: Path) -> Dict[str, Condition]:
    """Load condition data from a Python or JSON file."""
    if path.suffix == ".py":
        rel_parts = path.with_suffix("").parts
        try:
            idx = rel_parts.index("pokemon")
            module_parts = rel_parts[idx:]
        except ValueError:
            module_parts = ["pokemon", "dex", path.stem]
        module_name = ".".join(module_parts)
        spec = importlib.util.spec_from_file_location(module_name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)
        data = getattr(mod, "py_dict")
    else:
        data = _load_json(path)
    return {name: Condition.from_dict(name, details) for name, details in data.items()}
