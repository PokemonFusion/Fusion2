# Tabs are intentional.
from __future__ import annotations

from django.conf import settings
from django.db import transaction
from django.forms import formset_factory
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object

from pokemon.spawns.adapters import (
	SpawnAdapterError,
	coerce_spawn_data_entries,
	normalize_frequency,
	spawn_chart_from_room,
	spawn_chart_from_spawn_table,
)
from pokemon.spawns.legacy_migration import (
	recommend_bands_from_level_range,
	recommend_frequency_from_weight,
)
from pokemon.spawns.preview import format_spawn_preview
from pokemon.spawns.rolltest import format_spawn_roll_test, run_spawn_roll_test

try:
	from evennia.utils.text2html import parse_html
except Exception:
	def parse_html(text, strip_ansi=False):
		return text

from utils.build_utils import reverse_dir

from ..auth import builder_required
from ..forms import EncounterSettingsForm, ExitForm, RoomForm, SpawnEntryForm, SpawnPreviewForm
from ..utils.locks import compose_exit_default, compose_room_default


SPAWN_FORMSET_PREFIX = "spawns"


def _room_typeclass_path() -> str:
	"""Return the configured room typeclass path."""

	return getattr(settings, "BASE_ROOM_TYPECLASS", "typeclasses.rooms.Room")


def _exit_typeclass_path() -> str:
	"""Return the configured exit typeclass path."""

	return getattr(settings, "BASE_EXIT_TYPECLASS", "typeclasses.exits.Exit")


def _room_qs():
	"""Queryset for room objects."""
	return ObjectDB.objects.filter(db_typeclass_path__icontains=".rooms.")

def _exit_qs():
	"""Queryset for exit objects."""
	return ObjectDB.objects.filter(db_typeclass_path__icontains=".exits.")

def _room_db(room, key: str, default=None):
	"""Read an Evennia AttributeHandler value with a plain-object fallback."""
	db = getattr(room, "db", None)
	if db is None:
		return default
	try:
		value = getattr(db, key)
	except Exception:
		return default
	return default if value is None else value

def _coerce_bool(value, default: bool = False) -> bool:
	"""Coerce stored room attributes that may be strings or booleans."""
	if value is None:
		return default
	if isinstance(value, bool):
		return value
	if isinstance(value, str):
		return value.strip().lower() in {"1", "true", "yes", "on"}
	return bool(value)

def _coerce_int(value, default: int = 0) -> int:
	"""Coerce numeric room attributes for form initials."""
	try:
		return int(value)
	except (TypeError, ValueError):
		return default

def _encounter_settings_initial(room) -> dict:
	"""Return room encounter settings as form initials."""
	return {
		"allow_hunting": _coerce_bool(_room_db(room, "allow_hunting", False)),
		"encounter_rate": _coerce_int(_room_db(room, "encounter_rate", 100), 100),
		"npc_chance": _coerce_int(_room_db(room, "npc_chance", 0), 0),
		"itemfinder_rate": _coerce_int(_room_db(room, "itemfinder_rate", 0), 0),
		"noitem": _coerce_bool(_room_db(room, "noitem", False)),
		"tp_cost": _coerce_int(_room_db(room, "tp_cost", 0), 0),
		"weather": str(_room_db(room, "weather", "clear") or "clear"),
		"spawn_area_key": str(_room_db(room, "spawn_area_key", "") or ""),
	}

def _room_spawn_source(room) -> str:
	"""Return the stored source currently feeding spawn adapters."""
	if _room_db(room, "hunt_chart", None):
		return "hunt_chart"
	if _room_db(room, "spawn_table", None):
		return "spawn_table"
	return "empty"

def _entry_frequency(entry: dict) -> str:
	"""Return a PF2 frequency for a saved spawn entry."""
	for key in ("frequency", "rarity"):
		if entry.get(key):
			try:
				return normalize_frequency(entry.get(key))
			except SpawnAdapterError:
				break
	recommended = recommend_frequency_from_weight(entry.get("weight"))
	return recommended or "common"

