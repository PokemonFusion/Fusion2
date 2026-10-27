"""Reviewed recovery equivalents shared by field and manual battle medicine.

Only the named battle subset is enabled; field flavor/EV feeding and held
callbacks retain their separate rules. See docs/battle-recovery-items.md.
"""

from pokemon.items import BATTLE_RECOVERY_FOODS, FIELD_RECOVERY_ITEMS


BERRY_HEALING = {"oranberry": 10, "berryjuice": 20, "berry": 10, "goldberry": 30}
BERRY_FRACTIONS = {
    "sitrusberry": 4,
    "figyberry": 3, "wikiberry": 3, "magoberry": 3,
    "aguavberry": 3, "iapapaberry": 3,
}
BERRY_STATUSES = {
    "cheriberry": {"par"}, "chestoberry": {"slp"},
    "pechaberry": {"psn", "tox"}, "rawstberry": {"brn"},
    "aspearberry": {"frz"},
    "lumberry": {"brn", "psn", "tox", "frz", "slp", "par"},
    "burntberry": {"frz"}, "iceberry": {"brn"}, "mintberry": {"slp"},
    "miracleberry": {"brn", "psn", "tox", "frz", "slp", "par"},
    "przcureberry": {"par"}, "psncureberry": {"psn", "tox"},
}
BERRY_PP = {"leppaberry": (10, False), "mysteryberry": (5, False)}
BATTLE_BERRY_FRACTIONS = {"sitrusberry": BERRY_FRACTIONS["sitrusberry"]}
BATTLE_FOOD_HEALING = {
    key: FIELD_RECOVERY_ITEMS[key].amount for key in BATTLE_RECOVERY_FOODS
    if FIELD_RECOVERY_ITEMS[key].effect == "heal"
}
BATTLE_STATUS_FOODS = frozenset(
    key for key in BATTLE_RECOVERY_FOODS if FIELD_RECOVERY_ITEMS[key].effect == "status"
)
BATTLE_REVIVAL_FOODS = frozenset(
    key for key in BATTLE_RECOVERY_FOODS if FIELD_RECOVERY_ITEMS[key].effect == "revive"
)
