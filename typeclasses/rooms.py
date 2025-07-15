"""
Room

Rooms are simple containers that has no location of their own.

"""

from evennia.objects.objects import DefaultRoom
import random
import textwrap


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
        # Track the current weather affecting this room
        self.db.weather = "clear"

    def set_hunt_chart(self, chart):
        """Helper to set this room's hunt chart."""
        self.db.hunt_chart = chart

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
        return self.db.get("weather", "clear")

    def set_weather(self, weather: str) -> None:
        """Set the room's weather."""
        self.db.weather = str(weather).lower()

    # ------------------------------------------------------------------
    # Look/appearance helpers
    # ------------------------------------------------------------------

    BOX_LINE = "-" * 76

    def return_appearance(self, looker, **kwargs):
        """Return the look description for this room."""
        if not looker:
            return ""

        is_builder = looker.check_permstring("Builder")

        title = f"|g|h📍 {self.key}|n"
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

        output = [title, "", f"|w📝|n {desc_text}"]

        weather = self.get_weather()
        if weather and weather != "clear":
            output.append(f"|w🌦️|n It's {weather} here.")

        exits = self.filter_visible(self.contents_get(content_type="exit"), looker, **kwargs)
        exit_lines = []
        for ex in exits:
            line = f"|c{ex.key}|n"
            if is_builder:
                line += f" |y(#{ex.id})|n"
            exit_lines.append(line)

        characters = self.filter_visible(self.contents_get(content_type="character"), looker, **kwargs)
        players = [c for c in characters if c.has_account and not c.attributes.get("npc")]
        npcs = [c for c in characters if not c.has_account or c.attributes.get("npc")]

        player_lines = []
        for p in players:
            line = p.key
            if is_builder:
                line += f" |y(#{p.id})|n"
            player_lines.append(line)

        npc_lines = []
        for npc in npcs:
            line = npc.key
            if is_builder:
                line += f" |y(#{npc.id})|n"
            npc_lines.append(line)

        box = [self.BOX_LINE, "|cExits:|n"]
        box.extend(exit_lines)
        box.append("|w|hPlayers:|n")
        box.extend(player_lines)
        box.append("|xNon-Player Characters:|n")
        box.extend(npc_lines)
        box.append(self.BOX_LINE)

        output.append("\n".join(box))

        return "\n".join(output)
