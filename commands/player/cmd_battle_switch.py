"""Command to switch active Pokémon during battle."""

from __future__ import annotations

from evennia import Command
from evennia.utils.evmenu import get_input

from pokemon.helpers.party_helpers import get_party_slots
from pokemon.services.pokemon_refs import parse_pokemon_ref
from world.system_init import get_system

from .cmd_battle_utils import NOT_IN_BATTLE_MSG, _get_participant

try:  # pragma: no cover - battle engine may not be available in tests
	from pokemon.battle import Action, ActionType

	if Action is None or ActionType is None:  # type: ignore[truthy-bool]
		raise ImportError
except Exception:  # pragma: no cover - fallback if engine isn't loaded
	from pokemon.battle.engine import Action, ActionType


class CmdBattleSwitch(Command):
	"""Switch your active Pokémon in battle.

	Usage:
		+battle/switch <slot|fusion>

	Examples:
		+switch 2
		+battle/switch 4
		+switch fusion

	Notes:
		Slots match +party, including gaps. With no slot, list available Pokemon.
		Use 'fusion' to select your active Fusion form, even with a full party.
	"""

	key = "+battle/switch"
	aliases = ["+switch", "+Switch", "+battleswitch"]
	locks = "cmd:all()"
	help_category = "Pokemon/Battle"

	def _choices(self, participant):
		"""Map displayed party slots to the battle roster's internal indices."""
		roster = participant.pokemons
		if getattr(self.caller, "storage", None) is None:
			return {i: (i, mon) for i, mon in enumerate(roster, 1) if mon is not None}
		party = get_party_slots(self.caller)
		choices = {}
		for slot, model in enumerate(party, 1):
			if model is None:
				continue
			identifier = str(getattr(model, "unique_id", "") or "")
			for index, mon in enumerate(roster, 1):
				kind, model_id = parse_pokemon_ref(getattr(mon, "model_id", None))
				if mon is model or (identifier and kind == "owned" and model_id == identifier):
					choices[slot] = (index, mon)
					break
		# The party sheet displays a reserved active Fusion in the first free
		# position. Preserve that display choice without changing its placement.
		fusion_id = str(getattr(self.caller.db, "fusion_id", "") or "")
		if fusion_id:
			for index, mon in enumerate(roster, 1):
				kind, model_id = parse_pokemon_ref(getattr(mon, "model_id", None))
				if kind == "owned" and model_id == fusion_id and not any(mon is p for _, p in choices.values()):
					key = party.index(None) + 1 if None in party else "fusion"
					choices[key] = (index, mon)
					break
		return dict(sorted(choices.items(), key=lambda choice: 7 if choice[0] == "fusion" else choice[0]))

	def _select(self, inst, participant, choice):
		"""Validate one canonical selection for both direct and prompted input."""
		if choice.lower() in {"0", "cancel", "quit", "exit", "abort", ".abort"}:
			self.caller.msg("Switch cancelled.")
			return False
		try:
			choices = self._choices(participant)
			if choice.lower() == "fusion":
				fusion_id = str(getattr(self.caller.db, "fusion_id", "") or "")
				key = next((slot for slot, (_, mon) in choices.items()
					if parse_pokemon_ref(getattr(mon, "model_id", None)) == ("owned", fusion_id)), "fusion")
			else:
				key = int(choice)
			index, pokemon = choices[key]
		except (ValueError, KeyError):
			self.caller.msg("Invalid Pokémon slot. Use +party or +switch to see available slots.")
			return True
		if pokemon in participant.active:
			self.caller.msg(f"{pokemon.name} is already active.")
			return True
		if getattr(pokemon, "hp", 0) <= 0:
			self.caller.msg(f"{pokemon.name} has fainted and cannot battle.")
			return True
		action = Action(participant, ActionType.SWITCH, priority=6)
		action.pokemon = pokemon
		action.target = pokemon
		participant.pending_action = action
		self.caller.msg(f"You prepare to switch to {pokemon.name}.")
		if hasattr(inst, "queue_switch"):
			inst.queue_switch(index, caller=self.caller)
		elif hasattr(inst, "maybe_run_turn"):
			inst.maybe_run_turn(actor=self.caller)
		return False

	def func(self):
		"""Prompt for or queue a switch using the same slots as the party view."""
		if not getattr(self.caller.db, "battle_control", False):
			self.caller.msg("|rWe aren't waiting for you to command right now.")
			return
		slot = self.args.strip()
		system = get_system()
		manager = getattr(system, "battle_manager", None)
		inst = manager.for_player(self.caller) if manager else None
		if not inst:
			try:  # pragma: no cover - battle session may be absent in tests
				from pokemon.battle.battleinstance import BattleSession
			except Exception:  # pragma: no cover

				class BattleSession:  # type: ignore[override]
					@staticmethod
					def ensure_for_player(caller):
						return getattr(caller.ndb, "battle_instance", None)

			inst = BattleSession.ensure_for_player(self.caller)
		if not inst or not getattr(inst, "battle", None):
			self.caller.msg(NOT_IN_BATTLE_MSG)
			return
		participant = _get_participant(inst, self.caller)
		if participant is None:
			self.caller.msg(NOT_IN_BATTLE_MSG)
			return

		if not slot:
			lines = []
			for idx, (_, poke) in self._choices(participant).items():
				status = " (fainted)" if getattr(poke, "hp", 0) <= 0 else ""
				active = " (active)" if poke in participant.active else ""
				lines.append(f"{idx}. {poke.name}{active}{status}")
			lines.append("0. Cancel")

			def _callback(caller, prompt, result):
				"""Resolve the current canonical slot when the player replies."""
				return self._select(inst, participant, result.strip())

			prompt = "Choose a Pokémon to switch to or 0 to cancel:\n" + "\n".join(lines)
			get_input(self.caller, prompt, _callback)
			return

		self._select(inst, participant, slot)
