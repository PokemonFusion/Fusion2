"""Optional explicit non-plot Daycare authoring for the reviewed teaching route."""

from pokemon.services.item_activity_routes import ItemActivityRoute


MIRROR_HERB_DAYCARE = ItemActivityRoute(
    "mirror-herb-daycare-v1", "Daycare Classroom", "daycare",
    "A Daycare sign explains free Mirror Herb teaching: +daycare herb <recipient>=<donor>/<exact move>, "
    "then +daycare herb confirm. Keep both owned hatched Pokemon in your party; the recipient holds "
    "the reusable Herb and needs an empty move slot. Do not deposit them for teaching. Ordinary "
    "Daycare deposit/retrieve and breeding retain their separate rules and fees. Back returns to the hub.",
    {"is_daycare": True, "allow_hunting": False, "noitem": True})
