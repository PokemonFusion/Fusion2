"""Party cards preserve battle selectors and active Fusion state."""

import re
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

# Only the Evennia transport/table needs a stand-in; party, dex, stat,
# Fusion, and battle-adapter behavior below use the production modules.
ROOT = Path(__file__).resolve().parents[2]


class TextTable:
    """Capture sheet table cells without starting an Evennia server."""

    def __init__(self, *headers, **kwargs):
        """Retain column headers as ordinary text."""
        self.rows = [headers] if headers else []

    def add_row(self, *columns, **kwargs):
        """Append the cells used by the real sheet renderer."""
        self.rows.append(columns)

    def __str__(self):
        """Expose sheet contents for player-facing assertions."""
        return "\n".join(" ".join(map(str, row)) for row in self.rows)


def plain(text):
    """Strip the simple Evennia colour tags emitted by these cards."""
    return re.sub(r"\|[a-zA-Z]", "", str(text))


evennia = types.ModuleType("evennia")
evennia.__path__ = [str(ROOT.parent / "evennia" / "evennia")]
evennia.Command = type("Command", (), {})
evennia_utils = types.ModuleType("evennia.utils")
evennia_utils.ansi = SimpleNamespace(parse_ansi=plain, strip_ansi=plain)
evennia_utils.utils = SimpleNamespace(strip_ansi=plain)
evtable = types.ModuleType("evennia.utils.evtable")
evtable.EvTable = TextTable
evennia_utils.evtable = evtable
evennia.utils = evennia_utils
sys.modules["evennia"] = evennia
sys.modules["evennia.utils"] = evennia_utils
sys.modules["evennia.utils.evtable"] = evtable

from commands.player.cmd_sheet import CmdSheetPokemon
from pokemon.helpers.party_helpers import get_battle_switch_choices
from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats
from pokemon.models.stats import exp_for_level
from utils.fusion import get_battle_party_with_fusion
from utils.party_view import PartyView
from utils.pokemon_utils import build_battle_pokemon_from_model


def pokemon(identifier, species="Squirtle", *, nickname="", level=5, hp=None, status="", held=""):
    """Build stored attributes and calculate HP through the production helper."""
    mon = SimpleNamespace(
        unique_id=identifier,
        species=species,
        nickname=nickname,
        name=nickname or species,
        level=level,
        total_exp=exp_for_level(level, "medium_fast"),
        growth_rate="medium_fast",
        gender="M",
        nature="Hardy",
        ability="Torrent",
        ivs=[0] * 6,
        evs=[0] * 6,
        status=status,
        held_item=held,
        moves=["Tackle"],
    )
    mon.max_hp = get_max_hp(mon)
    mon.current_hp = mon.max_hp if hp is None else hp
    return mon


def player(slots=(), fused=None, *, order="normal", participates=True):
    """Supply canonical storage and ownership without a database or server."""
    slots = list(slots) + [None] * (6 - len(slots))
    owned = {str(mon.unique_id): mon for mon in [*slots, fused] if mon is not None}
    messages = []
    caller = SimpleNamespace(
        key="Ash",
        db=SimpleNamespace(gender="M", fusion_battle_order=order, fusion_participates=participates),
        storage=SimpleNamespace(
            get_party_slots=lambda: list(slots), get_party=lambda: [mon for mon in slots if mon is not None]
        ),
        get_pokemon_by_id=lambda identifier: owned.get(str(identifier)),
        messages=messages,
        msg=messages.append,
    )
    if fused:
        caller.db.fusion_id = fused.unique_id
        caller.db.fusion_species = fused.species
        caller.db.fusion_kind = "permanent"
        caller.db.total_exp = fused.total_exp
    return caller


def command(caller, args=""):
    """Run the real command parser, card renderer, and detailed sheet routing."""
    cmd = CmdSheetPokemon()
    cmd.caller, cmd.args, cmd.switches = caller, args, []
    cmd.parse()
    cmd.func()
    return plain(caller.messages[-1])


def test_party_cards_show_types_items_nicknames_and_hints():
    """The overview exposes identity, exact health, preparation and next actions."""
    mon = pokemon("squirtle", nickname="Shell", held="Oran Berry")
    text = command(player([mon]))
    assert "Party Pokémon - 1/6 | 1 able to battle" in text
    assert "1: Shell (Squirtle)  M  Lv 5  [WATER] [LEAD]" in text
    assert f"HP [##########] {mon.current_hp}/{get_max_hp(mon)}  OK  Held: Oran Berry" in text
    assert "Summary: +party <slot>" in text
    assert "Moves:   +party/moves <slot>" in text
    assert "NORM" not in text


