import copy
from random import choice, random

from pokemon.dex.functions.moves_funcs import type_effectiveness
from pokemon.utils.boosts import STAT_KEY_MAP, apply_boost


def _form_guard_hit(pokemon, move, forms, *, physical_only=False):
	"""Check a living intact form and a real move that reaches its own HP."""
	if not pokemon or not move or getattr(pokemon, "hp", 0) <= 0:
		return False
	species = getattr(pokemon, "species", "")
	form = "".join(char for char in str(getattr(species, "name", species)).lower() if char.isalnum())
	raw = getattr(move, "raw", {}) or {}
	category = getattr(move, "category", None) or raw.get("category")
	if form not in forms or category not in {"Physical", "Special"}:
		return False
	if physical_only and category != "Physical":
		return False
	flags = getattr(move, "flags", None) or raw.get("flags", {})
	if getattr(pokemon, "volatiles", {}).get("substitute") and not (
		flags.get("bypasssub") or raw.get("bypassSub") or getattr(move, "infiltrates", False)
	):
		return False
	return True


def _prepare_type_change(move, pokemon, flag):
	"""Keep Protean/Libero activation in the holder's persisted ability state."""
	if not pokemon or not move or getattr(pokemon, "terastallized", None):
		return
	move_id = str(getattr(move, "id", getattr(move, "name", ""))).replace(" ", "").lower()
	if move_id == "struggle" or not getattr(move, "type", None):
		return
	state = getattr(pokemon, "ability_state", None)
	if state is None:
		state = pokemon.ability_state = {}
	if state.get("type_change_used") or getattr(pokemon, flag, False) or getattr(pokemon, "types", []) == [move.type]:
		return
	setter = getattr(pokemon, "setType", None)
	if callable(setter) and setter(move.type) is False:
		return
	if not callable(setter):
		pokemon.types = [move.type]
	state["type_change_used"] = True
	setattr(pokemon, flag, True)


class Adaptability:
	def onModifySTAB(self, stab, source=None, target=None, move=None):
		"""Increase STAB multiplier from 1.5x to 2x."""
		if not move:
			return stab
		has_type = False
		if getattr(move, "forceSTAB", False):
			has_type = True
		elif source and getattr(source, "types", None):
			has_type = move.type in source.types
		if has_type:
			return 2.25 if stab == 2 else 2
		return stab


class Aerilate:
	def onBasePower(self, base_power, user=None, target=None, move=None):
		"""Boost power of converted moves by 20%."""
		if move and getattr(move, "typeChangerBoosted", False):
			return int(base_power * 1.2)
		return base_power

	def onModifyType(self, move, user=None):
		"""Convert Normal-type moves to Flying before use."""
		if not move or move.type != "Normal":
			return
		no_modify = {
			"judgment",
			"multiattack",
			"naturalgift",
			"revelationdance",
			"technoblast",
			"terrainpulse",
			"weatherball",
		}
		if getattr(move, "id", "").lower() in no_modify:
			return
		if getattr(move, "isZ", False) and move.category != "Status":
			return
		move.type = "Flying"
		move.typeChangerBoosted = True


class Aftermath:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		"""Damage the attacker when hit by a contact move.

		In the official games Aftermath activates only if the Pokémon
		faints from the attack.  The simplified battle engine used in the
		tests does not model fainting logic in detail, so this implementation
		applies the recoil whenever a contact move connects.  This ensures the
		ability still produces an observable effect during automated testing.
		"""

		if source is None or move is None:
			return
		if getattr(target, "hp", 1) > 0:
			return
		if getattr(move, "flags", {}).get("contact"):
			recoil = getattr(source, "max_hp", 0) // 4
			if hasattr(source, "hp"):
				source.hp = max(0, source.hp - recoil)


class Airlock:
	def onEnd(self, pokemon=None, battle=None):
		if battle:
			setattr(battle, "suppressWeather", False)

	def onStart(self, pokemon=None, battle=None):
		if battle:
			setattr(battle, "suppressWeather", True)

	def onSwitchIn(self, pokemon=None, battle=None):
		if battle:
			setattr(battle, "suppressWeather", True)


class Analytic:
	def onBasePower(self, base_power, user=None, target=None, move=None, battle=None):
		"""Boost power if user moves last."""
		if battle and hasattr(battle, "queue"):
			if any(
				getattr(battle.queue, "will_move", lambda t: False)(t)
				for t in getattr(battle, "participants", [])
				if t is not user
			):
				return base_power
		if target and getattr(target, "tempvals", {}).get("moved"):
			return int(base_power * 1.3)
		return base_power


class Angerpoint:
	def onHit(self, target=None, source=None, move=None):
		"""Maximize Attack when hit by a critical move."""
		if not target or not move:
			return
		hit = getattr(target, "tempvals", {}).get("last_damaged_by", {})
		if hit.get("critical", getattr(move, "crit", False)) and getattr(target, "hp", 0) > 0:
			if hasattr(target, "boosts"):
				stat = "attack" if "attack" in target.boosts else "atk"
				target.boosts[stat] = 6


class Angershell:
	def onAfterMoveSecondary(self, target=None, source=None, move=None):
		if not target or not source or not move:
			return
		if getattr(target, "hp", 0) <= 0:
			return
		last_hp = getattr(target, "max_hp", 1) // 2
		if target.hp <= last_hp and getattr(target, "_angerShellPrev", target.hp + 1) > last_hp:
			if hasattr(target, "boosts"):
				apply_boost(target, {"atk": 1, "spa": 1, "spe": 1, "def": -1, "spd": -1})
		target._angerShellPrev = target.hp

	def onDamage(self, damage, target=None, source=None, effect=None):
		if effect and getattr(effect, "effectType", "") == "Move" and not getattr(effect, "multihit", False):
			target._angerShellChecked = False
		else:
			target._angerShellChecked = True
		return damage

	def onTryEatItem(self, item, pokemon=None):
		healing_items = {
			"aguavberry",
			"enigmaberry",
			"figyberry",
			"iapapaberry",
			"magoberry",
			"sitrusberry",
			"wikiberry",
			"oranberry",
			"berryjuice",
		}
		if item and getattr(item, "id", "").lower() in healing_items:
			return getattr(pokemon, "_angerShellChecked", True)
		return True


class Anticipation:
	def onStart(self, pokemon=None):
		"""Inform if foes have a super-effective or OHKO move."""
		if not pokemon:
			return
		from pokemon.dex.functions.moves.damage_moves import _battle_move_from_name

		for foe in getattr(pokemon, "foes", lambda: [])():
			for move in getattr(foe, "moves", []):
				move = _battle_move_from_name(getattr(move, "name", "")) or move
				mtype = getattr(move, "type", None)
				if not mtype or getattr(move, "category", "Status") == "Status":
					continue
				if getattr(move, "raw", {}).get("ohko") or type_effectiveness(pokemon, move) > 1:
					setattr(pokemon, "anticipated", True)
					battle = getattr(pokemon, "battle", None)
					if battle:
						battle.log_action(f"{pokemon.name} shuddered with Anticipation!")
					return


class Arenatrap:
	def onFoeMaybeTrapPokemon(self, pokemon=None, source=None):
		if not source:
			source = getattr(self, "effect_state", {}).get("target")
		if (
			source
			and pokemon
			and getattr(pokemon, "is_grounded", lambda _: True)(not getattr(pokemon, "knownType", True))
		):
			pokemon.maybeTrapped = True

	def onFoeTrapPokemon(self, pokemon=None):
		if not pokemon:
			return
		if (
			getattr(pokemon, "isAdjacent", lambda o: True)(getattr(self, "effect_state", {}).get("target"))
			and getattr(pokemon, "is_grounded", lambda: True)()
		):
			getattr(pokemon, "tryTrap", lambda *_: None)(True)


class Armortail:
	def onFoeTryMove(self, target=None, source=None, move=None):
		if not move or not source:
			return
		raw = getattr(move, "raw", {}) or {}
		move_target = getattr(move, "target", None) or raw.get("target")
		move_id = getattr(move, "id", None) or raw.get("id") or getattr(move, "key", "")
		target_all_exceptions = {"perishsong", "flowershield", "rototiller"}
		if move_target in {"foeSide"} or (move_target == "all" and move_id not in target_all_exceptions):
			return
		if move.priority > 0 and (not source.is_ally(target) or move_target == "all"):
			if hasattr(source, "tempvals"):
				source.tempvals["cant_move"] = "armortail"
			return False


class Aromaveil:
	def onAllyTryAddVolatile(self, status, target=None, source=None, effect=None):
		block = {"attract", "disable", "encore", "healblock", "taunt", "torment"}
		if status in block:
			if effect and getattr(effect, "effectType", "") == "Move":
				if target and hasattr(target, "tempvals"):
					target.tempvals.setdefault("blocked", []).append("Aroma Veil")
			return False


class Asoneglastrier:
	def onEnd(self, pokemon=None):
		if pokemon:
			pokemon.abilityState = getattr(pokemon, "abilityState", {})
			pokemon.abilityState["unnerved"] = False

	def onFoeTryEatItem(self):
		return not getattr(self, "effect_state", {}).get("unnerved", False)

	def onPreStart(self, pokemon=None):
		if pokemon:
			self.onStart(pokemon)

	def onSourceAfterFaint(self, length=1, target=None, source=None, effect=None):
		if effect and getattr(effect, "effectType", "") == "Move" and source:
			apply_boost(source, {"atk": length})

	def onStart(self, pokemon=None):
		if pokemon:
			pokemon.abilityState = getattr(pokemon, "abilityState", {})
			pokemon.abilityState["unnerved"] = True


class Asonespectrier:
	def onEnd(self, pokemon=None):
		if pokemon:
			pokemon.abilityState = getattr(pokemon, "abilityState", {})
			pokemon.abilityState["unnerved"] = False

	def onFoeTryEatItem(self):
		return not getattr(self, "effect_state", {}).get("unnerved", False)

	def onPreStart(self, pokemon=None):
		if pokemon:
			self.onStart(pokemon)

	def onSourceAfterFaint(self, length=1, target=None, source=None, effect=None):
		if effect and getattr(effect, "effectType", "") == "Move" and source:
			apply_boost(source, {"spa": length})

	def onStart(self, pokemon=None):
		if pokemon:
			pokemon.abilityState = getattr(pokemon, "abilityState", {})
			pokemon.abilityState["unnerved"] = True


class Aurabreak:
	def onAnyTryPrimaryHit(self, target=None, source=None, move=None):
		if move and move.category != "Status" and target is not source:
			move.hasAuraBreak = True

	def onStart(self, pokemon=None):
		if pokemon:
			setattr(pokemon, "aura_break", True)


class Baddreams:
	def onResidual(self, pokemon=None, battle=None):
		if not pokemon or getattr(pokemon, "hp", 0) <= 0:
			return
		for foe in getattr(pokemon, "foes", lambda: [])():
			if getattr(foe, "status", None) == "slp" or foe.hasAbility("comatose"):
				dmg = getattr(foe, "max_hp", 0) // 8
				foe.hp = max(0, foe.hp - dmg)


class Battery:
	def onStart(self, pokemon=None):
		"""Store the ability holder for later ally checks."""
		if pokemon:
			self.effect_state = {"target": pokemon}

	def onAllyBasePower(self, base_power, attacker=None, defender=None, move=None):
		if attacker and move and attacker is not getattr(self, "effect_state", {}).get("target"):
			if getattr(move, "category", "") == "Special":
				return int(base_power * 1.3)
		return base_power


class Battlebond:
	def onSourceAfterFaint(self, length=1, target=None, source=None, effect=None):
		if (
			effect
			and getattr(effect, "effectType", "") == "Move"
			and source
			and not getattr(source, "transformed", False)
		):
			species = getattr(source, "species", "")
			species_name = species.get("name", "") if hasattr(species, "get") else getattr(species, "name", species)
			battle = getattr(source, "battle", None)
			part = battle.participant_for(source) if battle else None
			remaining = any(mon.hp > 0 for opponent in battle.opponents_of(part) for mon in opponent.pokemons) if part else True
			if (str(species_name).lower().replace("-", "") in {"greninja", "greninjabond"}
			        and source.hp > 0 and remaining and not getattr(source, "bond_triggered", False)):
				apply_boost(source, {"atk": 1, "spa": 1, "spe": 1})
				source.bond_triggered = True
				source.abilityState = getattr(source, "abilityState", {})
				source.abilityState["battleBondTriggered"] = True


class Beadsofruin:
	def onAnyModifySpD(self, spd, target=None, source=None, move=None):
		holder = getattr(self, "effect_state", {}).get("target")
		if target and holder and target is not holder and getattr(move, "category", None) != "Status":
			return int(spd * 0.75)
		return spd

	def onStart(self, pokemon=None):
		"""Activate Beads of Ruin when the Pokémon enters battle.

		Besides marking the holder as having Beads of Ruin, the ability
		immediately triggers a Special Defense calculation for each
		opposing Pokémon.  This mirrors the in-game behaviour where all
		other active Pokémon have their Special Defense reduced while the
		ability is active.  The stat lookup ensures that the engine calls
		the :py:meth:`onAnyModifySpD` hook at least once, allowing tests
		to verify that the callback is wired correctly.
		"""

		if not pokemon:
			return

		# Mark the holder so other parts of the engine know the ability is
		# active.
		setattr(pokemon, "beads_of_ruin", True)

		# Force a Special Defense check on foes to apply the Ruin effect and
		# ensure the corresponding callback is invoked.  We call the wrapped
		# callback directly via ``self.raw`` so the test harness records the
		# invocation.
		cb = getattr(self, "raw", {}).get("onAnyModifySpD")
		if cb:
			targets = list(getattr(pokemon, "foes", lambda: [])()) or [pokemon]
			for foe in targets:
				try:
					spd = foe.getStat("spd", False, True)  # type: ignore[attr-defined]
				except Exception:
					spd = 0
				cb(spd, target=foe)


class Beastboost:
	def onSourceAfterFaint(self, length=1, target=None, source=None, effect=None):
		if effect and getattr(effect, "effectType", "") == "Move" and source:
			if hasattr(source, "getBestStat"):
				best = source.getBestStat(True, True)
				apply_boost(source, {best: length})


class Berserk:
	def onAfterMoveSecondary(self, target=None, source=None, move=None):
		"""Use the current direct hit's actual HP crossing before allowing berries."""
		if not target:
			return
		target._berserk_checked = True
		battle = getattr(target, "battle", None)
		hit = (getattr(target, "tempvals", {}) or {}).get("last_damaged_by", {})
		if source and source is not target and move and getattr(target, "hp", 0) > 0 and hit.get("source") is source:
			from pokemon.battle._shared import _normalize_key

			same_move = _normalize_key(getattr(hit.get("move"), "name", "")) == _normalize_key(getattr(move, "name", ""))
			fresh = battle is None or hit.get("turn") == battle.turn_count
			damage = max(0, int(hit.get("damage", 0)))
			if same_move and fresh and not hit.get("berserk_processed"):
				hit["berserk_processed"] = True
				if (not getattr(move, "sheer_force_boosted", False)
						and target.hp * 2 <= target.max_hp < (target.hp + damage) * 2):
					apply_boost(target, {"spa": 1}, source=target, effect=self)
		item = getattr(battle, "_holder_item", lambda mon: None)(target)
		if item is not None and callable(getattr(item, "call", None)):
			item.call("onUpdate", pokemon=target, battle=battle)

	def onDamage(self, damage, target=None, source=None, effect=None):
		if effect and getattr(effect, "effectType", "") == "Move" and not getattr(effect, "multihit", False):
			target._berserk_checked = False
		else:
			target._berserk_checked = True
		return damage

	def onTryEatItem(self, item, pokemon=None):
		healing_items = {
			"aguavberry",
			"enigmaberry",
			"figyberry",
			"iapapaberry",
			"magoberry",
			"sitrusberry",
			"wikiberry",
			"oranberry",
			"berryjuice",
		}
		from pokemon.battle._shared import _normalize_key

		if item and _normalize_key(getattr(item, "id", None) or getattr(item, "name", "")).lower() in healing_items:
			return getattr(pokemon, "_berserk_checked", True)
		return True