def _entry_bands(entry: dict) -> str:
	"""Return display text for bands/tiers stored on a spawn entry."""
	for key in ("tiers", "tier", "bands", "band"):
		if key not in entry:
			continue
		value = entry.get(key)
		if isinstance(value, str):
			return value
		try:
			values = list(value)
		except TypeError:
			values = [value]
		if values:
			return ", ".join(str(part) for part in values)
	recommended = recommend_bands_from_level_range(entry.get("min_level"), entry.get("max_level"))
	if recommended:
		return ", ".join(f"T{band}" for band in recommended)
	return "1"

def _entry_enabled(entry: dict) -> bool:
	"""Return the enabled state for a stored spawn entry."""
	if "enabled" in entry:
		return _coerce_bool(entry.get("enabled"), True)
	if "disabled" in entry:
		return not _coerce_bool(entry.get("disabled"), False)
	return True

def _spawn_form_initial(room) -> list[dict]:
	"""Build spawn-row initials from spawn_table or legacy hunt_chart data."""
	data = _room_db(room, "spawn_table", None) or _room_db(room, "hunt_chart", None) or []
	try:
		entries = coerce_spawn_data_entries(data)
	except SpawnAdapterError:
		return []
	rows = []
	for entry in entries:
		species = entry.get("species") or entry.get("name")
		if not species:
			continue
		rows.append(
			{
				"species": species,
				"frequency": _entry_frequency(entry),
				"bands": _entry_bands(entry),
				"enabled": _entry_enabled(entry),
			}
		)
	return rows

def _spawn_entry_formset(*args, **kwargs):
	"""Return the formset used by the room spawn editor."""
	formset_class = formset_factory(SpawnEntryForm, extra=5, can_delete=True)
	kwargs.setdefault("prefix", SPAWN_FORMSET_PREFIX)
	return formset_class(*args, **kwargs)

def _spawn_entries_from_formset(formset) -> list[dict]:
	"""Convert validated spawn-entry forms into persisted spawn_table rows."""
	entries = []
	for form in formset:
		cleaned = getattr(form, "cleaned_data", None) or {}
		if cleaned.get("DELETE") or not cleaned.get("species"):
			continue
		frequency = cleaned.get("frequency") or "common"
		entries.append(
			{
				"species": cleaned["species"],
				"frequency": frequency,
				"rarity": frequency,
				"tiers": cleaned.get("bands") or ["T1"],
				"enabled": bool(cleaned.get("enabled")),
			}
		)
	return entries

def _area_key_for_preview(room, settings_data: dict | None = None) -> str:
	"""Choose the area key used by preview and roll-test helpers."""
	if settings_data and settings_data.get("spawn_area_key"):
		return str(settings_data["spawn_area_key"]).strip()
	for value in (_room_db(room, "spawn_area_key", None), getattr(room, "key", None), getattr(room, "id", None)):
		if value is not None and str(value).strip():
			return str(value).strip()
	return "room"

def _format_spawn_outputs(
	chart,
	*,
	source: str,
	preview_band: int | None = None,
	roll_band: int = 1,
	roll_count: int = 100,
) -> tuple[str, str]:
	"""Render preview and roll-test text for a spawn chart."""
	preview_text = format_spawn_preview(chart, source=source, band=preview_band)
	roll_result = run_spawn_roll_test(
		chart,
		band=roll_band,
		count=roll_count,
		requested_count=roll_count,
	)
	roll_text = format_spawn_roll_test(roll_result, source=source)
	return preview_text, roll_text

def _preview_band_value(value) -> int | None:
	"""Return optional preview-band integer from form data."""
	return int(value) if value else None

def _spawn_outputs_for_room(room) -> tuple[str, str, str]:
	"""Return preview output for currently saved room spawn data."""
	try:
		chart = spawn_chart_from_room(room)
		preview_text, roll_text = _format_spawn_outputs(chart, source=_room_spawn_source(room))
	except (SpawnAdapterError, ValueError) as err:
		return "", "", str(err)
	return preview_text, roll_text, ""

