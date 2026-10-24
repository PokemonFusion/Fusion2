from world.help_entries import HELP_ENTRY_DICTS


def _guide_entries():
    return {entry["key"]: entry for entry in HELP_ENTRY_DICTS if entry.get("category", "").lower() == "guide"}


def test_player_guide_has_expected_topics():
    entries = _guide_entries()
    assert set(entries) >= {
        "getting started",
        "core commands",
        "fusion",
        "character mail",
        "support requests",
        "pokemon and storage",
        "exploring and hunting",
        "battle basics",
        "growth and moves",
        "dex reference",
        "pvp and spectating",
        "trading",
    }


def test_getting_started_covers_first_session_flow():
    text = _guide_entries()["getting started"]["text"]
    for command in ("charcreate", "goic", "chargen", "+starters", "+starter", "+hunt"):
        assert command in text


def test_core_command_reference_stays_player_facing():
    text = _guide_entries()["core commands"]["text"]
    for command in (
        "help",
        "look",
        "+sheet",
        "+inventory",
        "+uimode",
        "+battleui/style",
        "+fusion",
        "+profile",
        "+mail",
        "+request",
        "+staff",
    ):
        assert command in text
    for admin_command in ("@additem", "@adminheal", "@customhunt", "@alphaspawnapply"):
        assert admin_command not in text


def test_battle_guide_lists_regular_battle_actions():
    text = _guide_entries()["battle basics"]["text"]
    for command in (
        "+battle/attack",
        "+battle/switch",
        "+battle/item",
        "+battle/flee",
        "+battle/concede",
        "+status",
    ):
        assert command in text


def test_trade_guide_requires_inspection_consent_and_current_availability():
    """Keep game/web guide text consistent with the shipped ordinary route."""
    entries = _guide_entries()
    text = entries["trading"]["text"]
    for command in ("+trade offer", "+trade inspect", "+trade accept", "+trade counter", "+trade decline", "+trade cancel"):
        assert command in text
    for rule in ("15 minutes", "Previous inspection", "Party", "boxed Pokemon", "Pokemon Center"):
        assert rule.lower() in text.lower()
    assert "+trade remains disabled" not in entries["growth and moves"]["text"]
    assert "Trading is temporarily unavailable" not in entries["pokemon and storage"]["text"]
