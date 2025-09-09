# Tabs are intentional.
from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from evennia.objects.models import ObjectDB

try:
	from evennia.utils.text2html import parse_html
except Exception:
	def parse_html(text, strip_ansi=False):
		return text
from django.db import transaction

from utils.build_utils import reverse_dir

from ..forms import ExitForm, RoomForm
from ..utils.locks import apply_default_locks

try:
	from evennia import DefaultExit
except Exception:
	class DefaultExit:
		path = ""

try:
	from evennia import DefaultRoom
except Exception:
	class DefaultRoom:
		path = "typeclasses.rooms.Room"


def _room_qs():
	"""Queryset for room objects."""
	return ObjectDB.objects.filter(db_typeclass_path__icontains=".rooms.")

def _exit_qs():
	"""Queryset for exit objects."""
	return ObjectDB.objects.filter(db_typeclass_path__icontains=".exits.")

def room_list(request: HttpRequest):
	"""Display a list of rooms available for editing."""
	rooms = _room_qs().order_by("db_key")
	incoming_ids = set(_exit_qs().values_list("db_destination_id", flat=True))
	dangling_ids = {room.id for room in rooms if room.id not in incoming_ids}
	return render(
		request,
		"roomeditor/room_list.html",
		{"rooms": rooms, "dangling_ids": dangling_ids},
	)

def room_new(request: HttpRequest):
	"""Create a new room."""
	if request.method == "POST":
		form = RoomForm(request.POST)
		if form.is_valid():
			data = getattr(form, "cleaned_data", form.data)
			room = ObjectDB.objects.create(
				typeclass_path=DefaultRoom.path,
				db_key=data.get("db_key", ""),
				db_location=data.get("db_location") or None,
				db_lock_storage=data.get("db_lock_storage") or "",
			)
			room.db.desc = data.get("desc") or data.get("db_desc") or ""
			apply_default_locks(room, as_exit=False, user_id=getattr(getattr(request, "user", None), "id", 0), caller_id=None)
			if request.headers.get("X-Requested-With") == "XMLHttpRequest":
				html = render(
					request,
					"roomeditor/_room_row.html",
					{"room": room, "dangling_ids": {room.id}},
				).content.decode("utf-8")
				return JsonResponse({"ok": True, "row_html": html})
			return redirect("roomeditor:room_edit", pk=room.id)
		elif request.headers.get("X-Requested-With") == "XMLHttpRequest":
			return JsonResponse({"ok": False, "error": form.errors.as_text()}, status=400)
	else:
		form = RoomForm()
	return render(request, "roomeditor/_room_form.html", {"form": form})

def room_edit(request: HttpRequest, pk: int):
	"""Edit an existing room."""
	room = get_object_or_404(_room_qs(), pk=pk)
	if request.method == "POST":
		form = RoomForm(request.POST, instance=room)
		if form.is_valid():
			form.save()
			if request.headers.get("Hx-Request") or request.headers.get("X-Requested-With") == "XMLHttpRequest":
				return JsonResponse({"ok": True})
			return redirect("roomeditor:room_edit", pk=room.pk)
		elif request.headers.get("Hx-Request") or request.headers.get("X-Requested-With") == "XMLHttpRequest":
			return JsonResponse({"ok": False, "error": form.errors.as_text()}, status=400)
	else:
		form = RoomForm(instance=room)
	incoming = _exit_qs().filter(db_destination_id=room.id).exists()
	return render(
		request,
		"roomeditor/room_form.html",
		{
			"form": form,
			"room": room,
			"has_incoming": incoming,
			"exits": _exit_qs().filter(db_location_id=room.id).order_by("db_key"),
		},
	)

@require_POST
def room_delete(request: HttpRequest, pk: int):
	"""Delete a room."""
	room = get_object_or_404(_room_qs(), pk=pk)
	room.delete()
	if request.headers.get("X-Requested-With") == "XMLHttpRequest":
		return JsonResponse({"ok": True})
	return redirect("roomeditor:room-list")

@require_POST
def ansi_preview(request: HttpRequest):
	"""Return ANSI text rendered to HTML."""
	text = request.POST.get("text", "")
	html = parse_html(text, strip_ansi=False)
	return JsonResponse({"html": html})

