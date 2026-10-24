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
        "gyms",
        "multi battles",
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


def test_marketplace_guide_describes_exact_price_review_and_recovery():
    """Keep the two guide surfaces aligned with bounded ordinary commerce."""
    text = _guide_entries()["marketplace"]["text"]
    for command in ("+market list", "+market inspect", "+market buy", "+market cancel", "+market mine"):
        assert command in text
    for rule in ("24 hours", "1,000,000", "no fee", "hatched", "historical", "box"):
        assert rule in text


def test_daycare_guide_distinguishes_custody_from_explicit_breeding():
    """Custody itself never promises passive production or progression."""
    text = _guide_entries()["daycare"]["text"]
    for command in ("+daycare deposit", "+daycare retrieve", "+daycare"):
        assert command in text
    for rule in ("two", "100", "free", "no cooldown", "box", "separate +breed"):
        assert rule in text


def test_breeding_guide_matches_one_cycle_and_current_owner_hatching():
    """Publish costs, real-time policy, retry and supported-scope limits together."""
    text = _guide_entries()["breeding"]["text"]
    for command in ("+breed check", "+breed start", "+breed collect", "+breed hatch", "+breed cancel"):
        assert command in text
    for rule in ("500", "30 wall-clock", "24-hour", "20 wall-clock", "current owner", "same Pokemon ID", "excluded"):
        assert rule in text


def test_beginner_index_links_current_core_systems_and_adoption_decision():
    """Players can discover the supported routes without a staff-only entry point."""
    text = _guide_entries()['getting started']['text']
    for topic in ('pokemon and storage', 'growth and moves', 'fusion', 'trading',
                  'marketplace', 'daycare', 'breeding', 'gyms', 'pvp and spectating', 'multi battles'):
        assert 'help ' + topic in text
    assert 'Adoption is deferred from beta' in text


def test_pvp_guidance_distinguishes_two_and_four_human_controllers():
    """A doubles example must not imply four-player control or automatic mechanics."""
    text = _guide_entries()['pvp and spectating']['text']
    for command in ('+pvp/create single', '+pvp/create double', '+pvp/join Ash', '+pvp/start', '+pvp/multi create'):
        assert command in text
    assert 'at least two conscious eligible battlers' in text
    assert 'does not add two more controllers' in text


def test_gym_guidance_includes_prerequisites_and_interrupted_claim_recovery():
    """Find/check/challenge and claim are the shipped player route."""
    text = _guide_entries()['gyms']['text']
    for command in ('+gym list', '+gym check tempo_gym', '+gym challenge tempo_gym', '+gym claim', '+battle/retry'):
        assert command in text
    assert 'not award a duplicate badge' in text
    assert 'location' in text and 'rematch' in text


def test_storage_moves_and_battles_explain_current_selectors_and_failure_recovery():
    """Examples preserve gaps, owned items, real move eligibility and action targets."""
    entries = _guide_entries()
    for text, fragments in (
        (entries['pokemon and storage']['text'], ('+store, choose Buy items', '+hold 2=', 'full Pokemon ID', 'reserved')),
        (entries['growth and moves']['text'], ('+party/moves 3', '+learn 3', '+teach 3=Water Gun', 'preserves PP')),
        (entries['battle basics']['text'], ('+attack A2 Water Gun B1', '+switch A2 6', '+item A2 Potion=3', 'Ally Switch')),
    ):
        for fragment in fragments:
            assert fragment in text
