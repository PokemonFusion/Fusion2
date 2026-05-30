"""Diff and guarded apply helpers for syncing Alpha room spawn seed data."""

from __future__ import annotations

import ast
import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from .adapters import SpawnAdapterError, coerce_spawn_data_entries, normalize_band, normalize_frequency
from .preview import format_species_group


ALPHA_SEED_PATH = Path(__file__).resolve().parents[2] / "world" / "alpha_test_zone.ev"
COMPARE_FIELDS = ("weight", "min_level", "max_level", "frequency", "tiers")


class AlphaSpawnSyncError(ValueError):
    """Raised when Alpha spawn seed data cannot be parsed for diffing."""


@dataclass(frozen=True)
class AlphaLiveRoomMatch:
    room: Any | None
    error: str = ""


@dataclass(frozen=True)
class AlphaEntryFieldDiff:
    field_name: str
    live_value: Any
    seed_value: Any


@dataclass(frozen=True)
class AlphaEntryDiff:
    species_id: str
    field_diffs: tuple[AlphaEntryFieldDiff, ...]


@dataclass(frozen=True)
class AlphaRoomSpawnDiff:
    room_key: str
    live_dbref: str | None
    live_found: bool
    seed_found: bool
    live_entry_count: int
    seed_entry_count: int
    species_only_live: tuple[str, ...]
    species_only_seed: tuple[str, ...]
    entry_diffs: tuple[AlphaEntryDiff, ...]
    safe_to_update: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    live_room: Any | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class AlphaSpawnDiffReport:
    rooms: tuple[AlphaRoomSpawnDiff, ...]


@dataclass(frozen=True)
class AlphaRoomApplyResult:
    room_key: str
    live_dbref: str | None
    entry_count: int


@dataclass(frozen=True)
class AlphaSpawnApplyResult:
    before_report: AlphaSpawnDiffReport
    after_report: AlphaSpawnDiffReport | None
    updated_rooms: tuple[AlphaRoomApplyResult, ...]
    refused_rooms: tuple[AlphaRoomSpawnDiff, ...]

    @property
    def applied(self) -> bool:
        return bool(self.updated_rooms) and not self.refused_rooms


def parse_alpha_seed_charts(text: str) -> dict[str, list[dict[str, Any]]]:
    charts: dict[str, list[dict[str, Any]]] = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        if "/hunt_chart = " not in line:
            continue
        try:
            lhs, raw_chart = line.split(" = ", 1)
        except ValueError as exc:
            raise AlphaSpawnSyncError(f"Invalid hunt_chart line {line_number}.") from exc
        room_key = lhs.removeprefix("@set ").removesuffix("/hunt_chart").strip()
        if not room_key:
            raise AlphaSpawnSyncError(f"Missing room key on hunt_chart line {line_number}.")
        try:
            chart = ast.literal_eval(raw_chart)
        except (SyntaxError, ValueError) as exc:
            raise AlphaSpawnSyncError(f"Invalid hunt_chart data for {room_key!r}.") from exc
        try:
            charts[room_key] = coerce_spawn_data_entries(chart)
        except SpawnAdapterError as exc:
            raise AlphaSpawnSyncError(f"Invalid hunt_chart entries for {room_key!r}: {exc}") from exc
    return charts


def load_alpha_seed_charts(path: Path | str = ALPHA_SEED_PATH) -> dict[str, list[dict[str, Any]]]:
    path = Path(path)
    return parse_alpha_seed_charts(path.read_text(encoding="utf-8"))


def compare_alpha_spawn_data(
    *,
    seed_charts: dict[str, list[dict[str, Any]]] | None = None,
    live_room_lookup: Callable[[str], Any] | None = None,
    expected_room_keys: Iterable[str] | None = None,
) -> AlphaSpawnDiffReport:
    seed_charts = seed_charts if seed_charts is not None else load_alpha_seed_charts()
    room_keys = tuple(expected_room_keys or seed_charts.keys())
    room_diffs = []

    for room_key in room_keys:
        seed_entries = seed_charts.get(room_key)
        seed_found = seed_entries is not None
        live_match = _coerce_live_match(live_room_lookup(room_key) if live_room_lookup else None)
        live_room = live_match.room
        live_found = live_room is not None
        errors = [live_match.error] if live_match.error else []

        live_entries: list[dict[str, Any]] = []
        if live_room is not None:
            try:
                live_entries = coerce_spawn_data_entries(getattr(getattr(live_room, "db", None), "hunt_chart", None))
            except SpawnAdapterError as exc:
                errors.append(f"Live hunt_chart error: {exc}")
        if not seed_found:
            errors.append("Seed chart missing.")

        room_diffs.append(
            _compare_room_entries(
                room_key=room_key,
                live_room=live_room,
                live_entries=live_entries,
                seed_entries=seed_entries or [],
                seed_found=seed_found,
                errors=tuple(errors),
            )
        )

    return AlphaSpawnDiffReport(rooms=tuple(room_diffs))


