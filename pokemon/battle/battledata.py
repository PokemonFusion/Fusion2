"""Data structures and helpers for Pokemon battles.

This module is a simplified adaptation of an older battle engine.
It focuses on storing all data necessary to resume a battle at a
later time.  Each class implements `to_dict` and `from_dict`
methods used for JSON serialisation.  `BattleData` also provides
`save_to_file` and `load_from_file` helpers.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Optional

from utils.safe_import import safe_import

try:
	POKEDEX = safe_import("pokemon.dex").POKEDEX  # type: ignore[attr-defined]
except (ModuleNotFoundError, AttributeError):  # pragma: no cover - optional in tests
	POKEDEX = {}


@dataclass
class Move:
	"""Minimal representation of a Pokémon move.

	Parameters
	----------
	name
	    Name of the move.
	priority
	    Execution priority of the move.
	pokemon_types
	    Optional typing of the Pokémon using the move.  This is primarily
	    carried so ephemeral test battles can perform damage calculations with
	    the correct Same Type Attack Bonus.
	"""

	name: str
	priority: int = 0
	pokemon_types: Optional[List[str]] = None

	def to_dict(self) -> Dict:
		data = {"name": self.name, "priority": self.priority}
		if self.pokemon_types:
			data["pokemon_types"] = list(self.pokemon_types)
		pp_value = getattr(self, "pp", None)
		if pp_value is not None:
			data["pp"] = pp_value
		return data

	@classmethod
	def from_dict(cls, data: Dict) -> "Move":
		obj = cls(
			name=data["name"],
			priority=data.get("priority", 0),
			pokemon_types=data.get("pokemon_types"),
		)
		if "pp" in data:
			setattr(obj, "pp", data["pp"])
		return obj


class Pokemon:
	"""Very small Pokémon container used for battles.

	The constructor accepts optional item and stat data. IVs, EVs and nature
	are used to calculate the base stats for the battle instance.  Explicit
	typing can be supplied via the ``types`` argument; when omitted, typing is
	inferred from the Pokédex using the Pokémon's species name.
	"""

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
		item=None,
		ivs: Optional[List[int]] = None,
		evs: Optional[List[int]] = None,
		nature: str = "Hardy",
		model_id: Optional[int] = None,
		gender: str = "N",
		types: Optional[List[str]] = None,
	):
		self.name = name
		self.level = level
		self.hp = hp
		self.max_hp = max_hp if max_hp is not None else hp
		self.status = status
		self.toxic_counter = toxic_counter
		self.moves = moves or []
		self.ability = ability
		self.item = item
		self.model_id = model_id
		self.ivs = ivs or [0, 0, 0, 0, 0, 0]
		self.evs = evs or [0, 0, 0, 0, 0, 0]
		self.nature = nature
		self.gender = gender
		self.tempvals: Dict[str, int] = {}
		# Track volatile status effects such as confusion or curses
		self.volatiles: Dict[str, Any] = {}
		self.boosts: Dict[str, int] = {
			"atk": 0,
			"def": 0,
			"spa": 0,
			"spd": 0,
			"spe": 0,
			"accuracy": 0,
			"evasion": 0,
		}
		try:
			refresh_stats = safe_import("pokemon.helpers.pokemon_helpers").refresh_stats
			get_stats = safe_import("pokemon.helpers.pokemon_helpers").get_stats
			refresh_stats(self)
			stats_dict = get_stats(self)
			try:
				StatsCls = safe_import("pokemon.dex.entities").Stats
			except Exception:  # pragma: no cover - Stats class optional
				from types import SimpleNamespace as StatsCls  # type: ignore
			self.base_stats = StatsCls(**stats_dict)
		except Exception:  # pragma: no cover - helpers may be absent or fail in tests
			pass

		# Convert item name strings to Item objects when possible so that
		# item callbacks can fire during battle simulations.
		if isinstance(self.item, str):
			try:  # pragma: no cover - optional import paths
				dex_mod = safe_import("pokemon.dex")
				itemdex = getattr(dex_mod, "ITEMDEX", {})
				ItemCls = getattr(dex_mod, "Item", None)
				entry = (
					itemdex.get(self.item) or itemdex.get(str(self.item).lower()) or itemdex.get(str(self.item).title())
				)
				if entry and ItemCls:
					self.item = ItemCls.from_dict(str(self.item), entry)
			except Exception:
				pass

		# Ensure a ``types`` attribute is always available. Some parts of the
		# battle engine (such as damage calculation) expect this attribute to
		# exist.  Use the explicitly supplied types if provided; otherwise fall
		# back to a Pokédex lookup based on the Pokémon's species name.
		self.types = [str(t).title() for t in types] if types else self._lookup_species_types()

	def _lookup_species_types(self) -> List[str]:
		"""Return this Pokémon's types inferred from the Pokédex.

		The ``POKEDEX`` mapping may not always be populated during tests so
		this helper is intentionally defensive and falls back to an empty list
		if the lookup fails for any reason.
		"""

		species_name = self.name
		pdex: Dict[str, Any] = {}
		try:  # pragma: no cover - data lookup is optional in tests
			dex_mod = safe_import("pokemon.dex")
			module_dex = getattr(dex_mod, "POKEDEX", {})
			load_pokedex = getattr(dex_mod, "load_pokedex", None)
			abilitydex = getattr(dex_mod, "ABILITYDEX", None)
			pokedex_path = getattr(dex_mod, "POKEDEX_PATH", None)
			pdex = module_dex or {}
			if not pdex and load_pokedex and pokedex_path:
				pdex = load_pokedex(pokedex_path, abilitydex)  # type: ignore[misc]
		except Exception:
			pdex = POKEDEX

		if not pdex:
			try:  # pragma: no cover - last-resort direct file load
				dex_root = Path(__file__).resolve().parents[1] / "dex"
				pokedex_path = dex_root / "pokedex" / "__init__.py"
				if pokedex_path.exists():
					pkg_name = "pokemon.dex"
					pkg_snapshot = set(sys.modules)
					if pkg_name not in sys.modules:
						stub = ModuleType(pkg_name)
						stub.__path__ = [str(dex_root)]
						sys.modules[pkg_name] = stub
					spec = importlib.util.spec_from_file_location(
						f"{pkg_name}.pokedex", pokedex_path
					)
					module = importlib.util.module_from_spec(spec)
					sys.modules[spec.name] = module
					assert spec and spec.loader  # help mypy
					spec.loader.exec_module(module)
					pdex = getattr(module, "pokedex", getattr(module, "POKEDEX", {}))
			except Exception:
				pdex = {}
			finally:
				if "pkg_snapshot" in locals():
					new_modules = set(sys.modules) - pkg_snapshot
					for mod_name in new_modules:
						if mod_name.startswith("pokemon.dex"):
							sys.modules.pop(mod_name, None)


		try:  # pragma: no cover - POKEDEX access is optional
			entry = pdex.get(species_name) or pdex.get(species_name.lower()) or pdex.get(species_name.capitalize())
			if entry:
				types = getattr(entry, "types", None)
				if types is None and isinstance(entry, dict):
					types = entry.get("types")
				if types:
					return [str(t).title() for t in types if t]
		except Exception:
			pass
		return []

	def getName(self) -> str:
		return self.name

	def setStatus(
		self,
		status: str | int,
		*,
		source=None,
		battle=None,
		effect=None,
		bypass_protection: bool = False,
	) -> bool:
		"""Attempt to set a major status condition on this Pokémon."""

		previous_status = getattr(self, "status", 0)
		previous_toxic = getattr(self, "toxic_counter", 0)

		battle_obj = battle or getattr(self, "battle", None)

		def _normalize(value):
			if isinstance(value, str):
				normalized = value.strip().lower()
				return normalized or 0
			return value or 0

		previous_key = _normalize(previous_status)

		if isinstance(status, str):
			status_key = status.strip().lower()
		else:
			status_key = status

		if status_key in {None, "", 0}:
			self.status = 0
			self.toxic_counter = 0
			if battle_obj and previous_key not in {None, "", 0}:
				item_effect = effect if isinstance(effect, str) else None
				battle_obj.announce_status_change(
					self,
					previous_key,
					event="endFromItem" if item_effect and item_effect.startswith("item:") else "end",
					effect=effect,
				)
			return True

		self.status = status_key
		if status_key == "tox":
			self.toxic_counter = 1
		else:
			self.toxic_counter = 0

		try:
			from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS

			handler = CONDITION_HANDLERS.get(status_key)
		except Exception:
			handler = None

		ctx = {
			"battle": battle or getattr(self, "battle", None),
			"source": source,
			"effect": effect,
			"previous": previous_status,
			"bypass_protection": bypass_protection,
		}

		if handler and hasattr(handler, "onStart"):
			try:
				result = handler.onStart(self, **ctx)
			except TypeError:
				result = handler.onStart(self, ctx.get("battle"))
			if result is False:
				self.status = previous_status
				self.toxic_counter = previous_toxic
				return False
		if battle_obj and status_key not in {None, "", 0}:
			event = "alreadyStarted" if previous_key == status_key else "start"
			battle_obj.announce_status_change(
				self,
				status_key,
				event=event,
				source=source,
				effect=effect,
			)
		return True

	def to_dict(self) -> Dict:
		"""Return a serialisable representation of this Pokémon."""

		def _collect_slots(slots_obj):
			if slots_obj is None:
				return []
			ordered = slots_obj
			try:
				ordered = ordered.order_by("slot")
			except Exception:
				pass
			try:
				ordered = ordered.all()
			except Exception:
				pass
			try:
				slots_list = list(ordered)
			except Exception:
				return []
			if slots_list:
				try:
					slots_list.sort(key=lambda s: getattr(s, "slot", 0))
				except Exception:
					pass
			return slots_list

		slots = _collect_slots(getattr(self, "activemoveslot_set", None))
		slot_pp_by_index = [getattr(slot, "current_pp", None) for slot in slots]
		slot_pp_by_name: Dict[str, List[Optional[int]]] = {}
		for slot in slots:
			move_obj = getattr(slot, "move", None)
			move_name = getattr(move_obj, "name", move_obj)
			if move_name:
				key = str(move_name).lower()
				slot_pp_by_name.setdefault(key, []).append(getattr(slot, "current_pp", None))

		def _move_payload(move, index: int) -> Dict:
			if hasattr(move, "to_dict"):
				payload = dict(move.to_dict())  # type: ignore[assignment]
			else:
				name = getattr(move, "name", move)
				payload = {"name": name}
				priority = getattr(move, "priority", None)
				if priority is not None:
					payload["priority"] = priority
				pokemon_types = getattr(move, "pokemon_types", None)
				if pokemon_types:
					payload["pokemon_types"] = list(pokemon_types)
			pp_value = payload.get("pp", getattr(move, "pp", None))
			if pp_value is None:
				if 0 <= index < len(slot_pp_by_index):
					pp_value = slot_pp_by_index[index]
				if pp_value is None:
					name_key = str(payload.get("name", getattr(move, "name", ""))).lower()
					values = slot_pp_by_name.get(name_key)
					if values:
						pp_value = values.pop(0)
			if pp_value is not None:
				payload["pp"] = pp_value
			return payload

		info: Dict[str, Any] = {
			"current_hp": self.hp,
			"status": self.status,
			"boosts": self.boosts,
			"toxic_counter": self.toxic_counter,
			"tempvals": self.tempvals,
			"gender": self.gender,
		}

		if self.model_id:
			info["model_id"] = self.model_id

		if self.ability is not None:
			info["ability"] = getattr(self.ability, "name", self.ability)
		if self.item is not None:
			info["item"] = getattr(self.item, "name", self.item)

		info.update(
			{
				"name": self.name,
				"level": self.level,
				"hp": self.hp,
				"max_hp": self.max_hp,
				"moves": [_move_payload(m, index) for index, m in enumerate(self.moves)],
				"ivs": list(self.ivs),
				"evs": list(self.evs),
				"nature": self.nature,
				"types": list(self.types),
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
		model_id_raw = data.get("model_id")
		if isinstance(model_id_raw, str):
			cleaned = model_id_raw.strip()
			if not cleaned or cleaned.lower() in {"none", "null"}:
				model_id = None
			else:
				model_id = cleaned
		elif model_id_raw is None:
			model_id = None
		else:
			model_id = str(model_id_raw)
		ability = data.get("ability")
		item = data.get("item")
		ivs = data.get("ivs")
		evs = data.get("evs")
		nature = data.get("nature", "Hardy")
		types = data.get("types")
		gender = data.get("gender", "N")
		slots = None
		if model_id:
			try:
				OwnedPokemon = safe_import("pokemon.models").OwnedPokemon  # type: ignore[attr-defined]
			except Exception:  # pragma: no cover - DB not available in tests
				OwnedPokemon = None

			if OwnedPokemon:
				try:
					poke = OwnedPokemon.objects.get(unique_id=model_id)
					name = getattr(poke, "name", getattr(poke, "species", "Pikachu"))
					level = getattr(poke, "level", 1)
					ability = getattr(poke, "ability", ability)
					item = getattr(poke, "item", getattr(poke, "held_item", item))
					ivs = getattr(poke, "ivs", ivs)
					evs = getattr(poke, "evs", evs)
					nature = getattr(poke, "nature", nature)
					gender = getattr(poke, "gender", gender)
					types = getattr(poke, "type_", types)
					if max_hp is None:
						try:
							get_max_hp = safe_import("pokemon.helpers.pokemon_helpers").get_max_hp
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
							move_names = [s.move.name for s in poke.active_moveset.slots.order_by("slot")][:4]
						else:
							move_names = ["Tackle"]
						moves = [Move(name=m) for m in move_names]
				except Exception:
					pass

		obj = cls(
			name=name,
			level=level,
			hp=data.get("current_hp", data.get("hp", 100)),
			max_hp=max_hp,
			status=data.get("status", 0),
			moves=moves,
			toxic_counter=data.get("toxic_counter", 0),
			ability=ability,
			item=item,
			ivs=ivs,
			evs=evs,
			nature=nature,
			model_id=model_id,
			gender=gender,
			types=([t.strip() for t in types.split(",")] if isinstance(types, str) else types),
		)
		if slots is not None:
			obj.activemoveslot_set = slots
		stored_moves = data.get("moves", [])
		for move, move_data in zip(obj.moves, stored_moves):
			if isinstance(move_data, dict) and "pp" in move_data:
				setattr(move, "pp", move_data["pp"])
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


@dataclass
class DeclareAttack:
	"""Representation of a declared attack.

	Only the key of the move and its target are stored. Full move
	information is retrieved from the dex when needed by the battle
	engine.
	"""

	target: str
	move: str

	def __repr__(self) -> str:
		return f"{self.move} -> {self.target}"

	def to_dict(self) -> Dict:
		"""Serialise this declaration to a dictionary."""
		return {"target": self.target, "move": self.move}

	@classmethod
	def from_dict(cls, data: Dict) -> "DeclareAttack":
		"""Recreate a :class:`DeclareAttack` from stored data."""
		return cls(target=data["target"], move=data["move"])


class TurnInit:
	def __init__(self, switch=None, attack: Optional[DeclareAttack] = None, item=None, run=None, recharge=None):
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

	def getAction(self) -> Optional[str]:
		"""Return the key of the declared move, if any."""
		if self.turninit.attack:
			return self.turninit.attack.move
		return None

	def declareAttack(self, target: str, move: str) -> None:
		"""Declare a move to be used this turn.

		Parameters
		----------
		target : str
		    The target position for the move.
		move : str
		    Key of the move in the move dex.
		"""

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
		return [self.slot1, self.slot2, self.slot3, self.slot4, self.slot5, self.slot6]

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
