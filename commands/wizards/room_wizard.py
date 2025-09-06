from __future__ import annotations

"""Enhanced room creation wizard using Evennia's EvMenu."""

from evennia import DefaultExit
from evennia.objects.models import ObjectDB
from evennia.utils import create, evmenu

from fusion2.utils.build_utils import normalize_aliases, reverse_dir

MENU_COLORS = {"title": "|W", "key": "|y", "warn": "|r"}


def _search_rooms(query: str, limit: int = 20):
    """Find rooms by id or partial name (case-insensitive)."""
    query = (query or "").strip()
    if not query:
        return []
    if query.lower().startswith("id:"):
        try:
            pk = int(query.split(":", 1)[1])
            return list(ObjectDB.objects.filter(id=pk))
        except Exception:
            return []
    return list(
        ObjectDB.objects.filter(db_key__icontains=query).order_by("db_key")[:limit]
    )


def _incoming_exits(room) -> int:
    """Return count of exits leading into ``room``."""
    if not room:
        return 0
    return ObjectDB.objects.filter(
        db_destination_id=room.id, db_typeclass_path__icontains=".exits."
    ).count()


def _mk_exit(
    src_room,
    key,
    dest_room,
    aliases=None,
    desc=None,
    locks=None,
    err_msg=None,
):
    """Create an exit with optional fields."""
    exit_obj = create.create_object(
        DefaultExit, key=key, location=src_room, destination=dest_room
    )
    if aliases:
        exit_obj.aliases.add(*aliases)
    if desc:
        exit_obj.db.desc = desc
    if locks:
        exit_obj.locks.add(locks)
    if err_msg:
        exit_obj.db.err_traverse = err_msg
    return exit_obj


def node_start(caller, raw_string, **ctx):  # pragma: no cover - interactive
    """Entry point."""
    return "node_room_name"


def node_room_name(caller, raw_string, **ctx):  # pragma: no cover - interactive
    """Collect room name."""
    if raw_string:
        ctx["name"] = raw_string.strip()
        room = ctx.get("room_obj")
        if room:
            room.key = ctx["name"]
        return "node_room_desc"
    caller.msg("Enter room name:")


def node_room_desc(caller, raw_string, **ctx):  # pragma: no cover - interactive
    """Collect room description and create the room."""
    if raw_string:
        ctx["desc"] = raw_string.strip()
        room = ctx.get("room_obj")
        if not room:
            room = create.create_object(
                "typeclasses.rooms.Room", key=ctx.get("name", "Room")
            )
            ctx["room_obj"] = room
        room.db.desc = ctx["desc"]
        caller.msg(f"|GRoom '{room.key}' created (id:{room.id}).|n")
        return "node_add_exits"
    caller.msg("Enter room description:")


def node_add_exits(caller, raw_string, **ctx):  # pragma: no cover - interactive
    """Handle adding exits to the new room."""
    raw = (raw_string or "").strip()
    if raw.lower() in ("done", "finish", "quit"):
        return "node_post_exits"
    if raw.lower().startswith("list "):
        q = raw.split(" ", 1)[1]
        matches = _search_rooms(q)
        if not matches:
            caller.msg(f"{MENU_COLORS['warn']}No rooms match '{q}'.")
            return "node_add_exits"
        lines = [f"{MENU_COLORS['key']}{r.id}|n: {r.key}" for r in matches]
        caller.msg("|WMatches:|n\n" + "\n".join(lines))
        return "node_add_exits"
    if "=" not in raw:
        caller.msg(
            f"{MENU_COLORS['warn']}Use <direction>=<id:### or search text>. Type 'list <text>' to search. Type 'done' to finish."
        )
        return "node_add_exits"
    dir_part, q = [s.strip() for s in raw.split("=", 1)]
    if not dir_part:
        caller.msg(f"{MENU_COLORS['warn']}Direction is required.")
        return "node_add_exits"
    candidates = _search_rooms(q, limit=10)
    if not candidates:
        caller.msg(
            f"{MENU_COLORS['warn']}No destination found for '{q}'. Try 'list {q}'."
        )
        return "node_add_exits"
    dest = candidates[0]
    if len(candidates) > 1 and not q.lower().startswith("id:"):
        lines = [f"{MENU_COLORS['key']}{r.id}|n: {r.key}" for r in candidates]
        caller.msg(
            "|WMultiple matches. Pick with '=id:<id>' or refine search:|n\n"
            + "\n".join(lines)
        )
        return "node_add_exits"
    ctx["__new_exit_tmp__"] = {"dir": dir_part, "dest": dest}
    return "node_exit_fields"


