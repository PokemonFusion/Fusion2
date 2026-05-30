from __future__ import annotations

import pprint
from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from evennia import Command as _EvenniaCommand
from evennia import search_object as _evennia_search_object

from pokemon.battle.battleinstance import BattleSession
from pokemon.battle.handler import battle_handler
from pokemon.battle.interface import display_battle_interface, get_battle_ui_style, get_battle_ui_width
from pokemon.battle.storage import BattleDataWrapper
from pokemon.services.encounters import delete_encounter_by_ref
from utils.battle_display import render_move_gui
from utils.locks import clear_battle_lock

try:  # pragma: no cover - optional in lightweight command tests
    from evennia.utils.evmenu import get_input
except Exception:  # pragma: no cover
    get_input = None

if _EvenniaCommand is None:  # pragma: no cover - direct Django-shell imports
    from evennia.commands.command import Command
else:
    Command = _EvenniaCommand

if _evennia_search_object is None:  # pragma: no cover - direct Django-shell imports
    from evennia.utils.search import search_object
else:
    search_object = _evennia_search_object


BATTLE_STORAGE_PARTS = (
    "data",
    "state",
    "logic",
    "trainers",
    "temp_pokemon_ids",
    "meta",
    "field",
    "active",
    "last_action",
    "debug",
)


@dataclass
class BattleCleanupCandidate:
    """Battle record that can be cleaned by the admin cleanup command."""

    battle_id: int
    room: Any
    inst: Any = None
    sources: set[str] = dc_field(default_factory=set)
    stored_parts: List[str] = dc_field(default_factory=list)
    trainer_refs: List[Any] = dc_field(default_factory=list)
    created_at: datetime | None = None
    latest_part_at: datetime | None = None

    @property
    def is_live(self) -> bool:
        return self.inst is not None

    @property
    def status(self) -> str:
        return "LIVE" if self.is_live else "STALE"


def _resolve_battle_context(argument: str):
    """Return the battle instance, room and id for ``argument``."""

    arg = (argument or "").strip()
    inst = None
    room = None
    bid = None
    target = None

    if not arg:
        return inst, room, bid, target

    if arg.isdigit():
        bid = int(arg)
        inst = battle_handler.instances.get(bid)
        if inst:
            room = inst.room
    else:
        targets = search_object(arg)
        if targets:
            target = targets[0]
            inst = getattr(getattr(target, "ndb", None), "battle_instance", None)
            if inst:
                bid = inst.battle_id
                room = inst.room
            else:
                bid = getattr(getattr(target, "db", None), "battle_id", None)
                room = getattr(target, "location", None)

    return inst, room, bid, target


def _battle_room_key(room) -> tuple[str, Any]:
    """Return a stable dedupe key for a room-like object."""

    ident = getattr(room, "id", None)
    if ident is not None:
        return ("id", ident)
    return ("obj", id(room))


def _append_room_unique(rooms: List[Any], seen: set[tuple[str, Any]], room) -> None:
    """Append ``room`` if it has not already been collected."""

    if not room:
        return
    key = _battle_room_key(room)
    if key in seen:
        return
    seen.add(key)
    rooms.append(room)


def _handler_server_config():
    """Return the battle handler module's ServerConfig wrapper if available."""

    try:
        from pokemon.battle import handler as handler_mod
    except Exception:
        return None
    return getattr(handler_mod, "ServerConfig", None)


def _active_battle_room_mapping() -> Dict[int, Any]:
    """Return persisted battle id -> room id mapping from ServerConfig."""

    server_config = _handler_server_config()
    conf = getattr(getattr(server_config, "objects", None), "conf", None)
    if not callable(conf):
        return {}
    try:
        raw = conf("active_battle_rooms", default={}) or {}
    except Exception:
        return {}
    mapping: Dict[int, Any] = {}
    if isinstance(raw, dict):
        for battle_id, room_id in raw.items():
            try:
                mapping[int(battle_id)] = room_id
            except (TypeError, ValueError):
                continue
    return mapping


def _remove_active_battle_room(battle_id: int) -> None:
    """Remove ``battle_id`` from the persisted active-battle room map."""

    server_config = _handler_server_config()
    conf = getattr(getattr(server_config, "objects", None), "conf", None)
    if not callable(conf):
        return
    try:
        raw = conf("active_battle_rooms", default={}) or {}
    except Exception:
        return
    if not isinstance(raw, dict):
        return
    updated = {}
    removed = False
    for key, value in raw.items():
        try:
            key_int = int(key)
        except (TypeError, ValueError):
            updated[key] = value
            continue
        if key_int == battle_id:
            removed = True
            continue
        updated[key] = value
    if not removed:
        return
    if updated:
        conf(key="active_battle_rooms", value=updated)
    else:
        conf(key="active_battle_rooms", delete=True)


def _search_dbref(dbref: Any):
    """Resolve a dbref/id into an Evennia object when possible."""

    if dbref is None:
        return None
    text = str(dbref).strip()
    if not text:
        return None
    query = text if text.startswith("#") else f"#{text}"
    try:
        matches = search_object(query)
    except Exception:
        return None
    return matches[0] if matches else None


