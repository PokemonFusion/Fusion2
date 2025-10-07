"""Battle participant models.

This module defines :class:`BattleParticipant`, representing one side in a
battle. It was extracted from ``engine.py`` to improve modularity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from utils.safe_import import safe_import

if TYPE_CHECKING:  # pragma: no cover - circular imports for typing only
        from pokemon.battle.actions import Action
        from pokemon.battle.engine import Battle


class BattleParticipant:
        """Represents one side of a battle.

        Parameters
        ----------
        name:
            Display name for this participant.
        pokemons:
            List of Pokémon available to this participant.
        is_ai:
            If ``True`` this participant is controlled by the AI.
        player:
            Optional Evennia object representing the controlling player.
        max_active:
            Maximum number of simultaneously active Pokémon.
        team:
            Optional team identifier. Participants with the same team are treated
            as allies and should not be targeted by automatic opponent selection.
        """

        def __init__(
                self,
                name: str,
                pokemons: List,
                is_ai: bool = False,
                player=None,
                max_active: int = 1,
                team: str | None = None,
        ):
                self.name = name
                self.pokemons = pokemons
                self.active: List = []
                self.is_ai = is_ai
                self.has_lost = False
                self.pending_action: Optional[Action] = None
                # Track every Pokémon that enters the field for reward
                # distribution at the end of the battle. Lists preserve the
                # order Pokémon participated in while the set helps avoid
                # duplicates when a Pokémon switches in multiple times.
                self.participating_pokemon: List = []
                self._participant_cache: set[str] = set()

                battle_side_cls = getattr(safe_import("pokemon.battle.engine"), "BattleSide")
                self.side = battle_side_cls()
                self.player = player
                self.trainer = getattr(player, "trainer", None)
                self.max_active = max_active
                # Team is optional; if ``None`` participants are assumed to be enemies
                # of everyone else. When provided, participants sharing the same team
                # value are considered allies.
                self.team = team
                for poke in self.pokemons:
                        if poke is not None:
                                setattr(poke, "side", self.side)

        def record_participation(self, pokemon) -> None:
                """Record that ``pokemon`` has actively participated.

                The engine calls this whenever a Pokémon enters the field.
                Participation is tracked using the ``model_id``/``unique_id``
                attributes when available to ensure the correct storage
                Pokémon receives post-battle rewards.
                """

                if pokemon is None:
                        return
                identifier = None
                for attr in ("model_id", "unique_id", "id"):
                        value = getattr(pokemon, attr, None)
                        if value is not None:
                                identifier = str(value)
                                break
                if identifier is None:
                        identifier = str(id(pokemon))
                if identifier in self._participant_cache:
                        return
                self._participant_cache.add(identifier)
                self.participating_pokemon.append(pokemon)

        def choose_action(self, battle: "Battle") -> Optional[Action]:
                """Return an :class:`Action` object for this turn."""

                if self.pending_action:
                        action = self.pending_action
                        self.pending_action = None
                        # Validate the target against remaining opponents
                        if action.target and action.target not in battle.participants:
                                action.target = None
                        if not action.target:
                                opponents = battle.opponents_of(self)
                                if opponents:
                                        action.target = opponents[0]
                        return action

                if not self.is_ai or not self.active:
                        return None

                active_poke = self.active[0]
                _select_ai_action = safe_import("pokemon.battle.engine")._select_ai_action  # type: ignore[attr-defined]

                return _select_ai_action(self, active_poke, battle)

        def choose_actions(self, battle: "Battle") -> List[Action]:
                """Return a list of actions for all active Pokémon."""

                if self.pending_action:
                        action = self.pending_action
                        self.pending_action = None
                        if isinstance(action, list):
                                for act in action:
                                        if act.target and act.target not in battle.participants:
                                                act.target = None
                                        if not act.target:
                                                opps = battle.opponents_of(self)
                                                if opps:
                                                        act.target = opps[0]
                                return action
                        if action.target and action.target not in battle.participants:
                                action.target = None
                        if not action.target:
                                opps = battle.opponents_of(self)
                                if opps:
                                        action.target = opps[0]
                        return [action]

                if not self.is_ai:
                        return []

                actions: List[Action] = []
                _select_ai_action = safe_import("pokemon.battle.engine")._select_ai_action  # type: ignore[attr-defined]

                for active_poke in self.active:
                        action = _select_ai_action(self, active_poke, battle)
                        if action:
                                actions.append(action)
                return actions

        # ------------------------------------------------------------------
        # Inventory helpers
        # ------------------------------------------------------------------

        def _inventory_targets(self):
                """Yield objects that may manage this participant's inventory."""

                seen = []
                player = getattr(self, "player", None)
                for candidate in (player, getattr(self, "trainer", None), getattr(player, "trainer", None)):
                        if candidate and candidate not in seen:
                                seen.append(candidate)
                                yield candidate
                inventory = getattr(self, "inventory", None)
                if isinstance(inventory, dict):
                        yield inventory

        def _match_inventory_key(self, inventory, name: str):
                """Return the matching key in ``inventory`` for ``name`` ignoring case."""

                if isinstance(inventory, dict):
                        target = name.lower()
                        for key in list(inventory.keys()):
                                if str(key).lower() == target:
                                        return key
                return name

        def add_item(self, name: str, quantity: int = 1) -> None:
                """Add items to the first available inventory handler."""

                for target in self._inventory_targets():
                        if isinstance(target, dict):
                                key = self._match_inventory_key(target, name)
                                target[key] = target.get(key, 0) + quantity
                                return
                        adder = getattr(target, "add_item", None)
                        if callable(adder):
                                try:
                                        adder(name, quantity)
                                except TypeError:
                                        adder(name)
                                return

        def remove_item(self, name: str, quantity: int = 1) -> bool:
                """Remove items from the first handler that succeeds."""

                for target in self._inventory_targets():
                        if isinstance(target, dict):
                                key = self._match_inventory_key(target, name)
                                current = target.get(key, 0)
                                if current < quantity:
                                        continue
                                new_amount = current - quantity
                                if new_amount <= 0:
                                        target.pop(key, None)
                                else:
                                        target[key] = new_amount
                                return True
                        remover = getattr(target, "remove_item", None)
                        if callable(remover):
                                try:
                                        result = remover(name, quantity)
                                except TypeError:
                                        result = remover(name)
                                if result:
                                        return True
                return False

        def has_item(self, name: str, quantity: int = 1) -> bool:
                """Return ``True`` if any inventory handler has enough of ``name``."""

                for target in self._inventory_targets():
                        if isinstance(target, dict):
                                key = self._match_inventory_key(target, name)
                                if target.get(key, 0) >= quantity:
                                        return True
                                continue
                        checker = getattr(target, "has_item", None)
                        if callable(checker):
                                try:
                                        if checker(name, quantity):
                                                return True
                                except TypeError:
                                        if checker(name):
                                                return True
                                continue
                        getter = getattr(target, "get_item_quantity", None)
                        if callable(getter):
                                try:
                                        if getter(name) >= quantity:
                                                return True
                                except TypeError:
                                        try:
                                                if getter(name, quantity):
                                                        return True
                                        except Exception:
                                                continue
                return False


__all__ = ["BattleParticipant"]
