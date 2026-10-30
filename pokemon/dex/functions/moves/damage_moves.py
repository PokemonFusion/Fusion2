import copy
import re
from random import choice, random

from pokemon.data import TYPE_CHART
from pokemon.utils.boosts import STAT_KEY_MAP, apply_boost


def _effective_weight(pokemon):
	"""Read effective weight without changing owned data."""
	from pokemon.battle.effect_context import EffectContext
	return EffectContext.weight(pokemon)


def _battle_party(pokemon):
	"""Read the owning participant rather than a missing legacy party field."""
	from pokemon.battle.effect_context import EffectContext
	return EffectContext.party(pokemon)


def _battle_speed(pokemon):
	"""Include actual speed stages and current field/ability/item effects."""
	from pokemon.battle.effect_context import EffectContext
	return EffectContext.speed(pokemon)


def _species_base_attack(pokemon):
	"""Beat Up uses each eligible member's species Attack, not trained stats."""
	lookup = getattr(pokemon, "_lookup_species_entry", None)
	entry = lookup(str(getattr(pokemon, "species", ""))) if callable(lookup) else None
	stats = (getattr(entry, "raw", {}) or {}).get("baseStats", {})
	if stats:
		return int(stats.get("atk", 0))
	base = getattr(pokemon, "base_stats", None)
	return int(getattr(base, "atk", getattr(base, "attack", 0)) or 0)


def _imprison_blocks(pokemon, move, battle=None):
	"""Only a living opposing holder's shared moves are imprisoned."""
	battle = battle or getattr(pokemon, "battle", None)
	if battle is None or move is None or not hasattr(battle, "participant_for"):
		return False
	participant = battle.participant_for(pokemon)
	for other in getattr(battle, "participants", []):
		if other is participant:
			continue
		for holder in getattr(other, "active", []):
			if getattr(holder, "hp", 0) <= 0 or not getattr(holder, "volatiles", {}).get("imprison"):
				continue
			if any(_effect_id(known) == _effect_id(move) for known in getattr(holder, "moves", [])):
				return True
	return False


def _stockpile_layers(pokemon):
	"""Read the serializable layer state, retaining legacy callback adapters."""
	state = getattr(pokemon, "volatiles", {}).get("stockpile", {})
	return int(state.get("layers", getattr(pokemon, "stockpile_layers", 0)) if isinstance(state, dict)
	           else getattr(pokemon, "stockpile_layers", 0))


def _consume_stockpile(pokemon, battle=None):
	"""Remove the volatile through its tracked defensive-boost end callback."""
	battle = battle or getattr(pokemon, "battle", None)
	if battle is not None and hasattr(battle, "remove_volatile"):
		battle.remove_volatile(pokemon, "stockpile")
	else:
		Stockpile().onEnd(pokemon)
	pokemon.stockpile_layers = 0


def _swap_stored_defense_attack(pokemon):
	"""Swap the unboosted stat values actually consumed by battle damage."""
	attack, defense = _stored_battle_stat(pokemon, "atk"), _stored_battle_stat(pokemon, "def")
	if attack is not None and defense is not None:
		_set_stored_battle_stat(pokemon, "atk", defense)
		_set_stored_battle_stat(pokemon, "def", attack)


def _retaliation_hit(pokemon, battle=None, *, category=None):
	"""Load battle services only at execution, after dex initialization."""
	from pokemon.battle.retaliation import RetaliationHit

	return RetaliationHit.current(pokemon, battle, category=category)


def type_effectiveness(target, move):
	"""Return the type effectiveness multiplier for move callbacks."""
	if not move or not getattr(move, "type", None):
		return 1.0
	chart = TYPE_CHART.get(str(move.type).capitalize(), {})
	eff = 1.0
	for typ in getattr(target, "types", []) or []:
		val = chart.get(str(typ).capitalize(), 0)
		if val == 1:
			eff *= 2
		elif val == 2:
			eff *= 0.5
		elif val == 3:
			eff *= 0
	return eff


def _item_name(item):
	if item is None:
		return ""
	return getattr(item, "name", str(item))


def _effect_id(effect):
	if effect is None:
		return ""
	value = getattr(effect, "id", None) or getattr(effect, "name", None) or effect
	return str(value).replace(" ", "").lower()


def _normalize_key(value):
	return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _battle_move_from_name(name):
	try:
		from pokemon import dex
		from pokemon.battle.engine import BattleMove
	except Exception:
		return None
	entry = (getattr(dex, "MOVEDEX", {}).get(_normalize_key(name))
	         or getattr(dex, "MOVEDEX", {}).get(_normalize_key(name).capitalize()))
	if not entry:
		return None
	raw = copy.deepcopy(getattr(entry, "raw", {}) or {})
	display_name = raw.get("name") or getattr(entry, "name", name)
	return BattleMove(
		name=display_name,
		key=_normalize_key(display_name),
		power=int(raw.get("basePower", getattr(entry, "power", 0)) or 0),
		accuracy=raw.get("accuracy", getattr(entry, "accuracy", 100)),
		priority=int(raw.get("priority", 0) or 0),
		type=raw.get("type", getattr(entry, "type", None)),
		raw=raw,
		pp=raw.get("pp", getattr(entry, "pp", None)),
	)


def _execute_called_move(called_move, user, target, battle=None, *, power_multiplier=1.0):
	"""Execute a nested called move used by copy/random move callbacks."""
	if called_move is None:
		return False
	# Dex references need the full action pipeline; explicit custom executable
	# effects can also be used by reduced battle adapters without a dex entry.
	known = isinstance(called_move, str) or _battle_move_from_name(getattr(called_move, "name", "")) is not None
	if known and battle is not None and hasattr(battle, "run_called_move"):
		return battle.run_called_move(user, called_move, target, power_multiplier=power_multiplier)
	move = _battle_move_from_name(called_move) if isinstance(called_move, str) else called_move
	if move is None:
		return False
	if power_multiplier != 1.0:
		move = copy.deepcopy(move)
		power = getattr(move, "power", 0) or 0
		if power:
			move.power = int(power * power_multiplier)
		raw = dict(getattr(move, "raw", {}) or {})
		if raw.get("basePower"):
			raw["basePower"] = int(raw["basePower"] * power_multiplier)
		move.raw = raw
	name = getattr(move, "name", str(called_move))
	if user and hasattr(user, "tempvals"):
		user.tempvals["called_move"] = name
	called = None
	before_called_count = 0
	if battle is not None:
		called = getattr(battle, "called_moves", None)
		if called is None:
			called = []
			setattr(battle, "called_moves", called)
		before_called_count = len(called)
	if hasattr(move, "execute"):
		move.execute(user, target, battle)
		result = True
	else:
		on_hit = getattr(move, "onHit", None)
		result = on_hit(user, target, battle) if callable(on_hit) else False
	if called is not None and len(called) == before_called_count:
		called.append(name)
	return result


def _ability_flags(ability):
	ability_id = _effect_id(ability)
	raw = getattr(ability, "raw", None)
	if isinstance(raw, dict) and isinstance(raw.get("flags"), dict):
		return raw["flags"]
	try:
		from pokemon import dex

		entry = getattr(dex, "ABILITYDEX", {}).get(ability_id)
		raw = getattr(entry, "raw", None)
		if isinstance(raw, dict) and isinstance(raw.get("flags"), dict):
			return raw["flags"]
	except Exception:
		pass
	return {}


def _has_ability_flag(ability, flag):
	return bool(_ability_flags(ability).get(flag))


def _ability_change_blocked(target, *flags):
	if _effect_id(getattr(target, "item", None)) == "abilityshield":
		return True
	ability = getattr(target, "ability", None)
	return any(_has_ability_flag(ability, flag) for flag in flags)


def _boost_value(boosts, stat):
	aliases = {
		"atk": ("atk", "attack"),
		"def": ("def", "defense"),
		"spa": ("spa", "special_attack"),
		"spd": ("spd", "special_defense"),
		"spe": ("spe", "speed"),
	}.get(stat, (stat,))
	for key in aliases:
		if key in boosts:
			return boosts.get(key, 0)
	return 0


def _set_boost_value(boosts, stat, value):
	aliases = {
		"atk": ("atk", "attack"),
		"def": ("def", "defense"),
		"spa": ("spa", "special_attack"),
		"spd": ("spd", "special_defense"),
		"spe": ("spe", "speed"),
	}.get(stat, (stat,))
	for key in aliases:
		if key in boosts:
			boosts[key] = value
			return
	boosts[aliases[0]] = value


def _is_berry(item):
	return "berry" in _item_name(item).lower()


def _stored_battle_stat(pokemon, stat):
	"""Read an unboosted stat, including earlier split/swap state."""
	from pokemon.battle.utils import _safe_get_stats

	name = STAT_KEY_MAP.get(stat, stat)
	overrides = (getattr(pokemon, "tempvals", {}) or {}).get("stat_overrides", {})
	return overrides.get(name, _safe_get_stats(pokemon).get(name))


def _set_stored_battle_stat(pokemon, stat, value):
	"""Persist a temporary stat in existing battle state until that holder leaves."""
	state = getattr(pokemon, "tempvals", None)
	if state is None:
		state = pokemon.tempvals = {}
	state.setdefault("stat_overrides", {})[STAT_KEY_MAP.get(stat, stat)] = int(value)


def _iter_other_active_pokemon(battle, user):
	if not battle:
		return []
	active = []
	for participant in getattr(battle, "participants", []) or []:
		for pokemon in getattr(participant, "active", []) or []:
			if pokemon is None or pokemon is user or getattr(pokemon, "hp", 0) <= 0:
				continue
			active.append(pokemon)
	return active


def _iter_opposing_active_pokemon(battle, user):
	if not battle:
		return []
	user_participant = None
	if hasattr(battle, "participant_for"):
		try:
			user_participant = battle.participant_for(user)
		except Exception:
			user_participant = None
	foes = []
	for participant in getattr(battle, "participants", []) or []:
		if participant is user_participant:
			continue
		if (
			user_participant is not None
			and getattr(user_participant, "team", None) is not None
			and getattr(participant, "team", None) == getattr(user_participant, "team", None)
		):
			continue
		for pokemon in getattr(participant, "active", []) or []:
			if pokemon is None or getattr(pokemon, "hp", 0) <= 0:
				continue
			foes.append(pokemon)
	return foes


class Acrobatics:
	def basePowerCallback(self, user, target, move):
		"""Double power if the user holds no item."""
		item = getattr(user, "item", None) or getattr(user, "held_item", None)
		if not item:
			return (getattr(move, "power", 0) or 0) * 2
		return getattr(move, "power", 0)


class Anchorshot:
	def onHit(self, user, target, battle):
		"""Trap the target and prevent switching."""
		if hasattr(target, "volatiles"):
			target.volatiles["trapped"] = True
		return True


class Assurance:
	def basePowerCallback(self, user, target, move):
		"""Double power if the target already took damage this turn."""
		took_damage = getattr(target, "tempvals", {}).get("took_damage")
		base = getattr(move, "power", 0) or 0
		if took_damage:
			return base * 2
		return base


class Aurawheel:
	def onModifyType(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		if not move or not user:
			return
		species = getattr(getattr(user, "species", None), "name", "").lower()
		if "hangry" in species:
			move.type = "Dark"
		else:
			move.type = "Electric"

	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		species = getattr(getattr(user, "species", None), "name", "").lower()
		if "morpeko" not in species:
			return False
		return True


class Auroraveil:
	def durationCallback(self, *args, **kwargs):
		from pokemon.battle.item_effects import HeldItemRules
		source = args[1] if len(args) > 1 else kwargs.get("source")
		return HeldItemRules.field_duration(source, "lightclay")

	def onAnyModifyDamage(self, *args, **kwargs):
		damage = args[0] if args else kwargs.get("damage")
		source = args[1] if len(args) > 1 else kwargs.get("source")
		target = args[2] if len(args) > 2 else kwargs.get("target")
		move = args[3] if len(args) > 3 else kwargs.get("move")
		if not target or not source or not move or move.category == "Status":
			return damage
		if getattr(move, "infiltrates", False):
			return damage
		side = getattr(target, "side", None)
		if side and getattr(side, "screens", {}).get("auroraveil"):
			mult = 0.5
			if len(getattr(side, "active", [])) > 1:
				mult = 2 / 3
			return int(damage * mult)
		return damage

	def onSideEnd(self, *args, **kwargs):
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "screens"):
			side.screens.pop("auroraveil", None)
		return True

	def onSideStart(self, *args, **kwargs):
		"""Activate the Aurora Veil screen on the side."""
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "screens"):
			side.screens["auroraveil"] = True
		return True

	def onTry(self, *args, **kwargs):
		battle = kwargs.get("battle") if kwargs else None
		if len(args) > 3:
			battle = args[3] or battle
		field = getattr(battle, "field", None)
		weather = None
		if field and hasattr(field, "weather"):
			weather = field.weather
		elif battle and hasattr(battle, "weather"):
			weather = battle.weather
		elif battle and hasattr(battle, "state"):
			weather = getattr(battle.state, "roomweather", None)
		if str(weather).lower() in ("hail", "snow"):
			return True
		return False


class Autotomize:
	def onHit(self, user, target, battle):
		"""Reduce the user's weight and mark Autotomize as active.

		The actual Speed boost for Autotomize is handled by the move's raw
		data in :mod:`pokemon.battle.engine`.  If we were to apply the boost
		here as well it would be doubled, resulting in a +4 Speed increase
		instead of the expected +2.  We therefore only track the move's
		weight-reduction side effect in this handler and allow the default
		engine logic to apply the stat boosts once.
		"""
		if hasattr(user, "tempvals"):
			user.tempvals["autotomize"] = True
		state = getattr(user, "volatiles", {}).get("autotomize")
		if not isinstance(state, dict):
			state = user.volatiles["autotomize"] = {"layers": 0}
		state["layers"] = int(state.get("layers", 0)) + 1
		return True

	def onTryHit(self, user, *args, **kwargs):
		"""Fail if the user's Speed is already maximized."""
		boosts = getattr(user, "boosts", {})
		if _boost_value(boosts, "spe") >= 6:
			return False
		return True


class Avalanche:
	def basePowerCallback(self, user, target, move):
		"""Double power if the user was damaged earlier this turn."""
		took_damage = getattr(user, "tempvals", {}).get("took_damage")
		base = getattr(move, "power", 0) or 0
		if took_damage:
			return base * 2
		return base


