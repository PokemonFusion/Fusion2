from evennia import DefaultRoom
from evennia.utils import ansi


class MapRoom(DefaultRoom):
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

    def at_object_receive(self, moved_obj, source_location):
        super().at_object_receive(moved_obj, source_location)
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
