"""Minimal implementations for common battle conditions."""

from __future__ import annotations

import random


from pokemon.battle.status import BurnStatus


class Brn:
        """Burn status condition."""

        def __init__(self) -> None:
                self._impl = BurnStatus()

        def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
                return self._impl.modify_attack(
                        atk,
                        attacker=attacker,
                        defender=defender,
                        move=move,
                )

        def onResidual(self, pokemon, *_, battle=None, **__):
                return self._impl.on_residual(pokemon, battle=battle)

        def onStart(self, pokemon, *_, battle=None, source=None, effect=None, previous=None, bypass_protection=False, **__):
                return self._impl.on_start(
                        pokemon,
                        battle=battle,
                        source=source,
                        effect=effect,
                        previous=previous,
                        bypass_protection=bypass_protection,
                )


class Par:
	"""Paralysis condition."""

	def onBeforeMove(self, pokemon, *_, **__):
		"""25% chance to be unable to act."""
		if random.random() < 0.25:
			if hasattr(pokemon, "tempvals"):
				pokemon.tempvals["cant_move"] = "par"
			return False
		return True

	def onModifySpe(self, spe, *_, **__):
		"""Halve the Speed stat."""
		return spe // 2

	def onStart(self, pokemon, *_, **__):
		setattr(pokemon, "status", "par")
		return True


class Slp:
	"""Sleep condition."""

	def onBeforeMove(self, pokemon, *_, **__):
		turns = getattr(pokemon, "tempvals", {}).get("slp_turns")
		if turns is None:
			return True
		if turns <= 0:
			pokemon.status = 0
			pokemon.tempvals.pop("slp_turns", None)
			return True
		pokemon.tempvals["slp_turns"] = turns - 1
		return False

	def onStart(self, pokemon, *_, **__):
		if hasattr(pokemon, "tempvals"):
			pokemon.tempvals["slp_turns"] = random.randint(1, 3)
		setattr(pokemon, "status", "slp")
		return True


class Frz:
	"""Frozen condition."""

	def onAfterMoveSecondary(self, *_, **__):
		return True

	def onBeforeMove(self, pokemon, *_, **__):
		if random.random() < 0.2:
			pokemon.status = 0
			return True
		return False

	def onDamagingHit(self, *_, **__):
		return True

	def onModifyMove(self, *_, **__):
		return True

	def onStart(self, pokemon, *_, **__):
		setattr(pokemon, "status", "frz")
		return True


