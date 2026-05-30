from world.help_entries import HELP_ENTRY_DICTS


def _guide_entries():
    return {entry["key"]: entry for entry in HELP_ENTRY_DICTS if entry.get("category", "").lower() == "guide"}


def test_player_guide_has_expected_topics():
    entries = _guide_entries()
    assert set(entries) >= {
        "getting started",
        "core commands",
        "pokemon and storage",
        "exploring and hunting",
        "battle basics",
        "growth and moves",
        "dex reference",
        "pvp and spectating",
    }


def test_getting_started_covers_first_session_flow():
    text = _guide_entries()["getting started"]["text"]
    for command in ("charcreate", "goic", "chargen", "+starters", "+starter", "+hunt"):
        assert command in text


def test_core_command_reference_stays_player_facing():
    text = _guide_entries()["core commands"]["text"]
    for command in ("help", "look", "+sheet", "+inventory", "+uimode", "+battleui/style"):
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