def _spawn_outputs_for_entries(room, entries: list[dict], settings_data: dict, preview_data: dict) -> tuple[str, str, str]:
	"""Return preview output for form-provided spawn rows."""
	try:
		chart = spawn_chart_from_spawn_table(entries, _area_key_for_preview(room, settings_data))
		preview_text, roll_text = _format_spawn_outputs(
			chart,
			source="spawn_table",
			preview_band=_preview_band_value(preview_data.get("preview_band")),
			roll_band=int(preview_data.get("roll_band") or 1),
			roll_count=int(preview_data.get("roll_count") or 100),
		)
	except (SpawnAdapterError, ValueError) as err:
		return "", "", str(err)
	return preview_text, roll_text, ""

def _save_room_encounters(room, settings_data: dict, spawn_entries: list[dict]) -> None:
	"""Persist encounter settings and canonical spawn_table rows."""
	room.db.allow_hunting = bool(settings_data.get("allow_hunting"))
	room.db.encounter_rate = int(settings_data.get("encounter_rate") or 0)
	room.db.npc_chance = int(settings_data.get("npc_chance") or 0)
	room.db.itemfinder_rate = int(settings_data.get("itemfinder_rate") or 0)
	room.db.noitem = bool(settings_data.get("noitem"))
	room.db.tp_cost = int(settings_data.get("tp_cost") or 0)
	room.db.weather = (settings_data.get("weather") or "clear").strip().lower()
	room.db.spawn_area_key = (settings_data.get("spawn_area_key") or "").strip()
	room.db.spawn_table = spawn_entries
	room.db.hunt_chart = []

def _add_aliases(obj, aliases):
	"""Add aliases through Evennia's one-alias-at-a-time handler API."""
	for alias in aliases:
		obj.aliases.add(alias)

def _combined_lockstring(*lockstrings: str) -> str:
	"""Combine optional lockstrings for Evennia's lock handler."""
	return ";".join(part for part in (lock.strip() for lock in lockstrings if lock) if part)

def _desc_attributes(*, desc: str = "", err_msg: str = "") -> list[tuple[str, str]]:
	"""Return Evennia create_object attributes for room/exit text fields."""
	attributes = []
	if desc:
		attributes.append(("desc", desc))
	if err_msg:
		attributes.append(("err_traverse", err_msg))
	return attributes

def _create_room(data, request: HttpRequest):
	"""Create a room through Evennia's typeclass-aware create API."""
	location = data.get("db_location") or None
	lockstring = compose_room_default(
		user_id=getattr(getattr(request, "user", None), "id", 0),
		creator_id=None,
	)
	return create_object(
		typeclass=_room_typeclass_path(),
		key=data.get("db_key", ""),
		location=location,
		home=location,
		locks=lockstring,
		attributes=_desc_attributes(desc=data.get("desc") or data.get("db_desc") or "") or None,
	)

def _create_exit(source_room, data, request: HttpRequest, aliases: list[str], key: str | None = None):
	"""Create an exit through Evennia's typeclass-aware create API."""
	lockstring = _combined_lockstring(
		compose_exit_default(
			user_id=getattr(getattr(request, "user", None), "id", 0),
			creator_id=None,
		),
		data.get("lockstring") or "",
	)
	return create_object(
		typeclass=_exit_typeclass_path(),
		key=key or data["key"],
		location=source_room,
		home=source_room,
		destination=data["destination"],
		aliases=aliases or None,
		locks=lockstring,
		attributes=_desc_attributes(
			desc=data.get("description") or "",
			err_msg=data.get("err_msg") or "",
		) or None,
	)

def _exit_source_room(ex):
	"""Return an exit's source room across real Evennia objects and tests."""
	return getattr(ex, "location", None) or getattr(ex, "db_location", None)

def _normalized_exit_terms(key: str, aliases: list[str]) -> set[str]:
	"""Normalize exit command keys and aliases for conflict checks."""
	return {term for term in [str(key or "").strip().lower(), *(str(alias or "").strip().lower() for alias in aliases)] if term}

def _existing_exit_terms(ex) -> set[str]:
	"""Return normalized command terms already claimed by an exit."""
	aliases = ex.aliases.all() if hasattr(getattr(ex, "aliases", None), "all") else []
	return _normalized_exit_terms(getattr(ex, "key", getattr(ex, "db_key", "")), aliases)

