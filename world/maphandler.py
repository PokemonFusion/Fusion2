from evennia import create_object

from typeclasses.rooms import MapRoom


def generate_blank_map(width: int, height: int):
	return {(x, y): "." for x in range(width) for y in range(height)}


def create_map_instance(caller, width: int = 10, height: int = 10):
	"""Create a new map instance and move caller into it."""
	room = create_object(MapRoom, key=f"Instance-{caller.key}")
	room.map_width = width
	room.map_height = height
	room.map_data = generate_blank_map(width, height)
	caller.move_to(room, quiet=True)
	return room