@pytest.mark.parametrize(
    "status, expected",
    [
        ("", "OK"),
        ("0", "OK"),
        ("brn", "BURNED"),
        ("psn", "POISONED"),
        ("tox", "BADLY POISONED"),
        ("par", "PARALYZED"),
        ("slp", "ASLEEP"),
        ("frz", "FROZEN"),
    ],
)
def test_party_status_names_are_explicit(status, expected):
    """Major conditions stay understandable without decoding three-letter codes."""
    assert f"  {expected}  Held: None" in command(player([pokemon("mon", status=status)]))


def test_fainted_lead_and_empty_gaps_match_battle_choices():
    """Fainting takes priority and slot six stays six after skipped empty slots."""
    second, sixth = pokemon("second", hp=0, status="psn"), pokemon("sixth", nickname="Sixth")
    caller = player([None, second, None, None, None, sixth])
    text = command(caller)
    assert "2: Squirtle" in text and "6: Sixth (Squirtle)" in text
    assert "HP [----------] 0/" in text and "FAINTED" in text
    assert "POISONED" not in text
    assert next(line for line in text.splitlines() if "[LEAD]" in line).startswith("6:")
    roster = [build_battle_pokemon_from_model(mon) for mon in get_battle_party_with_fusion(caller)]
    choices = get_battle_switch_choices(caller, roster)
    assert set(choices) == {2, 6}
    assert choices[6][1].model_id == "owned:sixth"
    assert "Slot 6: Sixth" in command(caller, "6")
    assert command(caller, "1") == "That slot is empty."


@pytest.mark.parametrize("order", ["first", "normal"])
def test_fusion_free_slot_matches_battle_selector_and_order(order):
    """Fusion occupies a display gap without changing the companion's selector."""
    fused, companion = pokemon("form", "Pikachu", status="par", held="Light Ball"), pokemon("second")
    caller = player([None, companion], fused, order=order)
    # Stale character HP/status must not override the owning Pokemon's state.
    caller.db.hp, caller.db.status, caller.db.level = 0, "brn", 99
    text = command(caller)
    assert "Party Pokémon - 1/6 + Fusion | 2 able to battle" in text
    assert "1: Ash (Pikachu form)" in text and "[YOU / FUSION]" in text
    assert "2: Squirtle" in text
    assert "PARALYZED" in text and "Held: Light Ball" in text and "BURNED" not in text
    assert "Lv 99" not in text
    lead = next(line for line in text.splitlines() if "[LEAD]" in line)
    assert lead.startswith("1:" if order == "first" else "2:")
    roster = [build_battle_pokemon_from_model(mon) for mon in get_battle_party_with_fusion(caller)]
    choices = get_battle_switch_choices(caller, roster)
    assert choices[1][1].model_id == "owned:form" and choices[2][1].model_id == "owned:second"
    for selector in ("1", "fusion", "/moves fusion"):
        assert "active Fusion form" in command(caller, selector)


@pytest.mark.parametrize("order", ["first", "normal"])
def test_full_party_keeps_six_slots_and_named_fusion(order):
    """A seventh battle participant is selectable without inventing slot seven."""
    companions = [pokemon(str(slot), nickname=f"Pal {slot}") for slot in range(1, 7)]
    caller = player(companions, pokemon("form", "Pikachu"), order=order)
    text = command(caller)
    assert "6/6 + Fusion | 7 able to battle" in text
    assert "6: Pal 6" in text and "fusion: Ash (Pikachu form)" in text
    assert "7:" not in text
    lead = next(line for line in text.splitlines() if "[LEAD]" in line)
    assert lead.startswith("fusion:" if order == "first" else "1:")
    roster = [build_battle_pokemon_from_model(mon) for mon in get_battle_party_with_fusion(caller)]
    assert set(get_battle_switch_choices(caller, roster)) == {1, 2, 3, 4, 5, 6, "fusion"}
    assert "active Fusion form" in command(caller, "fusion")
    assert "Pal 6" in command(caller, "/moves 6")
    assert "active Fusion form" in command(caller, "/all")
    assert command(caller, "7") == "No Pokémon in that slot."


def test_nonparticipating_fusion_cannot_claim_lead_or_ready_count():
    """Turning Fusion participation off is reflected in the party overview."""
    caller = player([None, pokemon("second")], pokemon("form", "Pikachu"), order="first", participates=False)
    text = command(caller)
    assert "[YOU / FUSION] [NOT BATTLING]" in text
    assert "1 able to battle" in text
    assert next(line for line in text.splitlines() if "[LEAD]" in line).startswith("2:")


def test_fainted_fusion_is_skipped_in_lead_order():
    """A fainted form cannot be labelled as the opener even with Fusion first."""
    caller = player([None, pokemon("second")], pokemon("form", "Pikachu", hp=0), order="first")
    text = command(caller)
    assert "FAINTED" in text and "1 able to battle" in text
    assert next(line for line in text.splitlines() if "[LEAD]" in line).startswith("2:")