def _rooms_with_battle_records(extra_room=None) -> List[Any]:
    """Collect rooms that may hold active or stale battle records."""

    rooms: List[Any] = []
    seen: set[tuple[str, Any]] = set()
    _append_room_unique(rooms, seen, extra_room)

    for inst in list(getattr(battle_handler, "instances", {}).values()):
        _append_room_unique(rooms, seen, getattr(inst, "room", None))

    for room_id in _active_battle_room_mapping().values():
        _append_room_unique(rooms, seen, _search_dbref(room_id))

    try:
        from evennia.objects.models import ObjectDB

        for room in ObjectDB.objects.filter(db_attributes__db_key="battles").distinct():
            _append_room_unique(rooms, seen, room)
    except Exception:
        pass

    return rooms


def _stored_battle_ids(room) -> List[int]:
    """Return battle ids listed on a room's persistent battle index."""

    raw = getattr(getattr(room, "db", None), "battles", None) or []
    ids: List[int] = []
    if isinstance(raw, (str, bytes)):
        values = [raw]
    else:
        try:
            values = list(raw)
        except TypeError:
            values = [raw]
    for value in values:
        try:
            battle_id = int(value)
        except (TypeError, ValueError):
            continue
        if battle_id not in ids:
            ids.append(battle_id)
    return ids


def _stored_parts(room, battle_id: int) -> List[str]:
    """Return stored data parts currently present for ``battle_id``."""

    storage = BattleDataWrapper(room, battle_id)
    parts: List[str] = []
    for part in BATTLE_STORAGE_PARTS:
        if storage.get(part) is not None:
            parts.append(part)
    return parts


def _battle_record_times(room, battle_id: int) -> tuple[datetime | None, datetime | None]:
    """Return first/latest stored attribute creation times for a battle."""

    try:
        from evennia.typeclasses.models import Attribute
    except Exception:
        return None, None

    keys = [f"battle_{battle_id}_{part}" for part in BATTLE_STORAGE_PARTS]
    try:
        dates = [
            attr.db_date_created
            for attr in Attribute.objects.filter(objectdb=room, db_key__in=keys)
            if getattr(attr, "db_date_created", None) is not None
        ]
    except Exception:
        return None, None
    if not dates:
        return None, None
    return min(dates), max(dates)


def _iter_trainer_refs(raw_trainers) -> List[Any]:
    """Flatten stored trainer ids from the known battle storage formats."""

    refs: List[Any] = []

    def add(value) -> None:
        if value in (None, ""):
            return
        if value not in refs:
            refs.append(value)

    if hasattr(raw_trainers, "values"):
        for value in raw_trainers.values():
            if isinstance(value, (str, bytes)):
                add(value)
            else:
                try:
                    values = list(value)
                except TypeError:
                    values = [value]
                for item in values:
                    add(item)
    elif isinstance(raw_trainers, (str, bytes)):
        add(raw_trainers)
    else:
        try:
            values = list(raw_trainers)
        except TypeError:
            values = [raw_trainers]
        for value in values:
            if isinstance(value, (str, bytes)):
                add(value)
            else:
                try:
                    nested_values = list(value)
                except TypeError:
                    nested_values = [value]
                for item in nested_values:
                    add(item)
    return refs


def _candidate_trainer_refs(room, battle_id: int, inst=None) -> List[Any]:
    """Return trainer refs for live or stored battle cleanup."""

    refs: List[Any] = []
    if inst:
        for trainer in list(getattr(inst, "teamA", []) or []) + list(getattr(inst, "teamB", []) or []):
            if trainer and trainer not in refs:
                refs.append(trainer)
    stored = BattleDataWrapper(room, battle_id).get("trainers")
    for ref in _iter_trainer_refs(stored):
        if ref not in refs:
            refs.append(ref)
    return refs


def _merge_cleanup_candidate(
    candidates: Dict[tuple[int, tuple[str, Any]], BattleCleanupCandidate],
    battle_id: int,
    room,
    *,
    inst=None,
    source: str,
) -> None:
    """Merge one source into a battle cleanup candidate."""

    if not room:
        return
    key = (battle_id, _battle_room_key(room))
    candidate = candidates.get(key)
    if candidate is None:
        candidate = BattleCleanupCandidate(battle_id=battle_id, room=room)
        candidates[key] = candidate
    if inst is not None:
        candidate.inst = inst
    candidate.sources.add(source)
    candidate.stored_parts = _stored_parts(room, battle_id)
    candidate.trainer_refs = _candidate_trainer_refs(room, battle_id, candidate.inst)
    candidate.created_at, candidate.latest_part_at = _battle_record_times(room, battle_id)