def apply_alpha_spawn_seed_updates(
    *,
    seed_charts: dict[str, list[dict[str, Any]]] | None = None,
    live_room_lookup: Callable[[str], Any] | None = None,
    expected_room_keys: Iterable[str] | None = None,
) -> AlphaSpawnApplyResult:
    seed_charts = seed_charts if seed_charts is not None else load_alpha_seed_charts()
    before_report = compare_alpha_spawn_data(
        seed_charts=seed_charts,
        live_room_lookup=live_room_lookup,
        expected_room_keys=expected_room_keys,
    )
    refused_rooms = tuple(room for room in before_report.rooms if not room.safe_to_update)
    if refused_rooms:
        return AlphaSpawnApplyResult(
            before_report=before_report,
            after_report=None,
            updated_rooms=(),
            refused_rooms=refused_rooms,
        )

    updated_rooms = []
    for room_diff in before_report.rooms:
        live_room = room_diff.live_room
        if live_room is None:
            refused_rooms = (room_diff,)
            return AlphaSpawnApplyResult(
                before_report=before_report,
                after_report=None,
                updated_rooms=(),
                refused_rooms=refused_rooms,
            )
        seed_entries = copy.deepcopy(seed_charts[room_diff.room_key])
        getattr(live_room, "db").hunt_chart = seed_entries
        updated_rooms.append(
            AlphaRoomApplyResult(
                room_key=room_diff.room_key,
                live_dbref=room_diff.live_dbref,
                entry_count=len(seed_entries),
            )
        )

    after_report = compare_alpha_spawn_data(
        seed_charts=seed_charts,
        live_room_lookup=live_room_lookup,
        expected_room_keys=expected_room_keys,
    )
    return AlphaSpawnApplyResult(
        before_report=before_report,
        after_report=after_report,
        updated_rooms=tuple(updated_rooms),
        refused_rooms=(),
    )


def format_alpha_spawn_diff(report: AlphaSpawnDiffReport, *, limit: int = 12) -> str:
    lines = ["Alpha Spawn Data Diff", "Read-only: no room attrs were modified."]
    if not report.rooms:
        lines.append("No Alpha seed hunt_chart data found.")
        return "\n".join(lines)

    for room in report.rooms:
        dbref = f"#{room.live_dbref}" if room.live_dbref else "-"
        status = "safe to update" if room.safe_to_update else "review needed"
        lines.extend(
            [
                "",
                f"{room.room_key} ({dbref}) - {status}",
                f"  Live room found: {'yes' if room.live_found else 'no'}",
                f"  Seed chart found: {'yes' if room.seed_found else 'no'}",
                f"  Entries: live {room.live_entry_count} / seed {room.seed_entry_count}",
                f"  Species only live: {format_species_group(room.species_only_live, limit)}",
                f"  Species only seed: {format_species_group(room.species_only_seed, limit)}",
            ]
        )
        if room.errors:
            lines.append("  Errors:")
            lines.extend(f"    {error}" for error in room.errors)
        if room.entry_diffs:
            lines.append("  Field differences:")
            for entry_diff in room.entry_diffs[:limit]:
                lines.append(f"    {entry_diff.species_id}: {_format_field_diffs(entry_diff.field_diffs)}")
            remaining = len(room.entry_diffs) - limit
            if remaining > 0:
                lines.append(f"    ... (+{remaining} more)")
        elif room.live_found and room.seed_found and not room.errors:
            lines.append("  Field differences: none")

    return "\n".join(lines)


def format_alpha_spawn_apply(result: AlphaSpawnApplyResult, *, limit: int = 12) -> str:
    lines = [
        "Alpha Spawn Apply",
        "WARNING: this command writes live Alpha room hunt_chart attrs.",
    ]

    if result.refused_rooms:
        lines.extend(
            [
                "Apply refused: one or more Alpha rooms are not safe to update.",
                "Updated rooms: 0",
                "Refused rooms:",
            ]
        )
        for room in result.refused_rooms:
            dbref = f"#{room.live_dbref}" if room.live_dbref else "-"
            lines.append(f"  {room.room_key} ({dbref})")
            for reason in _refusal_reasons(room):
                lines.append(f"    {reason}")
        lines.append("+hunt behavior itself was not changed.")
        return "\n".join(lines)

    lines.append("All target rooms were safe to update.")
    lines.append(f"Updated rooms: {len(result.updated_rooms)}")
    for update in result.updated_rooms[:limit]:
        dbref = f"#{update.live_dbref}" if update.live_dbref else "-"
        lines.append(f"  {update.room_key} ({dbref}): wrote {update.entry_count} entries")
    remaining = len(result.updated_rooms) - limit
    if remaining > 0:
        lines.append(f"  ... (+{remaining} more)")
    if result.after_report is not None:
        lines.append(f"Post-apply diff: {'clean' if alpha_spawn_diff_is_clean(result.after_report) else 'review needed'}")
    lines.append("+hunt behavior itself was not changed.")
    return "\n".join(lines)


