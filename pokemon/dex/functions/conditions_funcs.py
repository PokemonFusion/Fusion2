"""Minimal implementations for common battle conditions."""

from __future__ import annotations

import random

from pokemon.battle.random_source import resolve_rng
from pokemon.battle.status import (
        BadPoison,
        Burn,
        Freeze,
        Paralysis,
        Poison,
        Sleep,
)


class Brn:
        """Burn status condition wrapper."""

        def __init__(self) -> None:
                self._impl = Burn()

        def onStart(self, pokemon, *_, battle=None, source=None, effect=None, previous=None, bypass_protection=False, **__):
                if not self._impl.at_apply(
                        pokemon,
                        battle,
                        source=source,
                        effect=effect,
                        previous=previous,
                        allow_self_inflict=bypass_protection,
                ):
                        return False
                self._impl.on_start(pokemon, battle, effect=effect)
                return True

        def onResidual(self, pokemon, *_, battle=None, **__):
                self._impl.on_end_turn(pokemon, battle)
                return None

        def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
                if attacker is None:
                        return atk
                return self._impl.modify_attack(attacker, atk, move=move)


class Par:
        """Paralysis condition wrapper."""

        def __init__(self) -> None:
                self._impl = Paralysis()

        def onStart(self, pokemon, *_, battle=None, source=None, effect=None, previous=None, bypass_protection=False, **__):
                if not self._impl.at_apply(
                        pokemon,
                        battle,
                        source=source,
                        effect=effect,
                        previous=previous,
                        allow_self_inflict=bypass_protection,
                ):
                        return False
                self._impl.on_start(pokemon, battle)
                return True

        def onBeforeMove(self, pokemon, *_, battle=None, **__):
                return self._impl.on_before_move(pokemon, battle, rng=resolve_rng(battle=battle))

        def onModifySpe(self, spe, *args, pokemon=None, **kwargs):
                if pokemon is None and args:
                        pokemon = args[0]
                modifier = self._impl.speed_mod(pokemon)
                return int(spe * modifier)


class Slp:
        """Sleep condition wrapper."""

        def __init__(self) -> None:
                self._impl = Sleep()

        def onStart(self, pokemon, *_, battle=None, source=None, effect=None, previous=None, bypass_protection=False, **__):
                if not self._impl.at_apply(
                        pokemon,
                        battle,
                        source=source,
                        effect=effect,
                        previous=previous,
                        allow_self_inflict=bypass_protection,
                ):
                        return False
                self._impl.on_start(pokemon, battle, effect=effect)
                return True

        def onBeforeMove(self, pokemon, *_, battle=None, **__):
                return self._impl.on_before_move(pokemon, battle)


class Frz:
        """Frozen condition wrapper."""

        def __init__(self) -> None:
                self._impl = Freeze()

        def onStart(self, pokemon, *_, battle=None, source=None, effect=None, previous=None, bypass_protection=False, **__):
                if not self._impl.at_apply(
                        pokemon,
                        battle,
                        source=source,
                        effect=effect,
                        previous=previous,
                        allow_self_inflict=bypass_protection,
                ):
                        return False
                self._impl.on_start(pokemon, battle)
                return True

        def onBeforeMove(self, pokemon, *_, battle=None, **__):
                return self._impl.on_before_move(pokemon, battle, rng=resolve_rng(battle=battle))

        def onDamagingHit(self, pokemon, damage=None, source=None, move=None, battle=None, **__):
                self._impl.on_hit_by_move(pokemon, move, battle)
                return True


class Psn:
        """Poison condition wrapper."""

        def __init__(self) -> None:
                self._impl = Poison()

        def onStart(self, pokemon, *_, battle=None, source=None, effect=None, previous=None, bypass_protection=False, **__):
                if not self._impl.at_apply(
                        pokemon,
                        battle,
                        source=source,
                        effect=effect,
                        previous=previous,
                        allow_self_inflict=bypass_protection,
                ):
                        return False
                self._impl.on_start(pokemon, battle)
                return True

        def onResidual(self, pokemon, *_, battle=None, **__):
                self._impl.on_end_turn(pokemon, battle)
                return None


class Tox:
        """Badly poisoned condition wrapper."""

        def __init__(self) -> None:
                self._impl = BadPoison()

        def onStart(self, pokemon, *_, battle=None, source=None, effect=None, previous=None, bypass_protection=False, **__):
                if not self._impl.at_apply(
                        pokemon,
                        battle,
                        source=source,
                        effect=effect,
                        previous=previous,
                        allow_self_inflict=bypass_protection,
                ):
                        return False
                self._impl.on_start(pokemon, battle)
                return True

        def onResidual(self, pokemon, *_, battle=None, **__):
                self._impl.on_end_turn(pokemon, battle)
                return None

        def onSwitchIn(self, pokemon, *_, battle=None, **__):
                self._impl.on_switch_in(pokemon, battle)
                return True

        def onSwitchOut(self, pokemon, *_, battle=None, **__):
                self._impl.on_switch_out(pokemon, battle)
                return True


