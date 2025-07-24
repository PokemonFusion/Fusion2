"""
Room

Rooms are simple containers that has no location of their own.

"""

from evennia.objects.objects import DefaultRoom
import random
import textwrap
import re
from utils.ansi import ansi
from pokemon.battle.battleinstance import BattleSession

try:
    from evennia.utils.logger import log_info, log_err
except Exception:  # pragma: no cover - fallback if Evennia not available
    import logging

    _log = logging.getLogger(__name__)

    def log_info(*args, **kwargs):
        _log.info(*args, **kwargs)


from .objects import ObjectParent


class Room(ObjectParent, DefaultRoom):
    """
    Rooms are like any Object, except their location is None
    (which is default). They also use basetype_setup() to
    add locks so they cannot be puppeted or picked up.
    (to change that, use at_object_creation instead)

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects.
    """

    pass


class FusionRoom(Room):
    """Room with support for hunting and shop flags."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_pokemon_center = False
        self.db.is_item_store = False
        self.db.is_item_shop = False
        self.db.store_inventory = {}
        self.db.allow_hunting = False
        self.db.encounter_rate = 100
        self.db.hunt_chart = []
        # Extra hunting related settings
        self.db.npc_chance = 15  # percent chance of trainer battle
        self.db.itemfinder_rate = 5  # percent chance of finding item
        self.db.noitem = False
        self.db.tp_cost = 0
        # Track the current weather affecting this room
        self.db.weather = "clear"

    def set_hunt_chart(self, chart):
        """Helper to set this room's hunt chart."""
        self.db.hunt_chart = chart

    def at_object_receive(self, moved_obj, source_location, move_type="move", **kwargs):
        super().at_object_receive(
            moved_obj, source_location, move_type=move_type, **kwargs
        )
        if not hasattr(moved_obj, "id"):
            return

        battle_id = getattr(moved_obj.db, "battle_id", None)
        if battle_id is not None:
            instance = BattleSession.restore(self, battle_id)
            if instance:
                moved_obj.ndb.battle_instance = instance

    def at_init(self):
        """Rebuild non-persistent battle data after reload."""
        result = super().at_init()
        log_info(f"FusionRoom #{self.id} running at_init()...")
        battle_ids = getattr(self.db, "battles", None)
        if not isinstance(battle_ids, list):
            log_info("No battle list found or invalid format; skipping restore")
            return result or ""
        for bid in battle_ids:
            log_info(f"Restoring BattleSession {bid} in FusionRoom #{self.id}")
            try:
                BattleSession.restore(self, bid)
            except Exception:
                log_err(
                    f"Error restoring BattleSession {bid} in FusionRoom #{self.id}",
                    exc_info=True,
                )
        return result or ""


    def get_random_pokemon(self):
        """Return a Pokémon name selected from the hunt chart."""
        if not self.db.allow_hunting or not self.db.hunt_chart:
            return None
        population = [e.get("name") for e in self.db.hunt_chart]
        weights = [e.get("weight", 1) for e in self.db.hunt_chart]
        return random.choices(population, weights=weights, k=1)[0]

    # ------------------------------------------------------------------
    # Weather helpers
    # ------------------------------------------------------------------
    def get_weather(self) -> str:
        """Return the current weather in this room."""
        # `self.db` is an AttributeHandler. Using the handler's `get` method can
        # fail if an attribute named ``get`` was inadvertently stored on the
        # object, shadowing the method. Access the attribute directly instead to
        # avoid this edge case.
        return getattr(self.db, "weather", "clear")

    def set_weather(self, weather: str) -> None:
        """Set the room's weather."""
        self.db.weather = str(weather).lower()

    def _color_exit_name(self, name: str) -> str:
        """Return exit name with hotkey parentheses highlighted."""
        if not name:
            return "|c|n"

        def repl(match: re.Match) -> str:
            inner = match.group(1)
            return f"|c(|w{inner}|c)"

        colored = re.sub(r"\(([^)]*)\)", repl, name)
        return f"|c{colored}|n"

    # ------------------------------------------------------------------
    # Look/appearance helpers
    # ------------------------------------------------------------------

    BOX_LINE = "|g" + "-" * 76 + "|n"

    def return_appearance(self, looker, **kwargs):
        """Return the look description for this room."""
        if not looker:
            return ""

        is_builder = looker.check_permstring("Builder")

        # Title of the room for display. Show the room name in green and bold.
        title = f"|g|h{self.key}|n"
        if is_builder:
            title += f" |y(#{self.id})|n"

        desc = self.db.desc or self.default_description
        wrapper = textwrap.TextWrapper(width=76)
        paragraphs = []
        for para in desc.splitlines():
            para = para.strip()
            if not para:
                continue
            paragraphs.append("  " + wrapper.fill(para))
        desc_text = "\n".join(paragraphs)

        # Room description follows on the next line without added color so
        # user-specified codes remain untouched.
        output = [title, "", desc_text]

        weather = self.get_weather()
        if weather and weather != "clear":
            # Indicate current weather conditions if not clear.
            output.append(f"|wIt's {weather} here.|n")

        exits = self.filter_visible(
            self.contents_get(content_type="exit"), looker, **kwargs
        )
        prioritized = [ex for ex in exits if ex.db.priority is not None]
        unprioritized = [ex for ex in exits if ex.db.priority is None]
        prioritized.sort(key=lambda e: e.db.priority)
        exit_lines = []
        for ex in prioritized + unprioritized:
            if ex.db.dark and not is_builder:
                continue
            line = self._color_exit_name(ex.key)
            if not ex.access(looker, "traverse"):
                line += " |r(Locked)|n"
            if ex.db.dark:
                line += " |m(Dark)|n"
            if is_builder:
                line += f" |y(#{ex.id})|n"
            exit_lines.append("  " + line)

        characters = self.filter_visible(
            self.contents_get(content_type="character"), looker, **kwargs
        )
        players = [
            c for c in characters if c.has_account and not c.attributes.get("npc")
        ]
        # Make sure the looker shows up in the player list even if filtered out
        if (
            looker.has_account
            and not looker.attributes.get("npc")
            and looker not in players
        ):
            players.append(looker)
        npcs = [c for c in characters if not c.has_account or c.attributes.get("npc")]

        player_names = []
        for p in players:
            name = f"|w{p.key}|n"
            if is_builder:
                name += f" |y(#{p.id})|n"
            if p.db.dark and is_builder:
                name += " |m(Dark)|n"
            player_names.append(name)

        npc_names = []
        for npc in npcs:
            name = f"|y{npc.key}|n"
            if is_builder:
                name += f" |y(#{npc.id})|n"
            npc_names.append(name)

        green_rule = self.BOX_LINE
        box = [green_rule, "|g  :Exits:|n"]
        box.extend(exit_lines)
        box.append(green_rule)
        if player_names:
            box.append("|g  :Players:|n")
            box.append("  " + ", ".join(player_names))
            box.append(green_rule)
        if npc_names:
            box.append("|g  :Non-Player Characters:|n " + ", ".join(npc_names))
            box.append(green_rule)

        if self.db.is_item_store:
            box.append(
                "|yThere is a store here, use +store/list to see its contents.|n"
            )
        if self.db.is_pokemon_center:
            box.append(
                "|yThere is a Pokemon center here. Use +pokestore to access your Pokemon storage.|n"
            )

        output.append("\n".join(box))

        return "\n".join(output)