def alpha_spawn_diff_is_clean(report: AlphaSpawnDiffReport) -> bool:
    return bool(report.rooms) and all(
        room.live_found
        and room.seed_found
        and not room.errors
        and not room.species_only_live
        and not room.species_only_seed
        and not room.entry_diffs
        for room in report.rooms
    )


def _coerce_live_match(value: Any) -> AlphaLiveRoomMatch:
    if isinstance(value, AlphaLiveRoomMatch):
        return value
    return AlphaLiveRoomMatch(room=value)


def _compare_room_entries(
    *,
    room_key: str,
    live_room: Any | None,
    live_entries: list[dict[str, Any]],
    seed_entries: list[dict[str, Any]],
    seed_found: bool,
    errors: tuple[str, ...],
) -> AlphaRoomSpawnDiff:
    live_species = [_species_id(entry) for entry in live_entries if _species_id(entry)]
    seed_species = [_species_id(entry) for entry in seed_entries if _species_id(entry)]
    species_only_live = tuple(species for species in live_species if species not in set(seed_species))
    species_only_seed = tuple(species for species in seed_species if species not in set(live_species))
    species_lists_match = live_species == seed_species
    errors = list(errors)
    if live_species and seed_species and set(live_species) == set(seed_species) and not species_lists_match:
        errors.append("Species order differs between live and seed charts.")
    entry_diffs = _entry_diffs(live_entries, seed_entries) if species_lists_match else ()

    return AlphaRoomSpawnDiff(
        room_key=room_key,
        live_dbref=_room_dbref(live_room),
        live_found=live_room is not None,
        seed_found=seed_found,
        live_entry_count=len(live_entries),
        seed_entry_count=len(seed_entries),
        species_only_live=species_only_live,
        species_only_seed=species_only_seed,
        entry_diffs=entry_diffs,
        safe_to_update=live_room is not None and seed_found and species_lists_match and not errors,
        errors=tuple(errors),
        live_room=live_room,
    )


def _entry_diffs(
    live_entries: list[dict[str, Any]],
    seed_entries: list[dict[str, Any]],
) -> tuple[AlphaEntryDiff, ...]:
    results = []
    for live_entry, seed_entry in zip(live_entries, seed_entries):
        field_diffs = []
        for field_name in COMPARE_FIELDS:
            live_value = _normalized_field_value(live_entry, field_name)
            seed_value = _normalized_field_value(seed_entry, field_name)
            if live_value != seed_value:
                field_diffs.append(
                    AlphaEntryFieldDiff(
                        field_name=field_name,
                        live_value=live_value,
                        seed_value=seed_value,
                    )
                )
        if field_diffs:
            results.append(
                AlphaEntryDiff(
                    species_id=_species_id(seed_entry) or _species_id(live_entry),
                    field_diffs=tuple(field_diffs),
                )
            )
    return tuple(results)


def _normalized_field_value(entry: dict[str, Any], field_name: str):
    if field_name == "frequency":
        value = entry.get("frequency", entry.get("rarity"))
        if value is None or str(value).strip() == "":
            return None
        try:
            return normalize_frequency(value)
        except SpawnAdapterError:
            return str(value).strip()
    if field_name == "tiers":
        value = entry.get("tiers", entry.get("tier", entry.get("bands", entry.get("band"))))
        if value is None or value == "":
            return None
        if isinstance(value, str):
            values = [value]
        elif isinstance(value, Iterable):
            values = list(value)
        else:
            values = [value]
        normalized = []
        for item in values:
            try:
                normalized.append(normalize_band(item))
            except SpawnAdapterError:
                normalized.append(item)
        return normalized
    return _coerce_int(entry.get(field_name))


def _species_id(entry: dict[str, Any]) -> str:
    value = entry.get("species") or entry.get("name")
    return str(value).strip() if value is not None else ""


def _room_dbref(room: Any | None) -> str | None:
    if room is None:
        return None
    value = getattr(room, "id", None)
    return str(value) if value is not None else None


def _coerce_int(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def _format_field_diffs(field_diffs: tuple[AlphaEntryFieldDiff, ...]) -> str:
    return "; ".join(
        f"{diff.field_name} live {_display_value(diff.live_value)} -> seed {_display_value(diff.seed_value)}"
        for diff in field_diffs
    )


def _display_value(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "-"
    return str(value)


def _refusal_reasons(room: AlphaRoomSpawnDiff) -> list[str]:
    reasons = list(room.errors)
    if not room.live_found:
        reasons.append("Live room missing.")
    if not room.seed_found:
        reasons.append("Seed chart missing.")
    if room.species_only_live:
        reasons.append(f"Species only live: {format_species_group(room.species_only_live)}")
    if room.species_only_seed:
        reasons.append(f"Species only seed: {format_species_group(room.species_only_seed)}")
    if not reasons:
        reasons.append("Room was not marked safe to update.")
    return reasons