class Psn:
	"""Poison condition."""

	def onResidual(self, pokemon, *_, **__):
		max_hp = getattr(pokemon, "max_hp", getattr(pokemon, "hp", 1))
		damage = max(1, max_hp // 8)
		pokemon.hp = max(0, getattr(pokemon, "hp", 0) - damage)
		return damage

	def onStart(self, pokemon, *_, **__):
		setattr(pokemon, "status", "psn")
		return True


class Tox:
	"""Badly poisoned condition."""

	def onResidual(self, pokemon, *_, **__):
		max_hp = getattr(pokemon, "max_hp", getattr(pokemon, "hp", 1))
		counter = getattr(pokemon, "toxic_counter", 1)
		damage = max(1, (max_hp * counter) // 16)
		pokemon.hp = max(0, getattr(pokemon, "hp", 0) - damage)
		pokemon.toxic_counter = counter + 1
		return damage

	def onStart(self, pokemon, *_, **__):
		setattr(pokemon, "status", "tox")
		setattr(pokemon, "toxic_counter", 1)
		return True

	def onSwitchIn(self, pokemon, *_, **__):
		pokemon.status = "psn"
		pokemon.toxic_counter = 0
		return True


class Confusion:
	"""Confusion volatile status."""

	def onBeforeMove(self, pokemon, *_, **__):
		vol = getattr(pokemon, "volatiles", {}).get("confusion")
		if not vol:
			return True
		turns = vol.get("turns", 0)
		if turns <= 0:
			self.onEnd(pokemon)
			return True
		vol["turns"] = turns - 1
		if random.random() < 0.33:
			max_hp = getattr(pokemon, "max_hp", getattr(pokemon, "hp", 1))
			dmg = max(1, max_hp // 8)
			pokemon.hp = max(0, pokemon.hp - dmg)
			return False
		return True

	def onEnd(self, pokemon, *_, **__):
		if hasattr(pokemon, "volatiles"):
			pokemon.volatiles.pop("confusion", None)
		return True

	def onStart(self, pokemon, *_, **__):
		if hasattr(pokemon, "volatiles"):
			pokemon.volatiles.setdefault("confusion", {"turns": random.randint(2, 5)})
		return True


class Flinch:
	"""Flinch prevents moving this turn."""

	def onBeforeMove(self, pokemon, *_, **__):
		return False


class Trapped:
	"""Simple trapping condition."""

	def onStart(self, pokemon, *_, **__):
		setattr(pokemon, "trapped", True)
		return True

	def onTrapPokemon(self, *_, **__):
		return True


class Trapper:
	"""Marks the Pokémon as the source of a trapping effect."""

	def onStart(self, pokemon, *_, **__):
		setattr(pokemon, "trapper", True)
		return True


class Partiallytrapped:
	"""Damage over time trapping effect."""

	def durationCallback(self, *_, **__):
		return 5

	def onEnd(self, pokemon, *_, **__):
		if hasattr(pokemon, "volatiles"):
			pokemon.volatiles.pop("partiallytrapped", None)
		setattr(pokemon, "trapped", False)
		return True

	def onResidual(self, pokemon, *_, **__):
		vol = getattr(pokemon, "volatiles", {}).get("partiallytrapped")
		if not vol:
			return
		turns = vol.get("turns", 0)
		if turns <= 0:
			self.onEnd(pokemon)
			return
		max_hp = getattr(pokemon, "max_hp", getattr(pokemon, "hp", 1))
		dmg = max(1, max_hp // 8)
		pokemon.hp = max(0, pokemon.hp - dmg)
		vol["turns"] = turns - 1
		if vol["turns"] <= 0:
			self.onEnd(pokemon)
		return dmg

	def onStart(self, pokemon, *_, **__):
		if hasattr(pokemon, "volatiles"):
			pokemon.volatiles["partiallytrapped"] = {"turns": self.durationCallback()}
		setattr(pokemon, "trapped", True)
		return True

	def onTrapPokemon(self, *_, **__):
		return True


class Lockedmove:
	"""Effect for moves like Outrage locking the user."""

	def onEnd(self, pokemon, *_, **__):
		if hasattr(pokemon, "volatiles"):
			pokemon.volatiles.pop("lockedmove", None)
		return True

	def onLockMove(self, pokemon, *_, **__):
		vol = getattr(pokemon, "volatiles", {}).get("lockedmove")
		if vol:
			return vol.get("move")

	def onResidual(self, pokemon, *_, **__):
		vol = getattr(pokemon, "volatiles", {}).get("lockedmove")
		if not vol:
			return
		vol["turns"] -= 1
		if vol["turns"] <= 0:
			self.onEnd(pokemon)

	def onRestart(self, pokemon, *_, **__):
		self.onStart(pokemon)

	def onStart(self, pokemon, move=None, *_, **__):
		if hasattr(pokemon, "volatiles") and move:
			pokemon.volatiles["lockedmove"] = {"move": move, "turns": 2}
		return True


class Twoturnmove:
	"""Charging move like Fly or Dig."""

	def onEnd(self, pokemon, *_, **__):
		if hasattr(pokemon, "volatiles"):
			pokemon.volatiles.pop("twoturnmove", None)
		return True

	def onLockMove(self, pokemon, *_, **__):
		vol = getattr(pokemon, "volatiles", {}).get("twoturnmove")
		if vol:
			return vol.get("move")

	def onMoveAborted(self, pokemon, *_, **__):
		self.onEnd(pokemon)
		return True

	def onStart(self, pokemon, move=None, *_, **__):
		if hasattr(pokemon, "volatiles") and move:
			pokemon.volatiles["twoturnmove"] = {"move": move}
		return True


class Choicelock:
	"""Represents being locked into using one move."""

	def onBeforeMove(self, pokemon, move, *_, **__):
		vol = getattr(pokemon, "volatiles", {}).get("choicelock")
		if not vol:
			return True
		locked = vol.get("move")
		return move == locked

	def onDisableMove(self, pokemon, move_name, *_, **__):
		vol = getattr(pokemon, "volatiles", {}).get("choicelock")
		if not vol:
			return False
		return move_name != vol.get("move")

	def onStart(self, pokemon, move=None, *_, **__):
		if hasattr(pokemon, "volatiles") and move:
			pokemon.volatiles["choicelock"] = {"move": move}
		return True


class Mustrecharge:
	"""Condition for moves that require a recharge turn."""

	def onBeforeMove(self, pokemon, *_, **__):
		count = getattr(pokemon, "volatiles", {}).get("mustrecharge")
		if not count:
			return True
		if count > 0:
			pokemon.volatiles["mustrecharge"] = count - 1
			return False
		pokemon.volatiles.pop("mustrecharge", None)
		return True

	def onStart(self, pokemon, *_, **__):
		if hasattr(pokemon, "volatiles"):
			pokemon.volatiles["mustrecharge"] = 1
		return True


class Futuremove:
	"""Simplified Future Sight/Doom Desire effect."""

	def onStart(self, pokemon, target=None, move=None, *_, **__):
		if hasattr(pokemon, "volatiles"):
			pokemon.volatiles["futuremove"] = {
				"move": move,
				"target": target,
				"turns": 2,
			}
		return True

	def onResidual(self, pokemon, *_, **__):
		vol = getattr(pokemon, "volatiles", {}).get("futuremove")
		if not vol:
			return
		vol["turns"] -= 1
		if vol["turns"] <= 0:
			self.onEnd(pokemon)

	def onEnd(self, pokemon, *_, **__):
		if hasattr(pokemon, "volatiles"):
			pokemon.volatiles.pop("futuremove", None)
		return True


class Healreplacement:
	"""Stores HP to heal the next Pokémon that switches in."""

	def onStart(self, pokemon, amount=0, *_, **__):
		if hasattr(pokemon, "volatiles"):
			pokemon.volatiles["healreplacement"] = {"hp": amount}
		return True

	def onSwitchIn(self, pokemon, *_, **__):
		vol = getattr(pokemon, "volatiles", {}).pop("healreplacement", None)
		if not vol:
			return 0
		heal = vol.get("hp", 0)
		max_hp = getattr(pokemon, "max_hp", getattr(pokemon, "hp", 1))
		pokemon.hp = min(max_hp, getattr(pokemon, "hp", 0) + heal)
		return heal


class Stall:
	"""Track success rate for consecutive Protect/Detect use."""

	def onStart(self, pokemon, *_, **__):
		if hasattr(pokemon, "volatiles"):
			pokemon.volatiles["stall"] = {"counter": 1}
		return True

	def onRestart(self, pokemon, *_, **__):
		vol = getattr(pokemon, "volatiles", {}).get("stall")
		if vol:
			vol["counter"] = 1
		return True

	def onStallMove(self, pokemon, *_, **__):
		vol = getattr(pokemon, "volatiles", {}).get("stall")
		if not vol:
			return 1.0
		counter = vol.get("counter", 1)
		chance = 1.0 / counter
		vol["counter"] = min(counter * 2, 729)
		return chance


class Gem:
	"""One-time 1.3x power boost for the next move."""

	def onBasePower(self, base_power, *_, **__):
		return int(base_power * 1.3)


class Raindance:
	"""Standard rain weather effect."""

	def durationCallback(self, source=None, *_, **__):
		if getattr(source, "item", "").lower() == "damprock":
			return 8
		return 5

	def onFieldStart(self, field, source=None, *_, **__):
		field.pseudo_weather["raindance"] = {"duration": self.durationCallback(source=source)}
		return True

	def onFieldResidual(self, field, *_, **__):
		weather = field.pseudo_weather.get("raindance")
		if not weather:
			return
		weather["duration"] -= 1
		if weather["duration"] <= 0:
			self.onFieldEnd(field)

	def onFieldEnd(self, field, *_, **__):
		field.pseudo_weather.pop("raindance", None)
		return True

	def onWeatherModifyDamage(self, move, *_, **__):
		mtype = getattr(move, "type", "")
		if mtype == "Water":
			return 1.5
		if mtype == "Fire":
			return 0.5
		return 1.0


class Primordialsea:
	"""Permanent heavy rain."""

	def onFieldStart(self, field, *_, **__):
		field.pseudo_weather["primordialsea"] = {}
		return True

	def onFieldResidual(self, field, *_, **__):
		# does not wear off
		return

	def onFieldEnd(self, field, *_, **__):
		field.pseudo_weather.pop("primordialsea", None)
		return True

	def onTryMove(self, move, *_, **__):
		if getattr(move, "type", "") == "Fire":
			return False
		return True

	def onWeatherModifyDamage(self, move, *_, **__):
		mtype = getattr(move, "type", "")
		if mtype == "Water":
			return 1.5
		if mtype == "Fire":
			return 0.5
		return 1.0


class Sunnyday:
	"""Standard sunny weather."""

	def durationCallback(self, source=None, *_, **__):
		if getattr(source, "item", "").lower() == "heatrock":
			return 8
		return 5

	def onFieldStart(self, field, source=None, *_, **__):
		field.pseudo_weather["sunnyday"] = {"duration": self.durationCallback(source=source)}
		return True

	def onFieldResidual(self, field, *_, **__):
		weather = field.pseudo_weather.get("sunnyday")
		if not weather:
			return
		weather["duration"] -= 1
		if weather["duration"] <= 0:
			self.onFieldEnd(field)

	def onFieldEnd(self, field, *_, **__):
		field.pseudo_weather.pop("sunnyday", None)
		return True

	def onImmunity(self, type_name, *_, **__):
		if type_name == "Freeze":
			return False
		return True

	def onWeatherModifyDamage(self, move, *_, **__):
		mtype = getattr(move, "type", "")
		if mtype == "Fire":
			return 1.5
		if mtype == "Water":
			return 0.5
		return 1.0


class Desolateland:
	"""Permanent harsh sunlight."""

	def onFieldStart(self, field, *_, **__):
		field.pseudo_weather["desolateland"] = {}
		return True

	def onFieldResidual(self, field, *_, **__):
		return

	def onFieldEnd(self, field, *_, **__):
		field.pseudo_weather.pop("desolateland", None)
		return True

	def onImmunity(self, type_name, *_, **__):
		if type_name == "Freeze":
			return False
		return True

	def onTryMove(self, move, *_, **__):
		if getattr(move, "type", "") == "Water":
			return False
		return True

	def onWeatherModifyDamage(self, move, *_, **__):
		mtype = getattr(move, "type", "")
		if mtype == "Fire":
			return 1.5
		if mtype == "Water":
			return 0.5
		return 1.0


class Sandstorm:
	"""Damage-over-time sandstorm."""

	def durationCallback(self, source=None, *_, **__):
		if getattr(source, "item", "").lower() == "smoothrock":
			return 8
		return 5

	def onFieldStart(self, field, source=None, *_, **__):
		field.pseudo_weather["sandstorm"] = {"duration": self.durationCallback(source=source)}
		return True

	def onFieldResidual(self, field, *_, **__):
		weather = field.pseudo_weather.get("sandstorm")
		if not weather:
			return
		weather["duration"] -= 1
		if weather["duration"] <= 0:
			self.onFieldEnd(field)

	def onFieldEnd(self, field, *_, **__):
		field.pseudo_weather.pop("sandstorm", None)
		return True

	def onModifySpD(self, spd, pokemon=None, *_, **__):
		types = {getattr(pokemon, "type1", ""), getattr(pokemon, "type2", "")}
		if "Rock" in types:
			return int(spd * 1.5)
		return spd

	def onWeather(self, pokemon, *_, **__):
		types = {getattr(pokemon, "type1", ""), getattr(pokemon, "type2", "")}
		if types.isdisjoint({"Rock", "Ground", "Steel"}):
			max_hp = getattr(pokemon, "max_hp", getattr(pokemon, "hp", 1))
			damage = max(1, max_hp // 16)
			pokemon.hp = max(0, pokemon.hp - damage)
			return damage
		return 0


class Hail:
	"""Gen 3-7 hail weather."""

	def durationCallback(self, source=None, *_, **__):
		if getattr(source, "item", "").lower() == "icyrock":
			return 8
		return 5

	def onFieldStart(self, field, source=None, *_, **__):
		field.pseudo_weather["hail"] = {"duration": self.durationCallback(source=source)}
		return True

	def onFieldResidual(self, field, *_, **__):
		weather = field.pseudo_weather.get("hail")
		if not weather:
			return
		weather["duration"] -= 1
		if weather["duration"] <= 0:
			self.onFieldEnd(field)

	def onFieldEnd(self, field, *_, **__):
		field.pseudo_weather.pop("hail", None)
		return True

	def onWeather(self, pokemon, *_, **__):
		types = {getattr(pokemon, "type1", ""), getattr(pokemon, "type2", "")}
		if "Ice" not in types:
			max_hp = getattr(pokemon, "max_hp", getattr(pokemon, "hp", 1))
			dmg = max(1, max_hp // 16)
			pokemon.hp = max(0, pokemon.hp - dmg)
			return dmg
		return 0


class Snowscape:
	"""Modern snowy weather."""

	def durationCallback(self, source=None, *_, **__):
		return 5

	def onFieldStart(self, field, source=None, *_, **__):
		field.pseudo_weather["snowscape"] = {"duration": self.durationCallback(source=source)}
		return True

	def onFieldResidual(self, field, *_, **__):
		weather = field.pseudo_weather.get("snowscape")
		if not weather:
			return
		weather["duration"] -= 1
		if weather["duration"] <= 0:
			self.onFieldEnd(field)

	def onFieldEnd(self, field, *_, **__):
		field.pseudo_weather.pop("snowscape", None)
		return True

	def onModifyDef(self, defense, pokemon=None, *_, **__):
		types = {getattr(pokemon, "type1", ""), getattr(pokemon, "type2", "")}
		if "Ice" in types:
			return int(defense * 1.5)
		return defense


class Deltastream:
	"""Permanent strong winds weather."""

	def onFieldStart(self, field, *_, **__):
		field.pseudo_weather["deltastream"] = {}
		return True

	def onFieldResidual(self, field, *_, **__):
		return

	def onFieldEnd(self, field, *_, **__):
		field.pseudo_weather.pop("deltastream", None)
		return True

	def onEffectiveness(self, type_mod, move_type=None, target_type=None, *_, **__):
		if move_type in {"Rock", "Ice", "Electric"} and target_type == "Flying":
			return 0
		return type_mod


class Dynamax:
	"""Simple dynamax effect."""

	def onStart(self, pokemon, *_, **__):
		setattr(pokemon, "is_dynamax", True)
		if hasattr(pokemon, "volatiles"):
			pokemon.volatiles["dynamax"] = {"turns": 3}
		return True

	def onResidual(self, pokemon, *_, **__):
		vol = getattr(pokemon, "volatiles", {}).get("dynamax")
		if not vol:
			return
		vol["turns"] -= 1
		if vol["turns"] <= 0:
			self.onEnd(pokemon)

	def onEnd(self, pokemon, *_, **__):
		setattr(pokemon, "is_dynamax", False)
		if hasattr(pokemon, "volatiles"):
			pokemon.volatiles.pop("dynamax", None)
		return True

	def onSourceModifyDamage(self, damage, *_, **__):
		return int(damage * 2)

	def onDragOut(self, *_, **__):
		return False

	def onTryAddVolatile(self, *_, **__):
		return False

	def onBeforeSwitchOut(self, *_, **__):
		return False


class Commanded:
	"""Effect applied to Tatsugiri when inside Dondozo."""

	def onStart(self, pokemon, *_, **__):
		setattr(pokemon, "commanded", True)
		return True

	def onDragOut(self, *_, **__):
		return False

	def onTrapPokemon(self, *_, **__):
		return True


class Commanding:
	"""Effect applied to Dondozo commanding Tatsugiri."""

	def onBeforeTurn(self, *_, **__):
		return True

	def onDragOut(self, *_, **__):
		return False

	def onTrapPokemon(self, *_, **__):
		return True


class Arceus:
	"""Placeholder for Arceus type change."""

	def onType(self, types, *_, **__):
		return types


class Silvally:
	"""Placeholder for Silvally type change."""

	def onType(self, types, *_, **__):
		return types


class Rolloutstorage:
	"""Track Rollout's increasing power."""

	def onBasePower(self, base_power, pokemon=None, *_, **__):
		vol = getattr(pokemon, "volatiles", {}).get("rolloutstorage")
		stage = vol.get("stage", 1) if vol else 1
		return base_power * stage


# ----------------------------------------------------------------------
# Helper mapping to access condition handlers by status name
# ----------------------------------------------------------------------

CONDITION_HANDLERS = {
	"brn": Brn(),
	"par": Par(),
	"slp": Slp(),
	"frz": Frz(),
	"psn": Psn(),
	"tox": Tox(),
	"confusion": Confusion(),
	"flinch": Flinch(),
	"trapped": Trapped(),
	"partiallytrapped": Partiallytrapped(),
	"lockedmove": Lockedmove(),
	"twoturnmove": Twoturnmove(),
	"choicelock": Choicelock(),
	"mustrecharge": Mustrecharge(),
}
