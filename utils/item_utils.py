"""Inventory handling helpers for sheet display."""

__all__ = ["get_inventory_by_category", "render_inventory_table"]


def get_inventory_by_category(character):
	"""Return a mapping of inventory categories to item lists."""
	# TODO: Implement actual categorization of character inventory
	return {}


def render_inventory_table(category: str, items):
	"""Return a simple table string for one inventory category."""
	# TODO: Implement formatted inventory tables
	if not items:
		return f"{category}: none"
	listing = ", ".join(str(i) for i in items)
	return f"{category}: {listing}"
