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
        # `self.db` is an AttributeHandler. Using the handler's `get` method can
        # fail if an attribute named ``get`` was inadvertently stored on the
        # object, shadowing the method. Access the attribute directly instead to
        # avoid this edge case.
        return getattr(self.db, "weather", "clear")

    def set_weather(self, weather: str) -> None:
        """Set the room's weather."""
        self.db.weather = str(weather).lower()

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

        # Room description follows on the next line in white.
        output = [title, "", f"|w{desc_text}|n"]

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
            line = f"|C{ex.key}|n"
            if not ex.access(looker, "traverse"):
                line += " |W(Locked)|n"
            if ex.db.dark:
                line += " |W(Dark)|n"
            if is_builder:
                line += f" |W(#{ex.id})|n"
            exit_lines.append("  " + line)

        characters = self.filter_visible(
            self.contents_get(content_type="character"), looker, **kwargs
        )
        players = [c for c in characters if c.has_account and not c.attributes.get("npc")]
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
            box.append("|yThere is a store here, use +store/list to see its contents.|n")
        if self.db.is_pokemon_center:
            box.append("|yThere is a Pokemon center here. Use +pokestore to access your Pokemon storage.|n")

        output.append("\n".join(box))

        return "\n".join(output)