class BattleRoom(Room):
    """A basic room for handling battles."""

    def at_object_creation(self):
        super().at_object_creation()
        # Mark as temporary; cleanup should remove this room after battle
        self.locks.add("view:all();delete:perm(Builders)")


class MapRoom(Room):
    """Room representing a virtual 2D grid map."""

    map_width: int = 10
    map_height: int = 10
    tile_display: str = "."
    map_data: dict = {}

    def at_object_creation(self):
        super().at_object_creation()
        if not self.map_data:
            self.map_data = {
                (x, y): self.tile_display
                for x in range(self.map_width)
                for y in range(self.map_height)
            }

    def at_object_receive(self, moved_obj, source_location, move_type="move", **kwargs):
        super().at_object_receive(
            moved_obj, source_location, move_type=move_type, **kwargs
        )
        if not moved_obj.attributes.has("xy"):
            moved_obj.db.xy = (0, 0)
        self.display_map(moved_obj)

    def move_entity(self, entity, dx: int, dy: int) -> None:
        """Move entity inside the map."""
        x, y = entity.db.xy
        new_x = max(0, min(self.map_width - 1, x + dx))
        new_y = max(0, min(self.map_height - 1, y + dy))
        entity.db.xy = (new_x, new_y)
        self.display_map(entity)

    def display_map(self, viewer) -> None:
        """Display a simple ASCII map to viewer."""
        output = "|w-- Virtual Map --|n\n"
        px, py = viewer.db.xy
        for j in range(self.map_height):
            for i in range(self.map_width):
                if (i, j) == (px, py):
                    output += ansi.RED("@")
                else:
                    output += self.map_data.get((i, j), self.tile_display)
            output += "\n"
        viewer.msg(output)