class Confusion:
	"""Confusion volatile status."""

	def onBeforeMove(self, pokemon, *_, **__):
		"""Advance confusion, repairing legacy boolean or incomplete state once."""
		vol = getattr(pokemon, "volatiles", {}).get("confusion")
		if vol is None or vol is False:
			return True
		if not isinstance(vol, dict) or "turns" not in vol:
			self.onStart(pokemon)
			vol = pokemon.volatiles["confusion"]
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
		"""Initialize the duration inside the battle's existing effect state."""
		if hasattr(pokemon, "volatiles"):
			vol = pokemon.volatiles.get("confusion")
			if not isinstance(vol, dict):
				vol = pokemon.volatiles["confusion"] = {}
			vol.setdefault("turns", random.randint(2, 5))
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
	"""Finite native trapping, with source-bound item modifiers."""

	def durationCallback(self, *args, **kwargs):
		return 5

	def onEnd(self, pokemon, *args, **kwargs):
		pokemon.volatiles.pop("partiallytrapped", None)
		pokemon.trapped = False
		return True

	def onResidual(self, pokemon, *args, **kwargs):
		state = pokemon.volatiles.get("partiallytrapped")
		if not state:
			return
		battle = getattr(pokemon, "battle", None)
		source = state.get("source")
		if source is not None and battle is not None and not any(source is mon and mon.hp > 0 for part in battle.participants for mon in part.active):
			self.onEnd(pokemon)
			return
		if state.get("turns", 0) <= 0:
			self.onEnd(pokemon)
			return
		from pokemon.battle.indirect_damage import IndirectEffect, apply_indirect_damage
		damage = apply_indirect_damage(pokemon, max(1, pokemon.max_hp // state.get("divisor", 8)), battle=battle, source=source, effect=IndirectEffect("partiallytrapped", "Condition"))
		state["turns"] -= 1
		if state["turns"] <= 0:
			self.onEnd(pokemon)
		return damage

	def onStart(self, pokemon, source=None, effect=None, **kwargs):
		from pokemon.battle.effect_context import EffectContext
		item = EffectContext.key(EffectContext.item(source))
		pokemon.volatiles["partiallytrapped"] = {"turns": 7 if item == "gripclaw" else self.durationCallback(), "divisor": 6 if item == "bindingband" else 8, "source": source}
		pokemon.trapped = True
		return True

	def onTrapPokemon(self, *args, **kwargs):
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
		from pokemon.battle.effect_context import EffectContext
		if not EffectContext.item(pokemon):
			return True
		vol = getattr(pokemon, "volatiles", {}).get("choicelock")
		if not vol:
			return True
		locked = vol.get("move")
		from pokemon.battle.effect_context import EffectContext
		return EffectContext.key(move) == EffectContext.key(locked)

	def onDisableMove(self, pokemon, move_name, *_, **__):
		from pokemon.battle.effect_context import EffectContext
		if not EffectContext.item(pokemon):
			return False
		vol = getattr(pokemon, "volatiles", {}).get("choicelock")
		if not vol:
			return False
		from pokemon.battle.effect_context import EffectContext
		return EffectContext.key(move_name) != EffectContext.key(vol.get("move"))

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
		from pokemon.battle.item_effects import HeldItemRules
		return HeldItemRules.field_duration(source, "damprock")

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
		from pokemon.battle.item_effects import HeldItemRules
		return HeldItemRules.field_duration(source, "heatrock")

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


class _WeatherChip:
	"""Apply weather chip through actual types and the battle's guard events."""

	effectType = "Weather"

	def _chip(self, pokemon, weather, immune_types):
		"""Keep weather damage distinct from direct moves and retaliation hits."""
		if not pokemon or getattr(pokemon, "hp", 0) <= 0:
			return 0
		types = set(getattr(pokemon, "types", []) or [getattr(pokemon, "type1", ""), getattr(pokemon, "type2", "")])
		if not types.isdisjoint(immune_types):
			return 0
		battle = getattr(pokemon, "battle", None)
		from pokemon.battle._shared import weather_suppressed

		if weather_suppressed(battle):
			return 0
		run_event = getattr(battle, "runEvent", None)
		if callable(run_event) and run_event("Immunity", pokemon, None, self, weather) is False:
			return 0
		damage = max(1, getattr(pokemon, "max_hp", pokemon.hp) // 16)
		if callable(run_event):
			modified = run_event("Damage", pokemon, None, self, damage)
			if modified is False:
				return 0
			if isinstance(modified, (int, float)):
				damage = max(0, int(modified))
		actual = min(pokemon.hp, damage)
		pokemon.hp -= actual
		return actual


class Sandstorm(_WeatherChip):
	"""Damage-over-time sandstorm."""

	def durationCallback(self, source=None, *_, **__):
		from pokemon.battle.item_effects import HeldItemRules
		return HeldItemRules.field_duration(source, "smoothrock")

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
		return self._chip(pokemon, "sandstorm", {"Rock", "Ground", "Steel"})


class Hail(_WeatherChip):
	"""Gen 3-7 hail weather."""

	def durationCallback(self, source=None, *_, **__):
		from pokemon.battle.item_effects import HeldItemRules
		return HeldItemRules.field_duration(source, "icyrock")

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
		return self._chip(pokemon, "hail", {"Ice"})


class Snowscape:
	"""Modern snowy weather."""

	weather_id = "snowscape"

	def durationCallback(self, source=None, *_, **__):
		from pokemon.battle.item_effects import HeldItemRules
		return HeldItemRules.field_duration(source, "icyrock")

	def onFieldStart(self, field, source=None, *_, **__):
		field.pseudo_weather[self.weather_id] = {"duration": self.durationCallback(source=source)}
		return True

	def onFieldResidual(self, field, *_, **__):
		weather = field.pseudo_weather.get(self.weather_id)
		if not weather:
			return
		weather["duration"] -= 1
		if weather["duration"] <= 0:
			self.onFieldEnd(field)

	def onFieldEnd(self, field, *_, **__):
		field.pseudo_weather.pop(self.weather_id, None)
		return True

	def onModifyDef(self, defense, pokemon=None, *_, **__):
		types = set(getattr(pokemon, "types", []) or [getattr(pokemon, "type1", ""), getattr(pokemon, "type2", "")])
		if "Ice" in types:
			return int(defense * 1.5)
		return defense


class Snow(Snowscape):
	"""Canonical snow ID used by the loaded moves and Snow Warning ability."""

	weather_id = "snow"


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
	"""Dondozo receives five boosts and cannot switch while commanded."""

	def onStart(self, pokemon, *_, **__):
		setattr(pokemon, "commanded", True)
		from pokemon.utils.boosts import apply_boost

		apply_boost(pokemon, {"atk": 2, "def": 2, "spa": 2, "spd": 2, "spe": 2})
		return True

	def onDragOut(self, *_, **__):
		return False

	def onTrapPokemon(self, *_, **__):
		return True

	def onBeforeSwitchOut(self, *_, **__):
		return False


class Commanding:
	"""Tatsugiri inside Dondozo cannot act, be targeted, or switch."""

	def onBeforeTurn(self, *_, **__):
		return True

	def onBeforeMove(self, *_, **__):
		return False

	def onInvulnerability(self, *_, **__):
		return False

	def onBeforeSwitchOut(self, *_, **__):
		return False

	def onDragOut(self, *_, **__):
		return False

	def onTrapPokemon(self, *_, **__):
		return True


class Cudchew:
	"""Repeat one queued berry on expiry without replacing a new held item."""
	def onStart(self, pokemon, *args, **kwargs):
		pokemon.volatiles["cudchew"]["duration"] = 2
		return True

	def onResidual(self, pokemon, battle=None):
		state = pokemon.volatiles.get("cudchew", {})
		state["duration"] = state.get("duration", 2) - 1
		if state["duration"] <= 0 and battle:
			battle.remove_volatile(pokemon, "cudchew")

	def onEnd(self, pokemon, *args, battle=None, effect_state=None, **kwargs):
		state = effect_state or pokemon.volatiles.get("cudchew", {})
		if not battle or pokemon.hp <= 0 or not state.get("berry"):
			return
		item = battle._coerce_item(state["berry"])
		battle.singleEvent("Eat", item, {}, pokemon)
		battle.runEvent("EatItem", pokemon, None, "ability:cudchew", item)


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
	"commanding": Commanding(),
	"commanded": Commanded(),
	"cudchew": Cudchew(),
}
class Micleberry:
	"""One eligible accuracy check, bounded by the volatile's duration."""

	def onSourceAccuracy(self, accuracy, target=None, source=None, move=None):
		if not source or not move or getattr(move, "ohko", False):
			return accuracy
		source.volatiles.pop("micleberry", None)
		if isinstance(accuracy, (int, float)) and not isinstance(accuracy, bool):
			return accuracy * 1.2
		return accuracy