def _collect_battle_cleanup_candidates(extra_room=None) -> List[BattleCleanupCandidate]:
    """Return live and stored battle cleanup candidates."""

    candidates: Dict[tuple[int, tuple[str, Any]], BattleCleanupCandidate] = {}
    active_mapping = _active_battle_room_mapping()

    for battle_id, inst in getattr(battle_handler, "instances", {}).items():
        try:
            bid = int(battle_id)
        except (TypeError, ValueError):
            continue
        _merge_cleanup_candidate(
            candidates,
            bid,
            getattr(inst, "room", None),
            inst=inst,
            source="handler",
        )

    for battle_id, room_id in active_mapping.items():
        room = _search_dbref(room_id)
        _merge_cleanup_candidate(candidates, battle_id, room, source="server-config")

    for room in _rooms_with_battle_records(extra_room):
        for battle_id in _stored_battle_ids(room):
            _merge_cleanup_candidate(candidates, battle_id, room, source="room")

    return sorted(
        candidates.values(),
        key=lambda c: (
            0 if c.is_live else 1,
            str(getattr(c.room, "key", "")),
            c.battle_id,
        ),
    )


def _format_trainer_refs(refs: List[Any]) -> str:
    """Return a compact trainer-ref display for cleanup output."""

    labels = []
    for ref in refs:
        if hasattr(ref, "key") or hasattr(ref, "name"):
            labels.append(_summarize_obj(ref) or str(ref))
        else:
            labels.append(f"#{ref}" if str(ref).isdigit() else str(ref))
    return ", ".join(labels) if labels else "-"


def _as_utc(dt: datetime) -> datetime:
    """Return an aware UTC datetime."""

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _format_age(dt: datetime | None, *, now: datetime | None = None) -> str:
    """Return a compact age string for ``dt``."""

    if dt is None:
        return "unknown"
    base = _as_utc(dt)
    current = _as_utc(now or datetime.now(timezone.utc))
    seconds = max(0, int((current - base).total_seconds()))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m"
    return "<1m"


def _format_timestamp(dt: datetime | None) -> str:
    """Return a concise UTC timestamp or unknown."""

    if dt is None:
        return "unknown"
    return _as_utc(dt).strftime("%Y-%m-%d %H:%M UTC")


def _format_candidate_age(candidate: BattleCleanupCandidate) -> str:
    """Return age details for a cleanup candidate."""

    return (
        f"age={_format_age(candidate.created_at)}; "
        f"created={_format_timestamp(candidate.created_at)}"
    )


def _format_cleanup_candidates(candidates: List[BattleCleanupCandidate]) -> str:
    """Return a numbered candidate list for staff."""

    if not candidates:
        return "No battle cleanup candidates found."
    lines = ["Battle cleanup candidates:"]
    for index, candidate in enumerate(candidates, start=1):
        parts = ", ".join(candidate.stored_parts) if candidate.stored_parts else "-"
        sources = ", ".join(sorted(candidate.sources)) if candidate.sources else "-"
        lines.append(
            (
                f"{index}. #{candidate.battle_id} [{candidate.status}] "
                f"{_summarize_obj(candidate.room)}; {_format_candidate_age(candidate)}; "
                f"parts={parts}; "
                f"trainers={_format_trainer_refs(candidate.trainer_refs)}; "
                f"sources={sources}"
            )
        )
    lines.append("Choose a number, type 'stale' to clean all stale records, or '0' to cancel.")
    return "\n".join(lines)


def _resolve_cleanup_selection(selection: str, candidates: List[BattleCleanupCandidate]):
    """Resolve a menu number or battle id to a cleanup candidate."""

    text = str(selection or "").strip()
    if not text:
        return None
    try:
        value = int(text.lstrip("#"))
    except ValueError:
        return None
    if 1 <= value <= len(candidates):
        return candidates[value - 1]
    matches = [candidate for candidate in candidates if candidate.battle_id == value]
    if len(matches) == 1:
        return matches[0]
    return None


def _clear_trainer_battle_state(trainer_or_ref, battle_id: int) -> bool:
    """Clear battle state from one trainer object if it matches ``battle_id``."""

    trainer = trainer_or_ref
    if not (hasattr(trainer, "db") or hasattr(trainer, "ndb")):
        trainer = _search_dbref(trainer_or_ref)
    if not trainer:
        return False

    cleared = False
    ndb = getattr(trainer, "ndb", None)
    inst = getattr(ndb, "battle_instance", None) if ndb is not None else None
    if inst is not None and getattr(inst, "battle_id", battle_id) == battle_id:
        try:
            delattr(ndb, "battle_instance")
            cleared = True
        except Exception:
            pass

    db = getattr(trainer, "db", None)
    if db is not None and getattr(db, "battle_id", None) == battle_id:
        try:
            clear_battle_lock(trainer)
        except Exception:
            pass
        try:
            delattr(db, "battle_id")
            cleared = True
        except Exception:
            pass
    return cleared


def _remove_room_battle_index(room, battle_id: int) -> bool:
    """Remove ``battle_id`` from ``room.db.battles``."""

    db = getattr(room, "db", None)
    if db is None:
        return False
    battles = _stored_battle_ids(room)
    if battle_id not in battles:
        return False
    updated = [bid for bid in battles if bid != battle_id]
    try:
        if updated:
            db.battles = updated
        else:
            delattr(db, "battles")
    except Exception:
        return False
    return True


