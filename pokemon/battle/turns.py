"""Turn and action processing helpers for the battle engine."""

from __future__ import annotations

import logging
import random
from typing import List, Optional

from utils.safe_import import safe_import

from ._shared import _normalize_key
from .actions import Action, ActionType

logger = logging.getLogger("battle")


class TurnProcessor:
	"""Mixin supplying turn and action execution logic."""

	def run_action(self) -> None:
		"""Main action runner modeled on Showdown's ``runAction``."""
		for part in self.participants:
			acts = getattr(part, "pending_action", None)
			if not acts:
				continue
			if not isinstance(acts, list):
				acts = [acts]
			if part.active:
				switching = part.active[0]
			else:
				switching = None
			for act in list(acts):
				if act.action_type is ActionType.SWITCH and switching:
					for opp in self.participants:
						if opp is part or opp.has_lost:
							continue
						opp_act = getattr(opp, "pending_action", None)
						if isinstance(opp_act, list):
							opp_candidates = opp_act
						else:
							opp_candidates = [opp_act] if opp_act else []
						for oa in opp_candidates:
							if (
								oa
								and oa.action_type is ActionType.MOVE
								and getattr(getattr(oa, "move", None), "key", "") == "pursuit"
							):
								switching.tempvals["switching"] = True
								self.use_move(oa)
								switching.tempvals.pop("switching", None)
								if isinstance(opp_act, list):
									opp_candidates.remove(oa)
									opp.pending_action = opp_candidates
								else:
									opp.pending_action = None
		self.run_switch()
		self.run_after_switch()
		self.run_move()
		self.run_faint()
		self.residual()

	def start_turn(self) -> None:
		"""Reset temporary flags or display status."""

		self.turn_count += 1
		if self.turn_count == 1:
			for part in self.participants:
				for poke in part.active:
					self.register_handlers(poke)
					self.dispatcher.dispatch("pre_start", pokemon=poke, battle=self)
					self.dispatcher.dispatch("start", pokemon=poke, battle=self)
					self.dispatcher.dispatch("switch_in", pokemon=poke, battle=self)
			self._apply_misc_callbacks()
		for part in self.participants:
			if part.has_lost:
				continue
			for poke in part.active:
				self.dispatcher.dispatch("update", pokemon=poke, battle=self)

	def before_turn(self) -> None:
		"""Run simple BeforeTurn events for all active Pokémon."""
		try:
			from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS
		except Exception:
			CONDITION_HANDLERS = {}
		try:
			from pokemon.dex.functions.moves_funcs import VOLATILE_HANDLERS
		except Exception:
			VOLATILE_HANDLERS = {}

		for part in self.participants:
			if part.has_lost:
				continue
			for poke in part.active:
				self.dispatcher.dispatch("before_turn", pokemon=poke, battle=self)

				status = getattr(poke, "status", None)
				handler = CONDITION_HANDLERS.get(status)
				if handler and hasattr(handler, "onBeforeTurn"):
					try:
						handler.onBeforeTurn(poke, battle=self)
					except Exception:
						pass

				rng = getattr(self, "rng", random)
				if status == "slp":
					turns = poke.tempvals.get("slp_turns")
					if turns is None:
						turns = rng.randint(1, 3)
					else:
						turns -= 1
					if turns <= 0:
						poke.status = 0
						poke.tempvals.pop("slp_turns", None)
					else:
						poke.tempvals["slp_turns"] = turns

				vols = getattr(poke, "volatiles", {})
				for vol in list(vols.keys()):
					handler = CONDITION_HANDLERS.get(vol) or VOLATILE_HANDLERS.get(vol)
					if handler and hasattr(handler, "onBeforeTurn"):
						try:
							keep = handler.onBeforeTurn(poke, battle=self)
							if keep is False:
								vols.pop(vol, None)
						except Exception:
							pass

	def lock_choices(self) -> None:
		"""Apply locked-in transformations like Mega Evolution or Terastallization."""
		for part in self.participants:
			if part.has_lost:
				continue
			for poke in part.active:
				if getattr(poke, "pending_mega", False):
					self.perform_mega_evolution(poke)
					poke.pending_mega = False
				tera = getattr(poke, "pending_tera", None)
				if tera:
					self.perform_tera_change(poke, tera)
					poke.pending_tera = None

	def select_actions(self) -> List[Action]:
		actions: List[Action] = []
		for part in self.participants:
			if part.has_lost:
				continue
			if hasattr(part, "choose_actions"):
				part_actions = part.choose_actions(self)
				if isinstance(part_actions, list):
					actions.extend(part_actions)
				elif part_actions:
					actions.append(part_actions)
			elif hasattr(part, "choose_action"):
				action = part.choose_action(self)
				if action:
					actions.append(action)
			else:
				pending = getattr(part, "pending_action", None)
				if not pending:
					continue
				if isinstance(pending, list):
					for act in pending:
						if act and act.target and act.target not in self.participants:
							act.target = None
						if act and not getattr(act, "target", None):
							opps = self.opponents_of(part)
							if opps:
								act.target = opps[0]
					actions.extend(pending)
				else:
					if pending.target and pending.target not in self.participants:
						pending.target = None
					if not pending.target:
						opps = self.opponents_of(part)
						if opps:
							pending.target = opps[0]
					actions.append(pending)
				part.pending_action = None
		return actions

	def collect_actions(self) -> List[Action]:
		"""Alias for :py:meth:`select_actions`."""
		return self.select_actions()

	def order_actions(self, actions: List[Action]) -> List[Action]:
		"""Order actions by priority and speed following Showdown rules."""
		try:
			from pokemon.battle import utils
		except Exception:
			utils = None

		trick_room = bool(self.field.get_pseudo_weather("trickroom"))

		for action in actions:
			poke = action.pokemon or (action.actor.active[0] if action.actor.active else None)
			move = action.move
			base_priority = action.priority
			priority = base_priority

			ability = getattr(poke, "ability", None)
			item = getattr(poke, "item", None) or getattr(poke, "held_item", None)

			if poke:
				target = None
				if action.target and action.target.active:
					target = action.target.active[0]
				priority = self.apply_priority_modifiers(poke, move, priority, target)

			action.priority = priority
			action.priority_mod = priority - base_priority

			if action.action_type is not ActionType.MOVE:
				action.speed = 0
				action._tiebreak = 0
				continue

			if poke:
				safe_get_stats = getattr(utils, "_safe_get_stats", None)
				if safe_get_stats is None:
					try:
						from .utils import _safe_get_stats as safe_get_stats
					except Exception:
						safe_get_stats = None

				if utils and hasattr(utils, "get_modified_stat"):
					try:
						speed = utils.get_modified_stat(poke, "speed")
					except Exception:
						if safe_get_stats:
							try:
								speed = safe_get_stats(poke).get("speed", 0)
							except Exception:
								speed = getattr(getattr(poke, "base_stats", None), "speed", 0)
						else:
							speed = getattr(getattr(poke, "base_stats", None), "speed", 0)
				else:
					if safe_get_stats:
						try:
							speed = safe_get_stats(poke).get("speed", 0)
						except Exception:
							speed = getattr(getattr(poke, "base_stats", None), "speed", 0)
					else:
						speed = getattr(getattr(poke, "base_stats", None), "speed", 0)

				if ability and hasattr(ability, "call"):
					try:
						mod = ability.call("onModifySpe", speed, pokemon=poke)
						if isinstance(mod, (int, float)):
							speed = int(mod)
					except Exception:
						pass
				if item and hasattr(item, "call"):
					try:
						mod = item.call("onModifySpe", speed, pokemon=poke)
						if isinstance(mod, (int, float)):
							speed = int(mod)
					except Exception:
						pass
			else:
				speed = 0

			action.speed = speed
			rng = getattr(self, "rng", random)
			action._tiebreak = rng.random()

		if trick_room:
			key = lambda a: (a.priority, -a.speed, a._tiebreak)
		else:
			key = lambda a: (a.priority, a.speed, a._tiebreak)

		return sorted(actions, key=key, reverse=True)

	def determine_move_order(self, actions: List[Action]) -> List[Action]:
		"""Alias for :py:meth:`order_actions`."""
		return self.order_actions(actions)

	def apply_priority_modifiers(
		self,
		pokemon,
		move: Optional["BattleMove"],
		priority: float,
		target,
	) -> float:
		"""Apply ability, item and status priority modifiers."""
		try:
			from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS
		except Exception:
			CONDITION_HANDLERS = {}
		try:
			from pokemon.dex.functions.moves_funcs import VOLATILE_HANDLERS
		except Exception:
			VOLATILE_HANDLERS = {}

		ability = getattr(pokemon, "ability", None)
		if ability and hasattr(ability, "call"):
			try:
				mod = ability.call(
					"onModifyPriority",
					priority,
					pokemon=pokemon,
					target=target,
					move=move,
				)
				if isinstance(mod, (int, float)):
					priority = mod
			except Exception:
				pass
			try:
				frac = ability.call(
					"onFractionalPriority",
					priority,
					pokemon=pokemon,
					target=target,
					move=move,
				)
				if isinstance(frac, (int, float)):
					priority += frac if frac != priority else 0
			except Exception:
				pass

		item = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
		if item and hasattr(item, "call"):
			try:
				frac = item.call("onFractionalPriority", pokemon=pokemon)
				if isinstance(frac, (int, float)):
					priority += frac
			except Exception:
				pass

		status = getattr(pokemon, "status", None)
		handler = CONDITION_HANDLERS.get(status)
		if handler:
			if hasattr(handler, "onModifyPriority"):
				try:
					mod = handler.onModifyPriority(priority, pokemon=pokemon, target=target, move=move)
					if isinstance(mod, (int, float)):
						priority = mod
				except Exception:
					pass
			if hasattr(handler, "onFractionalPriority"):
				try:
					frac = handler.onFractionalPriority(priority, pokemon=pokemon, target=target, move=move)
					if isinstance(frac, (int, float)):
						priority += frac if frac != priority else 0
				except Exception:
					pass

		volatiles = getattr(pokemon, "volatiles", {})
		for vol in list(volatiles.keys()):
			handler = CONDITION_HANDLERS.get(vol) or VOLATILE_HANDLERS.get(vol)
			if not handler:
				continue
			if hasattr(handler, "onModifyPriority"):
				try:
					mod = handler.onModifyPriority(priority, pokemon=pokemon, target=target, move=move)
					if isinstance(mod, (int, float)):
						priority = mod
				except Exception:
					pass
			if hasattr(handler, "onFractionalPriority"):
				try:
					frac = handler.onFractionalPriority(priority, pokemon=pokemon, target=target, move=move)
					if isinstance(frac, (int, float)):
						priority += frac if frac != priority else 0
				except Exception:
					pass

		if getattr(pokemon, "tempvals", {}).pop("quash", False):
			priority = -7

		return priority

	def status_prevents_move(self, pokemon) -> bool:
		"""Return True if the Pokemon cannot act due to status."""
		status = getattr(pokemon, "status", None)
		try:
			from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS
		except Exception:
			CONDITION_HANDLERS = {}
		try:
			from pokemon.dex.functions.moves_funcs import VOLATILE_HANDLERS
		except Exception:
			VOLATILE_HANDLERS = {}

		ability = getattr(pokemon, "ability", None)
		if ability and hasattr(ability, "call"):
			try:
				res = ability.call("onBeforeMove", pokemon=pokemon, battle=self)
				if res is False:
					return True
			except Exception:
				pass

		item = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
		if item and hasattr(item, "call"):
			try:
				res = item.call("onBeforeMove", pokemon=pokemon, battle=self)
				if res is False:
					return True
			except Exception:
				pass

		handler = CONDITION_HANDLERS.get(status)
		if handler and hasattr(handler, "onBeforeMove"):
			result = handler.onBeforeMove(pokemon, battle=self)
			if result is False:
				return True

		volatiles = getattr(pokemon, "volatiles", {})
		if "flinch" in volatiles:
			volatiles.pop("flinch", None)
			return True
		for vol in list(volatiles.keys()):
			handler = CONDITION_HANDLERS.get(vol) or VOLATILE_HANDLERS.get(vol)
			if handler and hasattr(handler, "onBeforeMove"):
				try:
					result = handler.onBeforeMove(pokemon, battle=self)
				except Exception:
					result = handler.onBeforeMove(pokemon)
				if result is False:
					return True

		rng = getattr(self, "rng", random)
		if status == "par":
			if rng.random() < 0.25:
				if hasattr(self, "announce_status_change"):
					self.announce_status_change(pokemon, "par", event="cant")
				return True
			return False
		if status == "frz":
			if rng.random() < 0.2:
				pokemon.status = 0
				if hasattr(self, "announce_status_change"):
					self.announce_status_change(pokemon, "frz", event="end")
				return False
			if hasattr(self, "announce_status_change"):
				self.announce_status_change(pokemon, "frz", event="cant")
			return True
		if status == "slp":
			turns = pokemon.tempvals.get("slp_turns")
			if turns is None:
				turns = rng.randint(1, 3)
				pokemon.tempvals["slp_turns"] = turns
			if turns > 0:
				turns -= 1
				pokemon.tempvals["slp_turns"] = turns
				if turns == 0:
					pokemon.status = 0
					pokemon.tempvals.pop("slp_turns", None)
					if hasattr(self, "announce_status_change"):
						self.announce_status_change(pokemon, "slp", event="end")
					return False
				if hasattr(self, "announce_status_change"):
					self.announce_status_change(pokemon, "slp", event="cant")
				return True
		return False

	def modify_stat_stage(self, pokemon, stat: str, delta: int) -> None:
		"""Modify ``pokemon`` stat stage by ``delta``."""
		from pokemon.battle.utils import apply_boost

		apply_boost(pokemon, {stat: delta})

	def calculate_stat(self, pokemon, stat: str) -> int:
		"""Return ``pokemon``'s stat after modifiers."""
		from pokemon.battle.utils import get_modified_stat

		return get_modified_stat(pokemon, stat)

	def reset_stat_changes(self, pokemon) -> None:
		"""Clear temporary stat modifiers for ``pokemon``."""
		if hasattr(pokemon, "boosts"):
			pokemon.boosts = {}

	def _emit_battle_message(self, message: str) -> None:
		"""Send ``message`` using the available logging hooks."""

		if not message:
			return

		logger.debug("Battle message: %s", message)

		log_fn = getattr(self, "log_action", None)
		if callable(log_fn):
			try:
				log_fn(message)
				return
			except Exception:
				pass

		notify_fn = getattr(self, "notify", None)
		if callable(notify_fn):
			try:
				notify_fn(message)
			except Exception:
				pass

	def _get_speed_value(self, pokemon) -> int:
		"""Return a best-effort speed value for ``pokemon``."""

		if not pokemon:
			return 0

		direct_attrs = ("speed", "spe", "spd")
		for attr in direct_attrs:
			value = getattr(pokemon, attr, None)
			if isinstance(value, (int, float)):
				return int(value)

		base_stats = getattr(pokemon, "base_stats", None)
		if isinstance(base_stats, dict):
			for key in ("speed", "spe", "spd"):
				value = base_stats.get(key)
				if isinstance(value, (int, float)):
					return int(value)
		elif base_stats is not None:
			for attr in ("speed", "spe", "spd"):
				value = getattr(base_stats, attr, None)
				if isinstance(value, (int, float)):
					return int(value)

		calc_fn = getattr(self, "calculate_stat", None)
		if callable(calc_fn):
			try:
				return int(calc_fn(pokemon, "speed"))
			except Exception:
				pass

		return int(getattr(pokemon, "temp_speed", 0) or 0)

	def _ability_key(self, ability) -> str:
		"""Return a lowercase normalized key for ``ability``."""

		if not ability:
			return ""
		if isinstance(ability, str):
			normalized = _normalize_key(ability)
		else:
			for attr in ("name", "key", "id"):
				value = getattr(ability, attr, None)
				if value:
					normalized = _normalize_key(value)
					break
			else:
				normalized = _normalize_key(str(ability))
		return normalized.lower()

	def attempt_flee(self, action: Action) -> bool:
		"""Execute a flee attempt and return ``True`` on success."""

		from .engine import BattleType

		participant = getattr(action, "actor", None)
		pokemon = getattr(action, "pokemon", None)
		if pokemon is None and participant and getattr(participant, "active", None):
			pokemon = participant.active[0]

		result = {
			"success": False,
			"participant": participant,
			"pokemon": pokemon,
			"reason": "failed",
		}

		battle_type = getattr(self, "type", None)
		type_value = getattr(battle_type, "value", battle_type)
		trainer_name = getattr(participant, "name", "Trainer") if participant else "Trainer"

		if type_value != BattleType.WILD.value:
			message = f"{trainer_name} can't run from this battle!"
			self._emit_battle_message(message)
			result["reason"] = "restricted"
			result["message"] = message
			setattr(self, "_flee_result", result)
			if participant is not None:
				attempts = int(getattr(participant, "flee_attempts", 0))
				setattr(participant, "flee_attempts", attempts + 1)
			return False

		if participant is not None:
			attempts = int(getattr(participant, "flee_attempts", 0))
		else:
			attempts = 0

		ability_key = self._ability_key(getattr(pokemon, "ability", None))
		if ability_key == "runaway":
			success = True
			reason = "runaway"
		else:
			trapper_name = None
			opponents = []
			if hasattr(self, "opponents_of") and participant is not None:
				opponents = self.opponents_of(participant)
			trap_abilities = {"arenatrap", "shadowtag"}
			trapped = False
			for opp in opponents:
				if not getattr(opp, "active", None):
					continue
				for foe in opp.active:
					if not foe:
						continue
					opp_ability_key = self._ability_key(getattr(foe, "ability", None))
					if opp_ability_key in trap_abilities:
						trapped = True
						trapper_name = getattr(getattr(foe, "ability", None), "name", None)
						if not trapper_name:
							trapper_name = opp_ability_key.replace("-", " ").title()
						break
				if trapped:
					break

			if trapped and ability_key != "runaway":
				message = f"{trainer_name}'s Pokemon is trapped by {trapper_name or 'Arena Trap'}!"
				self._emit_battle_message(message)
				result["reason"] = "trapped"
				result["trapper"] = trapper_name or "Arena Trap"
				result["message"] = message
				setattr(self, "_flee_result", result)
				if participant is not None:
					setattr(participant, "flee_attempts", attempts + 1)
				return False

			player_speed = self._get_speed_value(pokemon)
			opponent_speed = 0
			for opp in opponents:
				if not getattr(opp, "active", None):
					continue
				for foe in opp.active:
					opponent_speed = max(opponent_speed, self._get_speed_value(foe))

			if player_speed > opponent_speed:
				success = True
				reason = "faster"
			else:
				rng = getattr(self, "rng", random)
				opponent_speed = max(1, opponent_speed)
				threshold = (player_speed * 128) // opponent_speed + attempts * 30
				if threshold >= 255:
					success = True
				else:
					roll = rng.randint(0, 255)
					success = roll < threshold
				reason = "formula" if success else "roll"
				result["reason"] = reason

		if participant is not None:
			setattr(participant, "flee_attempts", attempts + 1)

		pokemon_name = getattr(pokemon, "name", "Pokemon") if pokemon else "Pokemon"

		if success:
			message = f"{trainer_name} fled from the battle!"
			self._emit_battle_message(message)
			result["success"] = True
			result["reason"] = reason
			result["message"] = message
			setattr(self, "battle_over", True)
			setattr(self, "fled", participant)
		else:
			if result.get("reason") not in {"restricted", "trapped"}:
				message = f"{pokemon_name} couldn't get away!"
				self._emit_battle_message(message)
				result["message"] = message

		setattr(self, "_flee_result", result)
		return bool(result.get("success"))

	def execute_actions(self, actions: List[Action]) -> None:
		for action in actions:
			if getattr(self, "battle_over", False):
				break
			action_type = getattr(action, "action_type", None)
			if action_type is ActionType.RUN:
				if self.attempt_flee(action):
					break
				continue
			if action_type is ActionType.MOVE and action.move:
				actor_poke = action.pokemon or (action.actor.active[0] if action.actor.active else None)
				if self.status_prevents_move(actor_poke):
					continue
				self.use_move(action)
				if actor_poke is not None:
					try:
						actor_poke.tempvals["moved"] = True
					except Exception:
						pass
			elif action_type is ActionType.ITEM and action.item:
				self.execute_item(action)
			elif action.item:
				# ``ActionType`` enums may be reloaded during tests, so
				# fall back to the presence of ``action.item`` to detect
				# item usage.
				self.execute_item(action)

	def execute_turn(self, actions: List[Action]) -> None:
		"""Execute the supplied actions in proper order."""
		ordered = self.determine_move_order(actions)
		self.execute_actions(ordered)
		self.run_faint()
		self.residual()

	def execute_item(self, action: Action) -> None:
		"""Handle item usage during battle."""
		from .engine import BattleType, _normalize_key

		item_name = action.item.lower()
		target = action.target
		if target not in self.participants or target.has_lost or not target.active:
			opponents = self.opponents_of(action.actor)
			target = opponents[0] if opponents else None
		if not target or not target.active:
			return

		item_key = _normalize_key(item_name)
		if item_key.endswith("ball") and getattr(self.type, "value", self.type) == BattleType.WILD.value:
			target_poke = target.active[0]
			try:
				from pokemon.dex.functions import pokedex_funcs
			except Exception:
				class pokedex_funcs:  # type: ignore
					@staticmethod
					def get_catch_rate(name: str) -> int:
						return 255
			catch_rate = pokedex_funcs.get_catch_rate(getattr(target_poke, "name", "")) or 0
			status = getattr(target_poke, "status", None)
			max_hp = getattr(target_poke, "max_hp", getattr(target_poke, "hp", 1))
			from . import capture as capture_mod

			try:
			# Resolve ball modifiers at runtime to handle stubbed packages
				ball_mods = safe_import(
					"pokemon.dex.items.ball_modifiers"
				).BALL_MODIFIERS  # type: ignore[attr-defined]
			except ModuleNotFoundError:
				ball_mods = {}
			ball_mod = ball_mods.get(item_key, 1.0)
			rng = getattr(self, "rng", random)
			# Use the battle's RNG so callers can control determinism
			# via :class:`random.Random` instances.
			trainer = getattr(action.actor, "trainer", None)
			player = getattr(action.actor, "player", None)
			if trainer is None and player is not None:
				trainer = getattr(player, "trainer", None)

			critical_rate = None
			for source in (action.actor, player, trainer):
				rate = getattr(source, "critical_capture_rate", None)
				if rate is not None:
					try:
						critical_rate = float(rate)
					except (TypeError, ValueError):
						critical_rate = None
					else:
						break
			if critical_rate is None and player is not None:
				dex_caught = getattr(player, "dex_caught", None)
				caught_count: Optional[int] = None
				if dex_caught is not None:
					try:
						caught_count = len(list(dex_caught)) if callable(dex_caught) else len(dex_caught)
					except TypeError:
						try:
							caught_count = len(list(dex_caught()))
						except Exception:
							caught_count = None
				if caught_count is not None:
					critical_rate = min(0.5, max(0, caught_count) / 600)

			outcome = capture_mod.attempt_capture(
				max_hp,
				target_poke.hp,
				catch_rate,
				ball_modifier=ball_mod,
				status=status,
				rng=rng,
				critical_chance=critical_rate,
				return_details=True,
			)

			nickname_cb = getattr(self, "_pokemon_nickname", None)
			pokemon_name = None
			if callable(nickname_cb):
				try:
					pokemon_name = nickname_cb(target_poke)
				except Exception:
					pokemon_name = getattr(target_poke, "name", "Pokemon")
			if not pokemon_name:
				pokemon_name = getattr(target_poke, "name", "Pokemon")

			if getattr(outcome, "critical", False) and hasattr(self, "log_action"):
				self.log_action("A critical capture!")

			if hasattr(self, "log_action"):
				for _ in range(getattr(outcome, "shakes", 0)):
					self.log_action("The ball shook!")

			caught = getattr(outcome, "caught", bool(outcome))
			if caught:
				if hasattr(self, "log_action"):
					self.log_action(f"Gotcha! {pokemon_name} was caught!")
				target.active.remove(target_poke)
				if target_poke in target.pokemons:
					target.pokemons.remove(target_poke)
				if getattr(target_poke, "model_id", None) is not None:
					try:
						from pokemon.models.core import OwnedPokemon

						dbpoke = OwnedPokemon.objects.get(unique_id=target_poke.model_id)
						if hasattr(action.actor, "trainer"):
							dbpoke.trainer = action.actor.trainer
						dbpoke.current_hp = target_poke.hp
						dbpoke.is_wild = False
						dbpoke.ai_trainer = None
						if hasattr(dbpoke, "save"):
							dbpoke.save()
						if hasattr(action.actor, "storage") and hasattr(action.actor.storage, "stored_pokemon"):
							try:
								action.actor.storage.stored_pokemon.add(dbpoke)
							except Exception:
								pass
					except Exception:
						pass
				elif hasattr(action.actor, "add_pokemon_to_storage"):
					try:
						poke_types = getattr(target_poke, "types", [])
						type_ = ", ".join(poke_types) if isinstance(poke_types, list) else str(poke_types)
						action.actor.add_pokemon_to_storage(
							getattr(target_poke, "name", ""),
							getattr(target_poke, "level", 1),
							type_,
						)
					except Exception:
						pass

				species_id = getattr(target_poke, "species", None) or getattr(target_poke, "name", None)
				if trainer and species_id is not None:
					if hasattr(trainer, "log_seen_pokemon"):
						try:
							trainer.log_seen_pokemon(species_id)
						except Exception:
							pass
					if hasattr(trainer, "log_caught_pokemon"):
						try:
							trainer.log_caught_pokemon(species_id)
						except Exception:
							pass

				if player is not None:
					for method_name in ("mark_seen", "mark_caught"):
						func = getattr(player, method_name, None)
						if callable(func) and species_id is not None:
							try:
								func(str(species_id))
							except Exception:
								pass

				held_item = getattr(target_poke, "item", None) or getattr(target_poke, "held_item", None)
				held_name = None
				if held_item:
					held_name = getattr(held_item, "name", None)
					if not held_name:
						held_name = str(held_item)
					if hasattr(target_poke, "item"):
						try:
							target_poke.item = None
						except Exception:
							pass
					if hasattr(target_poke, "held_item"):
						try:
							target_poke.held_item = ""
						except Exception:
							pass
				if held_name:
					recipient = None
					if trainer and hasattr(trainer, "add_item"):
						recipient = trainer
					elif hasattr(action.actor, "add_item"):
						recipient = action.actor
					elif player and hasattr(player, "add_item"):
						recipient = player
					if recipient:
						try:
							recipient.add_item(held_name, 1)
						except Exception:
							pass

				storage = getattr(action.actor, "storage", None)
				party_full = False
				if storage and hasattr(storage, "get_party"):
					try:
						party = storage.get_party()
						party_count = len(list(party)) if party is not None else 0
					except Exception:
						party_count = 6
					party_full = party_count >= 6

				if player is not None and hasattr(player, "ndb"):
					pending = list(getattr(player.ndb, "pending_caught_pokemon", []) or [])
					pending.append({"species": pokemon_name, "to_storage": party_full})
					try:
						player.ndb.pending_caught_pokemon = pending
					except Exception:
						pass

				if hasattr(self, "log_action"):
					if party_full:
						self.log_action(f"{pokemon_name} was sent to your storage!")
					else:
						self.log_action(f"Would you like to give {pokemon_name} a nickname?")
				target.has_lost = True
				self.check_victory()
			else:
				if hasattr(action.actor, "remove_item"):
					try:
						action.actor.remove_item(action.item)
					except Exception:
						pass
				if hasattr(self, "log_action"):
					self.log_action(f"Oh no! {pokemon_name} broke free!")

	def perform_move_action(self, action: Action) -> None:
		"""Execute a move action."""
		self.use_move(action)

	def perform_item_action(self, action: Action) -> None:
		"""Use an item during battle."""
		self.execute_item(action)

	def perform_mega_evolution(self, pokemon) -> None:
		"""Placeholder for Mega Evolution mechanics."""
		setattr(pokemon, "mega_evolved", True)

	def perform_tera_change(self, pokemon, tera_type: str) -> None:
		"""Placeholder for Terastallization mechanics."""
		setattr(pokemon, "tera_type", tera_type)

	def end_turn(self) -> None:
		for part in self.participants:
			if all(getattr(p, "hp", 1) <= 0 for p in part.pokemons):
				part.has_lost = True
			for poke in part.active:
				self.dispatcher.dispatch("end_turn", pokemon=poke, battle=self)
		self.check_victory()

	def run_turn(self) -> None:
		logger.info("Run turn %s begin", self.turn_count + 1)
		self.dispatcher.dispatch("turn_start", battle=self)
		self.start_turn()
		logger.info("After start_turn")
		self.before_turn()
		logger.info("After before_turn")
		self.dispatcher.dispatch("lock_choices", battle=self)
		self.lock_choices()
		logger.info("After lock_choices")
		self.dispatcher.dispatch("switch", battle=self)
		self.run_switch()
		self.run_after_switch()
		logger.info("After switch")
		self.dispatcher.dispatch("move", battle=self)
		self.run_move()
		self.run_faint()
		logger.info("After move")
		self.dispatcher.dispatch("residual", battle=self)
		self.residual()
		logger.info("After residual")
		self.end_turn()
		logger.info("Run turn %s end", self.turn_count)


__all__ = ["TurnProcessor"]
