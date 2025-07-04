from __future__ import annotations

import random
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

    def perform_hunt(self, hunter) -> str:
        """Resolve a hunt attempt and return the result message."""
        room = self.room
        if not room.db.allow_hunting:
            return "You can't hunt here."

        encounter_rate = room.db.get("encounter_rate", 100)
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
        return f"A wild {selected_name} (Lv {level}) appeared!"

    def perform_fixed_hunt(self, hunter, name: str, level: int) -> str:
        """Resolve a hunt with a predetermined Pokémon and level."""
        room = self.room
        if not room.db.allow_hunting:
            return "You can't hunt here."

        result = {
            "name": name,
            "level": level,
            "data": {"name": name, "min_level": level, "max_level": level},
        }
        if self.spawn_callback:
            self.spawn_callback(hunter, result)
        return f"A wild {name} (Lv {level}) appeared!"
