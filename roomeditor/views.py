from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.utils.safestring import mark_safe
from evennia.objects.models import ObjectDB
from evennia import create_object
from typeclasses.rooms import Room
from typeclasses.exits import Exit

from .forms import RoomForm, ExitForm


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
    if request.method == "POST" and "save_room" in request.POST:
        form = RoomForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if room is None:
                room = create_object(Room, key=data["name"])
            room.key = data["name"]
            room.db.desc = data["desc"]
            room.db.is_pokemon_center = data["is_center"]
            room.db.is_item_shop = data["is_shop"]
            room.db.has_pokemon_hunting = data["has_hunting"]
            table = {}
            for entry in data["hunt_table"].split(','):
                if not entry.strip():
                    continue
                try:
                    mon, rate = entry.split(':')
                    table[mon.strip()] = int(rate.strip())
                except ValueError:
                    continue
            room.db.hunt_table = table
            room.save()
            return redirect("roomeditor:room-edit", room_id=room.id)
    else:
        initial = {}
        if room:
            table = room.db.hunt_table or {}
            initial = {
                "name": room.key,
                "desc": room.db.desc,
                "is_center": room.db.is_pokemon_center,
                "is_shop": room.db.is_item_shop,
                "has_hunting": room.db.has_pokemon_hunting,
                "hunt_table": ", ".join(f"{k}:{v}" for k, v in table.items()),
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
            dest = get_object_or_404(ObjectDB, id=exit_form.cleaned_data["dest_id"])
            create_object(Exit, key=exit_form.cleaned_data["direction"], location=room, destination=dest)
            return redirect("roomeditor:room-edit", room_id=room.id)

    context = {
        "form": form,
        "room": room,
        "exit_form": exit_form,
        "outgoing": outgoing,
        "incoming": incoming,
        "no_incoming": room is not None and not incoming,
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
def room_preview(request):
    """Render a preview of a room in a popup window."""
    if request.method != "POST":
        return redirect("roomeditor:room-list")

    form = RoomForm(request.POST)
    if not form.is_valid():
        return HttpResponse("Invalid data", status=400)

    from evennia.utils.text2html import parse_html

    data = form.cleaned_data
    context = {
        "name": data["name"],
        "desc_html": mark_safe(parse_html(data["desc"] or "")),
        "is_center": data["is_center"],
        "is_shop": data["is_shop"],
        "has_hunting": data["has_hunting"],
    }
    return render(request, "roomeditor/room_preview.html", context)