def node_exit_fields(caller, raw_string, **ctx):  # pragma: no cover - interactive
    """Collect extra exit fields and optionally create reverse exits."""
    tmp = ctx.get("__new_exit_tmp__", {})
    if not tmp:
        return "node_add_exits"
    raw = (raw_string or "").strip()
    if not raw:
        caller.msg(
            f"|WExit:|n dir={tmp.get('dir')} -> dest={getattr(tmp.get('dest'), 'key', None)} (id:{getattr(tmp.get('dest'),'id',None)})\n"
            "Enter:\n"
            "  desc <text>\n"
            "  aliases a,b,c\n"
            "  locks <lockstring>\n"
            "  err <text>\n"
            "  reverse yes|no\n"
            "  save | back"
        )
        return
    lc = raw.lower()
    if lc.startswith("desc "):
        tmp["desc"] = raw[5:].strip()
    elif lc.startswith("aliases "):
        tmp["aliases"] = normalize_aliases(raw[8:].strip())
    elif lc.startswith("locks "):
        tmp["locks"] = raw[6:].strip()
    elif lc.startswith("err "):
        tmp["err"] = raw[4:].strip()
    elif lc.startswith("reverse "):
        val = raw.split(" ", 1)[1].strip().lower()
        tmp["reverse"] = val in ("y", "yes", "1", "true", "on")
    elif lc == "back":
        ctx.pop("__new_exit_tmp__", None)
        return "node_add_exits"
    elif lc == "save":
        room = ctx.get("room_obj")
        if not room:
            caller.msg(f"{MENU_COLORS['warn']}Internal error: room missing.")
            return "node_add_exits"
        ex = _mk_exit(
            src_room=room,
            key=tmp["dir"],
            dest_room=tmp["dest"],
            aliases=tmp.get("aliases"),
            desc=tmp.get("desc"),
            locks=tmp.get("locks"),
            err_msg=tmp.get("err"),
        )
        caller.msg(
            f"|GCreated exit|n '{ex.key}' -> {tmp['dest'].key} (id:{tmp['dest'].id})."
        )
        if tmp.get("reverse"):
            rkey = reverse_dir(tmp["dir"])
            if rkey:
                _mk_exit(
                    src_room=tmp["dest"],
                    key=rkey,
                    dest_room=room,
                    aliases=tmp.get("aliases"),
                    desc=tmp.get("desc"),
                    locks=tmp.get("locks"),
                    err_msg=tmp.get("err"),
                )
                caller.msg(
                    f"|GCreated reverse exit|n in '{tmp['dest'].key}': '{rkey}' -> {room.key}."
                )
            else:
                caller.msg(
                    f"{MENU_COLORS['warn']}No known reverse for '{tmp['dir']}'. Skipped auto reverse."
                )
        ctx.pop("__new_exit_tmp__", None)
        return "node_add_exits"
    else:
        caller.msg(
            f"{MENU_COLORS['warn']}Unknown input. Use 'desc', 'aliases', 'locks', 'err', 'reverse', 'save', or 'back'."
        )


def node_post_exits(caller, raw_string, **ctx):  # pragma: no cover - interactive
    """Prepare summary after exits are added."""
    room = ctx.get("room_obj")
    if room:
        ctx["__summary__"] = (
            f"|gRoom Creation Summary|n\n"
            f"Name: {room.key}\n"
            f"Desc: {room.db.desc}\n"
            f"DBref: {room.id}\n"
        )
    return "node_summary"


def node_summary(caller, raw_string, **ctx):  # pragma: no cover - interactive
    """Show collected data, allow edits, and ask to create."""
    cmd = (raw_string or "").strip().lower()
    room = ctx.get("room_obj")
    if cmd in ("create", "ok", "y", "yes"):
        if room and _incoming_exits(room) == 0:
            caller.msg(
                f"{MENU_COLORS['warn']}Warning: No incoming exits point to '{room.key}'. It may be unreachable."
            )
        return "node_done"
    elif cmd.startswith("edit "):
        target = cmd.split(" ", 1)[1]
        if target in ("name", "title"):
            return "node_room_name"
        if target in ("desc", "description"):
            return "node_room_desc"
        caller.msg(
            f"{MENU_COLORS['warn']}Unknown edit target. Try 'edit name' or 'edit desc'."
        )
    elif cmd:
        caller.msg(
            f"{MENU_COLORS['warn']}Type 'create' to finalize or 'edit <field>' to revise."
        )
    else:
        caller.msg(ctx.get("__summary__", "|WSummary not available.|n"))
        caller.msg(
            "Type |Ycreate|n to finalize, or |Yedit name/desc|n to revise."
        )


def node_done(caller, raw_string, **ctx):  # pragma: no cover - interactive
    """Final node; remind about incoming exits."""
    room = ctx.get("room_obj")
    if room and _incoming_exits(room) == 0:
        caller.msg(
            f"{MENU_COLORS['warn']}Reminder: No incoming exits lead to '{room.key}'. Consider linking it."
        )
    caller.msg("|GDone.|n")
    return evmenu.EXIT

