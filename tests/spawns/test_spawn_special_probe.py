import copy
import importlib
import inspect
import sys
import types

import pytest

from pokemon.spawns.profile_data import SpawnProfileDataError
from pokemon.spawns.schema import SpawnChart, SpawnEntry
from pokemon.spawns.special_probe import (
    SPECIAL_PROBE_ROOM_SOURCE,
    build_special_probe_state,
    format_special_spawn_probe,
    parse_special_probe_args,
    run_profile_special_spawn_probe,
    run_special_spawn_probe,
)
from pokemon.spawns.specials import (
    SPECIAL_COOLDOWN_SECONDS,
    SPECIAL_MIN_DENOMINATOR,
    SpecialSpawnState,
)


class FixedSpecialProbeRng:
    def __init__(self, randrange_value=0, level=45):
        self.randrange_value = randrange_value
        self.level = level

    def randrange(self, stop):
        return self.randrange_value

    def choice(self, values):
        return list(values)[0]

    def randint(self, low, high):
        return self.level


def chart_with_specials(*species_ids):
    return SpawnChart(
        area_key="special-room",
        entries=[SpawnEntry(species_id=species_id, frequency="special", band=4) for species_id in species_ids],
    )


def ready_state():
    return SpecialSpawnState(
        current_time=SPECIAL_COOLDOWN_SECONDS,
        last_special_at=0,
        current_tick=40,
        last_special_tick=0,
    )


def test_room_backed_probe_with_special_entries():
    result = run_special_spawn_probe(
        chart_with_specials("144"),
        source=SPECIAL_PROBE_ROOM_SOURCE,
        state=ready_state(),
        rng=FixedSpecialProbeRng(randrange_value=0, level=52),
    )
    text = format_special_spawn_probe(result)

    assert result.source == "room"
    assert result.special_entry_count == 1
    assert result.eligible_species == ("144",)
    assert result.roll_passed is True
    assert result.spawn_result.species_id == "144"
    assert "Source: room" in text
    assert "Roll denominator: 1/1000 (0.10%)" in text
    assert "Selected special: 144 level 52" in text


def test_profile_backed_probe_with_special_entries():
    result = run_profile_special_spawn_probe(
        "special_test",
        state=ready_state(),
        rng=FixedSpecialProbeRng(randrange_value=0),
    )

    assert result.source == "profile"
    assert result.area_key == "special_test"
    assert result.eligible_species == ("144",)
    assert result.spawn_result.species_id == "144"


def test_profile_backed_unknown_area_handled():
    with pytest.raises(SpawnProfileDataError, match="Unknown area profile"):
        run_profile_special_spawn_probe(
            "missing_area",
            state=ready_state(),
            rng=FixedSpecialProbeRng(randrange_value=0),
        )


def test_no_special_entries_reported_cleanly():
    result = run_profile_special_spawn_probe(
        "route_1",
        state=ready_state(),
        rng=FixedSpecialProbeRng(randrange_value=0),
    )
    text = format_special_spawn_probe(result)

    assert result.special_entry_count == 0
    assert result.spawn_result is None
    assert "Eligible specials: -" in text
    assert "Simulated roll: blocked (no eligible band 4 special entries)" in text
    assert "No special would spawn." in text


def test_cooldown_remaining_blocks_roll():
    state = build_special_probe_state(["40", "0", "100"])
    result = run_special_spawn_probe(
        chart_with_specials("144"),
        source="room",
        state=state,
        rng=FixedSpecialProbeRng(randrange_value=0),
    )

    assert result.cooldown_remaining == SPECIAL_COOLDOWN_SECONDS - 100
    assert result.roll_passed is False
    assert result.blocked_reason == "cooldown active"


def test_pity_denominator_shown_and_calculated():
    state = build_special_probe_state(["1", "0", str(SPECIAL_COOLDOWN_SECONDS)])
    result = run_special_spawn_probe(
        chart_with_specials("144"),
        source="room",
        state=state,
        rng=FixedSpecialProbeRng(randrange_value=1),
    )
    text = format_special_spawn_probe(result)

    assert result.pity_ticks == 1
    assert result.roll_denominator == 9775
    assert "Roll denominator: 1/9775 (0.01%)" in text