class Axekick:
	def onMoveFail(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		max_hp = getattr(user, "max_hp", 0)
		recoil = max_hp // 2
		user.hp = max(0, getattr(user, "hp", 0) - recoil)
		return True


class Banefulbunker:
	def onHit(self, user, target, battle):
		"""Protect the user and poison contact attackers."""
		user.volatiles["protect"] = True
		user.volatiles["banefulbunker"] = True
		return True

	def onPrepareHit(self, *args, **kwargs):
		return True

	def onStart(self, *args, **kwargs):
		return True

	def onTryHit(self, target, source, move):
		"""Block the incoming move and poison contact attackers."""
		flags = getattr(move, "flags", {}) if move else {}
		if flags.get("contact") and hasattr(source, "setStatus"):
			source.setStatus("psn")
		return False


class Barbbarrage:
	def onBasePower(self, *args, **kwargs):
		"""Double power if the target is poisoned."""
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		if target and getattr(target, "status", None) in {"psn", "tox"}:
			return power * 2
		return power


class Batonpass:
	def onHit(self, user, target, battle):
		"""Flag that the user will switch out and pass boosts."""
		if hasattr(user, "tempvals"):
			user.tempvals["baton_pass"] = True
		return True


class Beakblast:
	def onAfterMove(self, *args, **kwargs):
		return True

	def onHit(self, user, target, battle):
		"""Burn the target on contact."""
		if hasattr(target, "setStatus"):
			target.setStatus(
				"brn",
				source=user,
				battle=battle,
				effect="move:beakblast",
			)
		return True

	def onStart(self, user, target, battle):
		if hasattr(user, "tempvals"):
			user.tempvals["beakblast"] = True
		return True

	def priorityChargeCallback(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["beakblast_charge"] = True
		return -3


class Beatup:
	def basePowerCallback(self, user, target, move):
		"""Calculate power based on each healthy ally's base Attack."""
		allies = getattr(move, "allies", None)
		if allies is None:
			party = _battle_party(user)
			allies = [ally for ally in party if getattr(ally, "hp", 0) > 0 and not getattr(ally, "status", 0)]
			move.allies = allies
			if isinstance(getattr(move, "raw", None), dict):
				move.raw["multihit"] = len(allies)
			current = allies[0] if allies else user
			base_atk = _species_base_attack(current)
			return 5 + (base_atk // 10)
		if not allies:
			allies = [user]
		current = allies.pop(0)
		base_atk = _species_base_attack(current)
		return 5 + (base_atk // 10)

	def onModifyMove(self, move, user):
		party = _battle_party(user)
		allies = [ally for ally in party if getattr(ally, "hp", 0) > 0 and not getattr(ally, "status", 0)]
		move.allies = allies
		if isinstance(getattr(move, "raw", None), dict):
			move.raw["multihit"] = len(allies)


class Belch:
	def onDisableMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		consumed = getattr(user, "ate_berry", False) or getattr(user, "consumed_berry", False)
		return not consumed


class Bellydrum:
	def onHit(self, user, target, battle):
		"""Halve HP and maximize Attack."""
		if getattr(user, "hp", 0) <= getattr(user, "max_hp", 0) // 2:
			return False
		user.hp -= getattr(user, "max_hp", 0) // 2
		user.hp = max(user.hp, 1)
		user.boosts["atk"] = 6
		return True


class Bestow:
	def onHit(self, user, target, battle):
		"""Give the user's held item to the target if possible."""
		if battle and hasattr(battle, "move_item"):
			return bool(battle.move_item(user, target, effect="move:bestow"))
		return False


class Bide:
	"""Keep storage and release in a checkpoint-safe per-holder state."""
	def beforeMoveCallback(self, user=None, target=None, move=None, battle=None):
		from pokemon.battle.delayed_moves import BideState
		return BideState.before_move(user, move, battle) if user and battle else False
	def onBeforeMove(self, *args, **kwargs):
		return True
	def onStart(self, pokemon=None, source=None, effect=None, battle=None):
		if pokemon:
			pokemon.volatiles["bide"] = {"turns": 1, "damage": 0}
		return True
	def onLockMove(self, *args, **kwargs):
		return "bide"
	def onDamage(self, damage, *args, **kwargs):
		return damage
	def onEnd(self, pokemon=None, *args, **kwargs):
		if pokemon:
			pokemon.volatiles.pop("bide", None)
		return True
	def onMoveAborted(self, pokemon=None, *args, **kwargs):
		return self.onEnd(pokemon)


class Bleakwindstorm:
	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		battle = kwargs.get("battle")
		if len(args) > 2:
			battle = args[2] or battle
		field = getattr(battle, "field", None)
		weather = getattr(field, "weather", getattr(battle, "weather", None))
		if str(weather).lower() in ("rain", "raindance") and hasattr(move, "accuracy"):
			move.accuracy = True


class Blizzard:
	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		battle = kwargs.get("battle")
		if len(args) > 2:
			battle = args[2] or battle
		field = getattr(battle, "field", None)
		weather = getattr(field, "weather", getattr(battle, "weather", None))
		if str(weather).lower() in ("hail", "snow") and hasattr(move, "accuracy"):
			move.accuracy = True


class Block:
	def onHit(self, user, target, battle):
		"""Prevent the target from switching out."""
		if hasattr(target, "volatiles"):
			target.volatiles["trapped"] = True
		return True


class Boltbeak:
	def basePowerCallback(self, user, target, move):
		"""Double power if the target has not moved yet this turn."""
		moved = getattr(target, "tempvals", {}).get("moved")
		base = getattr(move, "power", 0) or 0
		if not moved:
			return base * 2
		return base


class Bounce:
	def onInvulnerability(self, *args, **kwargs):
		move = args[2] if len(args) > 2 else kwargs.get("move")
		if not move:
			return True
		unblock = {"gust", "twister", "thunder", "hurricane", "skyuppercut"}
		mname = getattr(move, "name", "").replace(" ", "").lower()
		return mname not in unblock

	def onSourceBasePower(self, *args, **kwargs):
		power = args[0] if args else kwargs.get("power")
		return power

	def onTryMove(self, *args, **kwargs):
		"""Handle the two-turn Bounce behaviour."""
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		vol = getattr(user, "volatiles", {})
		if vol.get("bounce"):
			vol.pop("bounce", None)
			user.volatiles = vol
			return True
		vol["bounce"] = True
		user.volatiles = vol
		return False


class Brickbreak:
	def onTryHit(self, user, target, move):
		"""Shatter opposing Reflect, Light Screen, or Aurora Veil."""
		side = getattr(target, "side", None)
		if side and hasattr(side, "screens"):
			for screen in ("reflect", "lightscreen", "auroraveil"):
				side.screens.pop(screen, None)
		return True


class Brine:
	def onBasePower(self, *args, **kwargs):
		"""Double power if the target is at or below half HP."""
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		if target:
			cur_hp = getattr(target, "hp", 0)
			max_hp = getattr(target, "max_hp", cur_hp or 1)
			if cur_hp * 2 <= max_hp:
				return power * 2
		return power


class Bugbite:
	def onHit(self, user, target, battle):
		"""Consume the target's berry if it has one."""
		if battle and hasattr(battle, "eat_berry"):
			battle.eat_berry(user, target, effect="move:bugbite")
		return True


class Burningbulwark:
	def onHit(self, user, target, battle):
		"""Burn contact attackers."""
		user.volatiles["protect"] = True
		user.volatiles["burningbulwark"] = True
		return True

	def onPrepareHit(self, *args, **kwargs):
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["protect"] = True
		return True

	def onTryHit(self, target, source, move):
		"""Block the incoming move and burn contact attackers."""
		flags = getattr(move, "flags", {}) if move else {}
		if flags.get("contact") and hasattr(source, "setStatus"):
			battle = getattr(target, "battle", None)
			source.setStatus(
				"brn",
				source=target,
				battle=battle,
				effect="move:burningbulwark",
			)
		return False


class Burningjealousy:
	def onHit(self, user, target, battle):
		"""Burn the target if it has any stat boosts."""
		boosts = getattr(target, "boosts", {})
		if any(v > 0 for v in boosts.values()):
			if hasattr(target, "setStatus"):
				target.setStatus(
					"brn",
					source=user,
					battle=battle,
					effect="move:burningjealousy",
				)
		return True


class Burnup:
	def onHit(self, user, target, battle):
		"""Remove the Fire type from the user."""
		types = list(getattr(user, "types", []))
		user.types = [t for t in types if t.lower() != "fire"]
		return True

	def onTryMove(self, user, target, battle):
		"""Fail if the user is not Fire type."""
		types = getattr(user, "types", [])
		if not any(t.lower() == "fire" for t in types):
			return False
		return True


class Camouflage:
	def onHit(self, user, target, battle):
		"""Change the user's type to Normal."""
		user.types = ["Normal"]
		return True


class Captivate:
	def onTryImmunity(self, *args, **kwargs):
		target = args[0] if args else kwargs.get("target")
		source = args[1] if len(args) > 1 else kwargs.get("source")
		tg = getattr(target, "gender", "N") if target else "N"
		sg = getattr(source, "gender", "N") if source else "N"
		if tg == "N" or sg == "N" or tg == sg:
			return False
		return True


class Ceaselessedge:
	def onAfterHit(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else kwargs.get("target")
		side = getattr(target, "side", None)
		if side and hasattr(side, "hazards"):
			side.hazards["spikes"] = max(1, side.hazards.get("spikes", 0) + 1)
		return True

	def onAfterSubDamage(self, *args, **kwargs):
		return self.onAfterHit(*args, **kwargs)


class Celebrate:
	def onTryHit(self, user, *args, **kwargs):
		"""Always succeeds and shows a celebratory message."""
		return True


class Charge:
	def onAfterMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user and hasattr(user, "volatiles"):
			if "charge" in user.volatiles:
				user.volatiles["charge"] -= 1

	def onBasePower(self, *args, **kwargs):
		user = args[0] if args else None
		move = args[2] if len(args) > 2 else None
		power = getattr(move, "power", 0) if move else 0
		if move and getattr(move, "type", "").lower() == "electric":
			return power * 2
		return power

	def onEnd(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user and hasattr(user, "volatiles"):
			user.volatiles.pop("charge", None)
		return True

	def onMoveAborted(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles.pop("charge", None)
		return True

	def onRestart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["charge"] = 2
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["charge"] = 2
		return True


class Clangoroussoul:
	def onHit(self, user, target, battle):
		"""Lose 1/3 of the user's maximum HP.

		Stat boosts are handled by the move's raw ``boosts`` data; this
		method only applies the HP deduction after those boosts have been
		applied.
		"""
		max_hp = getattr(user, "max_hp", 0)
		if getattr(user, "hp", 0) <= max_hp // 3:
			return False
		user.hp -= max_hp // 3
		return True

	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		max_hp = getattr(user, "max_hp", 0)
		if max_hp <= 1:
			return False
		if getattr(user, "hp", 0) <= max_hp * 33 // 100:
			return False
		return True

	def onTryHit(self, user, *args, **kwargs):
		"""Allow the hit once :py:meth:`onTry` has validated available HP."""
		return True


class Clearsmog:
	def onHit(self, user, target, battle):
		"""Reset the target's stat changes."""
		if hasattr(target, "boosts"):
			for stat in target.boosts:
				target.boosts[stat] = 0
		return True


class Collisioncourse:
	def onBasePower(self, *args, **kwargs):
		"""Boost power if the move is super effective."""
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		if target and move and type_effectiveness(target, move) > 1:
			return int(power * 4 / 3)
		return power


class Comeuppance:
	def damageCallback(self, *args, **kwargs):
		user = args[0] if args else None
		hit = _retaliation_hit(user, kwargs.get("battle"))
		return int(hit.damage * 1.5) if hit else 0

	def onModifyTarget(self, *args, **kwargs):
		user = args[0] if args else None
		last = getattr(user, "tempvals", {}).get("last_damaged_by") if user else None
		if isinstance(last, dict):
			return last.get("source")

	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		return _retaliation_hit(user, kwargs.get("battle")) is not None


class Conversion:
	def onHit(self, user, target, battle):
		"""Change the user's type to match its first move."""
		moves = getattr(user, "moves", [])
		if not moves:
			return False
		first = moves[0]
		mtype = getattr(first, "type", None)
		if not mtype:
			resolved = _battle_move_from_name(getattr(first, "name", first))
			mtype = getattr(resolved, "type", None)
		if not mtype:
			return False
		if mtype in getattr(user, "types", []):
			return False
		if hasattr(user, "setType"):
			return bool(user.setType(mtype))
		user.types = [mtype]
		return True


class Conversion2:
	def onHit(self, user, target, battle):
		"""Choose a new type resisting or immune to the target's last move."""
		last_move = getattr(target, "last_move", None)
		if not last_move:
			return False
		attack_type = getattr(last_move, "type", None)
		if not attack_type:
			resolved = _battle_move_from_name(getattr(last_move, "name", last_move))
			attack_type = getattr(resolved, "type", None)
		chart = TYPE_CHART.get(attack_type, {})
		possible = [name for name in TYPE_CHART if name not in getattr(user, "types", [])
				and name not in {"Stellar", "Typeless", "???"} and chart.get(name) in {2, 3}]
		if not possible:
			return False
		rng = getattr(battle, "rng", None)
		new_type = rng.choice(possible) if rng is not None else choice(possible)
		if hasattr(user, "setType"):
			return bool(user.setType(new_type))
		user.types = [new_type]
		return True


class Copycat:
	def onHit(self, user, target, battle):
		"""Use the last move that was successfully used in battle."""
		move = getattr(battle, "last_move", None)
		if not move or _normalize_key(getattr(move, "name", "")) == "copycat":
			return False
		return bool(_execute_called_move(move, user, target, battle))


class Coreenforcer:
	def onAfterSubDamage(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else kwargs.get("target")
		if target and getattr(target, "moved_this_turn", False):
			target.ability_suppressed = True
		return True

	def onHit(self, user, target, battle):
		"""Suppress the target's ability until it switches out."""
		if hasattr(target, "__dict__"):
			target.ability_suppressed = True
		return True


class Corrosivegas:
	def onHit(self, user, target, battle):
		"""Remove held items from the other active Pokemon on the field."""
		removed_any = False
		targets = _iter_other_active_pokemon(battle, user) or ([target] if target else [])
		for mon in targets:
			item = getattr(mon, "item", None) or getattr(mon, "held_item", None)
			if not item:
				continue
			if battle and hasattr(battle, "remove_item"):
				removed_any = bool(
					battle.remove_item(mon, source=user, effect="move:corrosivegas")
				) or removed_any
			elif hasattr(mon, "set_item"):
				mon.set_item(None)
				removed_any = True
			else:
				setattr(mon, "item", None)
				setattr(mon, "held_item", None)
				removed_any = True
		return removed_any


class Counter:
	def beforeTurnCallback(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["counter"] = {"slot": None, "damage": 0}
		return True

	def damageCallback(self, *args, **kwargs):
		user = args[0] if args else None
		hit = _retaliation_hit(user, kwargs.get("battle"), category="Physical")
		return hit.damage * 2 if hit else 0

	def onDamagingHit(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else None
		source = args[2] if len(args) > 2 else None
		move = args[3] if len(args) > 3 else None
		if target and source and getattr(move, "category", "") == "Physical":
			vol = getattr(target, "volatiles", {}).get("counter")
			if vol is not None:
				vol["slot"] = source
				vol["damage"] = getattr(move, "damage", 0) * 2

	def onRedirectTarget(self, *args, **kwargs):
		user = args[0] if args else None
		vol = getattr(user, "volatiles", {}).get("counter") if user else None
		if vol:
			return vol.get("slot")

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "tempvals"):
			user.tempvals["counter_damage"] = 0
		return True

	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		return _retaliation_hit(user, kwargs.get("battle"), category="Physical") is not None


class Courtchange:
	def onHit(self, user, target, battle):
		"""Swap eligible canonical side states and their legacy views together."""
		parts = getattr(battle, "participants", None)
		sides = [part.side for part in parts] if parts else getattr(battle, "sides", [])
		if len(sides) != 2:
			return False
		side1, side2 = sides
		allowed = {"mist", "lightscreen", "reflect", "spikes", "safeguard", "tailwind", "toxicspikes",
			"stealthrock", "waterpledge", "firepledge", "grasspledge", "stickyweb", "auroraveil",
			"luckychant", "gmaxsteelsurge", "gmaxcannonade", "gmaxvinelash", "gmaxwildfire", "gmaxvolcalith"}
		missing, changed = object(), False
		for attr in ("conditions", "hazards", "screens"):
			left, right = getattr(side1, attr, {}), getattr(side2, attr, {})
			aliases = getattr(side1, "HAZARD_TO_CONDITION", {}) if attr == "hazards" else {}
			for name in set(left) | set(right):
				if aliases.get(name, name) not in allowed:
					continue
				before_left, before_right = left.pop(name, missing), right.pop(name, missing)
				if before_right is not missing:
					left[name] = before_right
				if before_left is not missing:
					right[name] = before_left
				changed = True
		for side in sides:
			for state in getattr(side, "conditions", {}).values():
				if isinstance(state, dict) and "target" in state:
					state["target"] = side
			if hasattr(side, "sync_hazard_conditions"):
				side.sync_hazard_conditions()
		return changed

	def onHitField(self, user, battle):
		return self.onHit(user, None, battle)


class Covet:
	def onAfterHit(self, *args, **kwargs):
		user = args[0] if args else None
		target = args[1] if len(args) > 1 else None
		battle = args[2] if len(args) > 2 else kwargs.get("battle") or getattr(user, "battle", None)
		if not user or not target:
			return True
		if battle and hasattr(battle, "steal_item"):
			battle.steal_item(user, target, effect="move:covet")
		return True


class Craftyshield:
	def onSideStart(self, *args, **kwargs):
		"""Protect the side from status moves this turn."""
		side = args[0] if args else kwargs.get("side")
		if side:
			vol = getattr(side, "volatiles", {})
			vol["craftyshield"] = True
			side.volatiles = vol
		return True

	def onTry(self, *args, **kwargs):
		battle = kwargs.get("battle") if kwargs else None
		if len(args) > 3:
			battle = args[3] or battle
		queue = getattr(battle, "queue", None)
		if queue and hasattr(queue, "willAct"):
			try:
				return bool(queue.willAct())
			except Exception:
				return True
		return True

	def onTryHit(self, target, source, move):
		"""Block status moves aimed at the user's side."""
		raw = getattr(move, "raw", {}) or {}
		if getattr(move, "category", "") == "Status" and raw.get("target", getattr(move, "target", "")) not in {"self", "all"}:
			return False
		return True


class Crushgrip:
	def basePowerCallback(self, user, target, move):
		"""Scale power based on the target's remaining HP."""
		cur_hp = getattr(target, "hp", 0)
		max_hp = getattr(target, "max_hp", cur_hp or 1)
		ratio = cur_hp / max_hp if max_hp else 0
		power = int(120 * ratio) + 1
		return max(1, power)


class Curse:
	def onHit(self, user, target, battle):
		"""Apply Curse differently for Ghost and non-Ghost users."""
		types = [t.lower() for t in getattr(user, "types", [])]
		if "ghost" in types:
			if getattr(user, "hp", 0) <= getattr(user, "max_hp", 0) // 2:
				return False
			user.hp -= getattr(user, "max_hp", 0) // 2
			user.hp = max(user.hp, 1)
			if hasattr(target, "volatiles"):
				target.volatiles["cursed"] = True
		else:
			apply_boost(user, {"atk": 1, "def": 1, "spe": -1})
		return True

	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		types = [t.lower() for t in getattr(user, "types", [])]
		if "ghost" in types:
			if move:
				move.target = "normal"
		else:
			if move:
				move.target = "self"

	def onResidual(self, *args, **kwargs):
		target = args[0] if args else None
		if not target:
			return False
		damage = getattr(target, "max_hp", 0) // 4
		target.hp = max(0, getattr(target, "hp", 0) - damage)
		return True

	def onStart(self, *args, **kwargs):
		return True

	def onTryHit(self, user, target, move):
		"""Fail if a Ghost already cursed the target."""
		if "ghost" in [t.lower() for t in getattr(user, "types", [])]:
			if getattr(target, "volatiles", {}).get("cursed"):
				return False
		return True


class Darkvoid:
	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		move = args[2] if len(args) > 2 else kwargs.get("move")
		species = getattr(getattr(user, "species", None), "name", "").lower()
		if "darkrai" in species or getattr(move, "has_bounced", False):
			return True
		return False


class Defog:
	def onHit(self, user, target, battle):
		"""Lower the target's evasion by one stage."""
		apply_boost(target, {"evasion": -1})
		sides = [part.side for part in getattr(battle, "participants", [])] or getattr(battle, "sides", [])
		for side in sides or []:
			if not side:
				continue
			if hasattr(side, "clear_hazard"):
				for hazard in ("spikes", "stealthrock", "toxicspikes", "stickyweb"):
					side.clear_hazard(hazard)
			else:
				for hazard in ("spikes", "stealthrock", "toxicspikes", "stickyweb"):
					getattr(side, "hazards", {}).pop(hazard, None)
					getattr(side, "conditions", {}).pop(hazard, None)
		target_side = getattr(target, "side", None)
		for name in ("reflect", "lightscreen", "auroraveil", "safeguard", "mist"):
			if hasattr(target_side, "remove_side_condition"):
				target_side.remove_side_condition(name)
			else:
				getattr(target_side, "conditions", {}).pop(name, None)
		if battle is not None and hasattr(battle, "clearTerrain"):
			battle.clearTerrain()
		return True


class Destinybond:
	def onBeforeMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user and hasattr(user, "volatiles"):
			user.volatiles["destinybond"] = True
		return True

	def onFaint(self, *args, **kwargs):
		user = args[0] if args else None
		last = getattr(user, "tempvals", {}).get("last_damaged_by") if user else None
		foe = last.get("source") if isinstance(last, dict) else None
		if foe and getattr(user, "volatiles", {}).get("destinybond"):
			foe.hp = 0
		if user and hasattr(user, "volatiles"):
			user.volatiles.pop("destinybond", None)
		return True

	def onMoveAborted(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles.pop("destinybond", None)
		return True

	def onPrepareHit(self, *args, **kwargs):
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["destinybond"] = True
		return True


class Detect:
	def onHit(self, user, target, battle):
		"""Grant the user protection from moves this turn."""
		if hasattr(user, "volatiles"):
			user.volatiles["protect"] = True
		return True

	def onPrepareHit(self, *args, **kwargs):
		return True


class Dig:
	def onImmunity(self, *args, **kwargs):
		return True

	def onInvulnerability(self, *args, **kwargs):
		move = args[2] if len(args) > 2 else kwargs.get("move")
		if not move:
			return True
		unblock = {"earthquake", "fissure", "magnitude"}
		mname = getattr(move, "name", "").replace(" ", "").lower()
		return mname not in unblock

	def onSourceModifyDamage(self, *args, **kwargs):
		damage = args[0] if args else kwargs.get("damage")
		move = args[3] if len(args) > 3 else kwargs.get("move")
		if move and getattr(move, "name", "").replace(" ", "").lower() in {"earthquake", "magnitude"}:
			return int(damage * 2)
		return damage

	def onTryMove(self, *args, **kwargs):
		"""Handle Dig as a two-turn move."""
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		vol = getattr(user, "volatiles", {})
		if vol.get("dig"):
			vol.pop("dig", None)
			user.volatiles = vol
			return True
		vol["dig"] = True
		user.volatiles = vol
		return False


class Direclaw:
	def onHit(self, user, target, battle):
		"""May inflict poison, paralysis, or sleep."""
		if getattr(target, "status", None):
			return True
		status = choice(["psn", "par", "slp"])
		if hasattr(target, "setStatus"):
			target.setStatus(status)
		return True


class Disable:
	def onBeforeMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		move = getattr(user, "volatiles", {}).get("disable") if user else None
		if move and getattr(move, "id", "") == getattr(args[1] if len(args) > 1 else kwargs.get("move"), "id", ""):
			return False
		return True

	def onDisableMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		disabled = getattr(user, "volatiles", {}).get("disable") if user else None
		return disabled.get("move") if isinstance(disabled, dict) else disabled

	def onResidual(self, pokemon, battle=None):
		state = getattr(pokemon, "volatiles", {}).get("disable")
		if isinstance(state, dict) and isinstance(state.get("duration"), int):
			state["duration"] -= 1
			if state["duration"] <= 0 and battle:
				battle.remove_volatile(pokemon, "disable")

	def onEnd(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user and hasattr(user, "volatiles"):
			user.volatiles.pop("disable", None)
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		target = args[1] if len(args) > 1 else None
		move = getattr(target, "last_move", None)
		if target and hasattr(target, "volatiles"):
			target.volatiles["disable"] = move
		return True

	def onTryHit(self, target, source, move):
		"""Fail if the target has no move to disable."""
		last = getattr(target, "last_move", None)
		if (
			not last
			or getattr(last, "isZ", False)
			or getattr(last, "isMax", False)
			or getattr(last, "id", "") == "struggle"
		):
			return False
		return True


class Dive:
	def onImmunity(self, *args, **kwargs):
		return True

	def onInvulnerability(self, *args, **kwargs):
		move = args[2] if len(args) > 2 else kwargs.get("move")
		if not move:
			return True
		unblock = {"surf", "whirlpool"}
		mname = getattr(move, "name", "").replace(" ", "").lower()
		return mname not in unblock

	def onSourceModifyDamage(self, *args, **kwargs):
		damage = args[0] if args else kwargs.get("damage")
		move = args[3] if len(args) > 3 else kwargs.get("move")
		if move and getattr(move, "name", "").replace(" ", "").lower() in {"surf", "whirlpool"}:
			return int(damage * 2)
		return damage

	def onTryMove(self, *args, **kwargs):
		"""Handle Dive as a two-turn move."""
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		vol = getattr(user, "volatiles", {})
		if vol.get("dive"):
			vol.pop("dive", None)
			user.volatiles = vol
			return True
		vol["dive"] = True
		user.volatiles = vol
		return False


class Doodle:
	def onHit(self, user, target, battle):
		"""Copy the target's ability onto the user."""
		ability = getattr(target, "ability", None)
		if not ability:
			return False
		participant = battle.participant_for(user) if battle and hasattr(battle, "participant_for") else None
		for ally in getattr(participant, "active", None) or [user]:
			if getattr(ally, "hp", 0) > 0:
				setattr(ally, "ability", ability)
		return True


class Doomdesire:
	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		target = args[1] if len(args) > 1 else None
		side = getattr(target, "side", None)
		if not side:
			return False
		return True


class Doubleshock:
	def onHit(self, user, target, battle):
		"""Lose the Electric type after attacking."""
		if hasattr(user, "types"):
			user.types = [t for t in user.types if t.lower() != "electric"]
		return True

	def onTryMove(self, *args, **kwargs):
		"""Fail if the user is not Electric type."""
		user = args[0] if args else kwargs.get("user")
		types = getattr(user, "types", []) if user else []
		return any(t.lower() == "electric" for t in types)


class Dragoncheer:
	def onModifyCritRatio(self, *args, **kwargs):
		ratio = args[0] if args else kwargs.get("ratio", 0)
		return ratio + 1

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["dragoncheer"] = True
		return True


class Dragonenergy:
	def basePowerCallback(self, user, target, move):
		"""Scale power based on the user's remaining HP."""
		cur_hp = getattr(user, "hp", 0)
		max_hp = getattr(user, "max_hp", cur_hp or 1)
		ratio = cur_hp / max_hp if max_hp else 0
		power = int(150 * ratio)
		return max(1, power)


class Dreameater:
	def onTryImmunity(self, *args, **kwargs):
		target = args[0] if args else kwargs.get("target")
		if getattr(target, "status", None) == "slp":
			return True
		return False


class Echoedvoice:
	"""Helper callbacks for the move Echoed Voice."""

	def basePowerCallback(self, user, target, move, battle=None):
		"""Scale base power based on the active echoed voice effect."""
		base_power = getattr(move, "basePower", getattr(move, "power", 0))
		chain = getattr(user, "echoed_voice_chain", 0)
		base_power *= max(1, chain + 1)
		field = getattr(battle, "field", None)
		if field and hasattr(field, "get_pseudo_weather"):
			effect = field.get_pseudo_weather("echoedvoice")
			if isinstance(effect, dict):
				multiplier = effect.get("multiplier", 1)
				base_power *= multiplier
		else:
			chain = getattr(user, "echoed_voice_chain", 0)
			if chain:
				base_power *= min(chain + 1, 5)
		return base_power

	def onFieldRestart(self, effect_state):
		"""Refresh the effect and increase the power multiplier."""
		if not isinstance(effect_state, dict):
			return
		if effect_state.get("duration") != 2:
			effect_state["duration"] = 2
			if effect_state.get("multiplier", 1) < 5:
				effect_state["multiplier"] = effect_state.get("multiplier", 1) + 1

	def onFieldStart(self, effect_state):
		"""Initialize the echoed voice multiplier."""
		if isinstance(effect_state, dict):
			effect_state["multiplier"] = 1

	def onTry(self, user=None, target=None, move=None, battle=None):
		"""Start the echoed voice field effect when the move is used."""
		if not battle:
			return
		field = getattr(battle, "field", None)
		if field is None:
			return
		effect = {
			"duration": 2,
			"onFieldStart": self.onFieldStart,
			"onFieldRestart": self.onFieldRestart,
		}
		if hasattr(field, "add_pseudo_weather"):
			field.add_pseudo_weather("echoedvoice", effect)


class Eeriespell:
	def onHit(self, user, target, battle):
		"""Reduce the PP of the target's last move by three."""
		move = getattr(target, "last_move", None)
		if not move:
			moves = getattr(target, "moves", [])
			move = moves[0] if moves else None
		if move and hasattr(move, "pp"):
			move.pp = max(0, move.pp - 3)
		return True


class Electricterrain:
	def durationCallback(self, *args, **kwargs):
		from pokemon.battle.item_effects import HeldItemRules
		source = args[1] if len(args) > 1 else kwargs.get("source")
		return HeldItemRules.field_duration(source, "terrainextender")

	def onBasePower(self, *args, **kwargs):
		attacker = args[0] if args else None
		move = args[2] if len(args) > 2 else None
		power = getattr(move, "power", 0) if move else 0
		if move and getattr(move, "type", "").lower() == "electric":
			grounded = getattr(attacker, "grounded", True)
			if grounded:
				return int(power * 1.3)
		return power

	def onFieldEnd(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field and hasattr(field, "terrain"):
			field.terrain = None
		return True

	def onFieldStart(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field is not None:
			field.terrain = "electricterrain"
		return True

	def onSetStatus(self, *args, **kwargs):
		status = args[0] if args else kwargs.get("status")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		if status == "slp" and target and getattr(target, "grounded", True):
			return False
		return True

	def onTryAddVolatile(self, *args, **kwargs):
		return True


class Electrify:
	def onModifyType(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		if move:
			move.type = "Electric"

	def onStart(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else args[0] if args else kwargs.get("pokemon")
		if target and hasattr(target, "volatiles"):
			target.volatiles["electrify"] = True
		return True

	def onTryHit(self, target, source, move):
		"""Electrify the target's next move if it is about to act."""
		return True


class Electroball:
	def basePowerCallback(self, user, target, move):
		"""Scale power based on the user's Speed compared to the target's."""
		u_speed = _battle_speed(user)
		t_speed = _battle_speed(target)
		if t_speed == 0:
			t_speed = 1
		ratio = u_speed / t_speed
		if ratio >= 4:
			return 150
		if ratio >= 3:
			return 120
		if ratio >= 2:
			return 80
		if ratio > 1:
			return 60
		return 40


class Electrodrift:
	def onBasePower(self, *args, **kwargs):
		"""Boost power if super effective."""
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		if target and move and type_effectiveness(target, move) > 1:
			return int(power * 4 / 3)
		return power


class Electroshot:
	def onTryMove(self, *args, **kwargs):
		"""Electro Shot has no additional move check in this stub."""
		return True


class Embargo:
	"""Suppress held effects for five residual turns without losing state."""

	def onEnd(self, *args, **kwargs):
		"""Remove suppression once the condition ends."""
		target = args[0] if args else kwargs.get("target")
		if target and hasattr(target, "volatiles"):
			target.volatiles.pop("embargo", None)
		return True

	def onStart(self, *args, **kwargs):
		"""Keep the engine's condition mapping and initialize its timer once."""
		target = kwargs.get("target") or kwargs.get("pokemon")
		if target is None:
			# Move-data adapters pass (user, target); singleEvent passes
			# (target, source, effect), including its explicit empty effect.
			target = args[1] if len(args) == 2 else args[0] if args else None
		if target and hasattr(target, "volatiles"):
			state = target.volatiles.get("embargo")
			if not isinstance(state, dict):
				state = {}
			state.setdefault("duration", 5)
			target.volatiles["embargo"] = state
		return True

	def onResidual(self, pokemon=None, battle=None, **kwargs):
		"""Expire the condition after its fifth ordinary residual boundary."""
		state = getattr(pokemon, "volatiles", {}).get("embargo")
		if state is None:
			return
		if not isinstance(state, dict):
			# Older checkpoints used a boolean and have no recoverable timer.
			state = {"duration": 5}
			pokemon.volatiles["embargo"] = state
		state["duration"] = state.get("duration", 5) - 1
		if state["duration"] <= 0:
			if battle is not None:
				battle.remove_volatile(pokemon, "embargo")
			else:
				pokemon.volatiles.pop("embargo", None)


class Encore:
	def onDisableMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		move = getattr(user, "volatiles", {}).get("encore") if user else None
		return move

	def onEnd(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user and hasattr(user, "volatiles"):
			user.volatiles.pop("encore", None)
		return True

	def onOverrideAction(self, *args, **kwargs):
		user = args[0] if args else None
		return getattr(user, "volatiles", {}).get("encore")

	def onResidual(self, *args, **kwargs):
		user = args[0] if args else None
		if not user:
			return False
		move = getattr(user, "volatiles", {}).get("encore")
		if not move:
			return True
		last = getattr(user, "last_move", None)
		if not last or getattr(last, "id", None) != getattr(move, "id", move):
			user.volatiles.pop("encore", None)
		elif getattr(last, "pp", 1) <= 0:
			user.volatiles.pop("encore", None)
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		target = args[1] if len(args) > 1 else None
		move = getattr(target, "last_move", None)
		if target and hasattr(target, "volatiles"):
			target.volatiles["encore"] = move
		return True


class Endeavor:
	def damageCallback(self, *args, **kwargs):
		user = args[0] if args else None
		target = args[1] if len(args) > 1 else None
		if not user or not target:
			return 0
		return max(0, getattr(target, "hp", 0) - getattr(user, "hp", 0))

	def onTryImmunity(self, *args, **kwargs):
		target = args[0] if args else kwargs.get("target")
		user = args[1] if len(args) > 1 else kwargs.get("source")
		if not user or not target:
			return False
		return getattr(target, "hp", 0) > getattr(user, "hp", 0)


class Endure:
	def onDamage(self, damage, target=None, source=None, move=None, **kwargs):
		if move is None or getattr(move, "category", None) not in {"Physical", "Special"}:
			return damage
		if target and getattr(target, "volatiles", {}).get("endure"):
			return min(damage, max(0, getattr(target, "hp", 1) - 1))
		return damage

	def onHit(self, user, target, battle):
		"""Allow the user to survive hits with at least 1 HP this turn."""
		if hasattr(user, "volatiles"):
			user.volatiles["endure"] = True
		return True

	def onPrepareHit(self, *args, **kwargs):
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["endure"] = True
		return True


class Entrainment:
	def onHit(self, user, target, battle):
		"""Give the target the user's ability."""
		ability = getattr(user, "ability", None)
		if not ability:
			return False
		if _ability_change_blocked(target, "noentrain", "cantsuppress"):
			return False
		setattr(target, "ability", ability)
		return True

	def onTryHit(self, target, source, move):
		"""Fail if the target already has the user's ability or is the user."""
		if target is source:
			return False
		if getattr(target, "ability", None) == getattr(source, "ability", None):
			return False
		if _ability_change_blocked(target, "noentrain", "cantsuppress"):
			return False
		return True


class Eruption:
	def basePowerCallback(self, user, target, move):
		"""Scale power based on the user's remaining HP."""
		cur_hp = getattr(user, "hp", 0)
		max_hp = getattr(user, "max_hp", cur_hp or 1)
		ratio = cur_hp / max_hp if max_hp else 0
		power = int(150 * ratio)
		return max(1, power)


class Expandingforce:
	def onBasePower(self, *args, **kwargs):
		"""Boost power on Psychic Terrain when grounded."""
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		terrain = getattr(user, "terrain", None)
		grounded = getattr(user, "grounded", True)
		if terrain == "psychicterrain" and grounded:
			return int(power * 1.5)
		return power

	def onModifyMove(self, *args, **kwargs):
		"""Adjust targeting on Psychic Terrain when the user is grounded."""
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		battle = kwargs.get("battle")
		if len(args) > 2:
			battle = args[2] or battle
		field = getattr(battle, "field", None)
		terrain = getattr(field, "terrain", getattr(battle, "terrain", None))
		if str(terrain).lower() == "psychicterrain" and getattr(user, "grounded", True):
			if move:
				move.target = "allAdjacentFoes"


class Facade:
	def onBasePower(self, *args, **kwargs):
		"""Double power if the user has a status condition (except sleep)."""
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		status = getattr(user, "status", None)
		if status and status != "slp":
			return power * 2
		return power


class Fairylock:
	def onFieldStart(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field:
			field.fairylock = 2
		return True

	def onTrapPokemon(self, *args, **kwargs):
		pokemon = args[0] if args else kwargs.get("pokemon")
		return True


class Fakeout:
	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		if getattr(user, "active_move_actions", 1) > 1:
			return False
		return True


class Falseswipe:
	def onDamage(self, *args, **kwargs):
		damage = args[1] if len(args) > 1 else kwargs.get("damage")
		target = args[0] if args else kwargs.get("target")
		if target and damage >= getattr(target, "hp", 0):
			return max(0, getattr(target, "hp", 0) - 1)
		return damage


class Fellstinger:
	def onAfterMoveSecondarySelf(self, *args, **kwargs):
		user = args[0] if args else None
		target = args[1] if len(args) > 1 else None
		if target and getattr(target, "hp", 1) <= 0:
			apply_boost(user, {"atk": 3})
		return True


class Ficklebeam:
	def onBasePower(self, *args, **kwargs):
		"""30% chance to double power."""
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		if random() < 0.3:
			return power * 2
		return power


class Filletaway:
	def onHit(self, user, target, battle):
		"""Halve the user's HP; boosts are handled by the engine."""
		max_hp = getattr(user, "max_hp", 0)
		if getattr(user, "hp", 0) <= max_hp // 2:
			return False
		user.hp -= max_hp // 2
		return True

	def onTry(self, *args, **kwargs):
		"""Ensure the user has enough HP to perform the move."""
		user = args[0] if args else None
		if not user:
			return False
		max_hp = getattr(user, "max_hp", 0)
		if getattr(user, "hp", 0) <= max_hp // 2 or max_hp == 1:
			return False
		return True

	def onTryHit(self, *args, **kwargs):
		"""No-op so the engine applies the standard boosts once."""
		return True


class Finalgambit:
	def damageCallback(self, *args, **kwargs):
		user = args[0] if args else None
		damage = getattr(user, "hp", 0) if user else 0
		if user:
			user.hp = 0
		return damage


class Firepledge:
	def basePowerCallback(self, user, target, move):
		"""Return boosted power if combined with another Pledge move."""
		if getattr(user, "pledge_combo", False):
			return 150
		return getattr(move, "power", 80) or 80

	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		if getattr(user, "pledge_combo", False) and move:
			move.pledge_combo = True

	def onPrepareHit(self, *args, **kwargs):
		return True

	def onResidual(self, *args, **kwargs):
		target = args[0] if args else None
		if not target:
			return False
		types = [t.lower() for t in getattr(target, "types", [])]
		if "fire" not in types:
			damage = getattr(target, "max_hp", 0) // 8
			target.hp = max(0, getattr(target, "hp", 0) - damage)
		return True

	def onSideEnd(self, *args, **kwargs):
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "conditions"):
			side.conditions.pop("firepledge", None)
		return True

	def onSideStart(self, *args, **kwargs):
		"""Start the Fire Pledge side condition."""
		side = args[0] if args else kwargs.get("side")
		if side:
			side.conditions["firepledge"] = {
				"turns": 4,
				"source": kwargs.get("source"),
			}
		return True


class Firstimpression:
	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		if getattr(user, "active_move_actions", 1) > 1:
			return False
		return True


class Fishiousrend:
	def basePowerCallback(self, user, target, move):
		"""Double power if the target has not moved yet this turn."""
		moved = getattr(target, "tempvals", {}).get("moved")
		base = getattr(move, "power", 0) or 0
		if not moved:
			return base * 2
		return base


class Flail:
	def basePowerCallback(self, user, target, move):
		"""Increase power as the user has less HP remaining."""
		cur_hp = getattr(user, "hp", 0)
		max_hp = getattr(user, "max_hp", cur_hp or 1)
		thresh = int((48 * cur_hp) / max_hp) if max_hp else 48
		if thresh <= 1:
			return 200
		if thresh <= 4:
			return 150
		if thresh <= 9:
			return 100
		if thresh <= 16:
			return 80
		if thresh <= 32:
			return 40
		return 20


class Flameburst:
	def onAfterSubDamage(self, *args, **kwargs):
		return self.onHit(*args, **kwargs)

	def onHit(self, user, target, battle):
		"""Also damage adjacent foes for minor damage."""
		side = getattr(target, "side", None)
		if side:
			others = [p for p in getattr(side, "active", []) if p is not target]
			for mon in others:
				damage = max(1, getattr(mon, "max_hp", 1) // 16)
				mon.hp = max(0, getattr(mon, "hp", 0) - damage)
		return True


class Fling:
	def onPrepareHit(self, *args, **kwargs):
		user = args[0] if args else None
		move = args[2] if len(args) > 2 else kwargs.get("move")
		item = getattr(user, "item", None) or getattr(user, "held_item", None)
		if not item:
			return False
		if move:
			item_raw = getattr(item, "raw", {}) or {}
			fling = item_raw.get("fling", {}) if isinstance(item_raw, dict) else {}
			power = getattr(item, "fling_power", None)
			if power is None and isinstance(fling, dict):
				power = fling.get("basePower")
			move.power = int(power if power is not None else getattr(move, "power", 0) or 0)
		return True

	def onAfterHit(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		battle = kwargs.get("battle") or getattr(user, "battle", None)
		if battle and hasattr(battle, "remove_item"):
			battle.remove_item(user, source=user, effect="move:fling", used=True)
		elif user and hasattr(user, "set_item"):
			user.set_item(None)
		elif user:
			setattr(user, "item", None)
			setattr(user, "held_item", None)
		return True

	def onUpdate(self, *args, **kwargs):
		"""Backward-compatible alias for older move data."""
		return self.onAfterHit(*args, **kwargs)


class Floralhealing:
	def onHit(self, user, target, battle):
		"""Restore half of the target's max HP."""
		max_hp = getattr(target, "max_hp", 0)
		heal = max_hp // 2
		target.hp = min(getattr(target, "hp", 0) + heal, max_hp)
		return True


class Flowershield:
	def onHit(self, user, target, battle):
		"""Raise Defense of all Grass-type PokÃ©mon on the field."""
		for side in getattr(battle, "sides", []):
			for mon in getattr(side, "active", []):
				types = [t.lower() for t in getattr(mon, "types", [])]
				if "grass" in types:
					apply_boost(mon, {"def": 1})
		return True

	def onHitField(self, user, battle):
		return self.onHit(user, None, battle)


class Fly:
	def onInvulnerability(self, *args, **kwargs):
		move = args[2] if len(args) > 2 else kwargs.get("move")
		if not move:
			return True
		unblock = {"gust", "twister", "thunder", "hurricane", "skyuppercut"}
		mname = getattr(move, "name", "").replace(" ", "").lower()
		return mname not in unblock

	def onSourceModifyDamage(self, *args, **kwargs):
		damage = args[0] if args else kwargs.get("damage")
		move = args[3] if len(args) > 3 else kwargs.get("move")
		if move and getattr(move, "name", "").replace(" ", "").lower() in {"gust", "twister"}:
			return int(damage * 2)
		return damage

	def onTryMove(self, *args, **kwargs):
		"""Handle Fly as a two-turn move."""
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		vol = getattr(user, "volatiles", {})
		if vol.get("fly"):
			vol.pop("fly", None)
			user.volatiles = vol
			return True
		vol["fly"] = True
		user.volatiles = vol
		return False


class Flyingpress:
	def onEffectiveness(self, *args, **kwargs):
		type_mod = args[0] if args else kwargs.get("typeMod")
		if type_mod is None:
			return
		return type_mod


class Focusenergy:
	def onModifyCritRatio(self, *args, **kwargs):
		ratio = args[0] if args else kwargs.get("ratio", 0)
		try:
			return ratio + 2
		except Exception:
			return ratio

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			# add_volatile already binds current target/source/effect. Retain
			# that structured state for reconnect instead of replacing it.
			user.volatiles.setdefault("focusenergy", {"id": "focusenergy", "target": user})
		return True


class Focuspunch:
	def beforeMoveCallback(self, *args, **kwargs):
		user = args[0] if args else None
		if user and getattr(user, "volatiles", {}).get("focuspunch", {}).get("lostFocus"):
			return True

	def onHit(self, user, target, battle):
		"""Deal heavy damage if the user kept its focus."""
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["focuspunch"] = True
		return True

	def onTryAddVolatile(self, *args, **kwargs):
		status = args[0] if args else kwargs.get("status")
		sid = getattr(status, "id", None) if status is not None else None
		if sid is None:
			sid = str(status).lower() if status is not None else ""
		if sid == "flinch":
			return False
		return True

	def priorityChargeCallback(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["focuspunch_charge"] = True
		return -3


class Followme:
	def onFoeRedirectTarget(self, *args, **kwargs):
		user = args[0] if args else None
		return user

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["followme"] = True
		return True

	def onTry(self, *args, **kwargs):
		battle = kwargs.get("battle") if kwargs else None
		if len(args) > 3:
			battle = args[3] or battle
		if not battle:
			return True
		participants = getattr(battle, "participants", [])
		multi = getattr(battle, 'multi', False) or any(len(getattr(p, "active", [])) > 1 for p in participants)
		return multi


class Foresight:
	def onModifyBoost(self, *args, **kwargs):
		boosts = args[0] if args else kwargs.get("boosts", {})
		if isinstance(boosts, dict) and "evasion" in boosts:
			boosts["evasion"] = 0
		return boosts

	def onNegateImmunity(self, *args, **kwargs):
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		target = args[1] if len(args) > 1 else None
		if target and hasattr(target, "volatiles"):
			target.volatiles["foresight"] = True
		return True

	def onTryHit(self, target, source, move):
		"""Fail if the target already has Miracle Eye active."""
		if getattr(target, "volatiles", {}).get("miracleeye"):
			return False
		return True


class Forestscurse:
	def onHit(self, user, target, battle):
		"""Add the Grass type to the target."""
		if hasattr(target, "types") and "Grass" not in target.types:
			target.types.append("Grass")
		return True


class Freezedry:
	def onEffectiveness(self, *args, **kwargs):
		type_mod = args[0] if args else kwargs.get("typeMod")
		target_type = None
		if len(args) > 2:
			target_type = args[2]
		else:
			target_type = kwargs.get("type")
		if isinstance(target_type, str) and target_type.capitalize() == "Water":
			return 1
		return type_mod


class Freezeshock:
	def onTryMove(self, *args, **kwargs):
		"""Handle Freeze Shock as a two-turn move."""
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		vol = getattr(user, "volatiles", {})
		if vol.get("freezeshock"):
			vol.pop("freezeshock", None)
			user.volatiles = vol
			return True
		vol["freezeshock"] = True
		user.volatiles = vol
		return False


class Freezyfrost:
	def onHit(self, user, target, battle):
		"""Reset the target's stat boosts."""
		if hasattr(target, "boosts"):
			for stat in target.boosts:
				target.boosts[stat] = 0
		return True


class Frustration:
	def basePowerCallback(self, user, target, move):
		"""Scale power based on the user's unhappiness."""
		happiness = getattr(user, "happiness", 0)
		power = int((255 - min(255, max(0, happiness))) * 10 / 25)
		return max(1, power)


class Furycutter:
	def basePowerCallback(self, user, target, move):
		"""Increase power with consecutive uses."""
		chain = getattr(user, "fury_cutter_chain", 0)
		if not getattr(move, "_fury_cutter_inc", False):
			chain = min(chain + 1, 4)
			setattr(user, "fury_cutter_chain", chain)
			setattr(move, "_fury_cutter_inc", True)
		return min(160, 40 * chain if chain else 40)

	def onRestart(self, user, target, move):
		setattr(user, "fury_cutter_chain", min(getattr(user, "fury_cutter_chain", 0) + 1, 4))

	def onStart(self, user, target, move):
		setattr(user, "fury_cutter_chain", 1)


class Fusionbolt:
	def onBasePower(self, *args, **kwargs):
		"""Double power if Fusion Flare was used this turn."""
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		last = getattr(user, "last_move_this_turn", "").lower() if user else ""
		if last == "fusionflare":
			return power * 2
		return power


class Fusionflare:
	def onBasePower(self, *args, **kwargs):
		"""Double power if Fusion Bolt was used this turn."""
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		last = getattr(user, "last_move_this_turn", "").lower() if user else ""
		if last == "fusionbolt":
			return power * 2
		return power


class Futuresight:
	def onTry(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else None
		if not target or not getattr(target, "side", None):
			return False
		return True


class Gastroacid:
	def onCopy(self, *args, **kwargs):
		return False

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		target = args[1] if len(args) > 1 else None
		if target and hasattr(target, "volatiles"):
			target.volatiles["gastroacid"] = True
		return True

	def onTryHit(self, target, source, move):
		"""Fail if the target's ability cannot be suppressed."""
		if _effect_id(getattr(target, "item", None)) == "abilityshield":
			return None
		if _ability_change_blocked(target, "cantsuppress"):
			return False
		return True


class Gearup:
	def onHitSide(self, user, battle):
		"""Raise Attack and Sp. Atk of allies with Plus or Minus."""
		side = getattr(user, "side", None)
		if not side:
			return False
		for mon in getattr(side, "active", []):
			ability = _effect_id(getattr(mon, "ability", None))
			if ability in {"plus", "minus"}:
				apply_boost(mon, {"atk": 1, "spa": 1})
		return True


class Genesissupernova:
	def onHit(self, user, target, battle):
		"""Set Psychic Terrain after dealing damage."""
		field = getattr(battle, "field", None)
		if field and hasattr(field, "set_terrain"):
			field.set_terrain("Psychic")
		return True


class Geomancy:
	def onTryMove(self, *args, **kwargs):
		"""Charge first; the ordinary second-turn move applies its boosts once."""

		user = args[0] if args else kwargs.get("user")
		if not user:
			return False

		vol = getattr(user, "volatiles", {})
		if vol.get("geomancy"):
			vol.pop("geomancy", None)
			user.volatiles = vol
			return True

		vol["geomancy"] = True
		user.volatiles = vol
		return False


class Glaiverush:
	def onAccuracy(self, *args, **kwargs):
		return True

	def onBeforeMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user and hasattr(user, "volatiles"):
			user.volatiles.pop("glaiverush", None)
		return True

	def onSourceModifyDamage(self, *args, **kwargs):
		damage = args[0] if args else kwargs.get("damage")
		try:
			return int(damage * 2)
		except Exception:
			return damage

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["glaiverush"] = True
		return True


class Gmaxbefuddle:
	def onHit(self, user, target, battle):
		"""Inflict a random status condition on the target."""
		if hasattr(target, "setStatus"):
			target.setStatus(choice(["par", "psn", "slp"]))
		return True


class Gmaxcannonade:
	def onHit(self, user, target, battle):
		"""Begin residual damage each turn to the target's side."""
		side = getattr(target, "side", None)
		if side and hasattr(side, "volatiles"):
			side.volatiles["gmaxcannonade"] = 4
		return True

	def onResidual(self, *args, **kwargs):
		side = args[0] if args else None
		if not side:
			return False
		for mon in getattr(side, "active", []):
			types = [t.lower() for t in getattr(mon, "types", [])]
			if "water" not in types:
				dmg = getattr(mon, "max_hp", 0) // 6
				mon.hp = max(0, getattr(mon, "hp", 0) - dmg)
		return True

	def onSideEnd(self, *args, **kwargs):
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "volatiles"):
			side.volatiles.pop("gmaxcannonade", None)
		return True

	def onSideStart(self, *args, **kwargs):
		"""Initialize residual G-Max Cannonade effect."""
		side = args[0] if args else kwargs.get("side")
		if side:
			vol = getattr(side, "volatiles", {})
			vol["gmaxcannonade"] = 4
			side.volatiles = vol
		return True


class Gmaxcentiferno:
	def onHit(self, user, target, battle):
		"""Trap the target and cause residual damage."""
		if hasattr(target, "volatiles"):
			target.volatiles["gmaxcentiferno"] = 4
			target.volatiles["trapped"] = True
		return True


class Gmaxchistrike:
	def onHit(self, user, target, battle):
		"""Boost the user's Attack and Defense."""
		apply_boost(user, {"atk": 1, "def": 1})
		return True

	def onModifyCritRatio(self, *args, **kwargs):
		ratio = args[0] if args else kwargs.get("ratio", 0)
		user = args[1] if len(args) > 1 else kwargs.get("user")
		layers = 1
		if user and hasattr(user, "volatiles"):
			layers = user.volatiles.get("gmaxchistrike_layers", 1)
		return ratio + layers

	def onRestart(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user and hasattr(user, "volatiles"):
			layers = user.volatiles.get("gmaxchistrike_layers", 1)
			layers = min(3, layers + 1)
			user.volatiles["gmaxchistrike_layers"] = layers
			user.volatiles["gmaxchistrike"] = True
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["gmaxchistrike"] = True
			user.volatiles["gmaxchistrike_layers"] = 1
		return True


class Gmaxcuddle:
	def onHit(self, user, target, battle):
		"""Infatuate foes of the opposite gender."""
		if hasattr(target, "volatiles"):
			target.volatiles["attract"] = True
		return True


class Gmaxdepletion:
	def onHit(self, user, target, battle):
		"""Lower PP of the target's last move."""
		last_move = getattr(target, "last_move", None)
		if last_move and hasattr(last_move, "pp"):
			last_move.pp = max(0, last_move.pp - 2)
		return True


class Gmaxfinale:
	def onHit(self, user, target, battle):
		"""Heal allies slightly after dealing damage."""
		side = getattr(user, "side", None)
		if side:
			for mon in getattr(side, "active", []):
				max_hp = getattr(mon, "max_hp", 0)
				heal = max_hp // 6
				mon.hp = min(getattr(mon, "hp", 0) + heal, max_hp)
		return True


class Gmaxfoamburst:
	def onHit(self, user, target, battle):
		"""Sharply lower the target's Speed."""
		apply_boost(target, {"spe": -2})
		return True


class Gmaxgoldrush:
	def onHit(self, user, target, battle):
		"""Confuse the target."""
		if hasattr(target, "volatiles"):
			target.volatiles["confusion"] = True
		return True


class Gmaxmalodor:
	def onHit(self, user, target, battle):
		"""Poison all foes."""
		opponents = []
		side = getattr(target, "side", None)
		if side:
			opponents = getattr(side, "active", [target])
		else:
			opponents = [target]
		for mon in opponents:
			if hasattr(mon, "setStatus"):
				mon.setStatus("psn")
		return True


class Gmaxmeltdown:
	def onHit(self, user, target, battle):
		"""Prevent the target from using the same move consecutively."""
		if hasattr(target, "volatiles"):
			target.volatiles["torment"] = True
		return True


class Gmaxreplenish:
	def onHit(self, user, target, battle):
		"""Attempt to restore allies' berries."""
		side = getattr(user, "side", None)
		if side:
			for mon in getattr(side, "active", []):
				if getattr(mon, "berry_consumed", False) and not getattr(mon, "item", None):
					setattr(mon, "item", getattr(mon, "berry_consumed"))
		return True


class Gmaxsandblast:
	def onHit(self, user, target, battle):
		"""Trap the target in a sandstorm."""
		field = getattr(battle, "field", None)
		if field and hasattr(field, "set_weather"):
			field.set_weather("Sandstorm")
		if hasattr(target, "volatiles"):
			target.volatiles["trapped"] = True
		return True


class Gmaxsmite:
	def onHit(self, user, target, battle):
		"""Confuse the target."""
		if hasattr(target, "volatiles"):
			target.volatiles["confusion"] = True
		return True


class Gmaxsnooze:
	def onAfterSubDamage(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else kwargs.get("target")
		if target and not getattr(target, "status", None) and random() < 0.5:
			if hasattr(target, "volatiles"):
				target.volatiles["drowsy"] = True
		return True

	def onHit(self, user, target, battle):
		"""Make the target drowsy, causing sleep later."""
		if hasattr(target, "volatiles"):
			target.volatiles["drowsy"] = True
		return True


class Gmaxsteelsurge:
	def onEntryHazard(self, *args, **kwargs):
		pokemon = args[0] if args else kwargs.get("pokemon")
		if not pokemon:
			return False
		item = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
		from pokemon.battle.effect_context import EffectContext
		if EffectContext.key(EffectContext.item(pokemon)) == "heavydutyboots":
			return True
		dmg = getattr(pokemon, "max_hp", 0) // 8
		eff = type_effectiveness(pokemon, type("Move", (), {"type": "Steel"}))
		try:
			dmg = int(getattr(pokemon, "max_hp", 0) * eff / 8)
		except Exception:
			pass
		pokemon.hp = max(0, getattr(pokemon, "hp", 0) - dmg)
		return True

	def onHit(self, user, target, battle):
		"""Lay a steel-type damaging hazard on the target's side."""
		side = getattr(target, "side", None)
		if side and hasattr(side, "hazards"):
			side.hazards["steelsurge"] = True
		return True

	def onSideStart(self, *args, **kwargs):
		"""Activate the Steel Surge hazard on this side."""
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "hazards"):
			side.hazards["steelsurge"] = True
		return True


class Gmaxstonesurge:
	def onHit(self, user, target, battle):
		"""Set up stealth rocks on the opponent's side."""
		side = getattr(target, "side", None)
		if side and hasattr(side, "hazards"):
			side.hazards["rocks"] = True
		return True


class Gmaxstunshock:
	def onHit(self, user, target, battle):
		"""Paralyze or poison the target."""
		if hasattr(target, "setStatus"):
			target.setStatus(choice(["par", "psn"]))
		return True


class Gmaxsweetness:
	def onHit(self, user, target, battle):
		"""Cure status conditions of the user's side."""
		side = getattr(user, "side", None)
		if side:
			for mon in getattr(side, "active", []):
				if hasattr(mon, "setStatus"):
					mon.setStatus(0)
		return True


class Gmaxtartness:
	def onHit(self, user, target, battle):
		"""Sharply lower the target's evasion."""
		apply_boost(target, {"evasion": -2})
		return True


class Gmaxterror:
	def onHit(self, user, target, battle):
		"""Prevent the target from switching out."""
		if hasattr(target, "volatiles"):
			target.volatiles["trapped"] = True
		return True


class Gmaxvinelash:
	def onHit(self, user, target, battle):
		"""Start residual damage on the target's side."""
		side = getattr(target, "side", None)
		if side and hasattr(side, "volatiles"):
			side.volatiles["gmaxvinelash"] = 4
		return True

	def onResidual(self, *args, **kwargs):
		side = args[0] if args else None
		if not side:
			return False
		for mon in getattr(side, "active", []):
			types = [t.lower() for t in getattr(mon, "types", [])]
			if "grass" not in types:
				dmg = getattr(mon, "max_hp", 0) // 6
				mon.hp = max(0, getattr(mon, "hp", 0) - dmg)
		return True

	def onSideEnd(self, *args, **kwargs):
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "volatiles"):
			side.volatiles.pop("gmaxvinelash", None)
		return True

	def onSideStart(self, *args, **kwargs):
		"""Begin the G-Max Vine Lash residual effect."""
		side = args[0] if args else kwargs.get("side")
		if side:
			vol = getattr(side, "volatiles", {})
			vol["gmaxvinelash"] = 4
			side.volatiles = vol
		return True


class Gmaxvolcalith:
	def onHit(self, user, target, battle):
		"""Set up a rockstorm dealing residual damage."""
		side = getattr(target, "side", None)
		if side and hasattr(side, "volatiles"):
			side.volatiles["gmaxvolcalith"] = 4
		return True

	def onResidual(self, *args, **kwargs):
		side = args[0] if args else None
		if not side:
			return False
		for mon in getattr(side, "active", []):
			types = [t.lower() for t in getattr(mon, "types", [])]
			if "rock" not in types:
				dmg = getattr(mon, "max_hp", 0) // 6
				mon.hp = max(0, getattr(mon, "hp", 0) - dmg)
		return True

	def onSideEnd(self, *args, **kwargs):
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "volatiles"):
			side.volatiles.pop("gmaxvolcalith", None)
		return True

	def onSideStart(self, *args, **kwargs):
		"""Start the G-Max Volcalith residual effect."""
		side = args[0] if args else kwargs.get("side")
		if side:
			vol = getattr(side, "volatiles", {})
			vol["gmaxvolcalith"] = 4
			side.volatiles = vol
		return True


class Gmaxvoltcrash:
	def onHit(self, user, target, battle):
		"""Paralyze the target."""
		if hasattr(target, "setStatus"):
			target.setStatus("par")
		return True


class Gmaxwildfire:
	def onHit(self, user, target, battle):
		"""Start a blazing field effect causing residual damage."""
		side = getattr(target, "side", None)
		if side and hasattr(side, "volatiles"):
			side.volatiles["gmaxwildfire"] = 4
		return True

	def onResidual(self, *args, **kwargs):
		side = args[0] if args else None
		if not side:
			return False
		for mon in getattr(side, "active", []):
			types = [t.lower() for t in getattr(mon, "types", [])]
			if "fire" not in types:
				dmg = getattr(mon, "max_hp", 0) // 6
				mon.hp = max(0, getattr(mon, "hp", 0) - dmg)
		return True

	def onSideEnd(self, *args, **kwargs):
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "volatiles"):
			side.volatiles.pop("gmaxwildfire", None)
		return True

	def onSideStart(self, *args, **kwargs):
		"""Begin the G-Max Wildfire residual effect."""
		side = args[0] if args else kwargs.get("side")
		if side:
			vol = getattr(side, "volatiles", {})
			vol["gmaxwildfire"] = 4
			side.volatiles = vol
		return True


class Gmaxwindrage:
	def onHit(self, user, target, battle):
		"""Remove hazards and screens from the target's side."""
		side = getattr(target, "side", None)
		if side:
			if hasattr(side, "hazards"):
				side.hazards.clear()
			if hasattr(side, "screens"):
				side.screens.clear()
		return True


class Grassknot:
	def basePowerCallback(self, user, target, move):
		"""Scale power with the target's weight."""
		weight = _effective_weight(target)
		if weight >= 200:
			return 120
		if weight >= 100:
			return 100
		if weight >= 50:
			return 80
		if weight >= 25:
			return 60
		if weight >= 10:
			return 40
		return 20

	def onTryHit(self, target, source, move):
		"""Fail against Dynamax targets."""
		if getattr(target, "volatiles", {}).get("dynamax"):
			return False
		return True


class Grasspledge:
	def basePowerCallback(self, user, target, move):
		"""Return 150 power when used in a pledge combo."""
		if getattr(move, "pledge_combo", False) or getattr(user, "pledge_combo", False):
			return 150
		return getattr(move, "power", 0) or 0

	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		if getattr(user, "pledge_combo", False) and move:
			move.pledge_combo = True

	def onModifySpe(self, *args, **kwargs):
		spe = args[0] if args else kwargs.get("spe")
		return spe

	def onPrepareHit(self, *args, **kwargs):
		return True

	def onSideEnd(self, *args, **kwargs):
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "conditions"):
			side.conditions.pop("grasspledge", None)
		return True

	def onSideStart(self, *args, **kwargs):
		"""Start the Grass Pledge side condition."""
		side = args[0] if args else kwargs.get("side")
		if side:
			side.conditions["grasspledge"] = {
				"turns": 4,
				"source": kwargs.get("source"),
			}
		return True


class Grassyglide:
	def onModifyPriority(self, *args, **kwargs):
		priority = args[0] if args else kwargs.get("priority", 0)
		user = args[1] if len(args) > 1 else kwargs.get("user")
		if getattr(user, "terrain", "") == "grassyterrain":
			return priority + 1
		return priority


class Grassyterrain:
	def durationCallback(self, *args, **kwargs):
		from pokemon.battle.item_effects import HeldItemRules
		source = args[1] if len(args) > 1 else kwargs.get("source")
		return HeldItemRules.field_duration(source, "terrainextender")

	def onBasePower(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		move_id = getattr(move, "name", "").replace(" ", "").lower() if move else ""
		if move_id in {"earthquake", "bulldoze", "magnitude"} and target and getattr(target, "grounded", True):
			return int(power * 0.5)
		if move and getattr(move, "type", "").lower() == "grass" and user and getattr(user, "grounded", True):
			return int(power * 1.3)
		return power

	def onFieldEnd(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field and hasattr(field, "terrain"):
			field.terrain = None
		return True

	def onFieldStart(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field is not None:
			field.terrain = "grassyterrain"
		return True

	def onResidual(self, *args, **kwargs):
		pokemon = args[0] if args else None
		if not pokemon:
			return False
		if getattr(pokemon, "grounded", True):
			max_hp = getattr(pokemon, "max_hp", 0)
			heal = max_hp // 16
			pokemon.hp = min(getattr(pokemon, "hp", 0) + heal, max_hp)
		return True


class Gravapple:
	def onBasePower(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		battle = args[3] if len(args) > 3 else kwargs.get("battle")
		field = getattr(battle, "field", None) if battle else None
		if field and getattr(field, "pseudo_weather", {}).get("gravity"):
			return int(power * 1.5)
		return power


class Gravity:
	def durationCallback(self, *args, **kwargs):
		source = args[1] if len(args) > 1 else kwargs.get("source")
		if _effect_id(getattr(source, "ability", None)) == "persistent":
			return 7
		return 5

	def onBeforeMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		move = args[1] if len(args) > 1 else kwargs.get("move")
		if move and getattr(move, "flags", {}).get("gravity") and not getattr(move, "isZ", False):
			if hasattr(user, "tempvals"):
				user.tempvals["cant_move"] = "gravity"
			return False
		return True

	def onDisableMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		move = args[1] if len(args) > 1 else kwargs.get("move")
		if move and getattr(move, "flags", {}).get("gravity"):
			return True
		return False

	def onFieldEnd(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field and hasattr(field, "pseudo_weather"):
			field.pseudo_weather.pop("gravity", None)
		return True

	def onFieldStart(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field:
			vol = getattr(field, "pseudo_weather", {})
			if not isinstance(vol.get("gravity"), dict):
				vol["gravity"] = {}
			field.pseudo_weather = vol
		return True

	def onModifyAccuracy(self, *args, **kwargs):
		acc = args[0] if args else kwargs.get("accuracy", 100)
		try:
			return min(100, int(acc * 5 / 3))
		except Exception:
			return acc

	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		if move and getattr(move, "accuracy", True) is not True:
			try:
				move.accuracy = min(100, int(move.accuracy * 5 / 3))
			except Exception:
				pass


class Growth:
	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		battle = kwargs.get("battle")
		if len(args) > 2:
			battle = args[2] or battle
		field = getattr(battle, "field", None)
		weather = getattr(field, "weather", getattr(battle, "weather", None))
		sunny = str(weather).lower() in ("sunnyday", "sunny", "desolateland")
		if move:
			move.boosts = {"atk": 2, "spa": 2} if sunny else {"atk": 1, "spa": 1}


class Grudge:
	def onBeforeMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user and hasattr(user, "volatiles"):
			user.volatiles.pop("grudge", None)
		return True

	def onFaint(self, *args, **kwargs):
		pokemon = args[0] if args else None
		last = getattr(pokemon, "tempvals", {}).get("last_damaged_by") if pokemon else None
		source = last.get("source") if isinstance(last, dict) else None
		move = getattr(source, "last_move", None)
		if move and hasattr(move, "pp"):
			battle = kwargs.get("battle") or getattr(pokemon, "battle", None)
			if battle is not None and hasattr(battle, "reduce_move_pp"):
				battle.reduce_move_pp(source, move, max(0, int(move.pp or 0)))
			else:
				move.pp = 0
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["grudge"] = True
		return True


class Guardianofalola:
	def damageCallback(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else kwargs.get("target")
		if not target:
			return 0
		hp75 = int(getattr(target, "max_hp", 0) * 3 / 4)
		protected = False
		vols = getattr(target, "volatiles", {})
		if vols.get("protect") or vols.get("banefulbunker") or vols.get("kingsshield") or vols.get("spikyshield"):
			protected = True
		side = getattr(target, "side", None)
		if side and getattr(side, "matblock", False):
			protected = True
		if protected:
			return max(1, int((hp75 / 4) + 0.5))
		return max(1, hp75)


class Guardsplit:
	def onHit(self, user, target, battle):
		"""Average the Defense and Sp. Def stats of user and target."""
		for stat in ["def", "spd"]:
			u_val = _stored_battle_stat(user, stat)
			t_val = _stored_battle_stat(target, stat)
			if u_val is not None and t_val is not None:
				avg = (u_val + t_val) // 2
				_set_stored_battle_stat(user, stat, avg)
				_set_stored_battle_stat(target, stat, avg)
		return True


class Guardswap:
	def onHit(self, user, target, battle):
		"""Swap Defense and Sp. Def stat boosts."""
		for stat in ["def", "spd"]:
			user_boosts = getattr(user, "boosts", {})
			target_boosts = getattr(target, "boosts", {})
			user_boost = _boost_value(user_boosts, stat)
			target_boost = _boost_value(target_boosts, stat)
			_set_boost_value(user_boosts, stat, target_boost)
			_set_boost_value(target_boosts, stat, user_boost)
		return True


class Gyroball:
	def basePowerCallback(self, user, target, move):
		"""Increase power the slower the user is compared to the target."""
		user_spe = _battle_speed(user)
		target_spe = _battle_speed(target)
		user_spe = max(1, user_spe)
		power = int((25 * target_spe / user_spe) + 1)
		return min(150, max(1, power))


class Happyhour:
	def onTryHit(self, user, *args, **kwargs):
		"""Simply succeed to display the effect."""
		return True


class Hardpress:
	def basePowerCallback(self, user, target, move):
		"""Scale power based on the target's remaining HP."""
		cur_hp = getattr(target, "hp", 0)
		max_hp = getattr(target, "max_hp", cur_hp or 1)
		ratio = cur_hp / max_hp if max_hp else 0
		power = int(100 * ratio)
		return max(1, power)


class Haze:
	def onHitField(self, user, battle):
		"""Remove all stat changes from all active PokÃ©mon."""
		for side in getattr(battle, "sides", []):
			for mon in getattr(side, "active", []):
				if hasattr(mon, "boosts"):
					for stat in mon.boosts:
						mon.boosts[stat] = 0
		return True


class Healbell:
	def onHit(self, user, target, battle):
		"""Cure status of all PokÃ©mon on the user's side."""
		party = _battle_party(user)
		for mon in party:
			if hasattr(mon, "setStatus"):
				mon.setStatus(0)
		return True


class Healblock:
	onResidualOrder = 20

	def durationCallback(self, *args, **kwargs):
		source = args[1] if len(args) > 1 else kwargs.get("source")
		effect = args[2] if len(args) > 2 else kwargs.get("effect")
		if getattr(effect, "name", "") == "Psychic Noise":
			return 2
		if _effect_id(getattr(source, "ability", None)) == "persistent":
			return 7
		return 5

	def onBeforeMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		move = args[1] if len(args) > 1 else kwargs.get("move")
		if move and getattr(move, "flags", {}).get("heal") and not getattr(move, "isZ", False):
			if hasattr(user, "tempvals"):
				user.tempvals["cant_move"] = "healblock"
			return False
		return True

	def onDisableMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		move = args[1] if len(args) > 1 else kwargs.get("move")
		if move and getattr(move, "flags", {}).get("heal"):
			return True
		return False

	def onEnd(self, *args, **kwargs):
		target = args[0] if args else kwargs.get("target")
		if target and hasattr(target, "volatiles"):
			target.volatiles.pop("healblock", None)
		return True

	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		if move:
			move.effect = "healblock"

	def onRestart(self, *args, **kwargs):
		"""An existing block retains its original remaining lifetime."""
		return False

	def onStart(self, *args, **kwargs):
		"""Keep condition state and apply the actual move's bounded lifetime."""
		target = kwargs.get("target") or kwargs.get("pokemon")
		if target is None:
			target = args[1] if len(args) == 2 else args[0] if args else None
		if target is not None:
			state = target.volatiles.get("healblock")
			state = state if isinstance(state, dict) else {}
			effect = kwargs.get("effect") or (args[2] if len(args) > 2 else None)
			source = kwargs.get("source") or (args[1] if len(args) > 2 else None)
			duration = self.durationCallback(source=source, effect=effect)
			state.setdefault("duration", duration)
			target.volatiles["healblock"] = state
		return True

	def onResidual(self, pokemon=None, battle=None, **kwargs):
		"""Expire once per residual boundary, including old boolean checkpoints."""
		state = getattr(pokemon, "volatiles", {}).get("healblock")
		if state is None:
			return
		if not isinstance(state, dict):
			state = {"duration": 5}
			pokemon.volatiles["healblock"] = state
		state["duration"] = state.get("duration", 5) - 1
		if state["duration"] <= 0:
			if battle:
				battle.remove_volatile(pokemon, "healblock")
			else:
				pokemon.volatiles.pop("healblock", None)

	def onTryHeal(self, amount=None, target=None, **kwargs):
		"""The relay value precedes the recipient in TryHeal events."""
		if target is None and hasattr(amount, "volatiles"):
			target = amount
		if target and getattr(target, "volatiles", {}).get("healblock"):
			return False
		return True


def _sacrifice_has_replacement(user, battle):
	"""Require a living inactive replacement, including while the user is trapped."""
	part = battle.participant_for(user) if battle and hasattr(battle, "participant_for") else None
	if part is None:
		return False
	return any(mon not in part.active and getattr(mon, "hp", 0) > 0 for mon in part.pokemons)


class Healingwish:
	def onSwap(self, *args, **kwargs):
		pokemon = args[0] if args else None
		battle = kwargs.get("battle")
		if pokemon and not getattr(pokemon, "is_fainted", False):
			needs_heal = (
				getattr(pokemon, "hp", 0) < getattr(pokemon, "max_hp", getattr(pokemon, "hp", 0))
				or bool(getattr(pokemon, "status", 0))
			)
			if not needs_heal:
				return True
			max_hp = getattr(pokemon, "max_hp", 0)
			pokemon.hp = max_hp
			if hasattr(pokemon, "clearStatus"):
				pokemon.clearStatus(battle=battle, effect="move:healingwish")
			elif hasattr(pokemon, "setStatus"):
				pokemon.setStatus(0)
			if battle and hasattr(battle, "remove_slot_condition"):
				battle.remove_slot_condition(pokemon, "healingwish")
		return True

	def onTryHit(self, *args, **kwargs):
		user = args[0] if args else None
		return _sacrifice_has_replacement(user, kwargs.get("battle") or getattr(user, "battle", None))


class Healpulse:
	def onHit(self, user, target, battle):
		"""Heal the target by half of its max HP."""
		max_hp = getattr(target, "max_hp", 0)
		heal = max_hp // 2
		target.hp = min(getattr(target, "hp", 0) + heal, max_hp)
		return True


class Heartswap:
	def onHit(self, user, target, battle):
		"""Swap all stat boosts between user and target."""
		user_boosts = getattr(user, "boosts", {})
		target_boosts = getattr(target, "boosts", {})
		user.boosts, target.boosts = target_boosts.copy(), user_boosts.copy()
		return True


class Heatcrash:
	def basePowerCallback(self, user, target, move):
		"""Scale power based on weight ratio."""
		user_wt = _effective_weight(user)
		target_wt = _effective_weight(target)
		if user_wt >= target_wt * 5:
			return 120
		if user_wt >= target_wt * 4:
			return 100
		if user_wt >= target_wt * 3:
			return 80
		if user_wt >= target_wt * 2:
			return 60
		return 40

	def onTryHit(self, target, source, move):
		"""Fail against Dynamax targets."""
		if getattr(target, "volatiles", {}).get("dynamax"):
			return False
		return True


class Heavyslam:
	def basePowerCallback(self, user, target, move):
		"""Scale power based on weight ratio."""
		user_wt = _effective_weight(user)
		target_wt = _effective_weight(target)
		if user_wt >= target_wt * 5:
			return 120
		if user_wt >= target_wt * 4:
			return 100
		if user_wt >= target_wt * 3:
			return 80
		if user_wt >= target_wt * 2:
			return 60
		return 40

	def onTryHit(self, target, source, move):
		"""Fail against Dynamax targets."""
		if getattr(target, "volatiles", {}).get("dynamax"):
			return False
		return True


class Helpinghand:
	def onBasePower(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		state = getattr(user, "volatiles", {}).get("helpinghand") if user else None
		multiplier = 1.0
		if isinstance(state, dict):
			multiplier = state.get("multiplier", 1.5)
		elif state:
			multiplier = 1.5
		return int(power * multiplier)

	def onRestart(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user and "helpinghand" in getattr(user, "volatiles", {}):
			state = user.volatiles.get("helpinghand")
			if isinstance(state, dict):
				state["multiplier"] = state.get("multiplier", 1.5) * 1.5
			else:
				user.volatiles["helpinghand"] = {"target": state, "multiplier": 1.5 * 1.5}
		return True

	def onStart(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else args[0] if args else kwargs.get("pokemon")
		if target and hasattr(target, "volatiles"):
			target.volatiles["helpinghand"] = {"multiplier": 1.5}
		return True

	def onTryHit(self, target, source, move):
		"""Only works if the ally is preparing to move."""
		return True


class Hex:
	def basePowerCallback(self, user, target, move):
		"""Double power if the target has a status condition."""
		if getattr(target, "status", None):
			return (getattr(move, "power", 0) or 0) * 2
		return getattr(move, "power", 0)


class Hiddenpower:
	def onModifyType(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		if move and user:
			move.type = getattr(user, "hp_type", "Dark")


class Highjumpkick:
	def onMoveFail(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		recoil = getattr(user, "max_hp", 0) // 2
		user.hp = max(0, getattr(user, "hp", 0) - recoil)
		return True


class Holdback:
	def onDamage(self, *args, **kwargs):
		damage = args[0] if args else kwargs.get("damage")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		if target and damage >= getattr(target, "hp", 0):
			return max(0, getattr(target, "hp", 0) - 1)
		return damage


class Hurricane:
	def onModifyMove(self, move, user=None, target=None, battle=None):
		weather = _holder_effective_weather(target, battle)
		if weather in {"rain", "raindance", "primordialsea"}:
			move.accuracy = True
		elif weather in {"sunnyday", "sunny", "desolateland"}:
			move.accuracy = 50


class Hyperspacefury:
	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		species = getattr(getattr(user, "species", None), "name", "").lower()
		if "hoopa-unbound" in species:
			return True
		return False


class Iceball:
	def basePowerCallback(self, user, target, move):
		"""Power doubles with each consecutive hit and after Defense Curl."""
		temp = getattr(user, "tempvals", {})
		hits = temp.get("iceball_hits", 0)
		bp = (getattr(move, "power", 30) or 30) * (2**hits)
		if getattr(user, "defensecurl", False):
			bp *= 2
		temp["iceball_hits"] = hits + 1
		setattr(user, "tempvals", temp)
		return bp

	def onAfterMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		state = getattr(user, "volatiles", {}).get("iceball")
		if state and state.get("hitCount", 0) == 5 and state.get("contactHitCount", 0) < 5:
			if hasattr(user, "volatiles"):
				user.volatiles["rolloutstorage"] = {"contactHitCount": state.get("contactHitCount", 0)}
		return True

	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		if user:
			temp = getattr(user, "tempvals", {})
			hits = temp.get("iceball_hits", 0)
			if move:
				move.hit = hits + 1
				move.is_multi_turn = True

	def onResidual(self, *args, **kwargs):
		target = args[0] if args else None
		if target and getattr(target, "last_move", {}).get("id") == "struggle":
			getattr(target, "volatiles", {}).pop("iceball", None)
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "tempvals"):
			user.tempvals["iceball_hits"] = 0
		return True


class Iceburn:
	def onTryMove(self, *args, **kwargs):
		"""Handle Ice Burn as a two-turn move."""
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		vol = getattr(user, "volatiles", {})
		if vol.get("iceburn"):
			vol.pop("iceburn", None)
			user.volatiles = vol
			return True
		vol["iceburn"] = True
		user.volatiles = vol
		return False


class Icespinner:
	def onAfterHit(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else kwargs.get("target")
		source = args[0] if args else kwargs.get("user")
		battle = kwargs.get("battle")
		if source and getattr(source, "hp", 0) > 0:
			field = getattr(battle, "field", None)
			if field and hasattr(field, "terrain"):
				field.terrain = None
		return True

	def onAfterSubDamage(self, *args, **kwargs):
		return self.onAfterHit(*args, **kwargs)


class Imprison:
	def onFoeBeforeMove(self, *args, **kwargs):
		pokemon = kwargs.get("pokemon")
		return not _imprison_blocks(pokemon, kwargs.get("move"), kwargs.get("battle"))

	def onFoeDisableMove(self, *args, **kwargs):
		pokemon = args[0] if args else kwargs.get("pokemon")
		move = args[1] if len(args) > 1 else kwargs.get("move")
		return _imprison_blocks(pokemon, move, kwargs.get("battle"))

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["imprison"] = True
		return True


class Incinerate:
	def onHit(self, user, target, battle):
		"""Destroy held berries for all opposing active Pokemon."""
		targets = _iter_opposing_active_pokemon(battle, user) or ([target] if target else [])
		for mon in targets:
			item = getattr(mon, "item", None) or getattr(mon, "held_item", None)
			if not _is_berry(item):
				continue
			if battle and hasattr(battle, "remove_item"):
				battle.remove_item(mon, source=user, effect="move:incinerate")
			elif hasattr(mon, "set_item"):
				mon.set_item(None)
			else:
				setattr(mon, "item", None)
				setattr(mon, "held_item", None)
		return True


class Infernalparade:
	def basePowerCallback(self, user, target, move):
		"""Double power if the target is statused."""
		if getattr(target, "status", None):
			return (getattr(move, "power", 0) or 0) * 2
		return getattr(move, "power", 0)


class Ingrain:
	def onDragOut(self, *args, **kwargs):
		return False

	def onResidual(self, *args, **kwargs):
		user = args[0] if args else None
		if not user:
			return False
		max_hp = getattr(user, "max_hp", 0)
		heal = max_hp // 16
		user.hp = min(getattr(user, "hp", 0) + heal, max_hp)
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["ingrain"] = True
		return True

	def onTrapPokemon(self, *args, **kwargs):
		pokemon = args[0] if args else kwargs.get("pokemon")
		if pokemon and hasattr(pokemon, "volatiles"):
			pokemon.volatiles["trapped"] = True
		return True


class Instruct:
	def onHit(self, user, target, battle):
		"""Force the target to repeat its last used move."""
		move = getattr(target, "last_move", None)
		if not move:
			return False
		if _normalize_key(getattr(move, "name", "")) == "instruct":
			return False
		known = _battle_move_from_name(getattr(move, "name", ""))
		definition = known or move
		raw = getattr(definition, "raw", {}) or {}
		flags = raw.get("flags", {})
		if flags.get("failinstruct") or flags.get("charge") or flags.get("recharge"):
			return False
		if known is not None and battle is not None and hasattr(battle, "run_called_move"):
			before = len(getattr(battle, "called_moves", []))
			battle.run_called_move(target, move, None, spend_pp=True)
			return len(getattr(battle, "called_moves", [])) > before
		return bool(_execute_called_move(move, target, target, battle))


class Iondeluge:
	def onFieldStart(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field:
			pw = getattr(field, "pseudo_weather", {})
			if not isinstance(pw.get("iondeluge"), dict):
				pw["iondeluge"] = {"duration": 1}
			field.pseudo_weather = pw
		return True

	def onFieldResidual(self, field):
		field.pseudo_weather.pop("iondeluge", None)

	def onModifyType(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		if move and getattr(move, "type", "").lower() == "normal":
			move.type = "Electric"


class Ivycudgel:
	def onModifyType(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		species = getattr(getattr(user, "species", None), "name", "") if user else ""
		if "wellspring" in species.lower():
			move.type = "Water"
		elif "hearthflame" in species.lower():
			move.type = "Fire"
		elif "cornerstone" in species.lower():
			move.type = "Rock"

	def onPrepareHit(self, *args, **kwargs):
		return True


class Jawlock:
	def onHit(self, user, target, battle):
		"""Trap both the user and the target."""
		for mon in (user, target):
			if hasattr(mon, "volatiles"):
				mon.volatiles["trapped"] = True
		return True


class Judgment:
	def onModifyType(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		if not (move and user):
			return
		item = getattr(user, "item", None) or getattr(user, "held_item", None)
		if item and hasattr(item, "onPlate"):
			move.type = getattr(item, "onPlate")


class Jumpkick:
	def onMoveFail(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		recoil = getattr(user, "max_hp", 0) // 2
		user.hp = max(0, getattr(user, "hp", 0) - recoil)
		return True


class Junglehealing:
	def onHit(self, user, target, battle):
		"""Heal all allies and cure their status."""
		party = getattr(user, "party", [user])
		for mon in party:
			max_hp = getattr(mon, "max_hp", 0)
			heal = max_hp // 4
			mon.hp = min(getattr(mon, "hp", 0) + heal, max_hp)
			if hasattr(mon, "setStatus"):
				mon.setStatus(0)
		return True


class Kingsshield:
	def onHit(self, user, target, battle):
		"""Protect the user and lower Attack on contact."""
		if hasattr(user, "volatiles"):
			user.volatiles["protect"] = True
			user.volatiles["kingsshield"] = True
		return True

	def onPrepareHit(self, *args, **kwargs):
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["protect"] = True
		return True

	def onTryHit(self, *args, **kwargs):
		"""Block the incoming move like Protect."""
		return False


class Knockoff:
	def onAfterHit(self, *args, **kwargs):
		target = kwargs.get("target") or (args[0] if args else None)
		source = kwargs.get("source") or (args[1] if len(args) > 1 else None)
		battle = args[2] if len(args) > 2 else kwargs.get("battle") or getattr(target, "battle", None)
		if source and getattr(source, "hp", 0) <= 0:
			return True
		if battle and hasattr(battle, "remove_item"):
			battle.remove_item(target, source=source, effect="move:knockoff")
		return True

	def onBasePower(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		item = getattr(target, "item", None) or getattr(target, "held_item", None)
		if item:
			return int(power * 1.5)
		return power


class Laserfocus:
	def onEnd(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user and hasattr(user, "volatiles"):
			user.volatiles.pop("laserfocus", None)
		return True

	def onModifyCritRatio(self, *args, **kwargs):
		return 5

	def onRestart(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user and hasattr(user, "volatiles"):
			user.volatiles["laserfocus"] = True
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["laserfocus"] = True
		return True


class Lashout:
	def onBasePower(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		if user and getattr(user, "statsLoweredThisTurn", False):
			return power * 2
		return power


class Lastresort:
	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		if not user or not getattr(user, "moves", None):
			return False
		if len(user.moves) < 2:
			return False
		has_lr = False
		used = set((getattr(user, "tempvals", {}) or {}).get("moves_used_since_entry", []))
		for mv in user.moves:
			move_id = _normalize_key(getattr(mv, "name", mv))
			if move_id == "lastresort":
				has_lr = True
				continue
			if move_id not in used and not getattr(mv, "used", False):
				return False
		return has_lr


class Lastrespects:
	def basePowerCallback(self, user, target, move):
		"""Increase power for each fainted ally."""
		party = getattr(user, "party", [user])
		fainted = sum(1 for p in party if p is not user and getattr(p, "hp", 0) <= 0)
		return 50 + 50 * fainted


class Leechseed:
	def onResidual(self, *args, **kwargs):
		target = args[0] if args else None
		if not target:
			return False
		source = getattr(target, "volatiles", {}).get("leechseed")
		if not source:
			return True
		if getattr(source, "hp", 0) <= 0:
			if hasattr(target, "volatiles"):
				target.volatiles.pop("leechseed", None)
			return True
		damage = getattr(target, "max_hp", 0) // 8
		target.hp = max(0, getattr(target, "hp", 0) - damage)
		if hasattr(source, "hp"):
			source.hp = min(getattr(source, "hp", 0) + damage, getattr(source, "max_hp", 0))
		if getattr(target, "hp", 0) <= 0 and hasattr(target, "volatiles"):
			target.volatiles.pop("leechseed", None)
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		target = args[1] if len(args) > 1 else None
		if target and hasattr(target, "volatiles"):
			target.volatiles["leechseed"] = user
		return True

	def onTryImmunity(self, *args, **kwargs):
		target = args[0] if args else kwargs.get("target")
		types = [t.lower() for t in getattr(target, "types", [])] if target else []
		return "grass" not in types


class Lightscreen:
	def durationCallback(self, *args, **kwargs):
		from pokemon.battle.item_effects import HeldItemRules
		source = args[1] if len(args) > 1 else kwargs.get("source")
		return HeldItemRules.field_duration(source, "lightclay")

	def onAnyModifyDamage(self, *args, **kwargs):
		damage = args[0] if args else kwargs.get("damage")
		source = args[1] if len(args) > 1 else kwargs.get("source")
		target = args[2] if len(args) > 2 else kwargs.get("target")
		move = args[3] if len(args) > 3 else kwargs.get("move")
		if not target or not source or not move or move.category != "Special":
			return damage
		if getattr(move, "infiltrates", False):
			return damage
		side = getattr(target, "side", None)
		if side and getattr(side, "screens", {}).get("lightscreen"):
			mult = 0.5
			if len(getattr(side, "active", [])) > 1:
				mult = 2 / 3
			return int(damage * mult)
		return damage

	def onSideEnd(self, *args, **kwargs):
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "screens"):
			side.screens.pop("lightscreen", None)
		return True

	def onSideStart(self, *args, **kwargs):
		"""Activate the Light Screen effect."""
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "screens"):
			side.screens["lightscreen"] = True
		return True


class Lightthatburnsthesky:
	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		if user and move:
			if getattr(user, "atk", 0) > getattr(user, "spa", 0):
				move.category = "Physical"
			else:
				move.category = "Special"


class Lockon:
	def onHit(self, user, target, battle):
		"""Ensure the user's next move hits the target."""
		if hasattr(user, "volatiles"):
			from pokemon.battle.accuracy import MoveAccuracy
			user.volatiles["lockon"] = {"target_ref": MoveAccuracy.reference(target), "duration": 2}
		return True

	def onSourceAccuracy(self, *args, **kwargs):
		return None  # MoveAccuracy resolves the matching stable target.

	def onSourceInvulnerability(self, *args, **kwargs):
		return None  # The ordinary invulnerability gate checks the same lock.

	def onResidual(self, pokemon, battle=None):
		state = getattr(pokemon, "volatiles", {}).get("lockon")
		if isinstance(state, dict):
			state["duration"] = state.get("duration", 0) - 1
			if state["duration"] <= 0:
				pokemon.volatiles.pop("lockon", None)

	def onTryHit(self, *args, **kwargs):
		"""Always succeeds, setting up the lock-on effect."""
		return True


class Lowkick:
	def basePowerCallback(self, user, target, move):
		"""Scale power with the target's weight."""
		wt = _effective_weight(target) * 10
		if wt >= 2000:
			return 120
		if wt >= 1000:
			return 100
		if wt >= 500:
			return 80
		if wt >= 250:
			return 60
		if wt >= 100:
			return 40
		return 20

	def onTryHit(self, *args, **kwargs):
		"""Fail on Dynamaxed targets."""
		target = args[0] if args else None
		if getattr(target, "volatiles", {}).get("dynamax"):
			return False
		return True


class Luckychant:
	def onSideEnd(self, *args, **kwargs):
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "screens"):
			side.screens.pop("luckychant", None)
		return True

	def onSideStart(self, *args, **kwargs):
		"""Prevent critical hits against this side for a few turns."""
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "screens"):
			side.screens["luckychant"] = True
		return True


class Lunarblessing:
	def onHit(self, user, target, battle):
		"""Heal and cure status of all allies."""
		party = getattr(user, "party", [user])
		for mon in party:
			max_hp = getattr(mon, "max_hp", 0)
			heal = max_hp // 3
			mon.hp = min(getattr(mon, "hp", 0) + heal, max_hp)
			if hasattr(mon, "setStatus"):
				mon.setStatus(0)
		return True


class Lunardance:
	def onSwap(self, *args, **kwargs):
		pokemon = args[0] if args else None
		battle = kwargs.get("battle")
		if battle is None:
			battle = getattr(pokemon, "battle", None)
		if pokemon and not getattr(pokemon, "is_fainted", False):
			move_slots = getattr(pokemon, "move_slots", None) or getattr(pokemon, "moves", [])
			def _max_pp(slot):
				return getattr(slot, "max_pp", getattr(slot, "maxpp", getattr(slot, "pp", 0)))
			needs_heal = (
				getattr(pokemon, "hp", 0) < getattr(pokemon, "max_hp", getattr(pokemon, "hp", 0))
				or bool(getattr(pokemon, "status", 0))
				or (battle.has_depleted_pp(pokemon) if callable(getattr(battle, "has_depleted_pp", None))
					else any(getattr(slot, "pp", 0) < _max_pp(slot) for slot in move_slots))
			)
			if not needs_heal:
				return True
			max_hp = getattr(pokemon, "max_hp", 0)
			pokemon.hp = max_hp
			if hasattr(pokemon, "clearStatus"):
				pokemon.clearStatus(battle=battle, effect="move:lunardance")
			elif hasattr(pokemon, "setStatus"):
				pokemon.setStatus(0)
			if callable(getattr(battle, "restore_move_pp", None)):
				battle.restore_move_pp(pokemon)
			else:
				for slot in move_slots:
					slot.pp = _max_pp(slot)
			if battle and hasattr(battle, "remove_slot_condition"):
				battle.remove_slot_condition(pokemon, "lunardance")
		return True

	def onTryHit(self, *args, **kwargs):
		"""Require a living inactive replacement before sacrificing the user."""
		user = args[0] if args else None
		return _sacrifice_has_replacement(user, kwargs.get("battle") or getattr(user, "battle", None))


class Magiccoat:
	def onAllyTryHitSide(self, *args, **kwargs):
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["magiccoat"] = True
		return True

	def onTryHit(self, *args, **kwargs):
		"""Reflect status moves back at the attacker."""
		move = kwargs.get("move")
		if move and getattr(move, "category", "") == "Status":
			return False
		return True


class Magicpowder:
	def onHit(self, user, target, battle):
		"""Change the target's type to Psychic."""
		if hasattr(target, "types"):
			target.types = ["Psychic"]
		return True


class Magicroom:
	def durationCallback(self, *args, **kwargs):
		source = args[1] if len(args) > 1 else kwargs.get("source")
		if _effect_id(getattr(source, "ability", None)) == "persistent":
			return 7
		return 5

	def onFieldEnd(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field and hasattr(field, "pseudo_weather"):
			field.pseudo_weather.pop("magicroom", None)
		return True

	def onFieldRestart(self, *args, **kwargs):
		field = kwargs.get("field") or args[0] if args else None
		if hasattr(field, "remove_pseudo_weather"):
			field.remove_pseudo_weather("magicroom")

	def onFieldStart(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field:
			pw = getattr(field, "pseudo_weather", {})
			pw["magicroom"] = True
			field.pseudo_weather = pw
		return True


class Magneticflux:
	def onHitSide(self, user, battle):
		"""Boost defenses of allies with Plus or Minus."""
		side = getattr(user, "side", None)
		if not side:
			return False
		for mon in getattr(side, "active", []):
			ability = _effect_id(getattr(mon, "ability", None))
			if ability in {"plus", "minus"}:
				apply_boost(mon, {"def": 1, "spd": 1})
		return True


class Magnetrise:
	def onEnd(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user and hasattr(user, "volatiles"):
			user.volatiles.pop("magnetrise", None)
		return True

	def onImmunity(self, *args, **kwargs):
		typ = args[0] if args else kwargs.get("type")
		if typ and str(typ).lower() == "ground":
			return False
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["magnetrise"] = True
		return True

	def onTry(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		battle = args[3] if len(args) > 3 else kwargs.get("battle")

		vols = getattr(user, "volatiles", {}) if user else {}
		if vols.get("smackdown") or vols.get("ingrain"):
			return False

		field = getattr(battle, "field", None) if battle else None
		if field and getattr(field, "pseudo_weather", {}).get("Gravity"):
			return False

		return True


class Magnitude:
	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		battle = kwargs.get("battle")
		if len(args) > 3:
			battle = args[3] or battle
		import random as _r

		choices = [(4, 10), (5, 30), (6, 50), (7, 70), (8, 90), (9, 110), (10, 150)]
		rng = getattr(battle, "rng", None)
		level, power = rng.choice(choices) if rng and hasattr(rng, "choice") else _r.choice(choices)
		if move:
			move.magnitude = level
			move.power = power

	def onUseMoveMessage(self, *args, **kwargs):
		return True


class Matblock:
	"""Protect against damaging hits only on the carrier's first action turn."""
	def onSideStart(self, side=None, *args, **kwargs):
		if side:
			side.volatiles["matblock"] = True
		return True
	def onTry(self, user=None, target=None, move=None, battle=None):
		if user is None:
			return False
		entered = getattr(user, "tempvals", {}).get("entry_action_turn")
		return (entered == battle.turn_count if entered is not None and battle else getattr(user, "active_move_actions", 1) <= 1)
	def onTryHit(self, target=None, source=None, move=None, **kwargs):
		if move is None or _normalize_key(getattr(move, "name", "")) == "matblock":
			return True
		return (getattr(move, "category", None) or getattr(move, "raw", {}).get("category")) == "Status"


class Maxairstream:
	def onHit(self, user, target, battle):
		"""Raise the user's Speed after dealing damage."""
		apply_boost(user, {"spe": 1})
		return True


class Maxdarkness:
	def onHit(self, user, target, battle):
		"""Lower the target's Special Defense."""
		apply_boost(target, {"spd": -1})
		return True


class Maxflare:
	def onHit(self, user, target, battle):
		"""Summon sunny weather."""
		field = getattr(battle, "field", None)
		if field and hasattr(field, "set_weather"):
			field.set_weather("SunnyDay")
		return True


class Maxflutterby:
	def onHit(self, user, target, battle):
		"""Lower the target's Special Attack."""
		apply_boost(target, {"spa": -1})
		return True


class Maxgeyser:
	def onHit(self, user, target, battle):
		"""Summon rain weather."""
		field = getattr(battle, "field", None)
		if field and hasattr(field, "set_weather"):
			field.set_weather("RainDance")
		return True


class Maxguard:
	def onHit(self, user, target, battle):
		"""Protect the user for the turn."""
		if hasattr(user, "volatiles"):
			user.volatiles["protect"] = True
		return True

	def onPrepareHit(self, *args, **kwargs):
		return True

	def onStart(self, *args, **kwargs):
		return True

	def onTryHit(self, *args, **kwargs):
		"""Block the incoming move."""
		return False


class Maxhailstorm:
	def onHit(self, user, target, battle):
		"""Summon hail weather."""
		field = getattr(battle, "field", None)
		if field and hasattr(field, "set_weather"):
			field.set_weather("Hail")
		return True


class Maxknuckle:
	def onHit(self, user, target, battle):
		"""Raise the user's Attack."""
		apply_boost(user, {"atk": 1})
		return True


class Maxlightning:
	def onHit(self, user, target, battle):
		"""Set Electric Terrain."""
		field = getattr(battle, "field", None)
		if field and hasattr(field, "set_terrain"):
			field.set_terrain("Electric")
		return True


class Maxmindstorm:
	def onHit(self, user, target, battle):
		"""Set Psychic Terrain."""
		field = getattr(battle, "field", None)
		if field and hasattr(field, "set_terrain"):
			field.set_terrain("Psychic")
		return True


class Maxooze:
	def onHit(self, user, target, battle):
		"""Raise the user's Special Attack."""
		apply_boost(user, {"spa": 1})
		return True


class Maxovergrowth:
	def onHit(self, user, target, battle):
		"""Set Grassy Terrain."""
		field = getattr(battle, "field", None)
		if field and hasattr(field, "set_terrain"):
			field.set_terrain("Grassy")
		return True


class Maxphantasm:
	def onHit(self, user, target, battle):
		"""Lower the target's Defense."""
		apply_boost(target, {"def": -1})
		return True


class Maxquake:
	def onHit(self, user, target, battle):
		"""Raise the user's Special Defense."""
		apply_boost(user, {"spd": 1})
		return True


class Maxrockfall:
	def onHit(self, user, target, battle):
		"""Summon a sandstorm."""
		field = getattr(battle, "field", None)
		if field and hasattr(field, "set_weather"):
			field.set_weather("Sandstorm")
		return True


class Maxstarfall:
	def onHit(self, user, target, battle):
		"""Set Misty Terrain."""
		field = getattr(battle, "field", None)
		if field and hasattr(field, "set_terrain"):
			field.set_terrain("Misty")
		return True


class Maxsteelspike:
	def onHit(self, user, target, battle):
		"""Raise the user's Defense."""
		apply_boost(user, {"def": 1})
		return True


class Maxstrike:
	def onHit(self, user, target, battle):
		"""Lower the target's Speed."""
		apply_boost(target, {"spe": -1})
		return True


class Maxwyrmwind:
	def onHit(self, user, target, battle):
		"""Lower the target's Attack."""
		apply_boost(target, {"atk": -1})
		return True


class Meanlook:
	def onHit(self, user, target, battle):
		"""Prevent the target from switching."""
		if hasattr(target, "volatiles"):
			target.volatiles["trapped"] = True
		return True


class Mefirst:
	def onBasePower(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		return int(power * 1.5)

	def onTryHit(self, *args, **kwargs):
		"""Use the target's chosen move first at boosted power."""
		target = args[0] if args else None
		source = args[1] if len(args) > 1 else kwargs.get("source")
		battle = kwargs.get("battle")
		move = battle.pending_move(target) if battle and hasattr(battle, "pending_move") else None
		if not source or not move:
			return False
		raw = getattr(move, "raw", {}) or {}
		if str(raw.get("category", getattr(move, "category", ""))).lower() == "status":
			return False
		return bool(_execute_called_move(move, source, target, battle, power_multiplier=1.5))


class Metalburst:
	def damageCallback(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		hit = _retaliation_hit(user, kwargs.get("battle"))
		return int(hit.damage * 1.5) if hit else 0

	def onModifyTarget(self, *args, **kwargs):
		user = args[0] if args else None
		last = getattr(user, "tempvals", {}).get("last_damaged_by") if user else None
		if isinstance(last, dict):
			return last.get("source")

	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		return _retaliation_hit(user, kwargs.get("battle")) is not None


class Meteorbeam:
	def onTryMove(self, *args, **kwargs):
		"""Handle Meteor Beam as a two-turn move."""
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		vol = getattr(user, "volatiles", {})
		if vol.get("meteorbeam"):
			vol.pop("meteorbeam", None)
			user.volatiles = vol
			return True
		vol["meteorbeam"] = True
		user.volatiles = vol
		return False


class Metronome:
	def onHit(self, user, target, battle):
		"""Use a random move from the battle's metronome pool."""
		pool = getattr(battle, "metronome_pool", None)
		if pool is None:
			from pokemon.dex import MOVEDEX
			pool = sorted({entry.raw.get("name", entry.name) for entry in MOVEDEX.values()
			               if entry.raw.get("flags", {}).get("metronome") and not entry.raw.get("isZ") and not entry.raw.get("isMax")})
		if not pool:
			return False
		move = getattr(battle, "rng", None).choice(pool) if getattr(battle, "rng", None) else choice(pool)
		return bool(_execute_called_move(move, user, target, battle))


class Mimic:
	"""Use isolated copy state and the canonical writer where required."""
	def onHit(self, user, target, battle):
		from pokemon.battle.copied_moves import BattleCopyState
		return BattleCopyState.mimic(user, target)


class Mindblown:
	def onAfterMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user:
			recoil = getattr(user, "max_hp", 0) // 2
			user.hp = max(0, getattr(user, "hp", 0) - recoil)
		return True


class Mindreader:
	def onHit(self, user, target, battle):
		"""Ensure the user's next move will hit the target."""
		return Lockon().onHit(user, target, battle)

	def onTryHit(self, *args, **kwargs):
		return True


class Minimize:
	def onAccuracy(self, *args, **kwargs):
		return True

	def onSourceModifyDamage(self, *args, **kwargs):
		damage = args[0] if args else kwargs.get("damage")
		move = args[3] if len(args) > 3 else kwargs.get("move")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		if target and getattr(target, "volatiles", {}).get("minimize") and move:
			mname = getattr(move, "name", "").replace(" ", "").lower()
			if mname in {"stomp", "steamroller", "dragonrush", "flyingpress", "maliciousmoonsault"}:
				try:
					return int(damage * 2)
				except Exception:
					return damage
		return damage


class Miracleeye:
	def onModifyBoost(self, *args, **kwargs):
		boosts = args[0] if args else kwargs.get("boosts", {})
		if isinstance(boosts, dict) and "evasion" in boosts:
			boosts["evasion"] = 0
		return boosts

	def onNegateImmunity(self, *args, **kwargs):
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		target = args[1] if len(args) > 1 else None
		if target and hasattr(target, "volatiles"):
			target.volatiles["miracleeye"] = True
		return True

	def onTryHit(self, *args, **kwargs):
		"""Allow Psychic moves to hit Dark types and negate evasion boosts."""
		return True


class Mirrorcoat:
	def beforeTurnCallback(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["mirrorcoat"] = {"slot": None, "damage": 0}
		return True

	def damageCallback(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		hit = _retaliation_hit(user, kwargs.get("battle"), category="Special")
		return hit.damage * 2 if hit else 0

	def onDamagingHit(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else None
		source = args[2] if len(args) > 2 else None
		move = args[3] if len(args) > 3 else None
		if target and source and getattr(move, "category", "") == "Special":
			vol = getattr(target, "volatiles", {}).get("mirrorcoat")
			if vol is not None:
				vol["slot"] = source
				vol["damage"] = getattr(move, "damage", 0) * 2

	def onRedirectTarget(self, *args, **kwargs):
		user = args[0] if args else None
		vol = getattr(user, "volatiles", {}).get("mirrorcoat") if user else None
		if vol:
			return vol.get("slot")

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "tempvals"):
			user.tempvals["mirrorcoat_damage"] = 0
		return True

	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		return _retaliation_hit(user, kwargs.get("battle"), category="Special") is not None


class Mirrormove:
	def onTryHit(self, *args, **kwargs):
		"""Use the last move used by the target."""
		target = args[0] if args else None
		source = args[1] if len(args) > 1 else kwargs.get("source")
		battle = kwargs.get("battle")
		move = getattr(target, "last_move", None)
		if not source or not move:
			return False
		if _normalize_key(getattr(move, "name", "")) == "mirrormove":
			return False
		return bool(_execute_called_move(move, source, target, battle))


class Mist:
	def onSideEnd(self, *args, **kwargs):
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "screens"):
			side.screens.pop("mist", None)
		return True

	def onSideStart(self, *args, **kwargs):
		"""Prevent stat reduction on this side for five turns."""
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "screens"):
			side.screens["mist"] = True
			if not hasattr(side, "conditions"):
				side.conditions = {}
			state = side.conditions.setdefault("mist", {"id": "mist"})
			state.setdefault("duration", 5)
			state.setdefault("source", args[1] if len(args) > 1 else kwargs.get("source"))
			state.setdefault("sourceEffect", "move:mist")
		return True

	def onTryBoost(self, *args, **kwargs):
		boosts = args[0] if args else kwargs.get("boosts")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		side = getattr(target, "side", None)
		source = args[2] if len(args) > 2 else kwargs.get("source")
		effect = args[3] if len(args) > 3 else kwargs.get("effect")
		if not isinstance(boosts, dict) or not side or not source or source is target:
			return boosts
		state = getattr(side, "conditions", {}).get("mist")
		if not isinstance(state, dict) or type(state.get("duration")) is not int or state["duration"] <= 0:
			return boosts
		battle = kwargs.get("battle") or getattr(target, "battle", None)
		if battle is not None:
			own, other = battle.participant_for(target), battle.participant_for(source)
			if own is None or other is None or battle._allied(own, other):
				return boosts
		from pokemon.battle.effect_context import EffectContext

		move_effect = getattr(effect, "effectType", None) == "Move"
		if move_effect and (getattr(effect, "infiltrates", False)
				or EffectContext.key(EffectContext.ability(source)) == "infiltrator"):
			return boosts
		return {stat: amount for stat, amount in boosts.items() if amount >= 0}


class Mistyexplosion:
	def onBasePower(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		terrain = getattr(user, "terrain", None)
		grounded = getattr(user, "grounded", True)
		if terrain == "mistyterrain" and grounded:
			return int(power * 1.5)
		return power


class Mistyterrain:
	def durationCallback(self, *args, **kwargs):
		from pokemon.battle.item_effects import HeldItemRules
		source = args[1] if len(args) > 1 else kwargs.get("source")
		return HeldItemRules.field_duration(source, "terrainextender")

	def onBasePower(self, *args, **kwargs):
		attacker = args[0] if args else kwargs.get("user")
		defender = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		if move and getattr(move, "type", "").lower() == "dragon" and defender and getattr(defender, "grounded", True):
			return int(power * 0.5)
		return power

	def onFieldEnd(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field and hasattr(field, "terrain"):
			field.terrain = None
		return True

	def onFieldStart(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field is not None:
			field.terrain = "mistyterrain"
		return True

	def onSetStatus(self, *args, **kwargs):
		status = args[0] if args else kwargs.get("status")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		if target and getattr(target, "grounded", True):
			return False
		return True

	def onTryAddVolatile(self, *args, **kwargs):
		status = args[0] if args else kwargs.get("status")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		if target and getattr(target, "grounded", True) and status in {"yawn", "confusion"}:
			return False
		return True


class Moonlight:
	def onHit(self, user, target, battle):
		"""Heal the user based on weather conditions."""
		max_hp = getattr(user, "max_hp", 0)
		heal = max_hp // 2
		weather = getattr(getattr(battle, "field", None), "weather", None)
		if weather == "SunnyDay":
			heal = int(max_hp * 2 / 3)
		elif weather in {"RainDance", "Sandstorm", "Hail"}:
			heal = max_hp // 4
		user.hp = min(getattr(user, "hp", 0) + heal, max_hp)
		return True


class Morningsun:
	def onHit(self, user, target, battle):
		"""Heal the user similar to Moonlight."""
		max_hp = getattr(user, "max_hp", 0)
		heal = max_hp // 2
		weather = getattr(getattr(battle, "field", None), "weather", None)
		if weather == "SunnyDay":
			heal = int(max_hp * 2 / 3)
		elif weather in {"RainDance", "Sandstorm", "Hail"}:
			heal = max_hp // 4
		user.hp = min(getattr(user, "hp", 0) + heal, max_hp)
		return True


class Mortalspin:
	def onAfterHit(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		if user:
			side = getattr(user, "side", None)
			if side and hasattr(side, "hazards"):
				for h in ("spikes", "stealthrock", "toxicspikes", "stickyweb"):
					side.hazards.pop(h, None)
		if target and getattr(target, "status", None) is None:
			if hasattr(target, "setStatus"):
				target.setStatus("psn")
		return True

	def onAfterSubDamage(self, *args, **kwargs):
		return self.onAfterHit(*args, **kwargs)


class Mudsport:
	def onBasePower(self, *args, **kwargs):
		attacker = args[0] if args else kwargs.get("user")
		defender = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		if move and getattr(move, "type", "").lower() == "electric":
			return int(power * 0.33)
		return power

	def onFieldEnd(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field and hasattr(field, "pseudo_weather"):
			field.pseudo_weather.pop("mudsport", None)
		return True

	def onFieldStart(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field:
			pw = getattr(field, "pseudo_weather", {})
			pw["mudsport"] = True
			field.pseudo_weather = pw
		return True


class Multiattack:
	def onModifyType(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		item = getattr(user, "item", None) or getattr(user, "held_item", None)
		if move and item and hasattr(item, "memory_type"):
			move.type = getattr(item, "memory_type")


class Naturalgift:
	def onModifyType(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		item = getattr(user, "item", None) or getattr(user, "held_item", None)
		if move and item:
			move.type = getattr(item, "natural_type", getattr(move, "type", None))

	def onPrepareHit(self, *args, **kwargs):
		user = args[0] if args else None
		move = args[2] if len(args) > 2 else kwargs.get("move")
		from pokemon.battle.effect_context import EffectContext
		item = EffectContext.item(user)
		if not item or not _is_berry(item):
			return False
		if move:
			move.type = getattr(item, "natural_type", getattr(move, "type", None))
			move.power = getattr(item, "natural_power", getattr(move, "power", 0))
		battle = kwargs.get("battle") or getattr(user, "battle", None)
		if battle is not None and hasattr(battle, "remove_item"):
			return battle.remove_item(user, source=user, effect="move:naturalgift", used=True) is not None
		user.item = None
		return True


class Naturepower:
	def onTryHit(self, *args, **kwargs):
		"""Choose and use a move based on the active terrain."""
		target = args[0] if args else None
		source = args[1] if len(args) > 1 else kwargs.get("source")
		battle = kwargs.get("battle")
		if not source:
			return False
		override = getattr(battle, "nature_power_move", None) if battle else None
		if override is not None:
			return bool(_execute_called_move(override, source, target, battle))
		field = getattr(battle, "field", None)
		terrain = getattr(field, "terrain", None) if field else None
		called = {
			"electricterrain": "Thunderbolt",
			"grassyterrain": "Energy Ball",
			"mistyterrain": "Moonblast",
			"psychicterrain": "Psychic",
		}.get(_normalize_key(terrain), "Tri Attack")
		return bool(_execute_called_move(called, source, target, battle))


class Naturesmadness:
	def damageCallback(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else kwargs.get("target")
		if not target:
			return 0
		hp = getattr(target, "hp", 0)
		return max(1, hp // 2)


class Nightmare:
	def onResidual(self, *args, **kwargs):
		target = args[0] if args else None
		if not target:
			return False
		if getattr(target, "status", None) == "slp":
			dmg = getattr(target, "max_hp", 0) // 4
			target.hp = max(0, getattr(target, "hp", 0) - dmg)
		return True

	def onStart(self, *args, **kwargs):
		target = args[0] if args else None
		if target and hasattr(target, "volatiles"):
			target.volatiles["nightmare"] = True
		return True


class Noretreat:
	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["noretreat"] = True
		return True

	def onTrapPokemon(self, *args, **kwargs):
		pokemon = args[0] if args else kwargs.get("pokemon")
		if pokemon and getattr(pokemon, "volatiles", {}).get("noretreat"):
			pokemon.volatiles["trapped"] = True
		return True

	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		if user and getattr(user, "volatiles", {}).get("noretreat"):
			return False
		if user and getattr(user, "volatiles", {}).get("trapped"):
			return True
		return True


class Obstruct:
	def onHit(self, user, target, battle):
		"""Protect the user and harshly lower contact attackers' Defense."""
		if hasattr(user, "volatiles"):
			user.volatiles["protect"] = True
			user.volatiles["obstruct"] = True
		return True

	def onPrepareHit(self, *args, **kwargs):
		return True

	def onStart(self, *args, **kwargs):
		return True

	def onTryHit(self, *args, **kwargs):
		"""Block the incoming move like Protect."""
		return False


class Octolock:
	def onResidual(self, *args, **kwargs):
		target = args[0] if args else None
		user = getattr(target, "volatiles", {}).get("octolock") if target else None
		if not target or not user:
			return False
		if not getattr(user, "hp", 0):
			target.volatiles.pop("octolock", None)
			return True
		apply_boost(target, {"def": -1, "spd": -1})
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		target = args[1] if len(args) > 1 else None
		if target and hasattr(target, "volatiles"):
			target.volatiles["octolock"] = user
		return True

	def onTrapPokemon(self, *args, **kwargs):
		pokemon = args[0] if args else kwargs.get("pokemon")
		if pokemon and getattr(pokemon, "volatiles", {}).get("octolock"):
			pokemon.volatiles["trapped"] = True
		return True

	def onTryImmunity(self, *args, **kwargs):
		target = args[0] if args else kwargs.get("target")
		types = [t.lower() for t in getattr(target, "types", [])] if target else []
		return "ghost" not in types


class Odorsleuth:
	def onTryHit(self, *args, **kwargs):
		"""Remove the target's evasion boosts and Ghost immunity."""
		return True


class Orderup:
	def onAfterMoveSecondarySelf(self, *args, **kwargs):
		user = args[0] if args else None
		if user:
			apply_boost(user, {"atk": 1})
		return True


class Outrage:
	def onAfterMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		vol = getattr(user, "volatiles", {})
		turns = vol.get("outrage", 0)
		if not turns:
			vol["outrage"] = 2
		else:
			vol["outrage"] = turns - 1
			if vol["outrage"] <= 0:
				vol.pop("outrage", None)
				vol["confusion"] = 2
		user.volatiles = vol
		return True


class Painsplit:
	def onHit(self, user, target, battle):
		"""Average HP between user and target."""
		u_hp = getattr(user, "hp", 0)
		t_hp = getattr(target, "hp", 0)
		avg = (u_hp + t_hp) // 2
		user.hp = avg
		target.hp = avg
		return True


class Partingshot:
	def onHit(self, user, target, battle):
		"""Lower target's offenses then switch the user out."""
		apply_boost(target, {"atk": -1, "spa": -1})
		if hasattr(user, "tempvals"):
			user.tempvals["switch_out"] = True
		return True


class Payback:
	def basePowerCallback(self, user, target, move):
		"""Double power if the target already moved."""
		moved = getattr(target, "tempvals", {}).get("moved")
		base = getattr(move, "power", 0) or 0
		return base * 2 if moved else base


class Perishsong:
	"""Apply one bounded countdown to every eligible active Pokemon."""
	def onHitField(self, user, battle):
		from pokemon.battle.effect_context import EffectContext
		changed = False
		for participant in battle.participants:
			for pokemon in participant.active:
				if pokemon.hp <= 0 or EffectContext.key(EffectContext.ability(pokemon)) == "soundproof":
					continue
				if "perishsong" not in pokemon.volatiles:
					changed = battle.apply_volatile_status(pokemon, "perishsong", source=user, effect=user.last_move) or changed
		return changed
	def onStart(self, pokemon=None, *args, **kwargs):
		if pokemon:
			pokemon.volatiles["perishsong"] = {"remaining": 4}
		return True
	def onResidual(self, pokemon=None, battle=None):
		if not pokemon:
			return
		state = pokemon.volatiles.get("perishsong")
		if not isinstance(state, dict):
			state = {"remaining": int(state or 0) + 1}
			pokemon.volatiles["perishsong"] = state
		state["remaining"] -= 1
		if state["remaining"] <= 0:
			pokemon.hp = 0
			pokemon.volatiles.pop("perishsong", None)
	def onEnd(self, pokemon=None, *args, **kwargs):
		if pokemon:
			pokemon.volatiles.pop("perishsong", None)
		return True


class Petaldance:
	def onAfterMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		vol = getattr(user, "volatiles", {})
		turns = vol.get("petaldance", 0)
		if not turns:
			vol["petaldance"] = 2
		else:
			vol["petaldance"] = turns - 1
			if vol["petaldance"] <= 0:
				vol.pop("petaldance", None)
				vol["confusion"] = 2
		user.volatiles = vol
		return True


class Phantomforce:
	def onTryMove(self, *args, **kwargs):
		"""Handle Phantom Force as a two-turn move."""
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		vol = getattr(user, "volatiles", {})
		if vol.get("phantomforce"):
			vol.pop("phantomforce", None)
			user.volatiles = vol
			return True
		vol["phantomforce"] = True
		user.volatiles = vol
		return False


class Photongeyser:
	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		if user and move:
			if getattr(user, "atk", 0) > getattr(user, "spa", 0):
				move.category = "Physical"
			else:
				move.category = "Special"


class Pikapapow:
	def basePowerCallback(self, user, target, move):
		"""Power scales with the user's happiness."""
		happiness = getattr(user, "happiness", 0)
		return max(1, int((happiness * 10) / 25))


class Pluck:
	def onHit(self, user, target, battle):
		"""Eat the target's berry if it has one."""
		if battle and hasattr(battle, "eat_berry"):
			battle.eat_berry(user, target, effect="move:pluck")
		return True


class Pollenpuff:
	def onHit(self, user, target, battle):
		"""Heal allies or damage foes."""
		if getattr(user, "side", None) is getattr(target, "side", None):
			max_hp = getattr(target, "max_hp", 0)
			heal = max_hp // 2
			target.hp = min(getattr(target, "hp", 0) + heal, max_hp)
		else:
			# Damage already handled elsewhere; nothing extra here
			pass
		return True

	def onTryHit(self, *args, **kwargs):
		return True

	def onTryMove(self, *args, **kwargs):
		return True


class Poltergeist:
	def onTry(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else kwargs.get("target")
		item = None
		if target:
			item = getattr(target, "item", None) or getattr(target, "held_item", None)
		return bool(item)

	def onTryHit(self, *args, **kwargs):
		"""Fail if the target has no held item."""
		target = args[0] if args else None
		item = getattr(target, "item", None) or getattr(target, "held_item", None)
		if not item:
			return False
		return True


class Powder:
	def onStart(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else args[0] if args else kwargs.get("pokemon")
		if target and hasattr(target, "volatiles"):
			target.volatiles["powder"] = True
		return True

	def onBeforeMove(self, pokemon, move, battle=None):
		"""Explode on a Fire action, then stop that action before it attacks."""
		if str(getattr(move, "type", "")).lower() != "fire":
			return True
		from pokemon.battle.indirect_damage import IndirectEffect, apply_indirect_damage
		apply_indirect_damage(pokemon, max(1, pokemon.max_hp // 4), battle=battle,
		                      effect=IndirectEffect("powder", "Condition"))
		return False

	def onTryMove(self, *args, **kwargs):
		"""Prevent Fire-type moves while powdered."""
		move = args[1] if len(args) > 1 else kwargs.get("move")
		if move and getattr(move, "type", "").lower() == "fire":
			return False
		return True


class Powershift:
	def onCopy(self, *args, **kwargs):
		return False

	def onEnd(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user and hasattr(user, "volatiles"):
			_swap_stored_defense_attack(user)
			user.volatiles.pop("powershift", None)
		return True

	def onRestart(self, *args, **kwargs):
		return self.onEnd(*args, **kwargs)

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			_swap_stored_defense_attack(user)
			user.volatiles["powershift"] = True
		return True


class Powersplit:
	def onHit(self, user, target, battle):
		"""Average the Attack and Sp. Atk stats of user and target."""
		for stat in ["atk", "spa"]:
			u_val = _stored_battle_stat(user, stat)
			t_val = _stored_battle_stat(target, stat)
			if u_val is not None and t_val is not None:
				avg = (u_val + t_val) // 2
				_set_stored_battle_stat(user, stat, avg)
				_set_stored_battle_stat(target, stat, avg)
		return True


class Powerswap:
	def onHit(self, user, target, battle):
		"""Swap Attack and Sp. Atk stat boosts."""
		for stat in ["atk", "spa"]:
			user_boosts = getattr(user, "boosts", {})
			target_boosts = getattr(target, "boosts", {})
			u_boost = _boost_value(user_boosts, stat)
			t_boost = _boost_value(target_boosts, stat)
			_set_boost_value(user_boosts, stat, t_boost)
			_set_boost_value(target_boosts, stat, u_boost)
		return True


class Powertrick:
	def onCopy(self, *args, **kwargs):
		return False

	def onEnd(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user:
			_swap_stored_defense_attack(user)
			if hasattr(user, "volatiles"):
				user.volatiles.pop("powertrick", None)
		return True

	def onRestart(self, *args, **kwargs):
		return self.onEnd(*args, **kwargs)

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user:
			_swap_stored_defense_attack(user)
			if hasattr(user, "volatiles"):
				user.volatiles["powertrick"] = True
		return True


class Powertrip:
	def basePowerCallback(self, user, target, move):
		"""Increase power for each positive stat boost."""
		boosts = getattr(user, "boosts", {})
		positive = sum(v for v in boosts.values() if v > 0)
		return (getattr(move, "power", 0) or 0) + 20 * positive


class Present:
	def onModifyMove(self, *args, **kwargs):
		"""Choose a per-use healing or damage branch without changing the dex."""
		move = args[0] if args else kwargs.get("move")
		from random import randint

		roll = randint(1, 100)
		if move:
			move.raw = copy.deepcopy(getattr(move, "raw", {}) or {})
			move.raw.pop("heal", None)
			move.raw.pop("bypassSub", None)
			move.heal = None
			if roll <= 20:
				move.heal = 0.25
				move.power = 0
				move.raw["heal"] = [1, 4]
				move.raw["bypassSub"] = True
			elif roll <= 60:
				move.power = 40
			elif roll <= 90:
				move.power = 80
			else:
				move.power = 120
			move.raw["basePower"] = move.power


class Protect:
	def onHit(self, user, target, battle):
		"""Protect the user from moves this turn."""
		if hasattr(user, "volatiles"):
			user.volatiles["protect"] = True
		return True

	def onPrepareHit(self, *args, **kwargs):
		return True

	def onStart(self, *args, **kwargs):
		return True

	def onTryHit(self, *args, **kwargs):
		"""Block the incoming move."""
		return False


class Psyblade:
	def onBasePower(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		terrain = getattr(user, "terrain", None)
		if terrain == "electricterrain":
			return int(power * 1.5)
		return power


class Psychicfangs:
	def onTryHit(self, *args, **kwargs):
		"""Shatter the target's screens before dealing damage."""
		target = args[0] if args else None
		side = getattr(target, "side", None)
		if side and hasattr(side, "screens"):
			for screen in ("reflect", "lightscreen", "auroraveil"):
				side.screens.pop(screen, None)
		return True


class Psychicterrain:
	def durationCallback(self, *args, **kwargs):
		from pokemon.battle.item_effects import HeldItemRules
		source = args[1] if len(args) > 1 else kwargs.get("source")
		return HeldItemRules.field_duration(source, "terrainextender")

	def onBasePower(self, *args, **kwargs):
		attacker = args[0] if args else kwargs.get("user")
		defender = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		if move and getattr(move, "type", "").lower() == "psychic" and attacker and getattr(attacker, "grounded", True):
			return int(power * 1.3)
		return power

	def onFieldEnd(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field and hasattr(field, "terrain"):
			field.terrain = None
		return True

	def onFieldStart(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field is not None:
			field.terrain = "psychicterrain"
		return True

	def onTryHit(self, *args, **kwargs):
		"""Prevent priority moves from hitting grounded PokÃ©mon."""
		move = kwargs.get("move")
		if move and getattr(move, "priority", 0) > 0:
			target = args[0] if args else None
			if getattr(target, "grounded", True):
				return False
		return True


class Psychoshift:
	def onHit(self, user, target, battle):
		"""Transfer the user's status condition to the target."""
		status = getattr(user, "status", 0)
		if not status:
			return False
		if hasattr(target, "setStatus"):
			target.setStatus(status)
		if hasattr(user, "setStatus"):
			user.setStatus(0)
		return True

	def onTryHit(self, *args, **kwargs):
		return True


class Psychup:
	def onHit(self, user, target, battle):
		"""Copy the target's stat boosts."""
		boosts = getattr(target, "boosts", {})
		user.boosts = boosts.copy()
		return True


class Psywave:
	def damageCallback(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		import random as _r

		level = getattr(user, "level", 1)
		mult = _r.randint(50, 150)
		return max(1, int(level * mult / 100))


class Punishment:
	def basePowerCallback(self, user, target, move):
		"""Increase power based on target's boosts, capped at 200."""
		boosts = getattr(target, "boosts", {})
		positive = sum(v for v in boosts.values() if v > 0)
		power = 60 + 20 * positive
		return min(200, power)


class Purify:
	def onHit(self, user, target, battle):
		"""Cure the target's status and heal the user if successful."""
		if getattr(target, "status", 0):
			if hasattr(target, "setStatus"):
				target.setStatus(0)
			max_hp = getattr(user, "max_hp", 0)
			heal = max_hp // 2
			user.hp = min(getattr(user, "hp", 0) + heal, max_hp)
			return True
		return False


class Pursuit:
	def basePowerCallback(self, user, target, move):
		"""Double power if the target is switching out."""
		if getattr(target, "tempvals", {}).get("switching"):
			return (getattr(move, "power", 0) or 0) * 2
		return getattr(move, "power", 0)

	def beforeTurnCallback(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["pursuit"] = True
		return True

	def onBeforeSwitchOut(self, *args, **kwargs):
		target = args[0] if args else None
		if target and getattr(target, "volatiles", {}).get("pursuit"):
			target.tempvals["switching"] = True
		return True

	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		if move:
			move.pursuit = True

	def onTryHit(self, target, source, move):
		"""Always succeeds, even on switching targets."""
		return True


class Quash:
	def onHit(self, user, target, battle):
		"""Make the target act last this turn."""
		queue = getattr(battle, "queue", None)
		action = queue.will_move(target) if queue is not None else None
		if action is None:
			return False
		changed = queue.defer_action(action) is not False
		if changed and getattr(user, "last_move", None):
			user.last_move._queue_changed = True
		return changed


class Quickguard:
	def onHitSide(self, user, battle):
		"""Protect the user's side from priority moves for the turn."""
		side = getattr(user, "side", None)
		if side and hasattr(side, "volatiles"):
			side.volatiles["quickguard"] = True
			return True
		return False

	def onSideStart(self, *args, **kwargs):
		"""Activate Quick Guard for this side."""
		side = args[0] if args else kwargs.get("side")
		if side:
			vol = getattr(side, "volatiles", {})
			vol["quickguard"] = True
			side.volatiles = vol
		return True

	def onTry(self, *args, **kwargs):
		battle = kwargs.get("battle") if kwargs else None
		if len(args) > 3:
			battle = args[3] or battle
		if battle and getattr(battle, "queue", None) and hasattr(battle.queue, "willAct"):
			try:
				return bool(battle.queue.willAct())
			except Exception:
				return True
		return True

	def onTryHit(self, target, source, move):
		"""Block priority moves for the turn."""
		if getattr(move, "effective_priority", getattr(move, "priority", 0)) > 0:
			return False
		return True


class Rage:
	def onBeforeMove(self, *args, **kwargs):
		return True

	def onHit(self, user, target, battle):
		"""Boost the user's Attack when hit."""
		apply_boost(user, {"atk": 1})
		if hasattr(user, "volatiles"):
			user.volatiles["rage"] = True
		return True

	def onStart(self, *args, **kwargs):
		return True


class Ragefist:
	def basePowerCallback(self, user, target, move):
		"""Increase power based on times the user was hit."""
		times = getattr(user, "times_attacked", 0)
		return min(350, 50 + 50 * times)


class Ragepowder:
	def onFoeRedirectTarget(self, *args, **kwargs):
		user = args[0] if args else None
		return user

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["ragepowder"] = True
		return True

	def onTry(self, *args, **kwargs):
		battle = kwargs.get("battle") if kwargs else None
		if len(args) > 3:
			battle = args[3] or battle
		if not battle:
			return True
		participants = getattr(battle, "participants", [])
		multi = getattr(battle, 'multi', False) or any(len(getattr(p, "active", [])) > 1 for p in participants)
		return multi


class Ragingbull:
	def onModifyType(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		species = getattr(getattr(user, "species", None), "name", "") if user else ""
		lower = species.lower()
		if "blaze" in lower:
			move.type = "Fire"
		elif "aqua" in lower:
			move.type = "Water"
		else:
			move.type = "Normal"

	def onTryHit(self, target, source, move):
		"""Remove the target's screens before damage."""
		side = getattr(target, "side", None)
		if side and hasattr(side, "screens"):
			for screen in ("reflect", "lightscreen", "auroraveil"):
				side.screens.pop(screen, None)
		return True


class Ragingfury:
	def onAfterMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		vol = getattr(user, "volatiles", {})
		turns = vol.get("ragingfury", 0)
		if not turns:
			vol["ragingfury"] = 2
		else:
			vol["ragingfury"] = turns - 1
			if vol["ragingfury"] <= 0:
				vol.pop("ragingfury", None)
				vol["confusion"] = 2
		user.volatiles = vol
		return True


class Rapidspin:
	def onAfterHit(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user:
			side = getattr(user, "side", None)
			if side and hasattr(side, "clear_hazard"):
				for h in ("spikes", "stealthrock", "toxicspikes", "stickyweb"):
					side.clear_hazard(h)
			elif side and hasattr(side, "hazards"):
				for h in ("spikes", "stealthrock", "toxicspikes", "stickyweb"):
					side.hazards.pop(h, None)
					getattr(side, "conditions", {}).pop(h, None)
		return True

	def onAfterSubDamage(self, *args, **kwargs):
		return self.onAfterHit(*args, **kwargs)


class Razorwind:
	def onTryMove(self, *args, **kwargs):
		"""Handle Razor Wind as a two-turn move."""
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		vol = getattr(user, "volatiles", {})
		if vol.get("razorwind"):
			vol.pop("razorwind", None)
			user.volatiles = vol
			return True
		vol["razorwind"] = True
		user.volatiles = vol
		return False


class Recycle:
	def onHit(self, user, target, battle):
		"""Restore one used item and retire its shared recovery aliases."""
		if getattr(user, "item", None) or getattr(user, "held_item", None):
			return False
		item = getattr(user, "last_used_item", None)
		if not item:
			item = getattr(user, "berry_consumed", None)
		if not item:
			return False
		if battle and hasattr(battle, "set_item"):
			if not battle.set_item(user, item, source=user, effect="move:recycle"):
				return False
		elif hasattr(user, "set_item"):
			user.set_item(item)
		else:
			setattr(user, "item", item)
			setattr(user, "held_item", item)
		from pokemon.battle.item_consumption import ItemUseHistory
		ItemUseHistory.recovered(user)
		return True


class Reflect:
	def durationCallback(self, *args, **kwargs):
		from pokemon.battle.item_effects import HeldItemRules
		source = args[1] if len(args) > 1 else kwargs.get("source")
		return HeldItemRules.field_duration(source, "lightclay")

	def onAnyModifyDamage(self, *args, **kwargs):
		damage = args[0] if args else kwargs.get("damage")
		source = args[1] if len(args) > 1 else kwargs.get("source")
		target = args[2] if len(args) > 2 else kwargs.get("target")
		move = args[3] if len(args) > 3 else kwargs.get("move")
		if not target or not source or not move or move.category != "Physical":
			return damage
		if getattr(move, "infiltrates", False):
			return damage
		side = getattr(target, "side", None)
		if side and getattr(side, "screens", {}).get("reflect"):
			mult = 0.5
			if len(getattr(side, "active", [])) > 1:
				mult = 2 / 3
			return int(damage * mult)
		return damage

	def onSideEnd(self, *args, **kwargs):
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "screens"):
			side.screens.pop("reflect", None)
		return True

	def onSideStart(self, *args, **kwargs):
		"""Activate the Reflect screen on the side."""
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "screens"):
			side.screens["reflect"] = True
		return True


class Reflecttype:
	def onHit(self, user, target, battle):
		"""Copy the target's type(s) to the user."""
		ttypes = getattr(target, "types", [])
		if not ttypes:
			return False
		user.types = list(ttypes)
		return True


class Refresh:
	def onHit(self, user, target, battle):
		"""Cure the user's major status condition."""
		if hasattr(user, "setStatus"):
			user.setStatus(0)
		return True


class Relicsong:
	def onAfterMoveSecondarySelf(self, *args, **kwargs):
		user = args[0] if args else None
		if user and getattr(user, "species", "").lower() == "meloetta":
			form = getattr(user, "form", "aria")
			user.form = "pirouette" if form == "aria" else "aria"
		return True

	def onHit(self, user, target, battle):
		"""10% chance to put the target to sleep."""
		if getattr(target, "status", None) is None:
			if random() < 0.1 and hasattr(target, "setStatus"):
				target.setStatus("slp")
		return True


class Rest:
	def onHit(self, user, target, battle):
		"""Fully heal the user and put it to sleep."""
		max_hp = getattr(user, "max_hp", getattr(user, "hp", 0))
		user.hp = max_hp
		if hasattr(user, "setStatus"):
			user.setStatus(0, battle=battle, effect="move:rest")
			user.setStatus(
				"slp",
				battle=battle,
				source=user,
				effect="move:rest",
				bypass_protection=True,
			)
		return True

	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		if not user:
			return False
		if getattr(user, "status", None) == "slp":
			return False
		return True


class Retaliate:
	def onBasePower(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		fainted = getattr(getattr(user, "side", None), "faintedLastTurn", False)
		if fainted:
			return power * 2
		return power


class Return:
	def basePowerCallback(self, user, target, move):
		"""Power scales with happiness."""
		happiness = getattr(user, "happiness", 0)
		return max(1, int((happiness * 10) / 25))


class Revelationdance:
	def onModifyType(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		types = getattr(user, "types", []) if user else []
		if move and types:
			move.type = types[0]


class Revenge:
	def basePowerCallback(self, user, target, move):
		"""Double power if the user was hit this turn."""
		if getattr(user, "tempvals", {}).get("took_damage"):
			return (getattr(move, "power", 0) or 0) * 2
		return getattr(move, "power", 0)


class Reversal:
	def basePowerCallback(self, user, target, move):
		"""Increase power as the user has less HP remaining."""
		cur_hp = getattr(user, "hp", 0)
		max_hp = getattr(user, "max_hp", cur_hp or 1)
		ratio = int((48 * cur_hp) / max_hp) if max_hp else 48
		if ratio <= 1:
			return 200
		if ratio <= 4:
			return 150
		if ratio <= 9:
			return 100
		if ratio <= 16:
			return 80
		if ratio <= 32:
			return 40
		return 20


class Revivalblessing:
	def onStart(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("target")
		battle = kwargs.get("battle")
		if not user:
			return False
		participant = battle.participant_for(user) if battle and hasattr(battle, "participant_for") else None
		party = getattr(participant, "pokemons", None) if participant is not None else None
		if not party:
			party = getattr(user, "party", [])
		for pokemon in party:
			if pokemon is user:
				continue
			if getattr(pokemon, "hp", 0) > 0:
				continue
			max_hp = getattr(pokemon, "max_hp", getattr(pokemon, "hp", 0))
			pokemon.hp = max(1, max_hp // 2)
			pokemon.is_fainted = False
			if hasattr(pokemon, "status"):
				pokemon.status = 0
			if battle and hasattr(battle, "remove_slot_condition"):
				battle.remove_slot_condition(user, "revivalblessing")
			return True
		return False

	def onTryHit(self, user, *args, **kwargs):
		"""Fail if there are no fainted allies to revive."""
		battle = kwargs.get("battle")
		participant = battle.participant_for(user) if battle and hasattr(battle, "participant_for") else None
		party = getattr(participant, "pokemons", None) if participant is not None else None
		if not party:
			party = getattr(user, "party", [])
		if not any(getattr(mon, "hp", 0) <= 0 for mon in party):
			return False
		return True


class Risingvoltage:
	def basePowerCallback(self, user, target, move):
		"""Double power on Electric Terrain against grounded foes."""
		terrain = getattr(user, "terrain", None)
		grounded = getattr(target, "grounded", True)
		base = getattr(move, "power", 0) or 0
		if terrain == "electricterrain" and grounded:
			return base * 2
		return base


class Roleplay:
	def onHit(self, user, target, battle):
		"""Copy the target's ability."""
		ability = getattr(target, "ability", None)
		if ability is None:
			return False
		if _has_ability_flag(ability, "failroleplay"):
			return False
		setattr(user, "ability", ability)
		return True

	def onTryHit(self, target, source, move):
		"""Fail if the abilities are the same or cannot be copied."""
		if getattr(target, "ability", None) == getattr(source, "ability", None):
			return False
		if _has_ability_flag(getattr(target, "ability", None), "failroleplay"):
			return False
		return True


class Rollout:
	def basePowerCallback(self, user, target, move):
		"""Power doubles with each consecutive hit and after Defense Curl."""
		temp = getattr(user, "tempvals", {})
		hits = temp.get("rollout_hits", 0)
		bp = (getattr(move, "power", 30) or 30) * (2**hits)
		if getattr(user, "defensecurl", False):
			bp *= 2
		temp["rollout_hits"] = hits + 1
		setattr(user, "tempvals", temp)
		return bp

	def onAfterMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		state = getattr(user, "volatiles", {}).get("rollout")
		if state and state.get("hitCount", 0) == 5 and state.get("contactHitCount", 0) < 5:
			if hasattr(user, "volatiles"):
				user.volatiles["rolloutstorage"] = {"contactHitCount": state.get("contactHitCount", 0)}
		return True

	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		if user and move:
			hits = getattr(user, "tempvals", {}).get("rollout_hits", 0)
			move.hit = hits + 1
			move.is_multi_turn = True

	def onResidual(self, *args, **kwargs):
		target = args[0] if args else None
		if target and getattr(target, "last_move", {}).get("id") == "struggle":
			getattr(target, "volatiles", {}).pop("rollout", None)
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "tempvals"):
			user.tempvals["rollout_hits"] = 0
		return True


class Roost:
	"""End a useful heal's temporary Flying removal through normal lifecycle hooks."""

	def onEnd(self, pokemon, *args, **kwargs):
		"""Switch, faint and turn/battle cleanup preserve any later independent type."""
		from pokemon.battle.recovery_moves import RoostTyping
		RoostTyping.end(pokemon)

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["roost"] = True
		return True

	def onType(self, *args, **kwargs):
		types = args[0] if args else kwargs.get("types")
		if isinstance(types, list):
			return [t for t in types if t.lower() != "flying"]
		return types


class Rototiller:
	def onHitField(self, user, battle):
		"""Boost Attack and Sp. Atk of grounded Grass types."""
		for side in getattr(battle, "sides", []):
			for mon in getattr(side, "active", []):
				grounded = getattr(mon, "grounded", True)
				types = [t.lower() for t in getattr(mon, "types", [])]
				if grounded and "grass" in types:
					apply_boost(mon, {"atk": 1, "spa": 1})
		return True


class Round:
	def basePowerCallback(self, user, target, move):
		"""Double power if used consecutively in the same turn."""
		if getattr(move, "sourceEffect", None) == "round":
			return (getattr(move, "power", 0) or 0) * 2
		return getattr(move, "power", 0)

	def onTry(self, *args, **kwargs):
		return True


class Ruination:
	def damageCallback(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else kwargs.get("target")
		if not target:
			return 0
		return max(1, getattr(target, "hp", 0) // 2)


class Safeguard:
	def durationCallback(self, *args, **kwargs):
		"""Light Clay extends damage-reducing screens, not Safeguard."""
		return 5

	def onSetStatus(self, *args, **kwargs):
		status = args[0] if args else kwargs.get("status")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		side = getattr(target, "side", None)
		if side and getattr(side, "screens", {}).get("safeguard") and status:
			return False
		return True

	def onSideEnd(self, *args, **kwargs):
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "screens"):
			side.screens.pop("safeguard", None)
		return True

	def onSideStart(self, *args, **kwargs):
		"""Protect the side from status conditions."""
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "screens"):
			side.screens["safeguard"] = True
		return True

	def onTryAddVolatile(self, *args, **kwargs):
		volatile = args[0] if args else kwargs.get("status")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		side = getattr(target, "side", None)
		if side and getattr(side, "screens", {}).get("safeguard") and volatile == "confusion":
			return False
		return True


class Saltcure:
	def onEnd(self, *args, **kwargs):
		target = args[0] if args else kwargs.get("target")
		if target and hasattr(target, "volatiles"):
			target.volatiles.pop("saltcure", None)
		return True

	def onResidual(self, *args, **kwargs):
		pokemon = args[0] if args else None
		if not pokemon:
			return False
		dmg = getattr(pokemon, "max_hp", 0)
		types = [t.lower() for t in getattr(pokemon, "types", [])]
		if "water" in types or "steel" in types:
			dmg //= 4
		else:
			dmg //= 8
		pokemon.hp = max(0, getattr(pokemon, "hp", 0) - dmg)
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		target = args[1] if len(args) > 1 else None
		if target and hasattr(target, "volatiles"):
			target.volatiles["saltcure"] = user
		return True


class Sandsearstorm:
	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		battle = kwargs.get("battle")
		if len(args) > 2:
			battle = args[2] or battle
		field = getattr(battle, "field", None)
		weather = getattr(field, "weather", getattr(battle, "weather", None))
		if str(weather).lower() in ("rain", "raindance") and hasattr(move, "accuracy"):
			move.accuracy = True


class Sappyseed:
	def onHit(self, user, target, battle):
		"""Seed the target, draining HP each turn."""
		if hasattr(target, "volatiles"):
			target.volatiles["leechseed"] = user
		return True


class Secretpower:
	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		battle = kwargs.get("battle")
		if len(args) > 2:
			battle = args[2] or battle
		field = getattr(battle, "field", None)
		terrain = getattr(field, "terrain", None)
		if not move:
			return
		if terrain == "electricterrain":
			move.secondary = {"status": "par"}
		elif terrain == "grassyterrain":
			move.secondary = {"status": "slp"}
		elif terrain == "mistyterrain":
			move.secondary = {"boosts": {"spa": -1}}
		elif terrain == "psychicterrain":
			move.secondary = {"boosts": {"spd": -1}}
		else:
			move.secondary = {"status": "par"}


class Shadowforce:
	def onTryMove(self, *args, **kwargs):
		"""Handle Shadow Force as a two-turn move."""
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		vol = getattr(user, "volatiles", {})
		if vol.get("shadowforce"):
			vol.pop("shadowforce", None)
			user.volatiles = vol
			return True
		vol["shadowforce"] = True
		user.volatiles = vol
		return False


class Shedtail:
	def onHit(self, user, target, battle):
		"""Pay HP, queue a switch, and hand a substitute to the replacement."""
		max_hp = getattr(user, "max_hp", 0)
		cost = (max_hp + 1) // 2
		if getattr(user, "hp", 0) <= cost:
			return False
		user.hp -= cost
		sub_hp = max(1, (max_hp + 3) // 4)
		if hasattr(user, "tempvals"):
			user.tempvals["switch_out"] = True
			user.tempvals["skip_before_switch_out"] = True
			user.tempvals["shedtail_substitute"] = {"hp": sub_hp}
		return True

	def onTryHit(self, user, *args, **kwargs):
		"""Fail if the user lacks HP, has a substitute, or cannot switch."""
		battle = kwargs.get("battle")
		max_hp = getattr(user, "max_hp", 0)
		cost = (max_hp + 1) // 2
		if getattr(user, "volatiles", {}).get("substitute"):
			return False
		if getattr(user, "hp", 0) <= cost:
			return False
		if battle and hasattr(battle, "participant_for"):
			participant = battle.participant_for(user)
			if participant is not None:
				available = [
					poke
					for poke in getattr(participant, "pokemons", [])
					if poke is not user and getattr(poke, "hp", 0) > 0 and poke not in getattr(participant, "active", [])
				]
				if not available:
					return False
		return True


class Shellsidearm:
	def onAfterSubDamage(self, *args, **kwargs):
		return self.onHit(*args, **kwargs)

	def onHit(self, user, target, battle):
		"""May poison the target."""
		if getattr(target, "status", None) is None and random() < 0.2:
			if hasattr(target, "setStatus"):
				target.setStatus("psn")
		return True

	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		target = args[2] if len(args) > 2 else kwargs.get("target")
		if user and target and move:
			atk = getattr(user, "atk", 0)
			spa = getattr(user, "spa", 0)
			defe = getattr(target, "def", getattr(target, "def_", 0))
			spd = getattr(target, "spd", 0)
			phys = atk / max(1, defe)
			spec = spa / max(1, spd)
			move.category = "Physical" if phys > spec else "Special"

	def onPrepareHit(self, *args, **kwargs):
		return True


class Shelltrap:
	"""Arm before all actions; release only after real opposing physical damage."""
	def priorityChargeCallback(self, user=None, *args, **kwargs):
		if user:
			user.volatiles["shelltrap"] = {"armed": True, "triggered": False}
	def onStart(self, user=None, *args, **kwargs):
		if user:
			user.volatiles.setdefault("shelltrap", {"armed": True, "triggered": False})
		return True
	def onTryMove(self, user=None, *args, **kwargs):
		state = getattr(user, "volatiles", {}).get("shelltrap", {})
		return isinstance(state, dict) and state.get("triggered", False)
	def onHit(self, user=None, *args, **kwargs):
		return self.onTryMove(user)


class Shoreup:
	def onHit(self, user, target, battle):
		"""Heal the user, more in a sandstorm."""
		max_hp = getattr(user, "max_hp", 0)
		heal = max_hp // 2
		weather = getattr(getattr(battle, "field", None), "weather", None)
		if weather == "Sandstorm":
			heal = int(max_hp * 2 / 3)
		user.hp = min(getattr(user, "hp", 0) + heal, max_hp)
		return True


class Silktrap:
	def onHit(self, user, target, battle):
		"""Protect the user and lower Speed on contact."""
		if hasattr(user, "volatiles"):
			user.volatiles["protect"] = True
			user.volatiles["silktrap"] = True
		return True

	def onPrepareHit(self, *args, **kwargs):
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["protect"] = True
		return True

	def onTryHit(self, target, source, move):
		"""Block the incoming move and drop Speed on contact."""
		flags = getattr(move, "flags", {}) if move else {}
		if flags.get("contact") and hasattr(source, "boosts"):
			apply_boost(source, {"spe": -1})
		return False


class Simplebeam:
	def onHit(self, user, target, battle):
		"""Change the target's ability to Simple."""
		if _ability_change_blocked(target, "noentrain", "cantsuppress"):
			return False
		if hasattr(target, "__dict__"):
			target.ability = "Simple"
		return True

	def onTryHit(self, target, source, move):
		"""Fail if the target already has Simple or is protected."""
		ability = _effect_id(getattr(target, "ability", None))
		if ability == "simple":
			return False
		if _ability_change_blocked(target, "noentrain", "cantsuppress"):
			return False
		return True


class Sketch:
	"""Use isolated copy state and the canonical writer where required."""
	def onHit(self, user, target, battle):
		from pokemon.battle.copied_moves import BattleCopyState
		return BattleCopyState.sketch(user, target)


class Skillswap:
	def onHit(self, user, target, battle):
		"""Swap abilities between user and target."""
		if _has_ability_flag(getattr(user, "ability", None), "failskillswap"):
			return False
		if _has_ability_flag(getattr(target, "ability", None), "failskillswap"):
			return False
		u_abil = getattr(user, "ability", None)
		t_abil = getattr(target, "ability", None)
		setattr(user, "ability", t_abil)
		setattr(target, "ability", u_abil)
		return True

	def onTryHit(self, target, source, move):
		"""Fail if either ability cannot be swapped."""
		banned = {"illusion", "multitype", "comatose"}
		if _effect_id(getattr(source, "ability", None)) in banned:
			return False
		if _effect_id(getattr(target, "ability", None)) in banned:
			return False
		if _has_ability_flag(getattr(source, "ability", None), "failskillswap"):
			return False
		if _has_ability_flag(getattr(target, "ability", None), "failskillswap"):
			return False
		return True


class Skullbash:
	def onTryMove(self, *args, **kwargs):
		"""Handle Skull Bash as a two-turn move."""
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		vol = getattr(user, "volatiles", {})
		if vol.get("skullbash"):
			vol.pop("skullbash", None)
			user.volatiles = vol
			return True
		vol["skullbash"] = True
		user.volatiles = vol
		return False


class Skyattack:
	def onTryMove(self, *args, **kwargs):
		"""Handle Sky Attack as a two-turn move."""
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		vol = getattr(user, "volatiles", {})
		if vol.get("skyattack"):
			vol.pop("skyattack", None)
			user.volatiles = vol
			return True
		vol["skyattack"] = True
		user.volatiles = vol
		return False


class Skydrop:
	def onAnyBasePower(self, *args, **kwargs):
		return args[0] if args else kwargs.get("power")

	def onAnyDragOut(self, *args, **kwargs):
		return False

	def onAnyInvulnerability(self, *args, **kwargs):
		return True

	def onFaint(self, *args, **kwargs):
		pokemon = args[0] if args else None
		if pokemon and hasattr(pokemon, "volatiles"):
			pokemon.volatiles.pop("skydrop", None)
		return True

	def onFoeBeforeMove(self, *args, **kwargs):
		target = args[0] if args else None
		if target and getattr(target, "volatiles", {}).get("skydrop"):
			return True
		return False

	def onFoeTrapPokemon(self, *args, **kwargs):
		target = args[0] if args else None
		return bool(target and getattr(target, "volatiles", {}).get("skydrop"))

	def onHit(self, user, target, battle):
		"""Release the target from Sky Drop."""
		if hasattr(target, "volatiles"):
			target.volatiles.pop("skydrop", None)
		return True

	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		source = args[1] if len(args) > 1 else kwargs.get("source") or kwargs.get("user")
		if not move:
			return
		if source and getattr(source, "volatiles", {}).get("skydrop"):
			move.is_sky_drop = True
			return
		move.accuracy = True
		flags = getattr(move, "flags", None)
		if isinstance(flags, dict):
			flags.pop("contact", None)
		if isinstance(getattr(move, "raw", None), dict):
			raw_flags = move.raw.get("flags")
			if isinstance(raw_flags, dict):
				raw_flags.pop("contact", None)

	def onMoveFail(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		for mon in (user, target):
			if mon and hasattr(mon, "volatiles"):
				mon.volatiles.pop("skydrop", None)
		return True

	def onRedirectTarget(self, *args, **kwargs):
		target = args[0] if args else None
		if target and getattr(target, "volatiles", {}).get("skydrop"):
			return target

	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		target = args[1] if len(args) > 1 else kwargs.get("target")
		battle = args[3] if len(args) > 3 else kwargs.get("battle")
		if target and getattr(target, "weightkg", 0) >= 200:
			return False
		if battle and getattr(getattr(battle, "field", None), "pseudo_weather", {}).get("Gravity"):
			return False
		return True

	def onTryHit(self, target, source, move):
		"""Fail if the target is too heavy or already airborne."""
		if getattr(target, "weightkg", 0) >= 200:
			return False
		if getattr(target, "volatiles", {}).get("skydrop"):
			return False
		return True


class Sleeptalk:
	def onHit(self, user, target, battle):
		"""Use a random move if the user is asleep."""
		if getattr(user, "status", None) != "slp":
			return False
		moves = [m for m in getattr(user, "moves", [])
		         if _normalize_key(getattr(m, "name", "")) not in {"sleeptalk", "rest"}
		         and not getattr(m, "raw", {}).get("flags", {}).get("nosleeptalk")]
		if not moves:
			return False
		move = getattr(battle, "rng", None).choice(moves) if getattr(battle, "rng", None) else choice(moves)
		return bool(_execute_called_move(move, user, target, battle))

	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		return getattr(user, "status", None) == "slp"


class Smackdown:
	def onRestart(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else kwargs.get("target")
		if target and hasattr(target, "volatiles"):
			target.volatiles["smackdown"] = True
		return True

	def onStart(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else None
		if target and hasattr(target, "volatiles"):
			target.volatiles["smackdown"] = True
		return True


class Smellingsalts:
	def basePowerCallback(self, user, target, move):
		"""Double power on paralyzed targets."""
		if getattr(target, "status", None) == "par":
			return (getattr(move, "power", 0) or 0) * 2
		return getattr(move, "power", 0)

	def onHit(self, user, target, battle):
		"""Cure the target's paralysis after hitting."""
		if getattr(target, "status", None) == "par" and hasattr(target, "setStatus"):
			target.setStatus(0)
		return True


class Snatch:
	def onAnyPrepareHit(self, *args, **kwargs):
		return None

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["snatch"] = True
		return True


class Snore:
	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		return getattr(user, "status", None) == "slp"


class Soak:
	def onHit(self, user, target, battle):
		"""Change the target's type to pure Water."""
		if hasattr(target, "types"):
			target.types = ["Water"]
		return True


class Solarbeam:
	def onBasePower(self, base_power, user=None, target=None, move=None):
		weather = _holder_effective_weather(user, getattr(user, "battle", None))
		return int(base_power * .5) if weather in {"raindance", "primordialsea", "sandstorm", "hail", "snow"} else base_power

	def onTryMove(self, user, target=None, battle=None):
		if not user:
			return False
		vol = getattr(user, "volatiles", {})
		if vol.pop("solarbeam", None):
			return True
		if _holder_effective_weather(user, battle) in {"sunnyday", "desolateland"}:
			return True
		vol["solarbeam"] = True
		user.volatiles = vol
		return False


class Solarblade:
	def onBasePower(self, base_power, user=None, target=None, move=None):
		weather = _holder_effective_weather(user, getattr(user, "battle", None))
		return int(base_power * .5) if weather in {"raindance", "primordialsea", "sandstorm", "hail", "snow"} else base_power

	def onTryMove(self, user, target=None, battle=None):
		if not user:
			return False
		vol = getattr(user, "volatiles", {})
		if vol.pop("solarblade", None):
			return True
		if _holder_effective_weather(user, battle) in {"sunnyday", "desolateland"}:
			return True
		vol["solarblade"] = True
		user.volatiles = vol
		return False


class Sparklingaria:
	def onAfterMove(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else kwargs.get("target")
		if target and getattr(target, "status", None) == "brn" and hasattr(target, "setStatus"):
			target.setStatus(0)
		return True


class Sparklyswirl:
	def onHit(self, user, target, battle):
		"""Heal and cure status of the user's party."""
		party = getattr(user, "party", [user])
		for mon in party:
			max_hp = getattr(mon, "max_hp", 0)
			heal = max_hp // 3
			mon.hp = min(getattr(mon, "hp", 0) + heal, max_hp)
			if hasattr(mon, "setStatus"):
				mon.setStatus(0)
		return True


class Speedswap:
	def onHit(self, user, target, battle):
		"""Swap the base Speed stats of user and target."""
		u_speed = _stored_battle_stat(user, "spe")
		t_speed = _stored_battle_stat(target, "spe")
		if u_speed is not None and t_speed is not None:
			_set_stored_battle_stat(user, "spe", t_speed)
			_set_stored_battle_stat(target, "spe", u_speed)
		return True


class Spiderweb:
	def onHit(self, user, target, battle):
		"""Trap the target, preventing switching."""
		if hasattr(target, "volatiles"):
			target.volatiles["trapped"] = True
		return True


class Spikes:
	def onEntryHazard(self, *args, **kwargs):
		pokemon = args[0] if args else kwargs.get("pokemon")
		if not pokemon:
			return False
		if not getattr(pokemon, "grounded", True):
			return True
		item = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
		from pokemon.battle.effect_context import EffectContext
		if EffectContext.key(EffectContext.item(pokemon)) == "heavydutyboots":
			return True
		side = getattr(pokemon, "side", None)
		layers = getattr(side, "hazards", {}).get("spikes", 0) if side else 0
		dmg_frac = {1: 1 / 8, 2: 3 / 16, 3: 1 / 4}.get(layers, 0)
		dmg = int(getattr(pokemon, "max_hp", 0) * dmg_frac)
		pokemon.hp = max(0, getattr(pokemon, "hp", 0) - dmg)
		return True

	def onSideRestart(self, *args, **kwargs):
		return True

	def onSideStart(self, *args, **kwargs):
		"""Lay a layer of Spikes on the opposing side."""
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "hazards"):
			layers = side.hazards.get("spikes", 0)
			side.hazards["spikes"] = min(layers + 1, 3)
		return True


class Spikyshield:
	def onHit(self, user, target, battle):
		"""Protect the user and damage contact attackers."""
		if hasattr(user, "volatiles"):
			user.volatiles["protect"] = True
			user.volatiles["spikyshield"] = True
		return True

	def onPrepareHit(self, *args, **kwargs):
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["protect"] = True
		return True

	def onTryHit(self, target, source, move):
		"""Block the move and hurt contact attackers."""
		flags = getattr(move, "flags", {}) if move else {}
		if flags.get("contact") and hasattr(source, "max_hp"):
			damage = max(1, getattr(source, "max_hp", 1) // 8)
			source.hp = max(0, getattr(source, "hp", 0) - damage)
		return False


class Spiritshackle:
	def onHit(self, user, target, battle):
		"""Trap the target, preventing it from switching."""
		if hasattr(target, "volatiles"):
			target.volatiles["trapped"] = True
		return True


class Spite:
	def onHit(self, user, target, battle):
		"""Reduce the PP of the target's last move by 4."""
		last_move = getattr(target, "last_move", None)
		if not last_move:
			return False
		if battle and hasattr(battle, "reduce_move_pp"):
			return battle.reduce_move_pp(target, last_move, 4) > 0
		if hasattr(last_move, "pp") and last_move.pp is not None:
			previous = last_move.pp
			last_move.pp = max(0, previous - 4)
			return last_move.pp < previous
		return False


class Spitup:
	def basePowerCallback(self, user, target, move):
		"""Power depends on stockpile layers."""
		layers = _stockpile_layers(user)
		return layers * 100 if layers else 0

	def onAfterMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user:
			_consume_stockpile(user, kwargs.get("battle"))
		return True

	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		layers = _stockpile_layers(user) if user else 0
		return layers > 0


class Splash:
	def onTry(self, *args, **kwargs):
		return True

	def onTryHit(self, *args, **kwargs):
		"""Always fails to have any effect."""
		return True


class Splinteredstormshards:
	def onAfterSubDamage(self, user, target, battle):
		"""Also clear terrain when hitting a substitute."""
		field = getattr(battle, "field", None)
		if field and hasattr(field, "set_terrain"):
			field.set_terrain(None)
		return True

	def onHit(self, user, target, battle):
		"""Clear any active terrain."""
		field = getattr(battle, "field", None)
		if field and hasattr(field, "set_terrain"):
			field.set_terrain(None)
		return True


class Spotlight:
	def onFoeRedirectTarget(self, *args, **kwargs):
		target = args[0] if args else None
		return target

	def onStart(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else None
		if target and hasattr(target, "volatiles"):
			target.volatiles["spotlight"] = True
		return True

	def onTryHit(self, target, source, move):
		"""Force foes to target the user this turn."""
		return True


class Stealthrock:
	def onEntryHazard(self, *args, **kwargs):
		pokemon = args[0] if args else kwargs.get("pokemon")
		if not pokemon:
			return False
		item = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
		from pokemon.battle.effect_context import EffectContext
		if EffectContext.key(EffectContext.item(pokemon)) == "heavydutyboots":
			return True
		from pokemon.battle.damage import type_effectiveness
		eff = type_effectiveness(pokemon, type("Move", (), {"type": "Rock"}))
		dmg = int(getattr(pokemon, "max_hp", 0) * eff / 8)
		pokemon.hp = max(0, getattr(pokemon, "hp", 0) - dmg)
		return True

	def onSideStart(self, *args, **kwargs):
		"""Set Stealth Rock on the opposing side."""
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "hazards"):
			side.hazards["rocks"] = True
		return True


class Steelbeam:
	def onAfterMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user:
			recoil = getattr(user, "max_hp", 0) // 2
			user.hp = max(0, getattr(user, "hp", 0) - recoil)
		return True


class Steelroller:
	def onAfterSubDamage(self, user, target, battle):
		"""Remove terrain after hitting a substitute."""
		field = getattr(battle, "field", None)
		if field and hasattr(field, "set_terrain"):
			field.set_terrain(None)
		return True

	def onHit(self, user, target, battle):
		"""Clear active terrain."""
		field = getattr(battle, "field", None)
		if field and hasattr(field, "set_terrain"):
			field.set_terrain(None)
		return True

	def onTry(self, *args, **kwargs):
		battle = kwargs.get("battle") if kwargs else None
		if len(args) > 3:
			battle = args[3] or battle
		field = getattr(battle, "field", None)
		terrain = getattr(field, "terrain", None) if field else None
		return bool(terrain)


class Stickyweb:
	def onEntryHazard(self, *args, **kwargs):
		pokemon = args[0] if args else kwargs.get("pokemon")
		if not pokemon or not getattr(pokemon, "grounded", True):
			return True
		item = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
		from pokemon.battle.effect_context import EffectContext
		if EffectContext.key(EffectContext.item(pokemon)) == "heavydutyboots":
			return True
		apply_boost(pokemon, {"spe": -1})
		return True

	def onSideStart(self, *args, **kwargs):
		"""Set Sticky Web on the opposing side."""
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "hazards"):
			side.hazards["stickyweb"] = True
		return True


class Stockpile:
	def onEnd(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user:
			state = getattr(user, "volatiles", {}).get("stockpile", {})
			if isinstance(state, dict):
				apply_boost(user, {stat: state.get(stat, 0) for stat in ("def", "spd")})
			setattr(user, "stockpile_layers", 0)
			if hasattr(user, "volatiles"):
				user.volatiles.pop("stockpile", None)
		return True

	def onRestart(self, *args, **kwargs):
		return self.onStart(*args, **kwargs)

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		layers = _stockpile_layers(user) if user else 0
		if user:
			if layers >= 3:
				return False
			state = getattr(user, "volatiles", {}).get("stockpile")
			if not isinstance(state, dict):
				state = user.volatiles["stockpile"] = {}
			before = {stat: _boost_value(user.boosts, stat) for stat in ("def", "spd")}
			apply_boost(user, {"def": 1, "spd": 1})
			for stat in before:
				if _boost_value(user.boosts, stat) != before[stat]:
					state[stat] = state.get(stat, 0) - 1
			state["layers"] = layers + 1
			setattr(user, "stockpile_layers", layers + 1)
		return True

	def onResidual(self, *args, **kwargs):
		return True

	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		if not user:
			return False
		layers = _stockpile_layers(user)
		return layers < 3


class Stompingtantrum:
	def basePowerCallback(self, user, target, move):
		"""Double power if the user's previous move failed."""
		if getattr(user, "move_failed", False):
			return (getattr(move, "power", 0) or 0) * 2
		return getattr(move, "power", 0)


class Stoneaxe:
	def onAfterHit(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else kwargs.get("target")
		side = getattr(target, "side", None)
		if side and hasattr(side, "hazards"):
			side.hazards["stoneaxe"] = True
		return True

	def onAfterSubDamage(self, *args, **kwargs):
		return self.onAfterHit(*args, **kwargs)


class Storedpower:
	def basePowerCallback(self, user, target, move):
		"""Increase power for each positive stat boost."""
		boosts = getattr(user, "boosts", {})
		positive = sum(v for v in boosts.values() if v > 0)
		return (getattr(move, "power", 0) or 0) + 20 * positive


class Strengthsap:
	def onHit(self, user, target, battle):
		"""Heal the user based on target's Attack and lower its Attack."""
		stats = getattr(target, "stats", None) or getattr(target, "base_stats", None)
		if isinstance(stats, dict):
			atk = stats.get("atk", stats.get("attack", getattr(target, "atk", 0)))
		else:
			atk = getattr(stats, "attack", getattr(stats, "atk", getattr(target, "atk", 0)))
		max_hp = getattr(user, "max_hp", 0)
		heal = min(atk, max_hp - getattr(user, "hp", 0))
		user.hp = getattr(user, "hp", 0) + heal
		apply_boost(target, {"atk": -1})
		return True


class Struggle:
	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		if move:
			move.type = "???"
			move.recoil = 0.25


class Stuffcheeks:
	def onDisableMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		item = getattr(user, "item", None) or getattr(user, "held_item", None)
		return not (item and "berry" in str(item).lower())

	def onHit(self, *args, **kwargs):
		user = args[0]
		battle = args[2] if len(args) > 2 else kwargs.get("battle") or getattr(user, "battle", None)
		item = getattr(user, "item", None) or getattr(user, "held_item", None)
		if not item or not _is_berry(item):
			return False
		before = dict(getattr(user, "boosts", {}) or {})
		apply_boost(user, {"def": 2}, source=user, effect="move:stuffcheeks")
		if _boost_value(before, "def") == _boost_value(getattr(user, "boosts", {}) or {}, "def"):
			return False
		if battle and hasattr(battle, "eat_item"):
			battle.eat_item(user, source=user, effect="move:stuffcheeks", force=True)
		elif hasattr(user, "set_item"):
			user.set_item(None)
		else:
			setattr(user, "item", None)
			setattr(user, "held_item", None)
		return True

	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		item = None
		if user:
			item = getattr(user, "item", None) or getattr(user, "held_item", None)
		return bool(item and "berry" in str(item).lower())


class Substitute:
	def onEnd(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user and hasattr(user, "volatiles"):
			user.volatiles.pop("substitute", None)
		return True

	def onHit(self, *args, **kwargs):
		user = args[0]
		max_hp = getattr(user, "max_hp", 0)
		if getattr(user, "hp", 0) <= max_hp // 4:
			return False
		user.hp -= max_hp // 4
		if hasattr(user, "volatiles"):
			user.volatiles["substitute"] = {"hp": max_hp // 4}
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			hp = getattr(user, "max_hp", getattr(user, "hp", 0)) // 4
			user.volatiles["substitute"] = {"hp": hp}
		return True

	def onTryHit(self, user, *args, **kwargs):
		"""Fail if a substitute already exists or HP is too low."""
		if getattr(user, "volatiles", {}).get("substitute"):
			return False
		max_hp = getattr(user, "max_hp", 0)
		if getattr(user, "hp", 0) <= max_hp // 4:
			return False
		return True

	def onTryPrimaryHit(self, *args, **kwargs):
		target = args[0] if args else None
		move = args[2] if len(args) > 2 else kwargs.get("move")
		if target and getattr(target, "volatiles", {}).get("substitute"):
			category = getattr(move, "category", None)
			if category is None and move is not None:
				category = getattr(move, "raw", {}).get("category")
			if str(category or "").lower() == "status":
				return False
		return True


class Suckerpunch:
	def onTry(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else kwargs.get("target")
		battle = kwargs.get("battle")
		move = battle.pending_move(target) if battle and hasattr(battle, "pending_move") else None
		if not move:
			return False
		category = getattr(move, "category", "").lower()
		return category != "status"


class Supercellslam:
	def onMoveFail(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		recoil = getattr(user, "max_hp", 0) // 2
		user.hp = max(0, getattr(user, "hp", 0) - recoil)
		return True


class Superfang:
	def damageCallback(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else kwargs.get("target")
		if not target:
			return 0
		return max(1, getattr(target, "hp", 0) // 2)


class Swallow:
	def onHit(self, *args, **kwargs):
		user = args[0]
		layers = _stockpile_layers(user)
		if not layers:
			return False
		max_hp = getattr(user, "max_hp", 0)
		if layers == 1:
			heal = max_hp // 4
		elif layers == 2:
			heal = max_hp // 2
		else:
			heal = max_hp
		user.hp = min(getattr(user, "hp", 0) + heal, max_hp)
		_consume_stockpile(user, kwargs.get("battle"))
		return True

	def onTry(self, *args, **kwargs):
		user = args[0] if args else None
		layers = _stockpile_layers(user) if user else 0
		return layers > 0


class Switcheroo:
	def onHit(self, *args, **kwargs):
		user, target = args[0], args[1]
		battle = args[2] if len(args) > 2 else kwargs.get("battle") or getattr(user, "battle", None)
		if battle and hasattr(battle, "swap_items"):
			return bool(battle.swap_items(user, target, effect="move:switcheroo"))
		return False

	def onTryImmunity(self, *args, **kwargs):
		target = args[0] if args else kwargs.get("target")
		user = args[1] if len(args) > 1 else kwargs.get("source")
		my_item = getattr(user, "item", None) or getattr(user, "held_item", None)
		your_item = getattr(target, "item", None) or getattr(target, "held_item", None)
		return my_item is not None or your_item is not None


class Synchronoise:
	def onTryImmunity(self, *args, **kwargs):
		target = args[0] if args else kwargs.get("target")
		source = args[1] if len(args) > 1 else kwargs.get("source")
		t_types = [t.lower() for t in getattr(target, "types", [])] if target else []
		s_types = [t.lower() for t in getattr(source, "types", [])] if source else []
		return any(t in s_types for t in t_types)


class Synthesis:
	def onHit(self, user, target, battle):
		"""Use effective weather and the ordinary healing event gate."""
		max_hp = getattr(user, "max_hp", 0)
		weather = _holder_effective_weather(user, battle)
		numerator, denominator = (1, 2)
		if weather in {"sunnyday", "desolateland"}:
			numerator, denominator = (2, 3)
		elif weather in {"raindance", "primordialsea", "sandstorm", "hail", "snow", "snowscape"}:
			numerator, denominator = (1, 4)
		amount = max(1, max_hp * numerator // denominator)
		return battle.heal(user, amount, source=user, effect="move:synthesis") > 0


class Syrupbomb:
	def onEnd(self, *args, **kwargs):
		target = args[0] if args else kwargs.get("target")
		if target and hasattr(target, "volatiles"):
			target.volatiles.pop("syrupbomb", None)
		return True

	def onResidual(self, *args, **kwargs):
		target = args[0] if args else None
		if not target:
			return False
		vol = getattr(target, "volatiles", {}).get("syrupbomb")
		if not vol:
			return False
		apply_boost(target, {"spe": -1})
		turns = vol.get("turns", 2) if isinstance(vol, dict) else 2
		turns -= 1
		if turns <= 0:
			target.volatiles.pop("syrupbomb", None)
		else:
			target.volatiles["syrupbomb"] = {"turns": turns}
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		target = args[1] if len(args) > 1 else None
		if target and hasattr(target, "volatiles"):
			target.volatiles["syrupbomb"] = user
		return True

	def onUpdate(self, *args, **kwargs):
		target = args[0] if args else kwargs.get("target")
		if target and getattr(target, "hp", 0) <= 0:
			if hasattr(target, "volatiles"):
				target.volatiles.pop("syrupbomb", None)


class Tailwind:
	def durationCallback(self, *args, **kwargs):
		return 4

	def onModifySpe(self, *args, **kwargs):
		spe = args[0] if args else kwargs.get("spe")
		if spe is None:
			return None
		return spe * 2

	def onSideEnd(self, *args, **kwargs):
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "screens"):
			side.screens.pop("tailwind", None)
		return True

	def onSideStart(self, *args, **kwargs):
		"""Double the Speed of allies for four turns."""
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "screens"):
			side.screens["tailwind"] = True
		return True


class Takeheart:
	def onHit(self, user, target, battle):
		"""Raise user's Sp. Atk and Sp. Def and cure its status."""
		apply_boost(user, {"spa": 1, "spd": 1})
		if hasattr(user, "setStatus"):
			user.setStatus(0)
		else:
			setattr(user, "status", None)
		return True


class Tarshot:
	def onEffectiveness(self, *args, **kwargs):
		type_mod = args[0] if args else kwargs.get("typeMod")
		move_type = args[2] if len(args) > 2 else kwargs.get("type")
		if isinstance(move_type, str) and move_type.lower() == "fire":
			return type_mod + 1 if isinstance(type_mod, int) else 1
		return type_mod

	def onStart(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else None
		if target and hasattr(target, "volatiles"):
			target.volatiles["tarshot"] = True
		return True


class Taunt:
	def onBeforeMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		move = args[1] if len(args) > 1 else kwargs.get("move")
		if user and getattr(user, "volatiles", {}).get("taunt") and getattr(move, "category", "") == "Status":
			if hasattr(user, "tempvals"):
				user.tempvals["cant_move"] = "taunt"
			return False
		return True

	def onDisableMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		move = args[1] if len(args) > 1 else kwargs.get("move")
		if user and getattr(user, "volatiles", {}).get("taunt") and getattr(move, "category", "") == "Status":
			return True
		return False

	def onEnd(self, *args, **kwargs):
		target = args[0] if args else kwargs.get("target")
		if target and hasattr(target, "volatiles"):
			target.volatiles.pop("taunt", None)
		return True

	def onStart(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else None
		if target and hasattr(target, "volatiles"):
			target.volatiles["taunt"] = True
		return True


class Teatime:
	def onHit(self, user, target, battle):
		"""Force all active Pokemon to consume their held Berries."""
		for participant in getattr(battle, "participants", []) or []:
			for mon in getattr(participant, "active", []) or []:
				if getattr(mon, "hp", 0) <= 0:
					continue
				item = getattr(mon, "item", None) or getattr(mon, "held_item", None)
				if not _is_berry(item):
					continue
				if hasattr(battle, "eat_item"):
					battle.eat_item(mon, source=user, effect="move:teatime", force=True)
				elif hasattr(mon, "set_item"):
					mon.set_item(None)
				else:
					setattr(mon, "item", None)
					setattr(mon, "held_item", None)
		return True

	def onHitField(self, user, battle):
		return self.onHit(user, None, battle)

class Technoblast:
	def onModifyType(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		item = getattr(user, "item", None) or getattr(user, "held_item", None)
		if move and item and hasattr(item, "drive_type"):
			move.type = getattr(item, "drive_type")


class Telekinesis:
	def onAccuracy(self, *args, **kwargs):
		return True

	def onEnd(self, *args, **kwargs):
		target = args[0] if args else kwargs.get("target")
		if target and hasattr(target, "volatiles"):
			target.volatiles.pop("telekinesis", None)
		return True

	def onImmunity(self, *args, **kwargs):
		typ = args[0] if args else kwargs.get("type")
		if typ and str(typ).lower() == "ground":
			return False
		return True

	def onStart(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else None
		if target and hasattr(target, "volatiles"):
			target.volatiles["telekinesis"] = 3
		return True

	def onTry(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else kwargs.get("target")
		if target and getattr(target, "volatiles", {}).get("telekinesis"):
			return False
		return True

	def onUpdate(self, *args, **kwargs):
		target = args[0] if args else kwargs.get("target")
		if target and hasattr(target, "volatiles"):
			turns = target.volatiles.get("telekinesis")
			if isinstance(turns, int):
				turns -= 1
				if turns <= 0:
					target.volatiles.pop("telekinesis", None)
				else:
					target.volatiles["telekinesis"] = turns


class Teleport:
	def onTry(self, *args, **kwargs):
		return True


class Temperflare:
	def basePowerCallback(self, user, target, move):
		"""Double power if the user's previous move failed."""
		if getattr(user, "move_failed", False):
			return (getattr(move, "power", 0) or 0) * 2
		return getattr(move, "power", 0)


class Terablast:
	def basePowerCallback(self, user, target, move):
		"""Return 100 power if Tera type is Stellar."""
		if getattr(user, "terastallized", None) == "Stellar":
			return 100
		return getattr(move, "power", 0)

	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		if move:
			from pokemon.battle.terastallization import tera_blast_parameters

			move.type, move.category, move.power = tera_blast_parameters(user)
			if isinstance(getattr(move, "raw", None), dict):
				move.raw["category"] = move.category

	def onModifyType(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		tera = getattr(user, "terastallized", None)
		if tera and move:
			move.type = tera

	def onPrepareHit(self, *args, **kwargs):
		return True


class Terastarstorm:
	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		if move and str(getattr(user, "species", "")) == "Terapagos-Stellar":
			move.target = "allAdjacentFoes"
			move.raw = dict(move.raw or {}, target="allAdjacentFoes")

	def onModifyType(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		if move and str(getattr(user, "species", "")) == "Terapagos-Stellar":
			move.type = "Stellar"
			if getattr(user, "terastallized", None):
				from pokemon.battle.terastallization import tera_offensive_category
				move.category = tera_offensive_category(user)
				move.raw = dict(move.raw or {}, category=move.category)


class Terrainpulse:
	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		battle = kwargs.get("battle")
		if len(args) > 2:
			battle = args[2] or battle
		field = getattr(battle, "field", None)
		terrain = getattr(field, "terrain", None)
		if move and terrain and getattr(user, "grounded", True):
			move.power = 100
			move.type = terrain.replace("terrain", "").capitalize()

	def onModifyType(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		battle = kwargs.get("battle")
		if len(args) > 2:
			battle = args[2] or battle
		field = getattr(battle, "field", None)
		terrain = getattr(field, "terrain", None)
		if move and terrain and getattr(user, "grounded", True):
			move.type = terrain.replace("terrain", "").capitalize()


class Thief:
	def onAfterHit(self, *args, **kwargs):
		user = args[0] if args else None
		target = args[1] if len(args) > 1 else None
		battle = args[2] if len(args) > 2 else kwargs.get("battle") or getattr(user, "battle", None)
		if not user or not target:
			return True
		if battle and hasattr(battle, "steal_item"):
			battle.steal_item(user, target, effect="move:thief")
		return True


class Thousandarrows:
	def onEffectiveness(self, *args, **kwargs):
		type_mod = args[0] if args else kwargs.get("typeMod")
		target_type = args[2] if len(args) > 2 else kwargs.get("type")
		if isinstance(target_type, str) and target_type.capitalize() == "Flying":
			return 1
		return type_mod


class Thousandwaves:
	def onHit(self, user, target, battle):
		"""Trap the target, preventing switching."""
		if hasattr(target, "volatiles"):
			target.volatiles["trapped"] = True
		return True


class Thrash:
	def onAfterMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if not user:
			return False
		vol = getattr(user, "volatiles", {})
		turns = vol.get("thrash", 0)
		if not turns:
			vol["thrash"] = 2
		else:
			vol["thrash"] = turns - 1
			if vol["thrash"] <= 0:
				vol.pop("thrash", None)
				vol["confusion"] = 2
		user.volatiles = vol
		return True


class Throatchop:
	def onBeforeMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		move = args[1] if len(args) > 1 else kwargs.get("move")
		if user and getattr(user, "volatiles", {}).get("throatchop"):
			flags = getattr(move, "flags", {}) if move else {}
			if flags.get("sound"):
				if hasattr(user, "tempvals"):
					user.tempvals["cant_move"] = "throatchop"
				return False
		return True

	def onDisableMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		move = args[1] if len(args) > 1 else kwargs.get("move")
		if user and getattr(user, "volatiles", {}).get("throatchop"):
			return getattr(move, "flags", {}).get("sound")
		return False

	def onEnd(self, *args, **kwargs):
		target = args[0] if args else kwargs.get("target")
		if target and hasattr(target, "volatiles"):
			target.volatiles.pop("throatchop", None)
		return True

	def onHit(self, *args, **kwargs):
		user, target = args[0], args[1]
		if hasattr(target, "volatiles"):
			target.volatiles["throatchop"] = 2
		return True

	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		if move:
			move.flags = getattr(move, "flags", {})
			move.flags["sound"] = False

	def onStart(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else None
		if target and hasattr(target, "volatiles"):
			target.volatiles["throatchop"] = 2
		return True


class Thunder:
	def onModifyMove(self, move, user=None, target=None, battle=None):
		weather = _holder_effective_weather(target, battle)
		if weather in {"rain", "raindance", "primordialsea"}:
			move.accuracy = True
		elif weather in {"sunnyday", "sunny", "desolateland"}:
			move.accuracy = 50


class Thunderclap:
	def onTry(self, *args, **kwargs):
		return True


class Tidyup:
	def onHit(self, user, target, battle):
		"""Remove hazards on the user's side and boost Attack and Speed."""
		sides = [part.side for part in getattr(battle, "participants", [])]
		if not sides and getattr(user, "side", None) is not None:
			sides = [user.side]
		for side in sides:
			for hazard in ("spikes", "toxicspikes", "stealthrock", "stickyweb", "gmaxsteelsurge"):
				if hasattr(side, "clear_hazard"):
					side.clear_hazard(hazard)
				else:
					getattr(side, "hazards", {}).pop(hazard, None)
					getattr(side, "conditions", {}).pop(hazard, None)
		for part in getattr(battle, "participants", []):
			for pokemon in getattr(part, "active", []):
				if hasattr(battle, "remove_volatile"):
					battle.remove_volatile(pokemon, "substitute")
				else:
					getattr(pokemon, "volatiles", {}).pop("substitute", None)
		apply_boost(user, {"atk": 1, "spe": 1})
		return True


class Topsyturvy:
	def onHit(self, user, target, battle):
		"""Invert the target's stat boosts."""
		boosts = getattr(target, "boosts", {})
		for stat in boosts:
			boosts[stat] = -boosts[stat]
		return True


class Torment:
	def onDisableMove(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		move = args[1] if len(args) > 1 else kwargs.get("move")
		if user and getattr(user, "volatiles", {}).get("torment"):
			last = getattr(user, "last_move", None)
			if last and getattr(last, "id", None) == getattr(move, "id", None):
				return True
		return False

	def onEnd(self, *args, **kwargs):
		target = args[0] if args else kwargs.get("target")
		if target and hasattr(target, "volatiles"):
			target.volatiles.pop("torment", None)
		return True

	def onStart(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else None
		if target and hasattr(target, "volatiles"):
			target.volatiles["torment"] = True
		return True


class Toxicspikes:
	def onEntryHazard(self, *args, **kwargs):
		pokemon = args[0] if args else kwargs.get("pokemon")
		if not pokemon or not getattr(pokemon, "grounded", True):
			return True
		item = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
		from pokemon.battle.effect_context import EffectContext
		if EffectContext.key(EffectContext.item(pokemon)) == "heavydutyboots":
			return True
		side = getattr(pokemon, "side", None)
		layers = getattr(side, "hazards", {}).get("toxicspikes", 0) if side else 0
		types = [t.lower() for t in getattr(pokemon, "types", [])]
		if "poison" in types:
			if side and layers:
				if hasattr(side, "clear_hazard"):
					side.clear_hazard("toxicspikes")
				else:
					side.hazards["toxicspikes"] = 0
					getattr(side, "conditions", {}).pop("toxicspikes", None)
			return True
		status = "tox" if layers > 1 else "psn"
		if hasattr(pokemon, "setStatus"):
			pokemon.setStatus(status, source=None)
		return True

	def onSideRestart(self, *args, **kwargs):
		return True

	def onSideStart(self, *args, **kwargs):
		"""Set Toxic Spikes on the opposing side."""
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "hazards"):
			layers = side.hazards.get("toxicspikes", 0)
			new_layers = min(layers + 1, 2)
			if hasattr(side, "set_hazard"):
				side.set_hazard("toxicspikes", new_layers)
			else:
				side.hazards["toxicspikes"] = new_layers
		return True


class Transform:
	"""Use isolated copy state and the canonical writer where required."""
	def onHit(self, user, target, battle):
		from pokemon.battle.copied_moves import BattleCopyState
		return BattleCopyState.transform(user, target, battle)


class Triattack:
	def onHit(self, user, target, battle):
		"""20% chance to burn, paralyze, or freeze the target."""
		if random() < 0.2 and hasattr(target, "setStatus"):
			status = choice(["brn", "par", "frz"])
			target.setStatus(
				status,
				source=user,
				battle=battle,
				effect="move:triattack",
			)
		return True


class Trick:
	def onHit(self, user, target, battle):
		"""Swap held items with the target."""
		if battle and hasattr(battle, "swap_items"):
			return bool(battle.swap_items(user, target, effect="move:trick"))
		return False

	def onTryImmunity(self, *args, **kwargs):
		target = args[0] if args else kwargs.get("target")
		source = args[1] if len(args) > 1 else kwargs.get("source")
		my_item = getattr(source, "item", None) or getattr(source, "held_item", None)
		your_item = getattr(target, "item", None) or getattr(target, "held_item", None)
		return my_item is not None or your_item is not None


class Trickortreat:
	def onHit(self, user, target, battle):
		"""Add Ghost type to the target."""
		types = list(getattr(target, "types", []))
		if "Ghost" not in types and "ghost" not in [t.lower() for t in types]:
			types.append("Ghost")
			setattr(target, "types", types)
		return True


class Trickroom:
	def durationCallback(self, *args, **kwargs):
		source = args[1] if len(args) > 1 else kwargs.get("source")
		if _effect_id(getattr(source, "ability", None)) == "persistent":
			return 7
		return 5

	def onFieldEnd(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field and hasattr(field, "pseudo_weather"):
			field.pseudo_weather.pop("trickroom", None)
		return True

	def onFieldRestart(self, *args, **kwargs):
		field = kwargs.get("field") or args[0] if args else None
		if hasattr(field, "remove_pseudo_weather"):
			field.remove_pseudo_weather("trickroom")

	def onFieldStart(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field:
			pw = getattr(field, "pseudo_weather", {})
			# Keep the engine's duration and source state for residuals/rebuilds.
			if not isinstance(pw.get("trickroom"), dict):
				pw["trickroom"] = {"duration": 5}
			field.pseudo_weather = pw
		return True


class Tripleaxel:
	def basePowerCallback(self, user, target, move):
		"""Power increases with each hit."""
		hit = getattr(move, "hit", 1)
		return 20 * hit


class Triplekick:
	def basePowerCallback(self, user, target, move):
		hit = getattr(move, "hit", 1)
		return 10 * hit


class Trumpcard:
	def basePowerCallback(self, user, target, move):
		pp = getattr(move, "pp", 5)
		if pp == 0:
			return 200
		if pp == 1:
			return 80
		if pp == 2:
			return 60
		if pp == 3:
			return 50
		return 40


class Upperhand:
	def onTry(self, *args, **kwargs):
		target = args[1] if len(args) > 1 else kwargs.get("target")
		battle = kwargs.get("battle")
		move = battle.pending_move(target) if battle and hasattr(battle, "pending_move") else None
		priority = getattr(move, "priority", 0) if move else 0
		category = getattr(move, "category", None) or (getattr(move, "raw", {}) or {}).get("category")
		return priority > 0 and category != "Status"


class Uproar:
	def onAnySetStatus(self, *args, **kwargs):
		status = args[1] if len(args) > 1 else kwargs.get("status")
		if status == "slp":
			return False
		return True

	def onEnd(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		if user and hasattr(user, "volatiles"):
			user.volatiles.pop("uproar", None)
		return True

	def onResidual(self, *args, **kwargs):
		user = args[0] if args else None
		if user and getattr(user, "volatiles", {}).get("uproar"):
			user.volatiles["uproar"] -= 1
			if user.volatiles["uproar"] <= 0:
				user.volatiles.pop("uproar", None)
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		if user and hasattr(user, "volatiles"):
			user.volatiles["uproar"] = 3
		return True

	def onTryHit(self, *args, **kwargs):
		"""Always succeeds and prevents Sleep for several turns."""
		return True


class Veeveevolley:
	def basePowerCallback(self, user, target, move):
		"""Power scales with happiness."""
		happiness = getattr(user, "happiness", 0)
		return max(1, int((happiness * 10) / 25))


class Venomdrench:
	def onHit(self, user, target, battle):
		"""Lower target's Attack, Sp. Atk, and Speed if poisoned."""
		if getattr(target, "status", None) in {"psn", "tox"}:
			apply_boost(target, {"atk": -1, "spa": -1, "spe": -1})
		return True


class Venoshock:
	def onBasePower(self, *args, **kwargs):
		user = args[0] if args else kwargs.get("user")
		target = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		if target and getattr(target, "status", None) in {"psn", "tox"}:
			return power * 2
		return power


class Wakeupslap:
	def basePowerCallback(self, user, target, move):
		"""Double power on sleeping targets."""
		if getattr(target, "status", None) == "slp":
			return (getattr(move, "power", 0) or 0) * 2
		return getattr(move, "power", 0)

	def onHit(self, *args, **kwargs):
		target = args[1]
		if getattr(target, "status", None) == "slp" and hasattr(target, "setStatus"):
			target.setStatus(0)
		return True


class Waterpledge:
	def basePowerCallback(self, user, target, move):
		"""Return 150 power when used in a pledge combo."""
		if getattr(move, "sourceEffect", None) in {"grasspledge", "firepledge"}:
			return 150
		return getattr(move, "power", 0) or 0

	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		user = args[1] if len(args) > 1 else kwargs.get("user")
		if getattr(user, "pledge_combo", False) and move:
			move.pledge_combo = True

	def onPrepareHit(self, *args, **kwargs):
		return True

	def onSideEnd(self, *args, **kwargs):
		side = args[0] if args else kwargs.get("side")
		if side and hasattr(side, "conditions"):
			side.conditions.pop("waterpledge", None)
		return True

	def onSideStart(self, *args, **kwargs):
		"""Start the Water Pledge side condition."""
		side = args[0] if args else kwargs.get("side")
		if side:
			side.conditions["waterpledge"] = {
				"turns": 4,
				"source": kwargs.get("source"),
			}
		return True


class Watershuriken:
	def basePowerCallback(self, user, target, move):
		"""Ash-Greninja's Battle Bond boosts power by 5."""
		species = getattr(user, "species", None)
		ability = getattr(user, "ability", None)
		power = getattr(move, "power", 15) or 15
		if species == "Greninja-Ash" and ability == "battlebond" and not getattr(user, "transformed", False):
			return power + 5
		return power


class Watersport:
	def onBasePower(self, *args, **kwargs):
		attacker = args[0] if args else kwargs.get("user")
		defender = args[1] if len(args) > 1 else kwargs.get("target")
		move = args[2] if len(args) > 2 else kwargs.get("move")
		power = getattr(move, "power", 0) if move else 0
		if move and getattr(move, "type", "").lower() == "fire":
			return int(power * 0.33)
		return power

	def onFieldEnd(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field and hasattr(field, "pseudo_weather"):
			field.pseudo_weather.pop("watersport", None)
		return True

	def onFieldStart(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field:
			pw = getattr(field, "pseudo_weather", {})
			pw["watersport"] = True
			field.pseudo_weather = pw
		return True


class Waterspout:
	def basePowerCallback(self, user, target, move):
		"""Power scales with the user's remaining HP."""
		cur_hp = getattr(user, "hp", 0)
		max_hp = getattr(user, "max_hp", cur_hp or 1)
		return (getattr(move, "power", 150) or 150) * cur_hp / max_hp


class Weatherball:
	def onModifyMove(self, move, user=None, target=None, battle=None):
		weather = _holder_effective_weather(user, battle)
		types = {"sunnyday": "Fire", "sunny": "Fire", "desolateland": "Fire", "rain": "Water", "raindance": "Water", "primordialsea": "Water", "hail": "Ice", "snow": "Ice", "sandstorm": "Rock", "sand": "Rock"}
		if weather in types:
			move.power, move.type = 100, types[weather]

	def onModifyType(self, move, user=None, target=None, battle=None):
		self.onModifyMove(move, user, target, battle)


class Wideguard:
	def onHitSide(self, user, battle):
		"""Protect the side from multi-target moves for the turn."""
		side = getattr(user, "side", None)
		if side and hasattr(side, "volatiles"):
			side.volatiles["wideguard"] = True
			return True
		return False

	def onSideStart(self, *args, **kwargs):
		"""Activate Wide Guard for this side."""
		side = args[0] if args else kwargs.get("side")
		if side:
			vol = getattr(side, "volatiles", {})
			vol["wideguard"] = True
			side.volatiles = vol
		return True

	def onTry(self, *args, **kwargs):
		battle = kwargs.get("battle") if kwargs else None
		if len(args) > 3:
			battle = args[3] or battle
		if battle and getattr(battle, "queue", None) and hasattr(battle.queue, "willAct"):
			try:
				return bool(battle.queue.willAct())
			except Exception:
				return True
		return True

	def onTryHit(self, target, source, move):
		"""Block moves that hit multiple targets."""
		raw = getattr(move, "raw", {}) or {}
		if raw.get("target", getattr(move, "target", "")) in {"allAdjacent", "allAdjacentFoes"}:
			return False
		return True


class Wildboltstorm:
	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		battle = kwargs.get("battle")
		if len(args) > 2:
			battle = args[2] or battle
		field = getattr(battle, "field", None)
		weather = getattr(field, "weather", getattr(battle, "weather", None))
		if str(weather).lower() in ("rain", "raindance") and hasattr(move, "accuracy"):
			move.accuracy = True


class Wish:
	def onEnd(self, *args, **kwargs):
		target = args[0] if args else kwargs.get("target")
		battle = kwargs.get("battle")
		effect_state = kwargs.get("effect_state") or {}
		if not target:
			return False
		heal = effect_state.get("hp")
		if heal:
			if battle and hasattr(battle, "heal"):
				battle.heal(target, heal, source=effect_state.get("source"), effect="move:wish")
			else:
				target.hp = min(getattr(target, "hp", 0) + heal, getattr(target, "max_hp", heal))
		return True

	def onStart(self, *args, **kwargs):
		user = args[0] if args else None
		effect_state = kwargs.get("effect_state") or {}
		source = kwargs.get("source") or (args[1] if len(args) > 1 else None)
		if user:
			effect_state["source"] = source or user
			effect_state["target"] = user
			effect_state["hp"] = getattr(source or user, "max_hp", 0) // 2
		return True


class Wonderroom:
	def durationCallback(self, *args, **kwargs):
		source = args[1] if len(args) > 1 else kwargs.get("source")
		if _effect_id(getattr(source, "ability", None)) == "persistent":
			return 7
		return 5

	def onFieldEnd(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field and hasattr(field, "pseudo_weather"):
			field.pseudo_weather.pop("wonderroom", None)
		return True

	def onFieldRestart(self, *args, **kwargs):
		field = kwargs.get("field") or args[0] if args else None
		if hasattr(field, "remove_pseudo_weather"):
			field.remove_pseudo_weather("wonderroom")

	def onFieldStart(self, *args, **kwargs):
		field = args[0] if args else kwargs.get("field")
		if field:
			pw = getattr(field, "pseudo_weather", {})
			pw["wonderroom"] = True
			field.pseudo_weather = pw
		return True

	def onModifyMove(self, *args, **kwargs):
		move = args[0] if args else kwargs.get("move")
		if move:
			move.creates_wonderroom = True


class Worryseed:
	def onHit(self, user, target, battle):
		"""Replace the target's ability with Insomnia."""
		if _ability_change_blocked(target, "noentrain", "cantsuppress"):
			return False
		setattr(target, "ability", "insomnia")
		return True

	def onTryHit(self, target, source, move):
		"""Fail if the target already has Insomnia or is protected."""
		if _effect_id(getattr(target, "ability", None)) == "insomnia":
			return False
		if _ability_change_blocked(target, "noentrain", "cantsuppress"):
			return False
		return True

	def onTryImmunity(self, *args, **kwargs):
		target = args[0] if args else kwargs.get("target")
		return not (_effect_id(getattr(target, "ability", None)) == "insomnia")


class Wringout:
	def basePowerCallback(self, user, target, move):
		"""Scale power with the target's remaining HP."""
		cur_hp = getattr(target, "hp", 0)
		max_hp = getattr(target, "max_hp", cur_hp or 1)
		return max(1, int(120 * cur_hp / max_hp))


class Yawn:
	"""Apply sleep only when the two-turn drowsy countdown actually expires."""
	def onTryHit(self, target, source, move):
		return not (getattr(target, "status", None) or "yawn" in getattr(target, "volatiles", {}))
	def onStart(self, *args, **kwargs):
		target = args[1] if len(args) == 2 else args[0] if args else kwargs.get("target")
		if target:
			target.volatiles["yawn"] = {"remaining": 2}
		return True
	def onResidual(self, target=None, battle=None):
		if not target:
			return
		state = target.volatiles.get("yawn")
		if not isinstance(state, dict):
			state = {"remaining": int(state or 2)}
			target.volatiles["yawn"] = state
		state["remaining"] -= 1
		if state["remaining"] <= 0:
			target.volatiles.pop("yawn", None)
			if not getattr(target, "status", None) and getattr(target, "hp", 0) > 0:
				if battle:
					battle.apply_status_condition(target, "slp", effect="move:yawn")
				else:
					target.setStatus("slp")
	def onEnd(self, target=None, *args, **kwargs):
		if target:
			target.volatiles.pop("yawn", None)
		return True


def _holder_effective_weather(pokemon, battle=None):
	"""Read holder-local weather without changing the shared field."""
	weather = getattr(pokemon, "effective_weather", None)
	if callable(weather):
		return str(weather()).lower()
	field = getattr(battle, "field", None)
	return str(getattr(field, "weather", getattr(battle, "weather", "")) or "").lower()