def test_fusion_in_existing_party_slot_does_not_move_to_earlier_gap():
    """Legacy colocated Fusion data retains the same selector used by battle."""
    fused = pokemon("form", "Pikachu")
    caller = player([None, pokemon("second"), None, None, None, fused], fused)
    text = command(caller)
    assert "6: Ash (Pikachu form)" in text
    assert "1: Ash" not in text
    assert "active Fusion form" in command(caller, "6")


def test_empty_and_all_fainted_parties_have_no_false_lead():
    """Empty parties remain explicit; no member is ready when everyone fainted."""
    assert command(player()) == "You have no Pokémon in your party."
    text = command(player([pokemon("first", hp=0), pokemon("second", hp=0)]))
    assert "0 able to battle" in text and "[LEAD]" not in text


@pytest.mark.parametrize("setting", ["ui_mode", "sheet_screen_reader"])
def test_screenreader_keeps_exact_information_without_health_bar_noise(setting):
    """Both existing accessibility preferences remove decorative bars/colours."""
    caller = player([pokemon("mon", "Bulbasaur")])
    if setting == "ui_mode":
        caller.db.ui_mode = "sr"
    else:
        caller.attributes = SimpleNamespace(get=lambda key, default=None: True)
    output = PartyView(caller).render()
    assert "[GRASS/POISON]" in output and "HP " in output
    assert "#" not in output and "|g" not in output


def test_fusion_summary_uses_battle_level_stats_and_moves():
    """Detailed summaries retain the form adapter's level, stats, HP and moves."""
    fused = pokemon("form", "Pikachu", level=20, hp=3, status="slp")
    caller = player([], fused)
    caller.db.total_exp = exp_for_level(10, "medium_fast")
    view = PartyView(caller)
    battle = build_battle_pokemon_from_model(get_battle_party_with_fusion(caller)[0])
    display = view.select("fusion").pokemon
    assert display.level == battle.level == 10
    assert get_max_hp(display) == battle.max_hp
    assert display.hp == 3 and display.status == "slp" and display.moves == fused.moves
    assert set(get_stats(display)) == {"hp", "attack", "defense", "special_attack", "special_defense", "speed"}


def test_legacy_form_is_inspectable_without_becoming_a_battle_lead():
    """Old character-only Fusion details remain visible and explicitly unavailable."""
    caller = player()
    caller.db.fusion_species, caller.db.fusion_id = "Pikachu", "missing"
    caller.db.level, caller.db.hp, caller.db.stats = 10, 3, {"hp": 30}
    text = command(caller)
    assert "Lv 10" in text and "3/30" in text and "[NOT BATTLING]" in text
    assert "0 able to battle" in text and "[LEAD]" not in text
    assert "active Fusion form" in command(caller, "fusion")


@pytest.mark.parametrize("fraction, color", [(1, "|g"), (0.5, "|y"), (0.2, "|r")])
def test_hp_bar_colours_follow_health_and_preserve_exact_numbers(fraction, color):
    """Full, half and critical health are recognisable without losing exact HP."""
    mon = pokemon("mon", level=50)
    mon.current_hp = int(get_max_hp(mon) * fraction)
    output = PartyView(player([mon])).render()
    assert f"HP {color}[" in output
    assert f" {mon.current_hp}/{get_max_hp(mon)} " in output


def test_view_matches_separately_loaded_fusion_models_without_mutating_storage():
    """Repeated ORM loads still identify one Fusion and keep all party gaps."""
    from copy import copy

    fused = pokemon("form", "Pikachu", hp=1, status="tox", held="Light Ball")
    caller = player([None, pokemon("second")], fused, order="first")
    caller.get_pokemon_by_id = lambda identifier: copy(fused) if identifier == fused.unique_id else None
    original_slots = caller.storage.get_party_slots()
    output = command(caller)
    assert output.count("[YOU / FUSION]") == 1
    assert next(line for line in output.splitlines() if "[LEAD]" in line).startswith("1:")
    assert "HP [#---------] 1/" in output and "BADLY POISONED" in output
    assert caller.storage.get_party_slots() == original_slots
    assert (fused.current_hp, fused.status, fused.held_item) == (1, "tox", "Light Ball")


def test_fusion_summary_keeps_its_declared_experience_curve():
    """A form with a non-default growth curve keeps the same progress as battle."""
    fused = pokemon("form", "Bulbasaur", level=10)
    fused.growth_rate = "slow"
    fused.total_exp = exp_for_level(10, "slow")
    caller = player([], fused)
    display = PartyView(caller).select("fusion").pokemon
    assert display.level == 10 and display.growth_rate == "slow"
    assert "(0% to next," in command(caller, "fusion")