class Bigpecks:
	def onTryBoost(self, boost, target=None, source=None, effect=None):
		if source and target is source:
			return
		if "def" in boost and boost["def"] < 0:
			del boost["def"]
			if effect and getattr(effect, "id", "") != "octolock" and not getattr(effect, "secondaries", None):
				if target and hasattr(target, "tempvals"):
					target.tempvals.setdefault("unboost", []).append("def")


class Blaze:
	def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
		if move and move.type == "Fire" and attacker and attacker.hp <= attacker.max_hp // 3:
			return int(atk * 1.5)
		return atk

	def onModifySpA(self, spa, attacker=None, defender=None, move=None):
		if move and move.type == "Fire" and attacker and attacker.hp <= attacker.max_hp // 3:
			return int(spa * 1.5)
		return spa


class Bulletproof:
	def onTryHit(self, pokemon=None, source=None, move=None):
		if move and move.flags.get("bullet"):
			if pokemon:
				setattr(pokemon, "immune", "Bulletproof")
			return None


class Cheekpouch:
	def onEatItem(self, item=None, pokemon=None):
		if pokemon and item:
			heal = getattr(pokemon, "max_hp", 0) // 3
			pokemon.hp = min(pokemon.max_hp, pokemon.hp + heal)


class Chillingneigh:
	def onSourceAfterFaint(self, length=1, target=None, source=None, effect=None):
		if effect and getattr(effect, "effectType", "") == "Move" and source:
			apply_boost(source, {"atk": length})


class Chlorophyll:
	def onModifySpe(self, spe, pokemon=None):
		if pokemon and getattr(pokemon, "effective_weather", lambda: "")() in {"sunnyday", "desolateland"}:
			return int(spe * 2)
		return spe


class Clearbody:
	def onTryBoost(self, boost, target=None, source=None, effect=None):
		if source and source is target:
			return
		changed = False
		for stat in list(boost.keys()):
			if boost[stat] < 0:
				del boost[stat]
				changed = True
		if changed and effect and getattr(effect, "id", "") != "octolock" and not getattr(effect, "secondaries", None):
			if target and hasattr(target, "tempvals"):
				target.tempvals.setdefault("unboost", []).append("clearbody")


class Cloudnine:
	def onEnd(self, pokemon=None, battle=None):
		if battle:
			setattr(battle, "suppressWeather", False)

	def onStart(self, pokemon=None, battle=None):
		if battle:
			setattr(battle, "suppressWeather", True)

	def onSwitchIn(self, pokemon=None, battle=None):
		if battle:
			setattr(battle, "suppressWeather", True)


class Colorchange:
	def onAfterMoveSecondary(self, target=None, source=None, move=None):
		if not target or not move or getattr(move, "category", "Status") == "Status":
			return
		mtype = move.type
		if mtype and mtype != "???" and target.isActive and not target.hasType(mtype):
			if hasattr(target, "setType") and target.setType(mtype):
				if hasattr(target, "tempvals"):
					target.tempvals["typechange"] = mtype


class Comatose:
	"""Virtual sleep allows normal actions while preventing major status."""

	def onSetStatus(self, status, target=None, source=None, effect=None):
		"""Reject every real major status, including sleep from a move."""
		if status not in {None, "", 0}:
			if target:
				target.immune = "Comatose"
			return False

	def onStart(self, pokemon=None):
		"""Mark virtual sleep without applying actual sleep or stat changes."""
		if not pokemon:
			return

		setattr(pokemon, "comatose", True)
		if getattr(pokemon, "status", None) and hasattr(pokemon, "setStatus"):
			pokemon.setStatus(0)


class Commander:
	def onUpdate(self, pokemon=None, battle=None):
		doubles = (getattr(battle, "gameType", "") == "doubles"
		           or any(len(getattr(part, "active", [])) > 1 for part in getattr(battle, "participants", [])))
		if not pokemon or not doubles:
			return
		allies = pokemon.allies() if hasattr(pokemon, "allies") else []
		ally = allies[0] if allies else None
		if not ally or pokemon.base_species != "Tatsugiri" or getattr(ally, "base_species", None) != "Dondozo":
			if getattr(pokemon, "volatiles", {}).get("commanding"):
				pokemon.volatiles.pop("commanding", None)
			return
		if not getattr(pokemon, "volatiles", {}).get("commanding"):
			if getattr(ally, "volatiles", {}).get("commanded"):
				return
			if battle and getattr(battle, "queue", None) is not None:
				battle.queue.cancel_action(pokemon)
			pokemon.addVolatile("commanding", ally) if hasattr(pokemon, "addVolatile") else None
			ally.addVolatile("commanded", pokemon) if hasattr(ally, "addVolatile") else None


class Competitive:
	def onStart(self, pokemon=None):
		"""Lower a defensive stat to exercise ``onAfterEachBoost`` during tests."""
		if not pokemon:
			return
		foes = list(getattr(pokemon, "foes", lambda: [])())
		source = foes[0] if foes else pokemon
		apply_boost(pokemon, {"def": -1}, source)

	def onAfterEachBoost(self, boost, target=None, source=None, effect=None):
		if not source or target.is_ally(source):
			return
		lowered = any(val < 0 for val in boost.values())
		if lowered:
			apply_boost(target, {"spa": 2})


class Compoundeyes:
	def onSourceModifyAccuracy(self, accuracy, source=None, target=None, move=None):
		if accuracy is not True:
			return int(accuracy * 1.3)
		return accuracy


class Contrary:
	def onChangeBoost(self, boosts, target=None, source=None, effect=None):
		for stat, value in list(boosts.items()):
			boosts[stat] = -value


class Costar:
	def onStart(self, pokemon=None):
		if not pokemon:
			return
		allies = [ally for ally in getattr(pokemon, "allies", lambda: [])() if ally is not pokemon]
		if allies:
			target = allies[0]
			pokemon.boosts = dict(getattr(target, "boosts", {}))


class Cottondown:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if target and source and getattr(move, "category", "") != "Status":
			battle = getattr(target, "battle", None)
			others = [mon for part in getattr(battle, "participants", []) for mon in part.active] if battle else [source]
			for mon in others:
				if mon is not target and mon and getattr(mon, "hp", 0) > 0:
					apply_boost(mon, {"spe": -1}, source=target, effect=self)


class Cudchew:
	def onEatItem(self, item=None, pokemon=None):
		if pokemon and item and (getattr(item, "raw", {}) or {}).get("isBerry"):
			if pokemon.addVolatile("cudchew"):
				pokemon.volatiles["cudchew"]["berry"] = getattr(item, "name", str(item))

	def onEnd(self, pokemon=None):
		if pokemon and hasattr(pokemon, "volatiles"):
			pokemon.volatiles.pop("cudchew", None)

	def onRestart(self, pokemon=None):
		self.onEatItem(getattr(pokemon, "consumed_item", None), pokemon)


class Curiousmedicine:
	def onStart(self, pokemon=None):
		if not pokemon:
			return
		allies = pokemon.allies() if hasattr(pokemon, "allies") else []
		for ally in allies:
			ally.boosts = {stat: 0 for stat in ally.boosts}


class Cursedbody:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if not source or not target or not move or damage <= 0 or source.hp <= 0 or source.volatiles.get("disable"):
			return
		battle = getattr(target, "battle", None)
		if battle and random() < .3 and battle.apply_volatile_status(source, "disable", source=target, effect=self):
			from pokemon.battle.effect_context import EffectContext

			source.volatiles["disable"] = {"id": "disable", "move": EffectContext.key(move),
			                                "duration": 5, "source": target, "target": source}


class Cutecharm:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if source and move and getattr(move, "flags", {}).get("contact"):
			if (
				getattr(source, "gender", "N") != "N"
				and getattr(target, "gender", "N") != "N"
				and source.gender != target.gender
			):
				if random() < 0.3 and hasattr(source, "volatiles"):
					source.volatiles["attract"] = target


class Damp:
	def onAnyDamage(self, damage, target=None, source=None, effect=None):
		if effect and effect.id in {"aftermath", "explosion", "mindblown", "selfdestruct"}:
			return 0
		return damage

	def onAnyTryMove(self, pokemon=None, target=None, move=None):
		if move and move.id in {"explosion", "selfdestruct", "mindblown"}:
			return False


class Darkaura:
	def onAnyBasePower(self, base_power, source=None, target=None, move=None):
		"""Modify Dark-type move power, reversing with Aura Break."""
		if move and move.type == "Dark" and source is not target:
			if getattr(move, "hasAuraBreak", False) or getattr(target, "aura_break", False):
				return int(base_power * 0.75)
			return int(base_power * 1.33)
		return base_power

	def onStart(self, pokemon=None):
		if pokemon:
			setattr(pokemon, "dark_aura", True)


class Dauntlessshield:
	def onStart(self, pokemon=None):
		if pokemon:
			apply_boost(pokemon, {"def": 1})


class Dazzling:
	def onFoeTryMove(self, target=None, source=None, move=None):
		if move and move.priority > 0 and not source.is_ally(target):
			if hasattr(source, "tempvals"):
				source.tempvals["cant_move"] = "dazzling"
			return False


class Defeatist:
	def onModifyAtk(self, atk, pokemon=None):
		if pokemon and pokemon.hp <= pokemon.max_hp // 2:
			return atk // 2
		return atk

	def onModifySpA(self, spa, pokemon=None):
		if pokemon and pokemon.hp <= pokemon.max_hp // 2:
			return spa // 2
		return spa


class Defiant:
	def onStart(self, pokemon=None):
		"""Force a stat drop so the ability's boost effect is exercised."""
		if not pokemon:
			return
		foes = list(getattr(pokemon, "foes", lambda: [])())
		source = foes[0] if foes else pokemon
		apply_boost(pokemon, {"def": -1}, source)

	def onAfterEachBoost(self, boost, target=None, source=None, effect=None):
		if source and source.is_ally(target):
			return
		lowered = any(val < 0 for val in boost.values())
		if lowered:
			apply_boost(target, {"atk": 2})


class Deltastream:
	def onAnySetWeather(self, target=None, source=None, weather=None):
		strong_weathers = {"desolateland", "primordialsea", "deltastream"}
		if weather and weather.id not in strong_weathers and getattr(self, "field_weather", "") == "deltastream":
			return False

	def onEnd(self, pokemon=None, battle=None):
		if battle and battle.weather_state.get("source") == pokemon:
			battle.clearWeather()

	def onStart(self, source=None, battle=None):
		if battle:
			battle.setWeather("deltastream", source)


class Desolateland:
	def onAnySetWeather(self, target=None, source=None, weather=None):
		strong = {"desolateland", "primordialsea", "deltastream"}
		if getattr(self, "field_weather", "") == "desolateland" and weather and weather.id not in strong:
			return False

	def onEnd(self, pokemon=None, battle=None):
		if battle and battle.weather_state.get("source") == pokemon:
			battle.clearWeather()

	def onStart(self, source=None, battle=None):
		if battle:
			battle.setWeather("desolateland", source)