def _reverse_aliases(forward_key: str, forward_aliases: list[str], reverse_key: str) -> list[str]:
	"""Generate safe directional aliases for an auto-created reverse exit."""
	aliases = []
	seen = _normalized_exit_terms(reverse_key, [forward_key, *forward_aliases])
	for source in [forward_key, *forward_aliases]:
		reverse_alias = reverse_dir(source)
		normalized = str(reverse_alias or "").strip().lower()
		if not normalized or normalized in seen:
			continue
		aliases.append(reverse_alias)
		seen.add(normalized)
	return aliases

def _exit_name_conflict(source_room, key: str, aliases: list[str], exclude=None):
	"""Find another exit in the source room using any requested key or alias."""
	if not source_room:
		return None
	wanted = _normalized_exit_terms(key, aliases)
	source_id = getattr(source_room, "id", source_room)
	exclude_id = getattr(exclude, "id", None)
	for existing in _exit_qs().filter(db_location_id=source_id):
		if exclude_id is not None and getattr(existing, "id", None) == exclude_id:
			continue
		overlap = wanted & _existing_exit_terms(existing)
		if overlap:
			return sorted(overlap)[0], existing
	return None

def _duplicate_exit_response(conflict, source_room):
	"""Return a consistent AJAX-safe duplicate error response."""
	term, existing = conflict
	room_name = getattr(source_room, "key", getattr(source_room, "db_key", source_room))
	return JsonResponse(
		{
			"ok": False,
			"error": f"Exit key or alias '{term}' already exists in {room_name} on exit #{existing.id}.",
		},
		status=400,
	)

def _refresh_exit_cmdset(ex) -> None:
	"""Rebuild an exit's dynamic ExitCmdSet after command-affecting edits."""
	refresh = getattr(ex, "at_cmdset_get", None)
	if callable(refresh):
		refresh(force_init=True)

@builder_required
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

@builder_required
def room_new(request: HttpRequest):
	"""Create a new room."""
	if request.method == "POST":
		form = RoomForm(request.POST)
		if form.is_valid():
			data = getattr(form, "cleaned_data", form.data)
			room = _create_room(data, request)
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

@builder_required
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

@builder_required
def room_spawns(request: HttpRequest, pk: int):
	"""Edit encounter settings and Pokemon spawn rows for a room."""
	room = get_object_or_404(_room_qs(), pk=pk)
	saved = False
	preview_text = ""
	roll_text = ""
	preview_error = ""

	if request.method == "POST":
		settings_form = EncounterSettingsForm(request.POST)
		spawn_formset = _spawn_entry_formset(request.POST)
		preview_form = SpawnPreviewForm(request.POST)
		if settings_form.is_valid() and spawn_formset.is_valid() and preview_form.is_valid():
			spawn_entries = _spawn_entries_from_formset(spawn_formset)
			if request.POST.get("action") == "save":
				_save_room_encounters(room, settings_form.cleaned_data, spawn_entries)
				saved = True
			preview_text, roll_text, preview_error = _spawn_outputs_for_entries(
				room,
				spawn_entries,
				settings_form.cleaned_data,
				preview_form.cleaned_data,
			)
	else:
		settings_form = EncounterSettingsForm(initial=_encounter_settings_initial(room))
		spawn_formset = _spawn_entry_formset(initial=_spawn_form_initial(room))
		preview_form = SpawnPreviewForm(initial={"preview_band": "", "roll_band": "1", "roll_count": 100})
		preview_text, roll_text, preview_error = _spawn_outputs_for_room(room)

	return render(
		request,
		"roomeditor/room_spawns.html",
		{
			"room": room,
			"settings_form": settings_form,
			"spawn_formset": spawn_formset,
			"preview_form": preview_form,
			"preview_text": preview_text,
			"roll_text": roll_text,
			"preview_error": preview_error,
			"saved": saved,
			"spawn_source": _room_spawn_source(room),
		},
	)

@builder_required
@require_POST
def room_delete(request: HttpRequest, pk: int):
	"""Delete a room."""
	room = get_object_or_404(_room_qs(), pk=pk)
	room.delete()
	if request.headers.get("X-Requested-With") == "XMLHttpRequest":
		return JsonResponse({"ok": True})
	return redirect("roomeditor:room-list")

@builder_required
@require_POST
def ansi_preview(request: HttpRequest):
	"""Return ANSI text rendered to HTML."""
	text = request.POST.get("text", "")
	html = parse_html(text, strip_ansi=False)
	return JsonResponse({"html": html})