def _remove_room_ndb_instance(room, battle_id: int) -> bool:
    """Remove a battle from the room's non-persistent instance map."""

    ndb = getattr(room, "ndb", None)
    battle_instances = getattr(ndb, "battle_instances", None) if ndb is not None else None
    if not isinstance(battle_instances, dict) or battle_id not in battle_instances:
        return False
    battle_instances.pop(battle_id, None)
    if not battle_instances:
        try:
            delattr(ndb, "battle_instances")
        except Exception:
            pass
    return True


def _purge_stored_battle(candidate: BattleCleanupCandidate) -> Dict[str, Any]:
    """Hard-delete a stored battle record without restoring it."""

    battle_id = candidate.battle_id
    room = candidate.room
    storage = BattleDataWrapper(room, battle_id)
    removed_parts: List[str] = []

    for temp_ref in storage.get("temp_pokemon_ids") or []:
        try:
            delete_encounter_by_ref(temp_ref)
        except Exception:
            pass

    for part in BATTLE_STORAGE_PARTS:
        if storage.get(part) is not None:
            storage.delete(part)
            removed_parts.append(part)

    handler_instances = getattr(battle_handler, "instances", {})
    inst = handler_instances.get(battle_id)
    if inst is not None:
        try:
            battle_handler.unregister(inst)
        except Exception:
            handler_instances.pop(battle_id, None)
    else:
        handler_instances.pop(battle_id, None)

    removed_room_index = _remove_room_battle_index(room, battle_id)
    removed_room_ndb = _remove_room_ndb_instance(room, battle_id)
    _remove_active_battle_room(battle_id)
    cleared_trainers = [
        ref for ref in candidate.trainer_refs if _clear_trainer_battle_state(ref, battle_id)
    ]

    return {
        "battle_id": battle_id,
        "room": _summarize_obj(room),
        "removed_parts": removed_parts,
        "removed_room_index": removed_room_index,
        "removed_room_ndb": removed_room_ndb,
        "cleared_trainers": cleared_trainers,
    }


def _cleanup_candidate(candidate: BattleCleanupCandidate, *, dry_run: bool = False) -> str:
    """Clean or preview one battle cleanup candidate."""

    parts = ", ".join(candidate.stored_parts) if candidate.stored_parts else "-"
    trainer_text = _format_trainer_refs(candidate.trainer_refs)
    if dry_run:
        action = "Abort live session" if candidate.is_live else "Purge stale stored record"
        return (
            f"Dry run for battle #{candidate.battle_id}: {action} in "
            f"{_summarize_obj(candidate.room)}; {_format_candidate_age(candidate)}; "
            f"parts={parts}; trainers={trainer_text}."
        )

    if candidate.is_live:
        candidate.inst.end()
        return f"Battle #{candidate.battle_id} aborted via live session cleanup."

    result = _purge_stored_battle(candidate)
    removed_parts = ", ".join(result["removed_parts"]) if result["removed_parts"] else "-"
    return (
        f"Purged stale battle #{candidate.battle_id} from {result['room']}; "
        f"{_format_candidate_age(candidate)}; "
        f"removed parts={removed_parts}; cleared trainers={len(result['cleared_trainers'])}."
    )


def _cleanup_all_stale(candidates: List[BattleCleanupCandidate], *, dry_run: bool = False) -> str:
    """Clean or preview all stale candidates."""

    stale = [candidate for candidate in candidates if not candidate.is_live]
    if not stale:
        return "No stale battle records found."
    lines = []
    for candidate in stale:
        lines.append(_cleanup_candidate(candidate, dry_run=dry_run))
    return "\n".join(lines)