def test_passed_roll_selects_special_species():
    result = run_special_spawn_probe(
        chart_with_specials("144", "145"),
        source="room",
        state=ready_state(),
        rng=FixedSpecialProbeRng(randrange_value=0, level=60),
    )

    assert result.roll_passed is True
    assert result.spawn_result.species_id == "144"
    assert result.spawn_result.level == 60


def test_failed_roll_reports_no_special_spawn():
    result = run_special_spawn_probe(
        chart_with_specials("144"),
        source="room",
        state=ready_state(),
        rng=FixedSpecialProbeRng(randrange_value=1),
    )
    text = format_special_spawn_probe(result)

    assert result.roll_passed is False
    assert result.spawn_result is None
    assert "Simulated roll: failed" in text
    assert "No special would spawn." in text


def test_bad_numeric_input_handled():
    with pytest.raises(ValueError, match="current_tick must be a non-negative integer"):
        parse_special_probe_args("room many")
    with pytest.raises(ValueError, match="last_special_tick must be a non-negative integer"):
        parse_special_probe_args("room 1 -1")
    with pytest.raises(ValueError, match="seconds_since_last_special must be a non-negative integer"):
        parse_special_probe_args("profile special_test 1 0 never")


def test_invalid_source_shows_usage():
    with pytest.raises(ValueError, match="Usage: @spawnspecialprobe"):
        parse_special_probe_args("wild")


def test_large_species_list_truncates():
    species_ids = tuple(f"{index:03d}" for index in range(1, 16))
    result = run_special_spawn_probe(
        chart_with_specials(*species_ids),
        source="room",
        state=ready_state(),
        rng=FixedSpecialProbeRng(randrange_value=1),
    )
    text = format_special_spawn_probe(result, group_limit=3)

    assert "Eligible specials: 001, 002, 003, ... (+12 more)" in text


def test_probe_does_not_mutate_special_spawn_state():
    state = ready_state()
    original = copy.deepcopy(state)

    run_special_spawn_probe(
        chart_with_specials("144"),
        source="room",
        state=state,
        rng=FixedSpecialProbeRng(randrange_value=0),
    )

    assert state == original


def test_default_mock_state_means_cooldown_passed_with_zero_pity():
    options = parse_special_probe_args("room")

    assert options.state.current_time == SPECIAL_COOLDOWN_SECONDS
    assert options.state.last_special_at == 0
    assert options.state.current_tick == 0
    assert options.state.last_special_tick == 0


def test_probe_module_does_not_import_battle_or_pokemon_creation_paths():
    import pokemon.spawns.special_probe as special_probe

    source = inspect.getsource(special_probe)

    assert "BattleSession" not in source
    assert "EncounterPokemon" not in source
    assert "OwnedPokemon" not in source


def test_command_profile_unknown_area_has_friendly_error(monkeypatch):
    cmd_mod = import_spawnspecialprobe_command(monkeypatch)

    class Caller:
        def __init__(self):
            self.location = object()
            self.messages = []

        def msg(self, text):
            self.messages.append(text)

    cmd = cmd_mod.CmdSpawnSpecialProbe()
    cmd.caller = Caller()
    cmd.args = "profile missing_area 40 0 86400"

    cmd.func()

    assert cmd.caller.messages == ["Special spawn probe error: Unknown area profile: 'missing_area'."]


def test_command_room_missing_location_has_friendly_error(monkeypatch):
    cmd_mod = import_spawnspecialprobe_command(monkeypatch)

    class Caller:
        def __init__(self):
            self.location = None
            self.messages = []

        def msg(self, text):
            self.messages.append(text)

    cmd = cmd_mod.CmdSpawnSpecialProbe()
    cmd.caller = Caller()
    cmd.args = "room"

    cmd.func()

    assert cmd.caller.messages == ["You must be in a room to probe room-backed special spawns."]


def test_min_denominator_used_at_pity_cap():
    result = run_special_spawn_probe(
        chart_with_specials("144"),
        source="room",
        state=ready_state(),
        rng=FixedSpecialProbeRng(randrange_value=1),
    )

    assert result.roll_denominator == SPECIAL_MIN_DENOMINATOR


def import_spawnspecialprobe_command(monkeypatch):
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)
    sys.modules.pop("commands.admin.cmd_spawnspecialprobe", None)
    return importlib.import_module("commands.admin.cmd_spawnspecialprobe")