@builder_required
def exit_new(request: HttpRequest, room_pk: int):
	"""Create a new exit from a room."""
	room = get_object_or_404(_room_qs(), pk=room_pk)
	if request.method == "POST":
		form = ExitForm(request.POST)
		if form.is_valid():
			aliases = form.cleaned_alias_list()
			conflict = _exit_name_conflict(room, form.cleaned_data["key"], aliases)
			if conflict:
				return _duplicate_exit_response(conflict, room)
			rev_key = reverse_dir(form.cleaned_data["key"]) if form.cleaned_data.get("auto_reverse") else None
			reverse_aliases = []
			if rev_key:
				reverse_aliases = _reverse_aliases(form.cleaned_data["key"], aliases, rev_key)
				rev_conflict = _exit_name_conflict(form.cleaned_data["destination"], rev_key, reverse_aliases)
				if rev_conflict:
					return _duplicate_exit_response(rev_conflict, form.cleaned_data["destination"])
			with transaction.atomic():
				ex = _create_exit(room, form.cleaned_data, request, aliases)
				if rev_key:
					reverse_data = {**form.cleaned_data, "destination": room}
					_create_exit(form.cleaned_data["destination"], reverse_data, request, reverse_aliases, key=rev_key)
			if request.headers.get("X-Requested-With") == "XMLHttpRequest":
				html = render(request, "roomeditor/_exit_row.html", {"ex": ex}).content.decode("utf-8")
				return JsonResponse({"ok": True, "row_html": html})
			return redirect("roomeditor:room_edit", pk=room.pk)
		elif request.headers.get("X-Requested-With") == "XMLHttpRequest":
			return JsonResponse({"ok": False, "error": form.errors.as_text()}, status=400)
	else:
		form = ExitForm()
	return render(request, "roomeditor/_exit_form.html", {"form": form, "room": room})

@builder_required
def exit_edit(request: HttpRequest, pk: int):
	"""Edit an existing exit."""
	ex = get_object_or_404(_exit_qs(), pk=pk)
	if request.method == "POST":
		form = ExitForm(request.POST)
		if form.is_valid():
			aliases = form.cleaned_alias_list()
			source_room = _exit_source_room(ex)
			conflict = _exit_name_conflict(source_room, form.cleaned_data["key"], aliases, exclude=ex)
			if conflict:
				return _duplicate_exit_response(conflict, source_room)
			with transaction.atomic():
				ex.key = form.cleaned_data["key"]
				ex.destination = form.cleaned_data["destination"]
				ex.aliases.clear()
				if aliases:
					_add_aliases(ex, aliases)
				ex.db.desc = form.cleaned_data.get("description") or ""
				ex.locks.clear()
				if form.cleaned_data.get("lockstring"):
					ex.locks.add(form.cleaned_data["lockstring"])
				ex.db.err_traverse = form.cleaned_data.get("err_msg") or ""
				_refresh_exit_cmdset(ex)
			ex.save()
			if request.headers.get("X-Requested-With") == "XMLHttpRequest":
				row = render(request, "roomeditor/_exit_row.html", {"ex": ex}).content.decode("utf-8")
				return JsonResponse({"ok": True, "row_html": row})
			return redirect("roomeditor:room_edit", pk=ex.db_location_id)
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

@builder_required
@require_POST
def exit_delete(request: HttpRequest, pk: int):
	"""Delete an exit."""
	ex = get_object_or_404(_exit_qs(), pk=pk)
	room_pk = ex.db_location_id
	ex.delete()
	if request.headers.get("X-Requested-With") == "XMLHttpRequest":
		return JsonResponse({"ok": True})
	return redirect("roomeditor:room_edit", pk=room_pk)

@builder_required
def room_search_api(request: HttpRequest):
	"""Return rooms matching a query for autocomplete."""
	q = (request.GET.get("q") or "").strip()
	results = []
	if q:
		qs = _room_qs().filter(db_key__icontains=q).order_by("db_key")[:20]
		results = [{"id": r.id, "text": f"{r.key} (#{r.id})"} for r in qs]
	return JsonResponse({"results": results})
