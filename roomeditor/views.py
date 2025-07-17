from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
import re
try:
    from evennia.utils import text2html
except Exception:  # pragma: no cover - fallback for tests without evennia
    class _Dummy:
        @staticmethod
        def parse_html(text, strip_ansi=False):
            return text

    text2html = _Dummy()
from evennia.objects.models import ObjectDB
from evennia import create_object
from typeclasses.rooms import Room
from typeclasses.exits import Exit

from .forms import RoomForm, ExitForm


def _parse_aliases(raw: str) -> list[str]:
    """Return a list of aliases from a raw string."""
    if not raw:
        return []
    pieces = re.split(r"[;,\s]+", raw)
    return [p for p in (s.strip() for s in pieces) if p]


def is_builder(user):
    """Return True if user has Builder or Admin permissions."""
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.check_permstring("Builder") or user.check_permstring("Builders")


@login_required
@user_passes_test(is_builder)
def room_list(request):
    """Display a list of all rooms."""
    rooms = ObjectDB.objects.filter(
        db_location__isnull=True, db_typeclass_path__contains="rooms"
    )
    dangling = {
        room.id: not ObjectDB.objects.filter(db_destination=room).exists()
        for room in rooms
    }
    dangling_ids = [rid for rid, val in dangling.items() if val]
    return render(
        request,
        "roomeditor/room_list.html",
        {"rooms": rooms, "dangling_ids": dangling_ids},
    )


@login_required
@user_passes_test(is_builder)
def room_edit(request, room_id=None):
    """Create or edit a room."""
    room = None
    if room_id:
        room = get_object_or_404(ObjectDB, id=room_id)
    if request.method == "POST" and (
        "save_room" in request.POST or "preview_room" in request.POST
    ):
        form = RoomForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if "save_room" in request.POST:
                if room is None:
                    room = create_object(data["room_class"], key=data["name"])
                elif room.typeclass_path != data["room_class"]:
                    room.swap_typeclass(data["room_class"], clean_attributes=False)
                room.key = data["name"]
                room.db.desc = data["desc"]
                room.db.is_pokemon_center = data["is_center"]
                room.db.is_item_shop = data["is_shop"]
                room.db.allow_hunting = data["allow_hunting"]
                chart = []
                for entry in data["hunt_chart"].split(','):
                    if not entry.strip():
                        continue
                    try:
                        mon, rate = entry.split(':')
                        chart.append({"name": mon.strip(), "weight": int(rate.strip())})
                    except ValueError:
                        continue
                room.db.hunt_chart = chart
                room.save()
                return redirect("roomeditor:room-list")
            else:
                data["desc_html"] = text2html.parse_html(data["desc"])
                return render(request, "roomeditor/room_preview.html", {"preview": data})
    else:
        initial = {"room_class": "typeclasses.rooms.Room"}
        if room:
            chart = room.db.hunt_chart or []
            initial = {
                "name": room.key,
                "desc": room.db.desc,
                "room_class": room.typeclass_path,
                "is_center": room.db.is_pokemon_center,
                "is_shop": room.db.is_item_shop,
                "allow_hunting": room.db.allow_hunting,
                "hunt_chart": ", ".join(f"{entry['name']}:{entry.get('weight',1)}" for entry in chart),
            }
        form = RoomForm(initial=initial)

    exit_form = ExitForm()
    outgoing = []
    incoming = []
    if room:
        outgoing = ObjectDB.objects.filter(db_location=room, db_typeclass_path__contains="exits")
        incoming = ObjectDB.objects.filter(db_destination=room)
    if request.method == "POST" and "add_exit" in request.POST and room:
        exit_form = ExitForm(request.POST)
        if exit_form.is_valid():
            dest = get_object_or_404(ObjectDB, id=int(exit_form.cleaned_data["dest_id"]))
            exit_obj = create_object(
                Exit,
                key=exit_form.cleaned_data["direction"],
                location=room,
                destination=dest,
            )
            exit_obj.db.desc = exit_form.cleaned_data.get("desc")
            exit_obj.db.err_traverse = exit_form.cleaned_data.get("err_traverse")
            lockstring = exit_form.cleaned_data.get("locks")
            if lockstring:
                exit_obj.locks.replace(lockstring)
            aliases = _parse_aliases(exit_form.cleaned_data.get("aliases"))
            if aliases:
                exit_obj.aliases.add(aliases)
            exit_obj.at_cmdset_get(force_init=True)
            return redirect("roomeditor:room-edit", room_id=room.id)

    context = {
        "form": form,
        "room": room,
        "exit_form": exit_form,
        "outgoing": outgoing,
        "incoming": incoming,
        "no_incoming": room is not None and not incoming,
        "default_locks": Exit.get_default_lockstring(account=request.user),
    }
    return render(request, "roomeditor/room_form.html", context)


@login_required
@user_passes_test(is_builder)
def delete_exit(request, exit_id, room_id):
    room = get_object_or_404(ObjectDB, id=room_id)
    exit_obj = get_object_or_404(ObjectDB, id=exit_id)
    exit_obj.delete()
    return redirect("roomeditor:room-edit", room_id=room.id)


@login_required
@user_passes_test(is_builder)
def edit_exit(request, room_id, exit_id):
    """Edit an existing exit."""
    room = get_object_or_404(ObjectDB, id=room_id)
    exit_obj = get_object_or_404(ObjectDB, id=exit_id)
    if request.method == "POST":
        form = ExitForm(request.POST)
        if form.is_valid():
            exit_obj.key = form.cleaned_data["direction"]
            exit_obj.destination = get_object_or_404(
                ObjectDB, id=int(form.cleaned_data["dest_id"])
            )
            exit_obj.db.desc = form.cleaned_data.get("desc")
            exit_obj.db.err_traverse = form.cleaned_data.get("err_traverse")
            lockstring = form.cleaned_data.get("locks")
            if lockstring:
                exit_obj.locks.replace(lockstring)
            else:
                exit_obj.locks.clear()
            exit_obj.aliases.clear()
            aliases = _parse_aliases(form.cleaned_data.get("aliases"))
            if aliases:
                exit_obj.aliases.add(aliases)
            exit_obj.save()
            exit_obj.at_cmdset_get(force_init=True)
            return redirect("roomeditor:room-edit", room_id=room.id)
    else:
        form = ExitForm(
            initial={
                "direction": exit_obj.key,
                "dest_id": exit_obj.destination.id if exit_obj.destination else None,
                "desc": exit_obj.db.desc,
                "err_traverse": exit_obj.db.err_traverse,
                "locks": str(exit_obj.locks),
                "aliases": "; ".join(exit_obj.aliases.all()),
                "exit_id": exit_obj.id,
            }
        )

    return render(
        request,
        "roomeditor/exit_form.html",
        {
            "form": form,
            "room": room,
            "exit": exit_obj,
            "default_locks": Exit.get_default_lockstring(account=request.user),
        },
    )