def _strip_empty(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return ``data`` without ``None`` values or empty containers."""

    return {k: v for k, v in data.items() if v is not None and v != [] and v != {}}


def _summarize_obj(obj) -> str | None:
    """Return a short human-readable description for ``obj``."""

    if not obj:
        return None
    name = getattr(obj, "key", None) or getattr(obj, "name", None)
    ident = getattr(obj, "id", None)
    if name and ident is not None:
        return f"{name} (#{ident})"
    if name:
        return str(name)
    if ident is not None:
        return f"#{ident}"
    return str(obj)


def _summarize_pokemon(pokemon) -> Dict[str, Any] | None:
    """Return a snapshot of a Pokémon's key battle attributes."""

    if not pokemon:
        return None

    moves = []
    for move in getattr(pokemon, "moves", []) or []:
        name = getattr(move, "name", None) or getattr(move, "key", None)
        if not name:
            name = str(move)
        moves.append(str(name))

    info: Dict[str, Any] = {
        "name": getattr(pokemon, "name", getattr(pokemon, "species", None)),
        "hp": getattr(pokemon, "hp", None),
        "max_hp": getattr(pokemon, "max_hp", None),
        "status": getattr(pokemon, "status", None),
        "moves": moves,
        "model_id": getattr(pokemon, "model_id", None),
    }

    ability = getattr(pokemon, "ability", None)
    if ability:
        info["ability"] = getattr(ability, "name", str(ability))

    item = getattr(pokemon, "item", None)
    if item:
        info["item"] = getattr(item, "name", str(item))

    return _strip_empty(info)


def _summarize_action(action) -> Dict[str, Any] | None:
    """Return a readable representation of a queued battle action."""

    if not action:
        return None

    data: Dict[str, Any] = {}
    a_type = getattr(action, "action_type", None)
    if a_type is not None:
        data["type"] = getattr(a_type, "name", str(a_type))
    move = getattr(action, "move", None)
    if move:
        data["move"] = getattr(move, "name", str(move))
    target = getattr(action, "target", None)
    if target:
        data["target"] = _summarize_obj(target)
    priority = getattr(action, "priority", None)
    if priority is not None:
        data["priority"] = priority
    return _strip_empty(data)


def _summarize_participant(participant) -> Dict[str, Any] | None:
    """Summarize a :class:`BattleParticipant` for debugging output."""

    if not participant:
        return None

    pokemons = [
        snap
        for snap in (
            _summarize_pokemon(poke)
            for poke in getattr(participant, "pokemons", []) or []
        )
        if snap
    ]
    active = [
        snap
        for snap in (
            _summarize_pokemon(poke)
            for poke in getattr(participant, "active", []) or []
        )
        if snap
    ]

    data: Dict[str, Any] = {
        "name": getattr(participant, "name", None),
        "team": getattr(participant, "team", None),
        "player": _summarize_obj(getattr(participant, "player", None)),
        "is_ai": getattr(participant, "is_ai", None),
        "pokemons": pokemons,
        "active": active,
    }

    pending = _summarize_action(getattr(participant, "pending_action", None))
    if pending:
        data["pending_action"] = pending

    return _strip_empty(data)


def _summarize_trainer(trainer) -> Dict[str, Any] | None:
    """Return relevant battle state stored on a trainer."""

    if not trainer:
        return None

    info: Dict[str, Any] = {"object": _summarize_obj(trainer)}

    battle_id = getattr(getattr(trainer, "db", None), "battle_id", None)
    if battle_id is not None:
        info.setdefault("db", {})["battle_id"] = battle_id

    inst = getattr(getattr(trainer, "ndb", None), "battle_instance", None)
    if inst is not None or hasattr(getattr(trainer, "ndb", None), "battle_instance"):
        ref = getattr(inst, "battle_id", None) if inst else None
        info.setdefault("ndb", {})["battle_instance"] = ref

    active = _summarize_pokemon(getattr(trainer, "active_pokemon", None))
    if active:
        info["active_pokemon"] = active

    team_members = [
        snap
        for snap in (
            _summarize_pokemon(poke)
            for poke in getattr(trainer, "team", []) or []
        )
        if snap
    ]
    if team_members:
        info["team"] = team_members

    return _strip_empty(info)


def _room_snapshot(room, battle_id: int) -> Dict[str, Any]:
    """Capture stored battle data on ``room`` for ``battle_id``."""

    info: Dict[str, Any] = {"object": _summarize_obj(room)}

    battles = getattr(getattr(room, "db", None), "battles", None)
    if battles is not None:
        info.setdefault("db", {})["battles"] = list(battles)

    storage = BattleDataWrapper(room, battle_id)
    stored: Dict[str, Any] = {}
    for part in ("data", "state", "trainers", "temp_pokemon_ids", "logic", "debug", "last_action"):
        value = storage.get(part)
        if value is not None:
            stored[part] = value
    if stored:
        info["stored"] = stored

    battle_map = getattr(getattr(room, "ndb", None), "battle_instances", None)
    if isinstance(battle_map, dict):
        info.setdefault("ndb", {})["battle_instances"] = {
            str(key): _summarize_obj(val) for key, val in battle_map.items()
        }
    elif battle_map is not None:
        info.setdefault("ndb", {})["battle_instances"] = str(battle_map)

    return _strip_empty(info)


def _session_snapshot(inst) -> Dict[str, Any]:
    """Return a consolidated view of live battle session data."""

    if not inst:
        return {"present": False}

    summary: Dict[str, Any] = {
        "present": True,
        "battle_id": getattr(inst, "battle_id", None),
        "captainA": _summarize_obj(getattr(inst, "captainA", None)),
        "captainB": _summarize_obj(getattr(inst, "captainB", None)),
        "teamA": [_summarize_obj(obj) for obj in getattr(inst, "teamA", []) if obj],
        "teamB": [_summarize_obj(obj) for obj in getattr(inst, "teamB", []) if obj],
        "observers": [_summarize_obj(obj) for obj in getattr(inst, "observers", []) if obj],
        "temp_pokemon_ids": list(getattr(inst, "temp_pokemon_ids", []) or []),
    }

    state = getattr(inst, "state", None)
    if state is not None:
        summary["state_turn"] = getattr(state, "turn", None)

    battle = getattr(inst, "battle", None)
    if battle is not None:
        summary["battle_turn"] = getattr(battle, "turn_count", None)

    inst_ndb = getattr(inst, "ndb", None)
    watchers_live = getattr(inst_ndb, "watchers_live", None)
    if watchers_live:
        summary["watchers_live"] = sorted(list(watchers_live))

    logic = getattr(inst, "logic", None)
    if logic is not None:
        logic_battle = getattr(logic, "battle", None)
        if logic_battle is not None:
            summary["logic_turn"] = getattr(logic_battle, "turn_count", None)
            participants = [
                snap
                for snap in (
                    _summarize_participant(part)
                    for part in getattr(logic_battle, "participants", []) or []
                )
                if snap
            ]
            if participants:
                summary["participants"] = participants

        logic_data = getattr(logic, "data", None)
        if logic_data is not None:
            teams = getattr(logic_data, "teams", {}) or {}
            team_info: Dict[str, Any] = {}
            for key in ("A", "B"):
                team = teams.get(key)
                if not team:
                    continue
                members = [
                    snap
                    for snap in (
                        _summarize_pokemon(poke)
                        for poke in getattr(team, "returnlist", lambda: [])()
                    )
                    if snap
                ]
                if members:
                    team_info[key] = members
            if team_info:
                summary["logic_team"] = team_info

    if state is not None:
        summary["debug"] = bool(getattr(state, "debug", False))

    if battle is not None:
        summary["show_damage_numbers"] = bool(
            getattr(battle, "show_damage_numbers", False)
        )

    debug_record = getattr(getattr(inst, "storage", None), "get", lambda *_: None)("debug")
    if debug_record:
        summary["debug_record"] = debug_record

    return _strip_empty(summary)


def _battle_snapshot(inst, room, battle_id: int) -> Dict[str, Any]:
    """Construct the full snapshot dictionary for output."""

    snapshot: Dict[str, Any] = {
        "room": _room_snapshot(room, battle_id),
        "session": _session_snapshot(inst),
    }

    trainers: List[Dict[str, Any]] = []
    seen: set[int] = set()
    if inst:
        for obj in list(getattr(inst, "teamA", []) or []) + list(getattr(inst, "teamB", []) or []):
            if not obj or id(obj) in seen:
                continue
            seen.add(id(obj))
            snapshot_info = _summarize_trainer(obj)
            if snapshot_info:
                trainers.append(snapshot_info)

    if trainers:
        snapshot["trainers"] = trainers

    return snapshot


class CmdAbortBattle(Command):
    """Force end an ongoing battle.

    Usage:
      @abortbattle <character or battle id>
    """

    key = "@abortbattle"
    aliases = ["+abortbattle"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: @abortbattle <character or battle id>")
            return
        arg = self.args.strip()
        inst = None
        if arg.isdigit():
            inst = battle_handler.instances.get(int(arg))
            if not inst:
                self.caller.msg("No battle with that ID found.")
                return
        else:
            targets = search_object(arg)
            if not targets:
                self.caller.msg("No such character.")
                return
            target = targets[0]
            inst = getattr(target.ndb, "battle_instance", None)
            if not inst:
                self.caller.msg("They are not currently in battle.")
                return
        bid = inst.battle_id
        inst.end()
        self.caller.msg(f"Battle #{bid} aborted.")


class CmdBattleCleanup(Command):
    """List and clean live or stale battle records.

    Usage:
      @battlecleanup
      @battlecleanup/list
      @battlecleanup/purge <number or battle id>
      @battlecleanup/dryrun <number, battle id, or stale>
      @battlecleanup/all-stale
    """

    key = "@battlecleanup"
    aliases = ["+battlecleanup", "@battleclean", "+battleclean"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def _candidates(self) -> List[BattleCleanupCandidate]:
        return _collect_battle_cleanup_candidates(getattr(self.caller, "location", None))

    def _send_list(self, candidates: List[BattleCleanupCandidate]) -> None:
        self.caller.msg(_format_cleanup_candidates(candidates))

    def _run_selection(
        self,
        selection: str,
        candidates: List[BattleCleanupCandidate],
        *,
        dry_run: bool = False,
    ) -> None:
        candidate = _resolve_cleanup_selection(selection, candidates)
        if not candidate:
            self.caller.msg("No cleanup candidate matches that number or battle id.")
            return
        self.caller.msg(_cleanup_candidate(candidate, dry_run=dry_run))

    def _open_menu(self, candidates: List[BattleCleanupCandidate]) -> None:
        if not candidates:
            self.caller.msg("No battle cleanup candidates found.")
            return
        if get_input is None:
            self._send_list(candidates)
            return

        prompt = _format_cleanup_candidates(candidates)

        def _callback(caller, _prompt, result):
            choice = (result or "").strip().lower()
            if choice in {"0", "cancel", "quit", "exit", "abort", ".abort"}:
                caller.msg("Battle cleanup cancelled.")
                return False
            if choice in {"stale", "all-stale", "all stale"}:
                caller.msg(_cleanup_all_stale(candidates))
                return False
            if choice.startswith("dryrun "):
                target = choice.split(None, 1)[1]
                if target in {"stale", "all-stale", "all"}:
                    caller.msg(_cleanup_all_stale(candidates, dry_run=True))
                    return False
                candidate = _resolve_cleanup_selection(target, candidates)
                if not candidate:
                    caller.msg("No cleanup candidate matches that number or battle id.")
                    return True
                caller.msg(_cleanup_candidate(candidate, dry_run=True))
                return False
            candidate = _resolve_cleanup_selection(choice, candidates)
            if not candidate:
                caller.msg("Enter a listed number, 'stale', 'dryrun <number>', or 0 to cancel.")
                return True
            caller.msg(_cleanup_candidate(candidate))
            return False

        get_input(self.caller, prompt, _callback)

    def func(self):
        switches = {switch.lower() for switch in getattr(self, "switches", [])}
        arg = (getattr(self, "args", "") or "").strip()
        candidates = self._candidates()

        if "list" in switches:
            self._send_list(candidates)
            return

        if "all-stale" in switches or "stale" in switches:
            self.caller.msg(_cleanup_all_stale(candidates, dry_run="dryrun" in switches))
            return

        if "dryrun" in switches:
            target = arg or "stale"
            if target.lower() in {"stale", "all-stale", "all"}:
                self.caller.msg(_cleanup_all_stale(candidates, dry_run=True))
                return
            self._run_selection(target, candidates, dry_run=True)
            return

        if "purge" in switches or "clean" in switches:
            if not arg:
                self.caller.msg("Usage: @battlecleanup/purge <number or battle id>")
                return
            self._run_selection(arg, candidates)
            return

        if arg:
            self._run_selection(arg, candidates)
            return

        self._open_menu(candidates)


class CmdRestoreBattle(Command):
    """Restore a saved battle in the current room for debugging.

    Usage:
      @restorebattle <battle_id>
    """

    key = "@restorebattle"
    aliases = ["+restorebattle"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: @restorebattle <battle_id>")
            return

        arg = self.args.strip()
        if not arg.isdigit():
            self.caller.msg("Battle ID must be numeric.")
            return

        battle_id = int(arg)
        inst = BattleSession.restore(self.caller.location, battle_id)
        if not inst:
            self.caller.msg(f"Could not restore battle {battle_id}.")
        else:
            self.caller.msg(f"Restored battle {battle_id}.")


class CmdBattleInfo(Command):
    """Display stored battle data for debugging.

    Usage:
      @battleinfo <character or battle id>
    """

    key = "@battleinfo"
    aliases = ["+battleinfo"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: @battleinfo <character or battle id>")
            return

        inst, room, bid, target = _resolve_battle_context(self.args)
        if bid is None or room is None:
            if target is None:
                self.caller.msg("No battle data found.")
            else:
                self.caller.msg("No battle data found for that target.")
            return

        storage = BattleDataWrapper(room, bid)
        parts = {
            "data": storage.get("data"),
            "state": storage.get("state"),
            "trainers": storage.get("trainers"),
            "temp_pokemon_ids": storage.get("temp_pokemon_ids"),
            "debug": storage.get("debug"),
            "last_action": storage.get("last_action"),
        }

        lines = [f"Battle {bid} info:"]
        for key, value in parts.items():
            if value is not None:
                formatted = pprint.pformat(value, indent=2, width=78)
                lines.append(f"{key.capitalize()}:\n{formatted}")

        if len(lines) == 1:
            self.caller.msg("No stored data for that battle.")
        else:
            self.caller.msg("\n".join(lines))


class CmdBattleSnapshot(Command):
    """Display stored and live battle values for comparison.

    Usage:
      @battlecheck <character or battle id>
    """

    key = "@battlecheck"
    aliases = ["+battlecheck"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: @battlecheck <character or battle id>")
            return

        inst, room, bid, target = _resolve_battle_context(self.args)
        if bid is None or room is None:
            if target is None:
                self.caller.msg("No battle data found.")
            else:
                self.caller.msg("No battle data found for that target.")
            return

        snapshot = _battle_snapshot(inst, room, bid)
        formatted = pprint.pformat(snapshot, indent=2, width=78, sort_dicts=False)
        self.caller.msg(f"Battle {bid} snapshot:\n{formatted}")


class CmdRetryTurn(Command):
    """Retry the current turn of a battle."""

    key = "@retryturn"
    aliases = ["+retryturn"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: @retryturn <character or battle id>")
            return

        arg = self.args.strip()
        inst = None
        if arg.isdigit():
            inst = battle_handler.instances.get(int(arg))
            if not inst:
                self.caller.msg("No battle with that ID found.")
                return
        else:
            targets = search_object(arg)
            if not targets:
                self.caller.msg("No such character.")
                return
            target = targets[0]
            inst = getattr(target.ndb, "battle_instance", None)
            if not inst:
                self.caller.msg("They are not currently in battle.")
                return

        inst.run_turn()
        self.caller.msg(f"Turn retried for battle {inst.battle_id}.")


class CmdToggleDamageNumbers(Command):
    """Toggle exact damage number announcements for a battle.

    Usage:
      @damage/toggle [<character or battle id>]

    Without an argument the caller's active battle will be toggled.
    """

    key = "@damage/toggle"
    aliases = ["+damage/toggle", "@damagenumbers", "+damagenumbers", "@damageexact", "+damageexact"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def func(self):
        arg = (self.args or "").strip()
        inst: Optional[BattleSession] = None

        if arg:
            inst, _, bid, target = _resolve_battle_context(arg)
            if not inst:
                if target is None and bid is None:
                    self.caller.msg("No battle data found.")
                else:
                    self.caller.msg("No battle found for that target.")
                return
        else:
            inst = getattr(getattr(self.caller, "ndb", None), "battle_instance", None)
            if not inst:
                self.caller.msg("You are not currently participating in a battle.")
                return

        battle = getattr(inst, "battle", None)
        if not battle:
            self.caller.msg("Battle data is not available.")
            return

        current = getattr(battle, "show_damage_numbers", False)
        battle.show_damage_numbers = not current
        state = "enabled" if battle.show_damage_numbers else "disabled"

        # Inform the caller and other battle participants of the new state.
        self.caller.msg(
            f"Exact damage numbers {state} for battle {inst.battle_id}."
        )
        try:
            inst.msg(f"Exact damage numbers have been {state}.")
        except Exception:
            pass


class CmdUiPreview(Command):
    """Admin: preview the battle UI with mock data."""

    key = "@ui/preview"
    aliases = ["+ui/preview", "@uiprev", "+uiprev"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def parse(self):
        """Normalize switches and extract optional /team and /waiting markers."""
        super().parse()
        switches = getattr(self, "switches", None) or []
        self.switches = {s.lower() for s in switches}
        self.viewer_team = None
        self.waiting_on = None
        args = (getattr(self, "args", "") or "").strip()
        if "/team " in args:
            part = args.split("/team ", 1)[1]
            val = (part.split(None, 1)[0] or "").upper()
            if val in ("A", "B"):
                self.viewer_team = val
        if "/waiting " in args:
            self.waiting_on = args.split("/waiting ", 1)[1].strip() or None

    def func(self):
        caller = self.caller
        state = make_mock_battle_state()
        captain_a, captain_b = state.captainA, state.captainB
        ui = display_battle_interface(
            captain_a,
            captain_b,
            state,
            viewer_team=self.viewer_team,
            waiting_on=self.waiting_on,
            style=get_battle_ui_style(caller),
            total_width=get_battle_ui_width(caller),
        )
        caller.msg(ui)
        view_team = self.viewer_team or "A"
        active = (
            captain_a.active_pokemon
            if view_team == "A"
            else captain_b.active_pokemon
        )
        slots, pp_overrides = build_moves_dict_from_active(active)
        gui = render_move_gui(slots, pp_overrides=pp_overrides)
        caller.msg("\n" + gui)


@dataclass
class MockPokemon:
    name: str
    level: int = 5
    hp: int = 20
    max_hp: int = 20
    status: str = ""
    moves: list = dc_field(default_factory=list)
    is_fainted: bool = False


@dataclass
class MockTrainer:
    name: str
    team: list
    active_pokemon: MockPokemon


@dataclass
class MockBattleState:
    captainA: MockTrainer
    captainB: MockTrainer
    weather: str = "Hail"
    field: str = "Electric Terrain"
    round: int = 5
    declare: dict = dc_field(default_factory=dict)
    watchers: set = dc_field(default_factory=set)


def make_mock_battle_state() -> MockBattleState:
    move_a = {"name": "Tackle", "type": "Normal", "category": "Physical", "pp": (35, 35), "power": 40, "accuracy": 100}
    move_b = {"name": "Ember", "type": "Fire", "category": "Special", "pp": (25, 25), "power": 40, "accuracy": 100}
    mon_a = MockPokemon(name="Eevee", hp=39, max_hp=55, moves=[move_a])
    mon_b = MockPokemon(name="Charmander", hp=39, max_hp=39, moves=[move_b])
    captainA = MockTrainer(name="Red", team=[mon_a], active_pokemon=mon_a)
    captainB = MockTrainer(name="Blue", team=[mon_b], active_pokemon=mon_b)
    state = MockBattleState(captainA=captainA, captainB=captainB)
    state.declare = {"A1": {"move": "Tackle", "target": "B1"}, "B1": {"move": "Ember", "target": "A1"}}
    return state


def build_moves_dict_from_active(active: Any) -> Tuple[List[Any], Dict[int, int]]:
    """Return move slots and PP overrides for an active Pokémon."""

    slots: List[Any] = []
    pp_overrides: Dict[int, int] = {}
    for idx, move in enumerate(getattr(active, "moves", [])[:4]):
        if isinstance(move, dict):
            pp_val = move.get("pp")
            if isinstance(pp_val, (tuple, list)):
                current, maximum = pp_val
                move = {**move, "pp": maximum}
                pp_overrides[idx] = current
            else:
                cur = move.get("current_pp")
                if cur is not None:
                    pp_overrides[idx] = cur
        else:
            cur = getattr(move, "current_pp", None)
            if cur is not None:
                pp_overrides[idx] = cur
        slots.append(move)
    return slots, pp_overrides
