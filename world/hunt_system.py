from __future__ import annotations

import random
import time
import builtins
from typing import Any, Callable, Dict, List, Optional

from evennia import DefaultRoom


class HuntSystem:
    """Utility for resolving Pokémon hunts in a room."""

    def __init__(self, room: DefaultRoom, spawn_callback: Optional[Callable[[Any, Dict[str, Any]], Any]] = None) -> None:
        self.room = room
        self.spawn_callback = spawn_callback

    def get_time_of_day(self) -> str:
        """Return the current time of day. Override for custom logic."""
        return "day"

    def get_current_weather(self) -> str:
        """Return the current weather for the room. Override for custom logic."""
        return getattr(self.room.db, "weather", "clear")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _pre_checks(self, hunter) -> Optional[str]:
        """Return an error string if hunting is not allowed."""
        room = self.room

        from pokemon.battle.battleinstance import (
            BattleInstance,
            BattleType,
            create_battle_pokemon,
        )

        # allow_hunting may be stored as a string or bool; coerce to boolean
        allow = getattr(room.db, "allow_hunting", False)
        if builtins.isinstance(allow, str):
            allow = allow.lower() in {"true", "yes", "1", "on"}
        if not allow:
            return "You can't hunt here."
        if getattr(hunter.ndb, "battle_instance", None):
            return "You are already in a battle!"
        last = getattr(hunter.ndb, "last_hunt_time", 0)
        if last and time.time() - last < 3:
            return "You need to wait before hunting again."
        storage = getattr(hunter, "storage", None)
        party = (
            storage.get_party() if storage and hasattr(storage, "get_party") else []
        )
        if not party:
            return "You don't have any Pokémon able to battle."
        tp_cost = getattr(self.room.db, "tp_cost", 0)
        if tp_cost:
            if hunter.db.get("training_points", 0) < tp_cost:
                return "You don't have enough training points."
        hunter.ndb.last_hunt_time = time.time()
        return None

    def _apply_walk_steps(self, hunter) -> None:
        """Placeholder simulation of egg/walking system."""
        storage = getattr(hunter, "storage", None)
        if not storage:
            return
        party = storage.get_party() if hasattr(storage, "get_party") else []
        for mon in party:
            steps = random.randint(2, 5)
            # Placeholder attributes for eggs/happiness
            mon.walked_steps = getattr(mon, "walked_steps", 0) + steps
            # Soothe Bell or happiness adjustments would go here
        if party:
            hunter.ndb.field_ability = getattr(party[0], "ability", None)

    def _check_itemfinder(self, hunter) -> Optional[str]:
        """Return an item message if itemfinder triggers."""
        room = self.room
        if getattr(room.db, "noitem", False):
            return None
        rate = getattr(room.db, "itemfinder_rate", 0)
        if random.randint(1, 100) <= rate:
            return "You found a mysterious item!"  # placeholder
        return None

    # ------------------------------------------------------------------
    # Main hunt entry points
    # ------------------------------------------------------------------
    def perform_hunt(self, hunter) -> str:
        """Resolve a hunt attempt and return the result message."""
        room = self.room
        err = self._pre_checks(hunter)
        if err:
            return err

        self._apply_walk_steps(hunter)

        item_msg = self._check_itemfinder(hunter)
        if item_msg:
            return item_msg

        from pokemon.battle.battleinstance import (
            BattleInstance,
            BattleType,
            create_battle_pokemon,
            generate_trainer_pokemon,
        )

        npc_chance = getattr(room.db, "npc_chance", 15)
        tp_cost = getattr(room.db, "tp_cost", 0)
        if random.randint(1, 100) <= npc_chance:
            poke = generate_trainer_pokemon()

            def _sel():
                return poke, "Trainer", BattleType.TRAINER

            inst = BattleInstance(hunter)
            inst._select_opponent = _sel
            inst.start()
            if tp_cost:
                hunter.db.training_points = hunter.db.get("training_points", 0) - tp_cost
            return f"A trainer challenges you with {poke.name}!"

        encounter_rate = getattr(room.db, "encounter_rate", 100)
        if random.randint(1, 100) > encounter_rate:
            return "You didn't find any Pokémon."

        chart: List[Dict[str, Any]] = room.db.hunt_chart or []
        time_of_day = self.get_time_of_day()
        weather = self.get_current_weather()

        valid: List[Dict[str, Any]] = []
        for entry in chart:
            times = entry.get("time", ["any"])
            weathers = entry.get("weather", ["any"])
            if ("any" in times or time_of_day in times) and (
                "any" in weathers or weather in weathers
            ):
                valid.append(entry)

        if not valid:
            return "No Pokémon are active right now."

        names = [entry["name"] for entry in valid]
        weights = [entry.get("weight", 1) for entry in valid]
        selected_name = random.choices(names, weights=weights, k=1)[0]
        selected_entry = next(e for e in valid if e["name"] == selected_name)
        min_level = selected_entry.get("min_level", 1)
        max_level = selected_entry.get("max_level", min_level)
        level = random.randint(min_level, max_level)

        result = {"name": selected_name, "level": level, "data": selected_entry}
        if self.spawn_callback:
            self.spawn_callback(hunter, result)

        # Start battle with the generated Pokémon
        poke = create_battle_pokemon(selected_name, level, is_wild=True)

        def _select_override():
            return poke, "Wild", BattleType.WILD

        inst = BattleInstance(hunter)
        inst._select_opponent = _select_override
        inst.start()

        if tp_cost:
            hunter.db.training_points = hunter.db.get("training_points", 0) - tp_cost

        return f"A wild {selected_name} (Lv {level}) appeared!"

    def perform_fixed_hunt(self, hunter, name: str, level: int) -> str:
        """Resolve a hunt with a predetermined Pokémon and level.

        This mirrors :meth:`perform_hunt` but skips random encounter logic and
        itemfinder checks, always spawning the specified Pokémon at the given
        level.
        """

        room = self.room

        from pokemon.battle.battleinstance import (
            BattleInstance,
            BattleType,
            create_battle_pokemon,
        )

        err = self._pre_checks(hunter)
        if err:
            return err

        self._apply_walk_steps(hunter)

        result = {
            "name": name,
            "level": level,
            "data": {"name": name, "min_level": level, "max_level": level},
        }
        if self.spawn_callback:
            self.spawn_callback(hunter, result)

        poke = create_battle_pokemon(name, level, is_wild=True)

        def _select_override():
            return poke, "Wild", BattleType.WILD

        inst = BattleInstance(hunter)
        inst._select_opponent = _select_override
        inst.start()

        tp_cost = getattr(room.db, "tp_cost", 0)
        if tp_cost:
            hunter.db.training_points = hunter.db.get("training_points", 0) - tp_cost

        return f"A wild {name} (Lv {level}) appeared!"