def exit_new(request: HttpRequest, room_pk: int):
	"""Create a new exit from a room."""
	room = get_object_or_404(_room_qs(), pk=room_pk)
	if request.method == "POST":
		form = ExitForm(request.POST)
		if form.is_valid():
			with transaction.atomic():
				ex = ObjectDB.objects.create(
					typeclass_path=DefaultExit.path,
					db_key=form.cleaned_data["key"],
					db_location=room,
					db_destination=form.cleaned_data["destination"],
				)
				apply_default_locks(ex, as_exit=True, user_id=getattr(getattr(request, "user", None), "id", 0), caller_id=None)
				aliases = form.cleaned_alias_list()
				if aliases:
					ex.aliases.add(*aliases)
				if form.cleaned_data.get("description"):
					ex.db.desc = form.cleaned_data["description"]
				if form.cleaned_data.get("lockstring"):
					ex.locks.add(form.cleaned_data["lockstring"])
				if form.cleaned_data.get("err_msg"):
					ex.db.err_traverse = form.cleaned_data["err_msg"]
				rev_obj = None
				if form.cleaned_data.get("auto_reverse"):
					rkey = reverse_dir(form.cleaned_data["key"])
					if rkey:
						rev_obj = ObjectDB.objects.create(
							typeclass_path=DefaultExit.path,
							db_key=rkey,
							db_location=form.cleaned_data["destination"],
							db_destination=room,
						)
						apply_default_locks(rev_obj, as_exit=True, user_id=getattr(getattr(request, "user", None), "id", 0), caller_id=None)
						if aliases:
							rev_obj.aliases.add(*aliases)
						if form.cleaned_data.get("description"):
							rev_obj.db.desc = form.cleaned_data["description"]
						if form.cleaned_data.get("lockstring"):
							rev_obj.locks.add(form.cleaned_data["lockstring"])
						if form.cleaned_data.get("err_msg"):
							rev_obj.db.err_traverse = form.cleaned_data["err_msg"]
			if request.headers.get("X-Requested-With") == "XMLHttpRequest":
				html = render(request, "roomeditor/_exit_row.html", {"ex": ex}).content.decode("utf-8")
				return JsonResponse({"ok": True, "row_html": html})
			return redirect("roomeditor:room_edit", pk=room.pk)
		elif request.headers.get("X-Requested-With") == "XMLHttpRequest":
			return JsonResponse({"ok": False, "error": form.errors.as_text()}, status=400)
	else:
		form = ExitForm()
	return render(request, "roomeditor/_exit_form.html", {"form": form, "room": room})

def exit_edit(request: HttpRequest, pk: int):
	"""Edit an existing exit."""
	ex = get_object_or_404(_exit_qs(), pk=pk)
	if request.method == "POST":
		form = ExitForm(request.POST)
		if form.is_valid():
			with transaction.atomic():
				ex.key = form.cleaned_data["key"]
				ex.destination = form.cleaned_data["destination"]
				ex.aliases.clear()
				aliases = form.cleaned_alias_list()
				if aliases:
					ex.aliases.add(*aliases)
				ex.db.desc = form.cleaned_data.get("description") or ""
				ex.locks.clear()
				if form.cleaned_data.get("lockstring"):
					ex.locks.add(form.cleaned_data["lockstring"])
				ex.db.err_traverse = form.cleaned_data.get("err_msg") or ""
			ex.save()
			if request.headers.get("X-Requested-With") == "XMLHttpRequest":
				row = render(request, "roomeditor/_exit_row.html", {"ex": ex}).content.decode("utf-8")
				return JsonResponse({"ok": True, "row_html": row})
			return redirect("roomeditor:room_edit", pk=ex.location_id)
		elif request.headers.get("X-Requested-With") == "XMLHttpRequest":
			return JsonResponse({"ok": False, "error": form.errors.as_text()}, status=400)
	else:
		locks = ex.locks.all()
		initial = {
			"key": ex.key,
			"destination": ex.db_destination_id,
			"description": ex.db.desc or "",
			"lockstring": locks[0] if locks else "",
			"err_msg": ex.db.err_traverse or "",
			"aliases": ", ".join(ex.aliases.all()),
			"auto_reverse": False,
		}
		form = ExitForm(initial=initial)
	return render(request, "roomeditor/_exit_form.html", {"form": form, "exit": ex})

@require_POST
def exit_delete(request: HttpRequest, pk: int):
	"""Delete an exit."""
	ex = get_object_or_404(_exit_qs(), pk=pk)
	room_pk = ex.location_id
	ex.delete()
	if request.headers.get("X-Requested-With") == "XMLHttpRequest":
		return JsonResponse({"ok": True})
	return redirect("roomeditor:room_edit", pk=room_pk)

def room_search_api(request: HttpRequest):
	"""Return rooms matching a query for autocomplete."""
	q = (request.GET.get("q") or "").strip()
	results = []
	if q:
		qs = _room_qs().filter(db_key__icontains=q).order_by("db_key")[:20]
		results = [{"id": r.id, "text": f"{r.key} (#{r.id})"} for r in qs]
	return JsonResponse({"results": results})

room_edit.__wrapped__ = room_edit