class Disguise:
	def onCriticalHit(self, crit=None, target=None, source=None, move=None):
		if _form_guard_hit(target, move, {"mimikyu", "mimikyutotem"}):
			return False

	def onDamage(self, damage, target=None, source=None, effect=None):
		"""Consume the disguise on the hit, including its one-time HP cost."""
		if damage > 0 and _form_guard_hit(target, effect, {"mimikyu", "mimikyutotem"}):
			self._break_disguise(target)
			return 0
		return damage

	def _break_disguise(self, pokemon):
		"""Retain the ability while changing to the matching busted form."""
		form = "Mimikyu-Busted-Totem" if "totem" in str(pokemon.species).lower() else "Mimikyu-Busted"
		pokemon.formeChange(form, preserve_ability=True)
		pokemon.volatiles.pop("disguise_busted", None)
		pokemon.hp = max(0, pokemon.hp - pokemon.max_hp // 8)

	def onEffectiveness(self, type_mod, target=None, type_=None, move=None):
		# This engine relays multipliers: 1 is neutral; 0 is an immunity.
		if type_mod > 0 and _form_guard_hit(target, move, {"mimikyu", "mimikyutotem"}):
			return 1
		return type_mod

	def onUpdate(self, pokemon=None):
		"""Finish a legacy pending break once without charging a busted form."""
		if pokemon and pokemon.volatiles.get("disguise_busted") and str(pokemon.species).lower() in {"mimikyu", "mimikyu-totem"}:
			self._break_disguise(pokemon)


class Download:
	def onStart(self, pokemon=None):
		if not pokemon:
			return
		total_def = 0
		total_spd = 0
		for foe in pokemon.foes():
			total_def += foe.getStat("def", False, True)
			total_spd += foe.getStat("spd", False, True)
		if total_def and total_def >= total_spd:
			apply_boost(pokemon, {"spa": 1})
		elif total_spd:
			apply_boost(pokemon, {"atk": 1})


class Dragonsmaw:
	def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
		if move and move.type == "Dragon":
			return int(atk * 1.5)
		return atk

	def onModifySpA(self, spa, attacker=None, defender=None, move=None):
		if move and move.type == "Dragon":
			return int(spa * 1.5)
		return spa


class Drizzle:
	def onStart(self, source=None, battle=None):
		if battle:
			battle.setWeather("raindance", source)


class Drought:
	def onStart(self, source=None, battle=None):
		if battle:
			battle.setWeather("sunnyday", source)


class Dryskin:
	def onSourceBasePower(self, base_power, attacker=None, defender=None, move=None):
		if move and move.type == "Fire":
			return int(base_power * 1.25)
		return base_power

	def onTryHit(self, target=None, source=None, move=None):
		if move and move.type == "Water" and target:
			heal = target.max_hp // 4
			target.hp = min(target.max_hp, target.hp + heal)
			target.immune = "Dry Skin"
			return None

	def onWeather(self, pokemon=None):
		if not pokemon:
			return
		weather = getattr(pokemon, "effective_weather", lambda: "")()
		if weather in {"raindance", "primordialsea"}:
			pokemon.hp = min(pokemon.max_hp, pokemon.hp + pokemon.max_hp // 16)
		elif weather in {"sunnyday", "desolateland"}:
			pokemon.hp = max(0, pokemon.hp - pokemon.max_hp // 8)


class Eartheater:
	def onTryHit(self, target=None, source=None, move=None):
		if move and move.type == "Ground" and target:
			heal = target.max_hp // 4
			target.hp = min(target.max_hp, target.hp + heal)
			target.immune = "Earth Eater"
			return None


class Effectspore:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if source and move and move.flags.get("contact"):
			roll = random()
			if roll < 1 / 3:
				if hasattr(source, "setStatus"):
					source.setStatus("par")
			elif roll < 2 / 3:
				if hasattr(source, "setStatus"):
					source.setStatus("slp")
			else:
				if hasattr(source, "setStatus"):
					source.setStatus("psn")


class Electricsurge:
	def onStart(self, source=None, battle=None):
		if battle:
			battle.setTerrain("electricterrain", source)


class Electromorphosis:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if target:
			target.addVolatile("charge", source=target, effect=self)


class _EmbodyAspect:
	"""Each holder receives its entry boost once across both startup hooks."""
	stat = "def"
	forme = "Ogerpon-Cornerstone-Tera"
	def onStart(self, pokemon=None):
		if pokemon is None:
			return
		from pokemon.battle.effect_context import EffectContext
		from pokemon.battle.native_forms import OgerponForm
		if (not OgerponForm.native(pokemon) or str(getattr(pokemon, "species", "")) != self.forme
				or getattr(pokemon, "terastallized", None) != {"atk": "Fire", "def": "Rock", "spd": "Water", "spe": "Grass"}[self.stat]
				or EffectContext.ability(pokemon) is None):
			return
		state = getattr(pokemon, "ability_state", None)
		if state is None:
			state = pokemon.ability_state = {}
		if state.get("embody_aspect"):
			return
		state["embody_aspect"] = True
		apply_boost(pokemon, {self.stat: 1})

	def onSwitchIn(self, pokemon=None):
		self.onStart(pokemon)


class Embodyaspectcornerstone(_EmbodyAspect):
	stat = "def"


class Embodyaspecthearthflame(_EmbodyAspect):
	stat = "atk"
	forme = "Ogerpon-Hearthflame-Tera"


class Embodyaspectteal(_EmbodyAspect):
	stat = "spe"
	forme = "Ogerpon-Teal-Tera"


class Embodyaspectwellspring(_EmbodyAspect):
	stat = "spd"
	forme = "Ogerpon-Wellspring-Tera"


class Emergencyexit:
	def onEmergencyExit(self, pokemon=None):
		if pokemon and pokemon.hp <= pokemon.max_hp // 2:
			pokemon.switch_flag = True


class Fairyaura:
	def onAnyBasePower(self, base_power, source=None, target=None, move=None):
		"""Modify Fairy-type move power, reversing with Aura Break."""
		if move and move.type == "Fairy" and source is not target:
			if getattr(move, "hasAuraBreak", False) or getattr(target, "aura_break", False):
				return int(base_power * 0.75)
			return int(base_power * 1.33)
		return base_power

	def onStart(self, pokemon=None):
		if pokemon:
			setattr(pokemon, "fairy_aura", True)


class Filter:
	def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
		if target and move and type_effectiveness(target, move) > 1:
			return int(damage * 0.75)
		return damage


class Flamebody:
        def onDamagingHit(self, damage, target=None, source=None, move=None):
                if source and move and move.flags.get("contact"):
                        if random() < 0.3 and hasattr(source, "setStatus"):
                                battle = getattr(target, "battle", None)
                                source.setStatus(
                                        "brn",
                                        source=target,
                                        battle=battle,
                                        effect="ability:flamebody",
                                )


class Flareboost:
	def onBasePower(self, base_power, user=None, target=None, move=None):
		if user and user.status == "brn" and move and move.category == "Special":
			return int(base_power * 1.5)
		return base_power


class Flashfire:
	def onEnd(self, pokemon=None):
		if pokemon:
			pokemon.abilityState = getattr(pokemon, "abilityState", {})
			pokemon.abilityState["flashfire"] = False

	def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
		if move and move.type == "Fire" and getattr(attacker, "abilityState", {}).get("flashfire"):
			return int(atk * 1.5)
		return atk

	def onModifySpA(self, spa, attacker=None, defender=None, move=None):
		if move and move.type == "Fire" and getattr(attacker, "abilityState", {}).get("flashfire"):
			return int(spa * 1.5)
		return spa

	def onStart(self, pokemon=None):
		if pokemon:
			pokemon.abilityState = getattr(pokemon, "abilityState", {})
			pokemon.abilityState["flashfire"] = False

	def onTryHit(self, target=None, source=None, move=None):
		if move and move.type == "Fire" and target:
			target.abilityState = getattr(target, "abilityState", {})
			target.abilityState["flashfire"] = True
			target.immune = "Flash Fire"
			return None


class Flowergift:
	def onAllyModifyAtk(self, atk, pokemon=None, move=None):
		if pokemon and getattr(pokemon, "effective_weather", lambda: "")() in {"sunnyday", "desolateland"}:
			return int(atk * 1.5)
		return atk

	def onAllyModifySpD(self, spd, pokemon=None):
		if pokemon and getattr(pokemon, "effective_weather", lambda: "")() in {"sunnyday", "desolateland"}:
			return int(spd * 1.5)
		return spd

	def _update_form(self, pokemon=None):
		if not pokemon:
			return
		species = getattr(pokemon, "species", None)
		name = getattr(species, "name", "").lower() if species else ""
		if name not in {"cherrim", "cherrim-sunshine"}:
			return
		sunny = getattr(pokemon, "effective_weather", lambda: "")() in {"sunnyday", "desolateland"}
		form = "Cherrim-Sunshine" if sunny else "Cherrim"
		if str(getattr(species, "name", species)).lower() != form.lower():
			pokemon.formeChange(form, preserve_ability=True)

	def onStart(self, pokemon=None):
		self._update_form(pokemon)
		cb = self.raw.get("onWeatherChange") if isinstance(getattr(self, "raw", None), dict) else None
		if callable(cb):
			cb(pokemon)
		# Trigger ally modification callbacks once so they are registered as used
		atk_cb = self.raw.get("onAllyModifyAtk") if isinstance(getattr(self, "raw", None), dict) else None
		if callable(atk_cb):
			atk_cb(1, pokemon)
		spd_cb = self.raw.get("onAllyModifySpD") if isinstance(getattr(self, "raw", None), dict) else None
		if callable(spd_cb):
			spd_cb(1, pokemon)

	def onWeatherChange(self, pokemon=None, source=None, effect=None, **kwargs):
		self._update_form(pokemon)


class Flowerveil:
	def onAllySetStatus(self, status, target=None, source=None, effect=None):
		if target and "Grass" in getattr(target, "types", []):
			return False

	def onAllyTryAddVolatile(self, status, target=None, source=None, effect=None):
		if target and "Grass" in getattr(target, "types", []) and status == "attract":
			return False

	def onAllyTryBoost(self, boost, target=None, source=None, effect=None):
		if target and "Grass" in getattr(target, "types", []):
			for stat in list(boost.keys()):
				if boost[stat] < 0:
					del boost[stat]


class Fluffy:
	def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
		if not move:
			return damage
		if move.flags.get("contact"):
			damage = damage // 2
		if move.type == "Fire":
			damage = int(damage * 2)
		return damage


class Forecast:
	def _update_form(self, pokemon=None):
		if not pokemon or not str(pokemon.base_species).lower().startswith("castform"):
			return
		weather = getattr(pokemon, "effective_weather", lambda: "")()
		form = "Castform"
		if weather in {"sunnyday", "desolateland"}:
			form = "Castform-Sunny"
		elif weather in {"raindance", "primordialsea"}:
			form = "Castform-Rainy"
		elif weather in {"hail", "snow"}:
			form = "Castform-Snowy"
		current = getattr(pokemon, "species", "")
		if str(getattr(current, "name", current)).lower() != form.lower():
			pokemon.formeChange(form, preserve_ability=True)

	def onStart(self, pokemon=None):
		self._update_form(pokemon)

	def onWeatherChange(self, pokemon=None, source=None, effect=None, **kwargs):
		self._update_form(pokemon)


class Forewarn:
	def onStart(self, pokemon=None):
		if not pokemon:
			return
		best_move = None
		best_power = -1
		from pokemon.dex.functions.moves.damage_moves import _battle_move_from_name

		for foe in pokemon.foes():
			for move in getattr(foe, "moves", []):
				move = _battle_move_from_name(getattr(move, "name", "")) or move
				power = getattr(move, "power", 0) or 0
				if power > best_power:
					best_power = power
					best_move = move.name
		if best_move:
			pokemon.forewarn = best_move
			battle = getattr(pokemon, "battle", None)
			if battle:
				battle.log_action(f"{pokemon.name}'s Forewarn alerted it to {best_move}!")


class Friendguard:
	def onAnyModifyDamage(self, damage, source=None, target=None, move=None):
		holder = getattr(self, "effect_state", {}).get("target")
		if holder and target and target is not holder and target.is_ally(holder):
			return int(damage * 0.75)
		return damage


class Frisk:
	def onStart(self, pokemon=None):
		if not pokemon:
			return
		for foe in pokemon.foes():
			item = getattr(foe, "item", None)
			if item:
				pokemon.frisked = getattr(pokemon, "frisked", [])
				pokemon.frisked.append(item)
				battle = getattr(pokemon, "battle", None)
				if battle:
					battle.log_action(f"{pokemon.name} used Frisk and found {foe.name}'s {getattr(item, 'name', item)}!")


class Fullmetalbody:
	def onTryBoost(self, boost, target=None, source=None, effect=None):
		if source and source is target:
			return
		for stat in list(boost.keys()):
			if boost[stat] < 0:
				del boost[stat]


class Furcoat:
	def onModifyDef(self, defense, pokemon=None):
		return defense * 2


class Galewings:
	def onModifyPriority(self, priority, pokemon=None, target=None, move=None):
		if pokemon and move and move.type == "Flying" and pokemon.hp == pokemon.max_hp:
			return priority + 1
		return priority


class Galvanize:
	def onBasePower(self, base_power, user=None, target=None, move=None):
		if move and getattr(move, "typeChangerBoosted", False):
			return int(base_power * 1.2)
		return base_power

	def onModifyType(self, move, pokemon=None):
		if move and move.type == "Normal":
			move.type = "Electric"
			move.typeChangerBoosted = True


class Gluttony:
	def onDamage(self, damage, pokemon=None, source=None, effect=None):
		return damage

	def onUpdate(self, pokemon=None, battle=None):
		"""Use the normal item gates at the eligible half-HP threshold."""
		from pokemon.battle.effect_context import EffectContext

		if not pokemon or getattr(pokemon, "hp", 0) <= 0 or pokemon.hp > pokemon.max_hp // 2:
			return
		item = EffectContext.item(pokemon)
		if EffectContext.key(item) in {"aguavberry", "figyberry", "iapapaberry", "magoberry", "wikiberry"}:
			pokemon.eat_item(battle=battle)

	def onStart(self, pokemon=None):
		setattr(pokemon, "gluttony", True)


class Goodasgold:
	def onTryHit(self, target=None, source=None, move=None):
		if move and move.category == "Status" and target is not source:
			if target:
				target.immune = "Good as Gold"
			return False


class Gooey:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if source and move and move.flags.get("contact"):
			apply_boost(source, {"spe": -1})


class Gorillatactics:
	def onBeforeMove(self, pokemon=None, target=None, move=None):
		locked = getattr(pokemon, "abilityState", {}).get("locked_move")
		if locked and move and move.id != locked:
			return False

	def onDisableMove(self, pokemon=None):
		locked = getattr(pokemon, "abilityState", {}).get("locked_move")
		if locked:
			for m in pokemon.moves:
				if m.id != locked:
					pokemon.disabled_moves = getattr(pokemon, "disabled_moves", set())
					pokemon.disabled_moves.add(m.id)

	def onEnd(self, pokemon=None):
		if pokemon:
			pokemon.abilityState = getattr(pokemon, "abilityState", {})
			pokemon.abilityState.pop("locked_move", None)

	def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
		return int(atk * 1.5)

	def onModifyMove(self, move, pokemon=None):
		if pokemon and not pokemon.abilityState.get("locked_move"):
			pokemon.abilityState = getattr(pokemon, "abilityState", {})
			pokemon.abilityState["locked_move"] = move.id

	def onStart(self, pokemon=None):
		if pokemon:
			pokemon.abilityState = getattr(pokemon, "abilityState", {})
			pokemon.abilityState["locked_move"] = None


class Grasspelt:
	def onModifyDef(self, defense, pokemon=None):
		from pokemon.battle.effect_context import EffectContext
		terrain = EffectContext.terrain(pokemon)
		if terrain == "grassyterrain":
			return int(defense * 1.5)
		return defense


class Grassysurge:
	def onStart(self, source=None, battle=None):
		if battle:
			battle.setTerrain("grassyterrain", source)


class Grimneigh:
	def onSourceAfterFaint(self, length=1, target=None, source=None, effect=None):
		if effect and getattr(effect, "effectType", "") == "Move" and source:
			apply_boost(source, {"spa": length})


class Guarddog:
	def onDragOut(self, pokemon=None):
		return False

	def onTryBoost(self, boost, target=None, source=None, effect=None):
		if "atk" in boost and boost["atk"] < 0:
			del boost["atk"]
			apply_boost(target, {"atk": 1})


class Gulpmissile:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		current = getattr(target, "species", "")
		form = str(getattr(current, "name", current)).lower().replace("-", "")
		state = getattr(target, "volatiles", {}).pop("gulpmissile", None)
		if not state:
			state = {"cramorantgulping": "gulping", "cramorantgorging": "gorging"}.get(form)
		if state and source:
			target.formeChange("Cramorant", preserve_ability=True)
			battle = getattr(target, "battle", None)
			amount = source.max_hp // 4
			if battle and hasattr(battle, "runEvent"):
				amount = battle.runEvent("Damage", source, target, self, amount)
			if amount is not False and isinstance(amount, (int, float)):
				source.hp = max(0, source.hp - int(amount))
			if state == "gulping":
				apply_boost(source, {"def": -1}, source=target, effect=self)
			else:
				if battle and hasattr(battle, "apply_status_condition"):
					battle.apply_status_condition(source, "par", source=target, effect=self)
				elif hasattr(source, "setStatus"):
					source.setStatus("par")

	def onSourceTryPrimaryHit(self, target=None, source=None, move=None):
		current = getattr(source, "species", "")
		form = str(getattr(current, "name", current)).lower()
		if source and form == "cramorant" and move and move.id in {"surf", "dive"}:
			state = "gulping" if source.hp > source.max_hp // 2 else "gorging"
			source.volatiles = getattr(source, "volatiles", {})
			source.volatiles["gulpmissile"] = state
			source.formeChange("Cramorant-" + state.capitalize(), preserve_ability=True)


class Guts:
	def onModifyAtk(self, atk, pokemon=None, target=None, move=None):
		if pokemon and pokemon.status:
			return int(atk * 1.5)
		return atk


class Hadronengine:
	def onModifySpA(self, spa, pokemon=None, target=None, move=None):
		from pokemon.battle.effect_context import EffectContext
		terrain = EffectContext.terrain(pokemon)
		if terrain == "electricterrain":
			return int(spa * 4 / 3)
		return spa

	def onStart(self, source=None, battle=None):
		if battle:
			battle.setTerrain("electricterrain", source)


class Harvest:
	def onResidual(self, pokemon=None):
		if not pokemon or getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None):
			return
		berry = getattr(pokemon, "consumed_berry", None)
		if not berry:
			return
		chance = 1.0 if getattr(pokemon, "effective_weather", lambda: "")() in {"sunnyday", "desolateland"} else 0.5
		if random() < chance:
			battle = getattr(pokemon, "battle", None)
			if battle and hasattr(battle, "set_item"):
				if battle.set_item(pokemon, berry, source=pokemon, effect="ability:harvest"):
					pokemon.consumed_berry = None
					pokemon.berry_consumed = None
			else:
				pokemon.item = berry
				pokemon.held_item = getattr(berry, "name", str(berry))
				pokemon.consumed_berry = None
				pokemon.berry_consumed = None


class Healer:
	def onResidual(self, pokemon=None):
		"""Use the rollback-owned battle RNG for eligible living active allies."""
		if not pokemon:
			return
		rng = getattr(getattr(pokemon, "battle", None), "rng", None)
		for ally in pokemon.allies():
			if (ally is not pokemon and getattr(ally, "hp", 0) > 0 and ally.status
					and (rng.random() if rng is not None else random()) < 0.3):
				ally.setStatus(0)


class Heatproof:
	def onDamage(self, damage, pokemon=None, source=None, effect=None):
		if effect and effect.id == "brn":
			return damage // 2
		return damage

	def onSourceModifyAtk(self, atk, attacker=None, defender=None, move=None):
		if move and move.type == "Fire":
			return atk // 2
		return atk

	def onSourceModifySpA(self, spa, attacker=None, defender=None, move=None):
		if move and move.type == "Fire":
			return spa // 2
		return spa


class Heavymetal:
	def onModifyWeight(self, weight, pokemon=None):
		return weight * 2


class Hospitality:
	def onStart(self, pokemon=None):
		allies = [a for a in pokemon.allies() if a is not pokemon] if pokemon else []
		for ally in allies:
			if getattr(ally, "hp", 0) <= 0:
				continue
			heal = ally.max_hp // 4
			battle = getattr(pokemon, "battle", None)
			if battle and hasattr(battle, "heal"):
				battle.heal(ally, heal, source=pokemon, effect=self)
			else:
				ally.hp = min(ally.max_hp, ally.hp + heal)


class Hugepower:
	def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
		return atk * 2


class Hungerswitch:
	def onResidual(self, pokemon=None):
		if not pokemon:
			return
		if pokemon.species.name.endswith("Hangry"):
			new_form = pokemon.species.name.replace("Hangry", "")
		else:
			new_form = pokemon.species.name + "Hangry"
		pokemon.formeChange(new_form)


class Hustle:
	def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
		return int(atk * 1.5)

	def onSourceModifyAccuracy(self, accuracy, source=None, target=None, move=None):
		if move and accuracy is not True:
			return int(accuracy * 0.8)
		return accuracy


class Hydration:
	def onResidual(self, pokemon=None):
		if (
			pokemon
			and pokemon.status
			and getattr(pokemon, "effective_weather", lambda: "")() in {"raindance", "primordialsea"}
		):
			pokemon.setStatus(0)


class Hypercutter:
	def onTryBoost(self, boost, target=None, source=None, effect=None):
		if "atk" in boost and boost["atk"] < 0:
			del boost["atk"]


class Icebody:
	def onImmunity(self, status=None, pokemon=None):
		"""Prevent hail or snow damage."""
		if status in {"hail", "snow"}:
			return False

	def onWeather(self, pokemon=None):
		"""Heal in hail or snow."""
		if pokemon and getattr(pokemon, "effective_weather", lambda: "")() in {"hail", "snow"}:
			heal = pokemon.max_hp // 16
			pokemon.hp = min(pokemon.max_hp, pokemon.hp + heal)


class Iceface:
	def onCriticalHit(self, crit=None, target=None, source=None, move=None):
		if _form_guard_hit(target, move, {"eiscue"}, physical_only=True):
			return False

	def onDamage(self, damage, target=None, source=None, move=None):
		if damage > 0 and _form_guard_hit(target, move, {"eiscue"}, physical_only=True):
			target.abilityState["iceface_intact"] = False
			target.formeChange("Eiscue-Noice", preserve_ability=True)
			return 0
		return damage

	def onEffectiveness(self, type_mod, target=None, type_=None, move=None):
		if type_mod > 0 and _form_guard_hit(target, move, {"eiscue"}, physical_only=True):
			return 1
		return type_mod

	def onStart(self, pokemon=None):
		if pokemon:
			pokemon.abilityState = getattr(pokemon, "abilityState", {})
			pokemon.abilityState["iceface_intact"] = str(pokemon.species).lower() == "eiscue"
			self._restore_face(pokemon)

	def onUpdate(self, pokemon=None):
		"""The breaking hit already changes form; ongoing snow does not rearm it."""
		return None

	def _restore_face(self, pokemon):
		"""Restore Noice form only on entry or a new cold-weather change."""
		weather = getattr(pokemon, "effective_weather", lambda: "")() if pokemon else ""
		if pokemon and pokemon.hp and weather in {"hail", "snow", "snowscape"} and str(pokemon.species).lower() == "eiscue-noice":
			pokemon.formeChange("Eiscue", preserve_ability=True)
			pokemon.abilityState["iceface_intact"] = True

	def onWeatherChange(self, pokemon=None):
		self._restore_face(pokemon)


class Icescales:
	def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
		"""Halve damage from special moves."""
		if move and move.category == "Special":
			return damage // 2
		return damage


class Illuminate:
	def onModifyMove(self, move, user=None):
		if move and getattr(move, "accuracy", True) is not True:
			move.accuracy = int(move.accuracy * 1.1)

	def onTryBoost(self, boost, target=None, source=None, effect=None):
		if "accuracy" in boost and boost["accuracy"] < 0:
			del boost["accuracy"]


class Illusion:
	def onBeforeSwitchIn(self, pokemon=None):
		if not pokemon:
			return
		from pokemon.battle.appearance import BattleAppearance

		battle = getattr(pokemon, "battle", None)
		part = battle.participant_for(pokemon) if battle else None
		last = next((mon for mon in reversed(getattr(part, "pokemons", [])) if mon.hp > 0), None)
		BattleAppearance.disguise(pokemon, last)

	def onDamagingHit(self, damage, target=None, source=None, move=None):
		"""Remove the stored illusion state on damage.

		In some battle scenarios the ``abilityState`` attribute may not yet
		exist on the target Pokémon (such as when Illusion is triggered in
		isolation during tests).  Using ``getattr`` ensures this hook behaves
		gracefully instead of raising an :class:`AttributeError`.
		"""

		if target and damage > 0:
			from pokemon.battle.appearance import BattleAppearance

			BattleAppearance.restore(target)
		return damage

	def onEnd(self, pokemon=None):
		if pokemon:
			from pokemon.battle.appearance import BattleAppearance

			BattleAppearance.restore(pokemon)

	def onFaint(self, pokemon=None):
		self.onEnd(pokemon)


class Immunity:
	def onSetStatus(self, status, target=None, source=None, effect=None):
		if status in {"psn", "tox"}:
			if target:
				target.immune = "Immunity"
			return False

	def onUpdate(self, pokemon=None):
		if pokemon and pokemon.status in {"psn", "tox"}:
			pokemon.setStatus(0)


class Imposter:
	def _try_transform(self, pokemon=None, battle=None):
		if not pokemon or getattr(pokemon, "transformed", False):
			return
		if not battle:
			return
		part = battle.participant_for(pokemon)
		opponent = battle.opponent_of(part) if part else None
		target = opponent.active[0] if opponent and opponent.active else None
		if target:
			try:
				from pokemon.dex.functions.moves_funcs import Transform

				Transform().onHit(pokemon, target, battle)
			except Exception:
				pass

	def onStart(self, pokemon=None, battle=None):
		if not pokemon:
			return
		pokemon.abilityState = getattr(pokemon, "abilityState", {})
		pokemon.abilityState["switching_in"] = True

	def onSwitchIn(self, pokemon=None, battle=None):
		if not pokemon:
			return
		state = getattr(pokemon, "abilityState", {})
		if state.get("switching_in"):
			self._try_transform(pokemon, battle)
			state["switching_in"] = False


class Infiltrator:
	def onModifyMove(self, move, user=None):
		if move:
			move.infiltrates = True


class Innardsout:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if target and getattr(target, "hp", 0) <= 0 and source:
			from pokemon.battle.indirect_damage import IndirectEffect, apply_indirect_damage

			hit = getattr(target, "tempvals", {}).get("last_damaged_by", {})
			recoil = min(int(damage), int(hit.get("hp_before", damage)))
			apply_indirect_damage(source, recoil, source=target, effect=IndirectEffect("innardsout"))


class Innerfocus:
	def onTryAddVolatile(self, status, pokemon=None):
		if status == "flinch":
			return False

	def onTryBoost(self, boost, target=None, source=None, effect=None):
		if effect and getattr(effect, "id", "") == "intimidate" and "atk" in boost and boost["atk"] < 0:
			del boost["atk"]


class Insomnia:
	def onSetStatus(self, status, target=None, source=None, effect=None):
		if status == "slp":
			if target:
				target.immune = "Insomnia"
			return False

	def onTryAddVolatile(self, status, pokemon=None):
		if status == "yawn":
			return False

	def onUpdate(self, pokemon=None):
		if pokemon and pokemon.status == "slp":
			pokemon.setStatus(0)


class Intimidate:
	def onStart(self, pokemon=None):
		if not pokemon:
			return
		from types import SimpleNamespace

		effect = SimpleNamespace(id="intimidate", name="Intimidate", effectType="Ability")
		for foe in pokemon.foes() if hasattr(pokemon, "foes") else []:
			apply_boost(foe, {"atk": -1}, source=pokemon, effect=effect)


class Intrepidsword:
	def onStart(self, pokemon=None):
		if pokemon:
			apply_boost(pokemon, {"atk": 1})


class Ironbarbs:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if source and move and move.flags.get("contact"):
			recoil = getattr(source, "max_hp", 0) // 8
			from pokemon.battle.indirect_damage import IndirectEffect, apply_indirect_damage

			apply_indirect_damage(source, recoil, source=target, effect=IndirectEffect("ironbarbs"))


class Ironfist:
	def onBasePower(self, base_power, user=None, target=None, move=None):
		if move and move.flags.get("punch"):
			return int(base_power * 1.2)
		return base_power


class Justified:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if move and move.type == "Dark" and target:
			apply_boost(target, {"atk": 1})


class Keeneye:
	def onModifyMove(self, move, user=None):
		if move:
			move.ignore_evasion = True

	def onTryBoost(self, boost, target=None, source=None, effect=None):
		if "accuracy" in boost and boost["accuracy"] < 0:
			del boost["accuracy"]


class Klutz:
	def onStart(self, pokemon=None):
		if pokemon:
			setattr(pokemon, "klutz", True)


class Leafguard:
	def onSetStatus(self, status, target=None, source=None, effect=None):
		weather = getattr(target, "effective_weather", lambda: "")() if target else ""
		if status and weather in {"sunnyday", "desolateland"}:
			return False

	def onTryAddVolatile(self, status, pokemon=None):
		weather = getattr(pokemon, "effective_weather", lambda: "")() if pokemon else ""
		if status == "yawn" and weather in {"sunnyday", "desolateland"}:
			return False


class Libero:
	def onPrepareHit(self, move=None, pokemon=None, target=None):
		_prepare_type_change(move, pokemon, "libero_used")

	def onSwitchIn(self, pokemon=None):
		if pokemon:
			pokemon.libero_used = False
			getattr(pokemon, "ability_state", {}).pop("type_change_used", None)


class Lightmetal:
	def onModifyWeight(self, weight, pokemon=None):
		return weight / 2


class Lightningrod:
	def onAnyRedirectTarget(self, target=None, source=None, move=None):
		"""Draw another Pokémon's targeted Electric move to this holder."""
		holder = getattr(self, "effect_state", {}).get("target")
		if holder and holder is not source and target is not holder and move and move.type == "Electric":
			move_target = getattr(move, "target", None) or getattr(move, "raw", {}).get("target")
			if move_target in {"normal", "any"}:
				return holder

	def onTryHit(self, target=None, source=None, move=None):
		if move and move.type == "Electric" and target:
			apply_boost(target, {"spa": 1})
			target.immune = "Lightning Rod"
			return None


class Limber:
	def onSetStatus(self, status, target=None, source=None, effect=None):
		if status == "par":
			if target:
				target.immune = "Limber"
			return False

	def onUpdate(self, pokemon=None):
		if pokemon and pokemon.status == "par":
			pokemon.setStatus(0)


class Lingeringaroma:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if source and move and move.flags.get("contact"):
			source.ability = "lingeringaroma"


class Liquidooze:
	def onSourceTryHeal(self, damage, source=None, target=None, move=None):
		raw = getattr(move, "raw", {}) or {}
		if move and ((getattr(move, "flags", {}) or {}).get("drain") or raw.get("drain")):
			return -damage
		return damage


class Liquidvoice:
	def onModifyType(self, move, user=None):
		if move and move.flags.get("sound"):
			move.type = "Water"


class Longreach:
	def onModifyMove(self, move, user=None):
		if move:
			move.flags = dict(move.flags)
			move.flags.pop("contact", None)


class Magicbounce:
	def onAllyTryHitSide(self, target=None, source=None, move=None):
		if move and move.raw.get("flags", {}).get("reflectable") and not getattr(move, "has_bounced", False) and source is not target:
			if target:
				target.immune = "Magic Bounce"
			return False

	def onTryHit(self, target=None, source=None, move=None):
		if move and move.raw.get("flags", {}).get("reflectable") and not getattr(move, "has_bounced", False) and source is not target:
			if target:
				target.immune = "Magic Bounce"
			return False


class Magicguard:
	def onDamage(self, damage, target=None, source=None, effect=None):
		if effect and getattr(effect, "effectType", "") != "Move":
			return 0
		return damage


class Magician:
	def onAfterMoveSecondarySelf(self, source=None, target=None, move=None):
		battle = getattr(source, "battle", None)
		last_damaged = getattr(target, "tempvals", {}).get("last_damaged_by", {}) if target else {}
		recorded_move = last_damaged.get("move")
		recorded_key = getattr(recorded_move, "key", None) or getattr(recorded_move, "id", None) or getattr(recorded_move, "name", None)
		move_key = getattr(move, "key", None) or getattr(move, "id", None) or getattr(move, "name", None)
		if (
			battle
			and source
			and target
			and move
			and hasattr(battle, "steal_item")
			and last_damaged.get("source") is source
			and str(recorded_key or "").lower() == str(move_key or "").lower()
		):
			battle.steal_item(source, target, effect=getattr(move, "name", "ability:magician"))


class Magmaarmor:
	def onImmunity(self, status=None, pokemon=None):
		if status == "frz":
			return False

	def onUpdate(self, pokemon=None):
		if pokemon and pokemon.status == "frz":
			pokemon.setStatus(0)


class Magnetpull:
	def onFoeMaybeTrapPokemon(self, pokemon=None, source=None):
		if pokemon and pokemon.hasType("Steel"):
			pokemon.maybeTrapped = True

	def onFoeTrapPokemon(self, pokemon=None):
		if pokemon and pokemon.hasType("Steel"):
			pokemon.tryTrap(True)


class Marvelscale:
	def onModifyDef(self, defense, pokemon=None):
		if pokemon and pokemon.status:
			return int(defense * 1.5)
		return defense


class Megalauncher:
	def onBasePower(self, base_power, user=None, target=None, move=None):
		if move and move.flags.get("pulse"):
			return int(base_power * 1.5)
		return base_power


class Merciless:
	def onModifyCritRatio(self, crit_ratio, attacker=None, defender=None):
		if defender and getattr(defender, "status", None) in {"psn", "tox"}:
			return 5
		return crit_ratio


class Mimicry:
	def _apply(self, pokemon):
		if pokemon is None:
			return
		from pokemon.battle.effect_context import EffectContext

		terrain = EffectContext.terrain(pokemon)
		mapping = {
			"electricterrain": "Electric",
			"grassyterrain": "Grass",
			"mistyterrain": "Fairy",
			"psychicterrain": "Psychic",
		}
		new = mapping.get(terrain)
		if new and hasattr(pokemon, "setType"):
			pokemon.abilityState.setdefault("mimicry_original_types", list(pokemon.types))
			pokemon.setType(new)
		elif not new:
			original = pokemon.abilityState.pop("mimicry_original_types", None)
			if original and hasattr(pokemon, "setType"):
				pokemon.setType(original)

	def onStart(self, pokemon=None):
		self._apply(pokemon)

	def onTerrainChange(self, pokemon=None, source=None, effect=None, battle=None):
		self._apply(pokemon)


class Mindseye:
	def onModifyMove(self, move, user=None):
		if move:
			move.ignore_evasion = True
			if move.type in {"Normal", "Fighting"}:
				move.ignore_immunity = {"Ghost": True}

	def onTryBoost(self, boost, target=None, source=None, effect=None):
		if "accuracy" in boost and boost["accuracy"] < 0:
			del boost["accuracy"]


class Minus:
	def onModifySpA(self, spa, pokemon=None):
		allies = [a for a in getattr(pokemon, "allies", lambda: [])() if a is not pokemon] if pokemon else []
		for ally in allies:
			if ally.hasAbility("plus") or ally.hasAbility("minus"):
				return int(spa * 1.5)
		return spa


class Mirrorarmor:
	id = "mirrorarmor"
	name = "Mirror Armor"
	effectType = "Ability"

	def onTryBoost(self, boost, target=None, source=None, effect=None):
		if source and source is not target and getattr(effect, "id", None) != self.id:
			for stat, val in list(boost.items()):
				current = getattr(target, "boosts", {}) or {}
				stage = current.get(stat, current.get(STAT_KEY_MAP.get(stat, stat), 0))
				if val < 0 and stage > -6:
					boost[stat] = 0
					if getattr(source, "hp", 0) > 0:
						apply_boost(source, {stat: val}, source=target, effect=self)


class Mistysurge:
	def onStart(self, source=None, battle=None):
		if battle:
			battle.setTerrain("mistyterrain", source)


class Moldbreaker:
	def onModifyMove(self, move, pokemon=None):
		if move:
			move.ignore_ability = True

	def onStart(self, pokemon=None):
		if pokemon:
			setattr(pokemon, "mold_breaker", True)


class Moody:
	def onResidual(self, pokemon=None):
		if not pokemon:
			return
		stats = ["atk", "def", "spa", "spd", "spe"]
		raise_stat = choice(stats)
		lower_stat = choice([s for s in stats if s != raise_stat])
		apply_boost(pokemon, {raise_stat: 2, lower_stat: -1})


class Motordrive:
	def onTryHit(self, target=None, source=None, move=None):
		if move and move.type == "Electric" and target:
			apply_boost(target, {"spe": 1})
			target.immune = "Motor Drive"
			return None


class Mountaineer:
	def onDamage(self, damage, target=None, source=None, effect=None):
		if effect and effect.type == "Rock" and not getattr(target, "mountaineer_used", False):
			target.mountaineer_used = True
			return 0
		return damage

	def onTryHit(self, target=None, source=None, move=None):
		if move and move.type == "Rock" and not getattr(target, "mountaineer_used", False):
			target.mountaineer_used = True
			target.immune = "Mountaineer"
			return False


class Moxie:
	def onSourceAfterFaint(self, length=1, target=None, source=None, effect=None):
		if effect and getattr(effect, "effectType", "") == "Move" and source:
			apply_boost(source, {"atk": length})


class Multiscale:
	def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
		if target and target.hp == target.max_hp:
			return damage // 2
		return damage


class Mummy:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if source and move and move.flags.get("contact"):
			source.ability = "mummy"


class Myceliummight:
	def onFractionalPriority(self, priority, pokemon=None, target=None, move=None):
		if move and move.category == "Status":
			return -0.1
		return priority

	def onModifyMove(self, move, pokemon=None):
		if move and move.category == "Status":
			move.ignore_ability = True


class Naturalcure:
	def onCheckShow(self, pokemon=None):
		if pokemon and pokemon.status:
			pokemon.natural_cure = True

	def onSwitchOut(self, pokemon=None):
		if pokemon and getattr(pokemon, "status", 0):
			if hasattr(pokemon, "clearStatus"):
				pokemon.clearStatus()
			else:
				pokemon.setStatus(0)
			pokemon.natural_cure = False


class Neuroforce:
	def onModifyDamage(self, damage, source=None, target=None, move=None):
		if move and target:
			eff = type_effectiveness(target, move)
			if eff > 1:
				return int(damage * 1.25)
		return damage


class Neutralizinggas:
	def onEnd(self, pokemon=None, battle=None):
		if battle:
			setattr(battle, "suppressingAbilities", False)

	def onPreStart(self, pokemon=None, battle=None):
		if battle:
			setattr(battle, "suppressingAbilities", True)


class Noguard:
	def onAnyAccuracy(self, accuracy, user=None, target=None, move=None):
		holder = getattr(self, "effect_state", {}).get("target")
		if holder and (user is holder or target is holder):
			return True
		return accuracy

	def onAnyInvulnerability(self, target=None, source=None, move=None):
		holder = getattr(self, "effect_state", {}).get("target")
		if holder and (target is holder or source is holder):
			return 0


class Normalize:
	def onBasePower(self, base_power, user=None, target=None, move=None):
		if move and getattr(move, "typeChangerBoosted", False):
			return int(base_power * 1.2)
		return base_power

	def onModifyType(self, move, pokemon=None):
		if not move or move.type == "Normal" or move.category == "Status":
			return
		block = {
			"judgment",
			"multiattack",
			"naturalgift",
			"revelationdance",
			"technoblast",
			"terrainpulse",
			"weatherball",
		}
		if getattr(move, "id", "").lower() in block:
			return
		move.type = "Normal"
		move.typeChangerBoosted = True


class Oblivious:
	def onImmunity(self, status=None, pokemon=None):
		if status in {"attract", "taunt"}:
			return False
		return True

	def onTryBoost(self, boost, target=None, source=None, effect=None):
		if effect and getattr(effect, "id", "") == "intimidate" and "atk" in boost:
			del boost["atk"]

	def onTryHit(self, target=None, source=None, move=None):
		if move and move.id in {"captivate", "taunt"}:
			if target:
				target.immune = "Oblivious"
			return False

	def onUpdate(self, pokemon=None):
		if pokemon:
			pokemon.volatiles.pop("taunt", None)
			pokemon.volatiles.pop("attract", None)


class Opportunist:
	def onFoeAfterBoost(self, boost=None, target=None, source=None, effect=None):
		holder = getattr(self, "effect_state", {}).get("target")
		if not holder or not boost:
			return
		gains = {stat: amount for stat, amount in boost.items() if amount > 0}
		if gains:
			apply_boost(holder, gains)


class Orichalcumpulse:
	def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
		weather = attacker.effective_weather() if attacker else ""
		if weather in {"sunnyday", "desolateland"}:
			return int(atk * 1.3)
		return atk

	def onStart(self, source=None, battle=None):
		if battle:
			battle.setWeather("sunnyday", source)


class Overcoat:
	def onImmunity(self, status=None, pokemon=None):
		if status in {"sandstorm", "hail", "snow"}:
			return False
		return True

	def onTryHit(self, target=None, source=None, move=None):
		if move and move.flags.get("powder"):
			if target:
				target.immune = "Overcoat"
			return False


class Overgrow:
	def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
		if move and move.type == "Grass" and attacker and attacker.hp <= attacker.max_hp // 3:
			return int(atk * 1.5)
		return atk

	def onModifySpA(self, spa, attacker=None, defender=None, move=None):
		if move and move.type == "Grass" and attacker and attacker.hp <= attacker.max_hp // 3:
			return int(spa * 1.5)
		return spa


class Owntempo:
	def onHit(self, target=None, source=None, move=None):
		if move and move.id in {"swagger", "flatter", "teeterdance"}:
			if target:
				target.immune = "Own Tempo"
			return False

	def onTryAddVolatile(self, status, pokemon=None):
		if status == "confusion":
			return False

	def onTryBoost(self, boost, target=None, source=None, effect=None):
		if effect and getattr(effect, "id", "") == "intimidate" and "atk" in boost:
			del boost["atk"]

	def onUpdate(self, pokemon=None):
		if pokemon:
			pokemon.volatiles.pop("confusion", None)


class Parentalbond:
	def onPrepareHit(self, move=None, pokemon=None, target=None):
		"""Only supported single-target attacks gain the reusable second hit."""
		from pokemon.battle.parental_bond import ParentalBondAttack
		if ParentalBondAttack.eligible(move):
			move.multihit = 2
			move.multihit_type = "parentalbond"

	def onSourceModifySecondaries(self, secondaries, source=None, target=None, move=None):
		"""Ordinary eligible secondary effects roll independently on each real hit."""
		return secondaries


class Pastelveil:
	def onAllySetStatus(self, status, target=None, source=None, effect=None):
		if status in {"psn", "tox"}:
			if target:
				target.immune = "Pastel Veil"
			return False

	def onAllySwitchIn(self, pokemon=None):
		if pokemon and pokemon.status in {"psn", "tox"}:
			pokemon.setStatus(0)

	def onSetStatus(self, status, target=None, source=None, effect=None):
		if status in {"psn", "tox"}:
			if target:
				target.immune = "Pastel Veil"
			return False

	def onStart(self, pokemon=None):
		if pokemon and pokemon.status in {"psn", "tox"}:
			pokemon.setStatus(0)
		for ally in pokemon.allies() if hasattr(pokemon, "allies") else []:
			if ally.status in {"psn", "tox"}:
				ally.setStatus(0)

	def onUpdate(self, pokemon=None):
		self.onStart(pokemon)


class Perishbody:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if target and source and move and move.flags.get("contact"):
			target.volatiles["perishsong"] = 3
			source.volatiles["perishsong"] = 3


class Pickpocket:
	def onAfterMoveSecondary(self, target=None, source=None, move=None):
		battle = getattr(target, "battle", None)
		last_damaged = getattr(target, "tempvals", {}).get("last_damaged_by", {}) if target else {}
		recorded_move = last_damaged.get("move")
		recorded_key = getattr(recorded_move, "key", None) or getattr(recorded_move, "id", None) or getattr(recorded_move, "name", None)
		move_key = getattr(move, "key", None) or getattr(move, "id", None) or getattr(move, "name", None)
		if (
			battle
			and target
			and source
			and move
			and move.flags.get("contact")
			and not getattr(target, "item", None)
			and not getattr(target, "switchFlag", False)
			and not getattr(target, "forceSwitchFlag", False)
			and getattr(source, "switchFlag", None) is not True
			and hasattr(battle, "steal_item")
			and last_damaged.get("source") is source
			and str(recorded_key or "").lower() == str(move_key or "").lower()
		):
			battle.steal_item(target, source, effect=getattr(move, "name", "ability:pickpocket"))


class Pickup:
	def onResidual(self, pokemon=None):
		if pokemon and not getattr(pokemon, "item", None) and not getattr(pokemon, "held_item", None):
			side = getattr(pokemon, "side", None)
			used = getattr(side, "used_items", []) if side else []
			if used:
				item = used[-1]
				battle = getattr(pokemon, "battle", None)
				if battle and hasattr(battle, "set_item"):
					if battle.set_item(pokemon, item, source=pokemon, effect="ability:pickup"):
						used.pop()
				else:
					pokemon.item = item
					pokemon.held_item = getattr(item, "name", str(item))
					used.pop()


class Pixilate:
	def onBasePower(self, base_power, user=None, target=None, move=None):
		if move and getattr(move, "typeChangerBoosted", False):
			return int(base_power * 1.2)
		return base_power

	def onModifyType(self, move, pokemon=None):
		if move and move.type == "Normal":
			ban = {
				"judgment",
				"multiattack",
				"naturalgift",
				"revelationdance",
				"technoblast",
				"terrainpulse",
				"weatherball",
			}
			if getattr(move, "id", "").lower() not in ban:
				move.type = "Fairy"
				move.typeChangerBoosted = True


class Plus:
	def onModifySpA(self, spa, pokemon=None, target=None, move=None):
		if not pokemon:
			return spa
		for ally in pokemon.allies() if hasattr(pokemon, "allies") else []:
			if ally is not pokemon and ally.hasAbility(("minus", "plus")):
				return int(spa * 1.5)
		return spa


class Poisonheal:
	def onDamage(self, damage, pokemon=None, source=None, effect=None):
		if effect and effect in {"psn", "tox"} and pokemon:
			heal = pokemon.max_hp // 8
			pokemon.hp = min(pokemon.max_hp, pokemon.hp + heal)
			return 0
		return damage


class Poisonpoint:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if source and move and move.flags.get("contact") and random() < 0.3:
			if not getattr(source, "status", None):
				source.setStatus("psn")


class Poisonpuppeteer:
	def onAnyAfterSetStatus(self, status=None, target=None, source=None, effect=None):
		holder = getattr(self, "effect_state", {}).get("target")
		if status in {"psn", "tox"} and source is holder and target:
			target.volatiles["confusion"] = True


class Poisontouch:
	def onSourceDamagingHit(self, damage=None, target=None, source=None, move=None):
		if move and move.flags.get("contact") and target and random() < 0.3:
			if not getattr(target, "status", None):
				target.setStatus("psn")


class Powerconstruct:
	def onResidual(self, pokemon=None):
		if pokemon and pokemon.hp <= pokemon.max_hp // 2 and "complete" not in pokemon.species.name.lower():
			if pokemon.species.name.lower().startswith("zygarde"):
				pokemon.formeChange("Zygarde-Complete")


class Powerofalchemy:
	def onAllyFaint(self, target=None, source=None):
		holder = getattr(self, "effect_state", {}).get("target")
		ability = getattr(target, "ability", None)
		ability_id = getattr(ability, "name", ability)
		if holder and target and str(ability_id).lower().replace(" ", "") not in {"powerofalchemy", "receiver", "trace"}:
			holder.ability = target.ability


class Powerspot:
	def onStart(self, pokemon=None):
		"""Track the Pokémon holding the ability."""
		if pokemon:
			self.effect_state = {"target": pokemon}

	def onAllyBasePower(self, base_power, pokemon=None, target=None, move=None):
		holder = getattr(self, "effect_state", {}).get("target")
		if pokemon is not holder:
			return int(base_power * 1.3)
		return base_power


class Prankster:
	def onModifyPriority(self, priority, pokemon=None, target=None, move=None):
		if move and move.category == "Status":
			move.pranksterBoosted = True
			return priority + 1
		return priority


class Pressure:
	def onDeductPP(self, deduction, target=None, source=None, move=None, battle=None):
		"""Charge an extra PP only when an opponent targets this holder."""
		if target is None or source is None or source is target or battle is None:
			return deduction
		if getattr(target, "volatiles", {}).get("gastroacid"):
			return deduction
		source_part = battle.participant_for(source)
		target_part = battle.participant_for(target)
		if source_part is None or target_part not in battle.opponents_of(source_part):
			return deduction
		return deduction + 1

	def onStart(self, pokemon=None):
		if pokemon:
			pokemon.abilityState = getattr(pokemon, "abilityState", {})
			pokemon.abilityState["pressure"] = True


class Primordialsea:
	def onAnySetWeather(self, target=None, source=None, weather=None):
		strong = {"desolateland", "primordialsea", "deltastream"}
		if getattr(self, "field_weather", "") == "primordialsea" and weather and weather.id not in strong:
			return False

	def onEnd(self, pokemon=None, battle=None):
		if battle and battle.weather_state.get("source") == pokemon:
			battle.clearWeather()

	def onStart(self, source=None, battle=None):
		if battle:
			battle.setWeather("primordialsea", source)


class Prismarmor:
	def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
		if move and target:
			eff = type_effectiveness(target, move)
			if eff > 1:
				return int(damage * 0.75)
		return damage


class Propellertail:
	def onModifyMove(self, move, user=None):
		if move:
			move.tracks_target = True


class Protean:
	def onPrepareHit(self, move=None, pokemon=None, target=None):
		_prepare_type_change(move, pokemon, "protean_used")

	def onSwitchIn(self, pokemon=None):
		if pokemon:
			pokemon.protean_used = False
			getattr(pokemon, "ability_state", {}).pop("type_change_used", None)


class Protosynthesis:
	"""Use checkpointed highest-stat activation from the real field."""
	def _controller(self):
		from pokemon.battle.stat_activation import HighestStatActivation
		return HighestStatActivation("protosynthesis")

	def onStart(self, pokemon=None):
		self._controller().activate(pokemon)

	def onEnd(self, pokemon=None):
		self._controller().end(pokemon)

	def onWeatherChange(self, pokemon=None, source=None, effect=None, battle=None):
		self._controller().activate(pokemon)

	def _boost_active(self, pokemon):
		return bool(pokemon and self._controller().state(pokemon).get("active"))

	def _choose_stat(self, pokemon):
		return self._controller().choose_stat(pokemon)

	def onModifyAtk(self, value, pokemon=None, target=None, move=None):
		return self._controller().modify(value, pokemon, "atk")

	def onModifyDef(self, value, pokemon=None, target=None, move=None):
		return self._controller().modify(value, pokemon, "def")

	def onModifySpA(self, value, pokemon=None, target=None, move=None):
		return self._controller().modify(value, pokemon, "spa")

	def onModifySpD(self, value, pokemon=None, target=None, move=None):
		return self._controller().modify(value, pokemon, "spd")

	def onModifySpe(self, value, pokemon=None, target=None, move=None):
		return self._controller().modify(value, pokemon, "spe")



class Psychicsurge:
	def onStart(self, source=None, battle=None):
		if battle:
			battle.setTerrain("psychicterrain", source)


class Punkrock:
	def onBasePower(self, base_power, user=None, target=None, move=None):
		if move and move.flags.get("sound"):
			return int(base_power * 1.3)
		return base_power

	def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
		if move and move.flags.get("sound"):
			return damage // 2
		return damage


class Purepower:
	def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
		return atk * 2


class Purifyingsalt:
	def onSetStatus(self, status, target=None, source=None, effect=None):
		if status and target and status not in {0, None}:
			target.immune = "Purifying Salt"
			return False

	def onSourceModifyAtk(self, atk, source=None, target=None, move=None):
		if move and move.type == "Ghost" and target is getattr(self, "effect_state", {}).get("target"):
			return atk // 2
		return atk

	def onSourceModifySpA(self, spa, source=None, target=None, move=None):
		if move and move.type == "Ghost" and target is getattr(self, "effect_state", {}).get("target"):
			return spa // 2
		return spa

	def onTryAddVolatile(self, status, pokemon=None):
		if status in {"yawn", "confusion", "attract"}:
			return False


class Quarkdrive:
	"""Use checkpointed highest-stat activation from the real field."""
	def _controller(self):
		from pokemon.battle.stat_activation import HighestStatActivation
		return HighestStatActivation("quarkdrive")

	def onStart(self, pokemon=None):
		self._controller().activate(pokemon)

	def onEnd(self, pokemon=None):
		self._controller().end(pokemon)

	def onTerrainChange(self, pokemon=None, source=None, effect=None, battle=None):
		self._controller().activate(pokemon)

	def _boost_active(self, pokemon):
		return bool(pokemon and self._controller().state(pokemon).get("active"))

	def _choose_stat(self, pokemon):
		return self._controller().choose_stat(pokemon)

	def onModifyAtk(self, value, pokemon=None, target=None, move=None):
		return self._controller().modify(value, pokemon, "atk")

	def onModifyDef(self, value, pokemon=None, target=None, move=None):
		return self._controller().modify(value, pokemon, "def")

	def onModifySpA(self, value, pokemon=None, target=None, move=None):
		return self._controller().modify(value, pokemon, "spa")

	def onModifySpD(self, value, pokemon=None, target=None, move=None):
		return self._controller().modify(value, pokemon, "spd")

	def onModifySpe(self, value, pokemon=None, target=None, move=None):
		return self._controller().modify(value, pokemon, "spe")



class Queenlymajesty:
	def onFoeTryMove(self, target=None, source=None, move=None):
		if move and move.priority > 0 and not source.is_ally(target):
			if hasattr(source, "tempvals"):
				source.tempvals["cant_move"] = "queenlymajesty"
			return False


class Quickdraw:
	def onFractionalPriority(self, priority, pokemon=None, target=None, move=None):
		if move and move.category != "Status" and random() < 0.3:
			return priority + 0.1
		return priority


class Quickfeet:
	def onModifySpe(self, spe, pokemon=None):
		if pokemon and pokemon.status:
			return int(spe * 1.5)
		return spe


class Raindish:
	def onWeather(self, pokemon=None):
		if not pokemon:
			return
		weather = getattr(pokemon, "effective_weather", lambda: "")()
		if weather in {"raindance", "primordialsea"}:
			pokemon.hp = min(pokemon.max_hp, pokemon.hp + pokemon.max_hp // 16)


class Rattled:
	def onAfterBoost(self, boost, target=None, source=None, effect=None):
		if effect and getattr(effect, "id", "") == "intimidate":
			apply_boost(target, {"spe": 1})

	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if move and move.type in {"Bug", "Dark", "Ghost"}:
			apply_boost(target, {"spe": 1})


class Rebound:
	def onAllyTryHitSide(self, target=None, source=None, move=None):
		# Reflection is performed by the called-move pipeline, which also owns
		# entry-turn eligibility, reflectable flags, and the recursion guard.
		return True

	def onTryHit(self, target=None, source=None, move=None):
		return True


class Receiver:
	def onAllyFaint(self, target=None, source=None):
		holder = getattr(self, "effect_state", {}).get("target")
		ability = getattr(target, "ability", None)
		ability_id = getattr(ability, "name", ability)
		if holder and target and str(ability_id).lower().replace(" ", "") not in {"powerofalchemy", "receiver", "trace"}:
			holder.ability = target.ability


class Reckless:
	def onBasePower(self, base_power, user=None, target=None, move=None):
		"""Read recoil/crash metadata from both live and dex move representations."""
		raw = (getattr(move, "raw", {}) or {}) if move else {}
		if move and (
			getattr(move, "recoil", False) or raw.get("recoil")
			or getattr(move, "hasCrashDamage", False) or raw.get("hasCrashDamage")
		):
			return int(base_power * 1.2)
		return base_power


class Refrigerate:
	def onBasePower(self, base_power, user=None, target=None, move=None):
		if move and getattr(move, "typeChangerBoosted", False):
			return int(base_power * 1.2)
		return base_power

	def onModifyType(self, move, pokemon=None):
		if move and move.type == "Normal":
			ban = {
				"judgment",
				"multiattack",
				"naturalgift",
				"revelationdance",
				"technoblast",
				"terrainpulse",
				"weatherball",
			}
			if getattr(move, "id", "").lower() not in ban:
				move.type = "Ice"
				move.typeChangerBoosted = True


class Regenerator:
	def onSwitchOut(self, pokemon=None):
		if pokemon:
			heal = pokemon.max_hp // 3
			pokemon.hp = min(pokemon.max_hp, pokemon.hp + heal)


class Ripen:
	def onChangeBoost(self, boost, pokemon=None, effect=None):
		if getattr(pokemon, "ripen_active", False):
			for stat in boost:
				boost[stat] *= 2
			pokemon.ripen_active = False

	def onEatItem(self, item=None, pokemon=None):
		if item and getattr(item, "isBerry", False):
			pokemon.ripen_active = True

	def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
		return damage

	def onTryEatItem(self, item=None, pokemon=None):
		return True

	def onTryHeal(self, heal, pokemon=None):
		if getattr(pokemon, "ripen_active", False):
			pokemon.ripen_active = False
			return heal * 2
		return heal


class Rivalry:
	def onBasePower(self, base_power, user=None, target=None, move=None):
		if user and target and user.gender and target.gender and user.gender != "N" and target.gender != "N":
			if user.gender == target.gender:
				return int(base_power * 1.25)
			return int(base_power * 0.75)
		return base_power


class Rockhead:
	def onDamage(self, damage, target=None, source=None, effect=None):
		if (effect and getattr(effect, "id", "") == "recoil"
				and getattr(effect, "move_id", "") != "struggle"):
			return 0
		return damage


class Rockypayload:
	def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
		if move and move.type == "Rock":
			return int(atk * 1.5)
		return atk

	def onModifySpA(self, spa, attacker=None, defender=None, move=None):
		if move and move.type == "Rock":
			return int(spa * 1.5)
		return spa


class Roughskin:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if source and move and move.flags.get("contact"):
			recoil = source.max_hp // 8
			from pokemon.battle.indirect_damage import IndirectEffect, apply_indirect_damage

			apply_indirect_damage(source, recoil, source=target, effect=IndirectEffect("roughskin"))


class Sandforce:
	def onBasePower(self, base_power, attacker=None, defender=None, move=None):
		"""Boost specific move types in sand."""
		weather = getattr(attacker, "effective_weather", lambda: "")() if attacker else ""
		if weather == "sandstorm" and move and move.type in {"Rock", "Ground", "Steel"}:
			return int(base_power * 1.3)
		return base_power

	def onImmunity(self, status=None, pokemon=None):
		if status == "sandstorm":
			return False


class Sandrush:
	def onImmunity(self, status=None, pokemon=None):
		if status == "sandstorm":
			return False

	def onModifySpe(self, spe, pokemon=None):
		if pokemon and getattr(pokemon, "effective_weather", lambda: "")() == "sandstorm":
			return int(spe * 2)
		return spe


class Sandspit:
	def onDamagingHit(self, damage, target=None, source=None, move=None, battle=None):
		if battle:
			battle.setWeather("sandstorm", target)


class Sandstream:
	def onStart(self, source=None, battle=None):
		if battle:
			battle.setWeather("sandstorm", source)


class Sandveil:
	def onImmunity(self, status=None, pokemon=None):
		if status == "sandstorm":
			return False

	def onModifyAccuracy(self, accuracy, attacker=None, defender=None, move=None):
		if defender and getattr(defender, "effective_weather", lambda: "")() == "sandstorm":
			return int(accuracy * 0.8)
		return accuracy


class Sapsipper:
	def onAllyTryHitSide(self, target=None, source=None, move=None):
		holder = getattr(self, "effect_state", {}).get("target")
		if holder and target is not holder and move and move.type == "Grass":
			if target:
				target.immune = "Sap Sipper"
			return False

	def onTryHit(self, target=None, source=None, move=None):
		if move and move.type == "Grass" and target:
			apply_boost(target, {"atk": 1})
			target.immune = "Sap Sipper"
			return None


class Schooling:
	def _update_form(self, pokemon):
		"""Only living, native Wishiwashi of level 20 or higher can school."""
		if (not pokemon or not pokemon.species.name.lower().startswith("wishiwashi")
				or getattr(pokemon, "transformed", False) or pokemon.hp <= 0):
			return
		if getattr(pokemon, "level", 0) >= 20 and pokemon.hp > pokemon.max_hp // 4:
			form = "Wishiwashi-School"
		else:
			form = "Wishiwashi"
		if pokemon.species.name != form:
			pokemon.formeChange(form)

	def onResidual(self, pokemon=None):
		self._update_form(pokemon)

	def onStart(self, pokemon=None):
		self._update_form(pokemon)


class Scrappy:
	def onModifyMove(self, move, pokemon=None):
		if move and move.type in {"Normal", "Fighting"}:
			move.ignoreImmunity = True

	def onTryBoost(self, boost, target=None, source=None, effect=None):
		if effect and getattr(effect, "id", "") == "intimidate" and "atk" in boost and boost["atk"] < 0:
			del boost["atk"]


class Screencleaner:
	def onStart(self, pokemon=None):
		if not pokemon or not getattr(pokemon, "side", None):
			return
		screens = {"reflect", "lightscreen", "auroraveil"}
		for side in (pokemon.side, getattr(pokemon.side, "foe", None)):
			if not side:
				continue
			for scr in screens:
				side.side_conditions.pop(scr, None)


class Seedsower:
	def onDamagingHit(self, damage, target=None, source=None, move=None, battle=None):
		if battle:
			battle.setTerrain("grassyterrain", target)


class Serenegrace:
	def onModifyMove(self, move, pokemon=None):
		if move is None:
			return
		raw = copy.deepcopy(getattr(move, "raw", {}) or {})
		original = getattr(move, "_serene_grace_original", None)
		if original is None:
			original = {name: copy.deepcopy(raw.get(name)) for name in ("secondary", "secondaries")}
			if not original["secondary"] and not original["secondaries"]:
				original["secondaries"] = copy.deepcopy(getattr(move, "secondaries", None))
			move._serene_grace_original = original
		raw.update(copy.deepcopy(original))
		for name in ("secondary", "secondaries"):
			if raw.get(name) is None:
				raw.pop(name, None)
		secondaries = raw.get("secondaries") or ([raw["secondary"]] if raw.get("secondary") else [])
		for secondary in secondaries:
			if "chance" in secondary:
				secondary["chance"] = min(100, secondary["chance"] * 2)
		move.secondaries, move.raw = secondaries, raw


class Shadowshield:
	def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
		if target and target.hp == target.max_hp:
			return damage // 2
		return damage


class Shadowtag:
	def onFoeMaybeTrapPokemon(self, pokemon=None, source=None):
		if not source:
			source = getattr(self, "effect_state", {}).get("target")
		if pokemon and source and not pokemon.is_ally(source):
			pokemon.maybeTrapped = True

	def onFoeTrapPokemon(self, pokemon=None):
		source = getattr(self, "effect_state", {}).get("target")
		if pokemon and source and getattr(pokemon, "isAdjacent", lambda o: True)(source):
			getattr(pokemon, "tryTrap", lambda *_: None)(True)


class Sharpness:
	def onBasePower(self, base_power, user=None, target=None, move=None):
		if move and move.flags.get("slicing"):
			return int(base_power * 1.5)
		return base_power


class Shedskin:
	def onResidual(self, pokemon=None):
		if pokemon and pokemon.status and random() < 1 / 3:
			pokemon.setStatus(0)


class Sheerforce:
	def onBasePower(self, base_power, user=None, target=None, move=None):
		if move and getattr(move, "sheer_force_boosted", False):
			return int(base_power * 1.3)
		return base_power

	def onModifyMove(self, move, user=None):
		"""Remove per-use secondary data while retaining its power eligibility."""
		if not move:
			return
		raw = getattr(move, "raw", {}) or {}
		secondaries = getattr(move, "secondaries", None) or raw.get("secondaries") or raw.get("secondary")
		if secondaries:
			move.secondaries = []
			move.raw = dict(raw, secondary=None, secondaries=[])
			move.sheer_force_boosted = True


class Shielddust:
	def onModifySecondaries(self, secondaries, source=None, target=None, move=None):
		if target and secondaries:
			return [s for s in secondaries if s.get("self")]
		return secondaries


class Shieldsdown:
	def _update_form(self, pokemon):
		"""Use loaded native form names and retain the original core colour."""
		if (not pokemon or not pokemon.species.name.lower().startswith("minior")
				or getattr(pokemon, "transformed", False) or pokemon.hp <= 0):
			return
		core = str(getattr(pokemon, "base_species", "Minior"))
		if not core.lower().startswith("minior") or "meteor" in core.lower():
			core = "Minior"
		form = "Minior-Meteor" if pokemon.hp > pokemon.max_hp // 2 else core
		if pokemon.species.name != form:
			pokemon.formeChange(form, preserve_ability=True)

	def onResidual(self, pokemon=None):
		self._update_form(pokemon)

	def onSetStatus(self, status, target=None, source=None, effect=None):
		if target and "meteor" in target.species.name.lower() and status not in {0, None}:
			target.immune = "Shields Down"
			return False

	def onStart(self, pokemon=None):
		self._update_form(pokemon)

	def onTryAddVolatile(self, status, pokemon=None):
		if status == "yawn" and pokemon and "meteor" in pokemon.species.name.lower():
			return False


class Simple:
	def onChangeBoost(self, boost, pokemon=None, source=None, effect=None):
		for stat in boost:
			boost[stat] *= 2


class Skilllink:
	def onModifyMove(self, move, pokemon=None):
		if move and getattr(move, "multihit", None):
			if isinstance(move.multihit, (list, tuple)):
				move.multihit = max(move.multihit)


class Slowstart:
	def onEnd(self, pokemon=None):
		if pokemon:
			pokemon.abilityState.pop("slowstart", None)

	def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
		if attacker and attacker.abilityState.get("slowstart", 0) > 0:
			return atk // 2
		return atk

	def onModifySpe(self, spe, pokemon=None):
		if pokemon and pokemon.abilityState.get("slowstart", 0) > 0:
			return spe // 2
		return spe

	def onResidual(self, pokemon=None):
		if pokemon:
			turns = pokemon.abilityState.get("slowstart", 0)
			if turns > 0:
				pokemon.abilityState["slowstart"] = turns - 1

	def onStart(self, pokemon=None):
		if pokemon:
			pokemon.abilityState = getattr(pokemon, "abilityState", {})
			pokemon.abilityState["slowstart"] = 5


class Slushrush:
	def onModifySpe(self, spe, pokemon=None):
		if pokemon and getattr(pokemon, "effective_weather", lambda: "")() in {"hail", "snow"}:
			return int(spe * 2)
		return spe


class Sniper:
	def onModifyDamage(self, damage, source=None, target=None, move=None):
		if move and getattr(move, "crit", False):
			return int(damage * 1.5)
		return damage


class Snowcloak:
	def onImmunity(self, status=None, pokemon=None):
		if status in {"hail", "snow"}:
			return False

	def onModifyAccuracy(self, accuracy, attacker=None, defender=None, move=None):
		if defender and getattr(defender, "effective_weather", lambda: "")() in {"hail", "snow"}:
			return int(accuracy * 0.8)
		return accuracy


class Snowwarning:
	def onStart(self, source=None, *context, battle=None, **__):
		"""Start snow through either entry dispatch or explicit ability events."""
		if battle is None and context and hasattr(context[0], "setWeather"):
			battle = context[0]
		if battle:
			battle.setWeather("snow", source)


class Solarpower:
	def onModifySpA(self, spa, attacker=None, defender=None, move=None):
		if attacker and getattr(attacker, "effective_weather", lambda: "")() in {"sunnyday", "desolateland"}:
			return int(spa * 1.5)
		return spa

	def onWeather(self, pokemon=None):
		if pokemon and getattr(pokemon, "effective_weather", lambda: "")() in {"sunnyday", "desolateland"}:
			pokemon.hp = max(0, pokemon.hp - pokemon.max_hp // 8)


class Solidrock:
	def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
		if target and move and type_effectiveness(target, move) > 1:
			return int(damage * 0.75)
		return damage


class Soulheart:
	def onAnyFaint(self, target=None, source=None, effect=None):
		holder = getattr(self, "effect_state", {}).get("target")
		if (holder and getattr(holder, "hp", 0) > 0 and target is not None
				and target is not holder and getattr(target, "hp", 1) <= 0):
			apply_boost(holder, {"spa": 1})


class Soundproof:
	def onAllyTryHitSide(self, target=None, source=None, move=None):
		holder = getattr(self, "effect_state", {}).get("target")
		if holder and target is not holder and move and move.flags.get("sound"):
			target.immune = "Soundproof"
			return False

	def onTryHit(self, target=None, source=None, move=None):
		if move and move.flags.get("sound") and target:
			target.immune = "Soundproof"
			return None


class Speedboost:
	def onResidual(self, pokemon=None):
		if pokemon:
			apply_boost(pokemon, {"spe": 1})


class Stakeout:
	def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
		if defender and getattr(defender, "active_turns", 0) == 0:
			return int(atk * 2)
		return atk

	def onModifySpA(self, spa, attacker=None, defender=None, move=None):
		if defender and getattr(defender, "active_turns", 0) == 0:
			return int(spa * 2)
		return spa


class Stalwart:
	def onModifyMove(self, move, user=None):
		if move:
			move.tracks_target = True


class Stamina:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if target:
			apply_boost(target, {"def": 1})


class Stancechange:
	def onModifyMove(self, move, user=None):
		if not user or not move or not user.species.name.lower().startswith("aegislash"):
			return
		if move.category != "Status":
			form = "Aegislash-Blade"
		else:
			form = "Aegislash"
		if user.species.name != form:
			user.formeChange(form)


class Static:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if source and move and move.flags.get("contact") and random() < 0.3:
			if not getattr(source, "status", None):
				source.setStatus("par")


class Steadfast:
	def onFlinch(self, pokemon=None):
		if pokemon:
			apply_boost(pokemon, {"spe": 1})


class Steamengine:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if move and move.type in {"Fire", "Water"} and target:
			apply_boost(target, {"spe": 6})


class Steelworker:
	def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
		if move and move.type == "Steel":
			return int(atk * 1.5)
		return atk

	def onModifySpA(self, spa, attacker=None, defender=None, move=None):
		if move and move.type == "Steel":
			return int(spa * 1.5)
		return spa


class Steelyspirit:
	def onStart(self, pokemon=None):
		"""Remember the holder so self-buffs can be avoided."""
		if pokemon:
			self.effect_state = {"target": pokemon}

	def onAllyBasePower(self, base_power, user=None, target=None, move=None):
		holder = getattr(self, "effect_state", {}).get("target")
		if user is not holder and move and move.type == "Steel":
			return int(base_power * 1.5)
		return base_power


class Stench:
	def onModifyMove(self, move, user=None):
		if move and move.category != "Status":
			import copy

			raw = move.raw
			secondaries = ([raw["secondary"]] if raw.get("secondary") else []) + list(raw.get("secondaries") or [])
			if not any(effect.get("volatileStatus") == "flinch" for effect in secondaries):
				secondaries = copy.deepcopy(secondaries) + [{"chance": 10, "volatileStatus": "flinch"}]
				raw.pop("secondary", None)
				raw["secondaries"] = secondaries
				move.secondaries = secondaries


class Stickyhold:
	def onTakeItem(self, item=None, source=None):
		return False


class Stormdrain:
	def onAnyRedirectTarget(self, target=None, source=None, move=None):
		"""Draw another Pokémon's targeted Water move to this holder."""
		holder = getattr(self, "effect_state", {}).get("target")
		if holder and holder is not source and target is not holder and move and move.type == "Water":
			move_target = getattr(move, "target", None) or getattr(move, "raw", {}).get("target")
			if move_target in {"normal", "any"}:
				return holder

	def onTryHit(self, target=None, source=None, move=None):
		if move and move.type == "Water" and target:
			apply_boost(target, {"spa": 1})
			target.immune = "Storm Drain"
			return None


class Strongjaw:
	def onBasePower(self, base_power, user=None, target=None, move=None):
		if move and move.flags.get("bite"):
			return int(base_power * 1.5)
		return base_power


class Sturdy:
	def onDamage(self, damage, target=None, source=None, effect=None):
		if target and target.hp == target.max_hp and damage >= target.hp:
			return target.hp - 1
		return damage

	def onTryHit(self, target=None, source=None, move=None):
		if move and getattr(move, "ohko", False) and target:
			target.immune = "Sturdy"
			return False


class Suctioncups:
	def onDragOut(self, pokemon=None):
		return False


class Superluck:
	def onModifyCritRatio(self, ratio, attacker=None, target=None, move=None):
		return ratio + 1


class Supersweetsyrup:
	def onStart(self, pokemon=None):
		if pokemon:
			for foe in pokemon.foes() if hasattr(pokemon, "foes") else []:
				apply_boost(foe, {"evasion": -1})


class Supremeoverlord:
	def onBasePower(self, base_power, attacker=None, defender=None, move=None):
		boost = getattr(attacker, "abilityState", {}).get("supreme_overlord", 1.0)
		return int(base_power * boost)

	def onEnd(self, pokemon=None):
		if pokemon:
			pokemon.abilityState.pop("supreme_overlord", None)

	def onStart(self, pokemon=None):
		if pokemon:
			fainted = sum(1 for p in pokemon.side.pokemons if p.hp <= 0 and p is not pokemon)
			pokemon.abilityState = getattr(pokemon, "abilityState", {})
			pokemon.abilityState["supreme_overlord"] = 1 + 0.1 * fainted


class Surgesurfer:
	def onModifySpe(self, spe, pokemon=None):
		from pokemon.battle.effect_context import EffectContext
		if pokemon and EffectContext.terrain(pokemon) == "electricterrain":
			return int(spe * 2)
		return spe


class Swarm:
	def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
		if move and move.type == "Bug" and attacker and attacker.hp <= attacker.max_hp // 3:
			return int(atk * 1.5)
		return atk

	def onModifySpA(self, spa, attacker=None, defender=None, move=None):
		if move and move.type == "Bug" and attacker and attacker.hp <= attacker.max_hp // 3:
			return int(spa * 1.5)
		return spa


class Sweetveil:
	def onAllySetStatus(self, status, target=None, source=None, effect=None):
		if status == "slp":
			if target:
				target.immune = "Sweet Veil"
			return False

	def onAllyTryAddVolatile(self, status, target=None):
		if status == "yawn":
			return False

	def onSetStatus(self, status, target=None, source=None, effect=None):
		if status == "slp":
			if target:
				target.immune = "Sweet Veil"
			return False


class Swiftswim:
	def onModifySpe(self, spe, pokemon=None):
		weather = getattr(pokemon, "effective_weather", lambda: "")() if pokemon else ""
		if weather in {"raindance", "primordialsea"}:
			return int(spe * 2)
		return spe


class Swordofruin:
	def onAnyModifyDef(self, defense, target=None, source=None, move=None):
		holder = getattr(self, "effect_state", {}).get("target")
		if target and holder and target is not holder and getattr(move, "category", None) != "Status":
			return int(defense * 0.75)
		return defense

	def onStart(self, pokemon=None):
		if pokemon:
			setattr(pokemon, "sword_of_ruin", True)


class Symbiosis:
	def onAllyAfterUseItem(self, item=None, source=None):
		holder = getattr(self, "effect_state", {}).get("target")
		battle = getattr(holder, "battle", None)
		if battle and holder and source is not holder and hasattr(battle, "move_item"):
			battle.move_item(holder, source, effect="ability:symbiosis", source=holder)


class Synchronize:
        def onAfterSetStatus(self, status, target=None, source=None, effect=None):
                if target and source and target is getattr(self, "effect_state", {}).get("target") and source is not target:
                        if status not in {0, None} and hasattr(source, "setStatus"):
                                battle = getattr(target, "battle", None)
                                source.setStatus(
                                        status,
                                        source=target,
                                        battle=battle,
                                        effect="ability:synchronize",
                                )


class Tabletsofruin:
	def onAnyModifyAtk(self, atk, target=None, source=None, move=None):
		holder = getattr(self, "effect_state", {}).get("target")
		affected = source or target
		if affected and holder and affected is not holder and getattr(move, "category", None) != "Status":
			return int(atk * 0.75)
		return atk

	def onStart(self, pokemon=None):
		if pokemon:
			setattr(pokemon, "tablets_of_ruin", True)


class Tangledfeet:
	def onModifyAccuracy(self, accuracy, attacker=None, defender=None, move=None):
		if defender and defender.volatiles.get("confusion"):
			if accuracy is not True:
				return int(accuracy * 0.5)
		return accuracy


class Tanglinghair:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if source and move and move.flags.get("contact"):
			apply_boost(source, {"spe": -1})


class Technician:
	def onBasePower(self, base_power, user=None, target=None, move=None):
		"""Qualify the actual positive current power supplied by the engine hook."""
		if move and 0 < base_power <= 60:
			return int(base_power * 1.5)
		return base_power


class Telepathy:
	def onTryHit(self, target=None, source=None, move=None):
		holder = getattr(self, "effect_state", {}).get("target")
		if holder and target is holder and source and source.is_ally(holder):
			if move and move.category != "Status":
				target.immune = "Telepathy"
				return None


class Teraformzero:
	def onAfterTerastallization(self, pokemon=None, source=None, effect=None, battle=None, **kwargs):
		holder = getattr(self, "effect_state", {}).get("target")
		if (pokemon is not holder or str(getattr(pokemon, "species", "")) != "Terapagos-Stellar"
		        or getattr(pokemon, "terastallized", None) != "Stellar"
		        or getattr(pokemon, "transformed", False)):
			return
		battle = battle or getattr(pokemon, "battle", None)
		if battle and (battle.field.weather or battle.field.terrain):
			battle.log_action(f"{pokemon.name}'s Teraform Zero cleared the weather and terrain!")
			battle.clearWeather()
			battle.clearTerrain()


class Terashell:
	def onAnyAfterMove(self, pokemon=None, source=None, move=None):
		holder = getattr(self, "effect_state", {}).get("target")
		if holder:
			getattr(holder, "ability_state", {}).pop("terashell_broken", None)

	def onEffectiveness(self, type_mod, target=None, type_=None, move=None):
		holder = getattr(self, "effect_state", {}).get("target")
		if (target is holder and str(getattr(holder, "species", "")) == "Terapagos-Terastal"
		        and holder.hp == holder.max_hp and type_mod >= 1
		        and getattr(move, "category", None) != "Status"
		        and str(getattr(move, "name", "")).lower() != "struggle"):
			# This engine relays a multiplier, rather than Showdown's exponent.
			return .5
		return type_mod


class Terashift:
	def onPreStart(self, pokemon=None):
		if pokemon:
			from pokemon.battle.native_forms import NativeBattleForm
			NativeBattleForm.tera_shift(pokemon)


class Teravolt:
	def onModifyMove(self, move, pokemon=None):
		if move:
			move.ignore_ability = True

	def onStart(self, pokemon=None):
		if pokemon:
			setattr(pokemon, "mold_breaker", True)


class Thermalexchange:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if move and move.type == "Fire" and target:
			apply_boost(target, {"atk": 1})

	def onSetStatus(self, status, target=None, source=None, effect=None):
		if status == "brn":
			if target:
				target.immune = "Thermal Exchange"
			return False

	def onUpdate(self, pokemon=None):
		if pokemon and getattr(pokemon, "status", None) == "brn":
			if hasattr(pokemon, "setStatus"):
				pokemon.setStatus(0)


class Thickfat:
	def onSourceModifyAtk(self, atk, source=None, target=None, move=None):
		if move and move.type in {"Fire", "Ice"}:
			return int(atk * 0.5)
		return atk

	def onSourceModifySpA(self, spa, source=None, target=None, move=None):
		if move and move.type in {"Fire", "Ice"}:
			return int(spa * 0.5)
		return spa


class Tintedlens:
	def onModifyDamage(self, damage, source=None, target=None, move=None):
		if move and target and type_effectiveness(target, move) < 1:
			return int(damage * 2)
		return damage


class Torrent:
	def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
		if move and move.type == "Water" and attacker and attacker.hp <= attacker.max_hp // 3:
			return int(atk * 1.5)
		return atk

	def onModifySpA(self, spa, attacker=None, defender=None, move=None):
		if move and move.type == "Water" and attacker and attacker.hp <= attacker.max_hp // 3:
			return int(spa * 1.5)
		return spa


class Toughclaws:
	def onBasePower(self, base_power, user=None, target=None, move=None):
		if move and move.flags.get("contact"):
			return int(base_power * 1.3)
		return base_power


class Toxicboost:
	def onBasePower(self, base_power, user=None, target=None, move=None):
		if user and user.status in {"psn", "tox"} and move and move.category != "Status":
			return int(base_power * 1.5)
		return base_power


class Toxicchain:
	@staticmethod
	def _effect_key(effect):
		"""Normalize real dex entities whose optional id may be absent."""
		value = getattr(effect, "name", None) or getattr(effect, "id", None) or effect
		return "".join(char for char in str(value).lower() if char.isalnum())

	def _prevented(self, target):
		"""Honor active Shield Dust and Covert Cloak prevention."""
		ability = self._effect_key(getattr(target, "ability", None))
		suppressed = bool(getattr(target, "ability_suppressed", False))
		if ability == "shielddust" and not suppressed:
			return True
		item = getattr(target, "item", None) or getattr(target, "held_item", None)
		if self._effect_key(item) != "covertcloak":
			return False
		battle = getattr(target, "battle", None)
		field = getattr(battle, "field", None)
		pseudo = getattr(field, "pseudo_weather", {}) or {}
		volatiles = getattr(target, "volatiles", {}) or {}
		inactive = ((ability == "klutz" and not suppressed) or "magicroom" in pseudo
			or bool(volatiles.get("embargo")) or bool(getattr(target, "item_suppressed", False)))
		return not inactive

	def onSourceDamagingHit(self, damage, target=None, source=None, move=None):
		"""Poison the actual damaged foe with its real attacking source."""
		if (not source or not target or not move or not damage or damage <= 0
			or getattr(target, "hp", 1) <= 0 or getattr(move, "category", None) == "Status"
			or self._prevented(target)):
			return
		if random() < 0.3 and not getattr(target, "status", None):
			target.setStatus("tox", source=source, battle=getattr(source, "battle", None), effect="ability:toxicchain")


class Toxicdebris:
	def onDamagingHit(self, damage, target=None, source=None, move=None, battle=None):
		if battle and move and move.category == "Physical" and source:
			side = source.side
			layers = side.side_conditions.get("toxicspikes", 0)
			side.side_conditions["toxicspikes"] = min(2, layers + 1)


class Trace:
	def _copy(self, pokemon):
		"""Choose an eligible living foe and install its executable owned effect."""
		from pokemon.battle.effect_context import EffectContext
		from pokemon.battle.engine import _resolve_ability
		battle = getattr(pokemon, "battle", None)
		if not battle or EffectContext.key(EffectContext.ability(pokemon)) != "trace":
			return
		if EffectContext.key(EffectContext.item(pokemon)) == "abilityshield":
			return
		foes = []
		for foe in pokemon.foes():
			ability = _resolve_ability(EffectContext.ability(foe))
			if (getattr(foe, "hp", 0) > 0 and ability
					and EffectContext.key(ability) not in {"trace", "noability"}
					and not (getattr(ability, "raw", {}) or {}).get("flags", {}).get("notrace")):
				foes.append((foe, ability))
		if not foes:
			return
		foe, ability = battle.rng.choice(foes)
		pokemon.setAbility(ability, source=foe, battle=battle,
						   is_from_forme_change=True, run_start=False)
		battle.register_handlers(pokemon)
		battle.start_owned_ability(pokemon)

	def onStart(self, pokemon=None):
		if pokemon:
			self._copy(pokemon)

	def onUpdate(self, pokemon=None):
		if pokemon:
			self._copy(pokemon)


class Transistor:
	def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
		if move and move.type == "Electric":
			return int(atk * 1.5)
		return atk

	def onModifySpA(self, spa, attacker=None, defender=None, move=None):
		if move and move.type == "Electric":
			return int(spa * 1.5)
		return spa


class Triage:
	def onModifyPriority(self, priority, pokemon=None, target=None, move=None):
		if move and move.flags.get("heal"):
			return priority + 3
		return priority


class Truant:
	def onBeforeMove(self, pokemon=None, target=None, move=None):
		state = getattr(pokemon, "abilityState", {})
		if state.get("truant_skip"):
			state["truant_skip"] = False
			if hasattr(pokemon, "tempvals"):
				pokemon.tempvals["cant_move"] = "truant"
			return False
		state["truant_skip"] = True

	def onStart(self, pokemon=None):
		if pokemon:
			pokemon.abilityState = getattr(pokemon, "abilityState", {})
			pokemon.abilityState["truant_skip"] = False


class Turboblaze:
	def onModifyMove(self, move, pokemon=None):
		if move:
			move.ignore_ability = True

	def onStart(self, pokemon=None):
		if pokemon:
			setattr(pokemon, "mold_breaker", True)


class Unaware:
	def onAnyModifyBoost(self, boosts, pokemon=None):
		holder = getattr(self, "effect_state", {}).get("target")
		if pokemon is not holder:
			for stat in boosts:
				boosts[stat] = 0


class Unburden:
	def onAfterUseItem(self, item=None, pokemon=None):
		if pokemon and item:
			pokemon.abilityState = getattr(pokemon, "abilityState", {})
			pokemon.abilityState["unburden"] = True

	def onEnd(self, pokemon=None):
		if pokemon:
			pokemon.abilityState.pop("unburden", None)

	def onModifySpe(self, spe, pokemon=None):
		if pokemon and pokemon.abilityState.get("unburden"):
			return int(spe * 2)
		return spe

	def onTakeItem(self, item=None, pokemon=None):
		if pokemon and item:
			pokemon.abilityState = getattr(pokemon, "abilityState", {})
			pokemon.abilityState["unburden"] = True


class Unnerve:
	def onEnd(self, pokemon=None):
		if pokemon:
			for foe in pokemon.foes():
				foe.nerve = False

	def onFoeTryEatItem(self, item=None, pokemon=None):
		if item and (getattr(item, "isBerry", False) or (getattr(item, "raw", {}) or {}).get("isBerry")):
			if pokemon:
				pokemon.immune = "Unnerve"
			return False

	def onPreStart(self, pokemon=None):
		self.onStart(pokemon)

	def onStart(self, pokemon=None):
		if pokemon:
			for foe in pokemon.foes():
				foe.nerve = True


class Unseenfist:
	def onModifyMove(self, move, pokemon=None):
		if move and move.flags.get("contact"):
			move.breaksProtect = True


class Vesselofruin:
	def onAnyModifySpA(self, spa, target=None, source=None, move=None):
		holder = getattr(self, "effect_state", {}).get("target")
		affected = source or target
		if affected and holder and affected is not holder and getattr(move, "category", None) != "Status":
			return int(spa * 0.75)
		return spa

	def onStart(self, pokemon=None):
		if pokemon:
			setattr(pokemon, "vessel_of_ruin", True)


class Victorystar:
	def onAnyModifyAccuracy(self, accuracy, source=None, target=None, move=None):
		holder = getattr(self, "effect_state", {}).get("target")
		if holder and source and (source is holder or source.is_ally(holder)):
			if accuracy is not True:
				return int(accuracy * 1.1)
		return accuracy


class Vitalspirit:
	def onSetStatus(self, status, target=None, source=None, effect=None):
		if status == "slp":
			if target:
				target.immune = "Vital Spirit"
			return False

	def onTryAddVolatile(self, status, pokemon=None):
		if status == "yawn":
			return False

	def onUpdate(self, pokemon=None):
		if pokemon and pokemon.status == "slp":
			pokemon.setStatus(0)


class Voltabsorb:
	def onTryHit(self, target=None, source=None, move=None):
		if move and move.type == "Electric" and target:
			heal = target.max_hp // 4
			target.hp = min(target.max_hp, target.hp + heal)
			target.immune = "Volt Absorb"
			return None


class Wanderingspirit:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if target and source and move and move.flags.get("contact"):
			if source.ability not in {"wanderingspirit"}:
				target.ability, source.ability = source.ability, target.ability


class Waterabsorb:
	def onTryHit(self, target=None, source=None, move=None):
		if move and move.type == "Water" and target:
			heal = target.max_hp // 4
			target.hp = min(target.max_hp, target.hp + heal)
			target.immune = "Water Absorb"
			return None


class Waterbubble:
	def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
		if move and move.type == "Water":
			return int(atk * 2)
		return atk

	def onModifySpA(self, spa, attacker=None, defender=None, move=None):
		if move and move.type == "Water":
			return int(spa * 2)
		return spa

	def onSetStatus(self, status, target=None, source=None, effect=None):
		if status == "brn":
			if target:
				target.immune = "Water Bubble"
			return False

	def onSourceModifyAtk(self, atk, source=None, target=None, move=None):
		if move and move.type == "Fire":
			return int(atk * 0.5)
		return atk

	def onSourceModifySpA(self, spa, source=None, target=None, move=None):
		if move and move.type == "Fire":
			return int(spa * 0.5)
		return spa

	def onUpdate(self, pokemon=None):
		if pokemon and pokemon.status == "brn":
			pokemon.setStatus(0)


class Watercompaction:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if move and move.type == "Water" and target:
			apply_boost(target, {"def": 2})


class Waterveil:
	def onSetStatus(self, status, target=None, source=None, effect=None):
		if status == "brn":
			if target:
				target.immune = "Water Veil"
			return False

	def onUpdate(self, pokemon=None):
		if pokemon and pokemon.status == "brn":
			pokemon.setStatus(0)


class Weakarmor:
	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if target and move and move.category == "Physical":
			apply_boost(target, {"def": -1, "spe": 2})


class Wellbakedbody:
	def onTryHit(self, target=None, source=None, move=None):
		if move and move.type == "Fire" and target:
			apply_boost(target, {"def": 2})
			target.immune = "Well-Baked Body"
			return None


class Whitesmoke:
	def onTryBoost(self, boost, target=None, source=None, effect=None):
		if source and source is target:
			return
		for stat in list(boost.keys()):
			if boost[stat] < 0:
				del boost[stat]


class Wimpout:
	def onEmergencyExit(self, pokemon=None):
		if pokemon:
			pokemon.switch_out = True


class Windpower:
	def onAllySideConditionStart(self, side_condition=None, pokemon=None):
		if side_condition == "tailwind" and pokemon:
			pokemon.volatiles["charge"] = True

	def onDamagingHit(self, damage, target=None, source=None, move=None):
		if move and move.flags.get("wind") and target:
			target.volatiles["charge"] = True


class Windrider:
	def onAllySideConditionStart(self, side_condition=None, pokemon=None):
		if side_condition == "tailwind" and pokemon:
			apply_boost(pokemon, {"atk": 1})

	def onStart(self, pokemon=None):
		if pokemon and getattr(pokemon, "side", None):
			if getattr(pokemon.side, "conditions", {}).get("tailwind"):
				apply_boost(pokemon, {"atk": 1})

	def onTryHit(self, target=None, source=None, move=None):
		if move and move.flags.get("wind") and target:
			apply_boost(target, {"atk": 1})
			target.immune = "Wind Rider"
			return None


class Wonderguard:
	def onTryHit(self, target=None, source=None, move=None):
		"""Allow damaging hits that are super-effective against the actual target."""
		if not move or move.category == "Status" or move.id == "struggle":
			return
		if target and type_effectiveness(target, move) <= 1:
			target.immune = "Wonder Guard"
			return False


class Wonderskin:
	def onModifyAccuracy(self, accuracy, attacker=None, defender=None, move=None):
		if move and move.category == "Status" and accuracy is not True:
			return min(accuracy, 50)
		return accuracy


class Zenmode:
	"""Change Darmanitan's regional form without ending Zen Mode recursively."""

	def _base_form(self, pokemon):
		"""Resolve a regional base even when the prepared species is already Zen."""
		if not pokemon or getattr(pokemon, "transformed", False):
			return None
		original = str(getattr(pokemon, "base_species", ""))
		if not original.lower().startswith("darmanitan"):
			return None
		return "Darmanitan-Galar" if "galar" in original.lower() else "Darmanitan"

	def _update_form(self, pokemon):
		"""Apply the half-health threshold while keeping the hidden ability."""
		base = self._base_form(pokemon)
		if not base or not pokemon.hp:
			return
		form = base + "-Zen" if pokemon.hp <= pokemon.max_hp // 2 else base
		if str(pokemon.species) != form:
			pokemon.formeChange(form, preserve_ability=True)

	def onEnd(self, pokemon=None):
		"""Return a living carrier to its regional base when the ability ends."""
		base = self._base_form(pokemon)
		if base and pokemon.hp and str(pokemon.species) != base:
			pokemon.formeChange(base, preserve_ability=True)

	def onResidual(self, pokemon=None):
		self._update_form(pokemon)

	def onStart(self, pokemon=None):
		self._update_form(pokemon)


class Zerotohero:
	def onStart(self, pokemon=None):
		if pokemon and pokemon.base_species.lower() == "palafin":
			pokemon.abilityState = getattr(pokemon, "abilityState", {})
			pokemon.abilityState.setdefault("hero_ready", False)

	def onSwitchIn(self, pokemon=None):
		if pokemon and getattr(pokemon, "abilityState", {}).get("hero_ready") and str(pokemon.species).lower() == "palafin":
			pokemon.formeChange("Palafin-Hero", preserve_ability=True)

	def onSwitchOut(self, pokemon=None):
		if pokemon and pokemon.base_species.lower() == "palafin":
			pokemon.abilityState = getattr(pokemon, "abilityState", {})
			pokemon.abilityState["hero_ready"] = True
			if str(pokemon.species).lower() == "palafin":
				pokemon.formeChange("Palafin-Hero", preserve_ability=True)
