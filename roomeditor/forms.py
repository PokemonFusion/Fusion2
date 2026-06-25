# Tabs are intentional.
from __future__ import annotations

import re

from django import forms
from evennia.objects.models import ObjectDB

from pokemon.spawns.adapters import SpawnAdapterError, normalize_band
from pokemon.spawns.constants import FREQUENCIES, SpawnFrequency
from utils.build_utils import normalize_aliases


FREQUENCY_CHOICES = [(frequency, frequency.title()) for frequency in FREQUENCIES]
BAND_CHOICES = [("", "All bands"), ("1", "Band 1"), ("2", "Band 2"), ("3", "Band 3"), ("4", "Band 4")]


class ExitForm(forms.Form):
    """Form for creating or editing exits."""

    key = forms.CharField(label="Exit name (direction)", max_length=64)
    try:
        empty_qs = ObjectDB.objects.none()
    except AttributeError:

        class _EmptyQS(list):
            def all(self):
                return self

        empty_qs = _EmptyQS()
    destination = forms.ModelChoiceField(
        queryset=empty_qs,
        widget=forms.Select(attrs={"data-role": "destination-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = ObjectDB.objects.filter(db_typeclass_path__icontains=".rooms.")
        if hasattr(qs, "order_by"):
            qs = qs.order_by("db_key")
        self.fields["destination"].queryset = qs
        # show both name and ID for clarity when selecting destinations
        self.fields["destination"].label_from_instance = (
            lambda obj: f"{obj.db_key} (#{obj.id})"
        )

    description = forms.CharField(label="Description", widget=forms.Textarea, required=False)
    lockstring = forms.CharField(
        label="Lockstring",
        required=False,
        help_text="Evennia lockstring, e.g. 'traverse:perm(Builder)'",
    )
    err_msg = forms.CharField(label="Failure message", required=False)
    aliases = forms.CharField(label="Aliases (comma-separated)", required=False)
    auto_reverse = forms.BooleanField(label="Auto-create reverse exit", required=False, initial=True)

    def cleaned_alias_list(self) -> list[str]:
        """Return aliases as a cleaned list."""
        return normalize_aliases(self.cleaned_data.get("aliases", ""))


if hasattr(ObjectDB, "_meta"):

    class RoomForm(forms.ModelForm):
        """Form for editing room attributes."""

        # expose desc as a normal form field, stored on obj.db.desc
        desc = forms.CharField(
            required=False,
            label="Description",
            widget=forms.Textarea(attrs={"data-role": "ansi-preview-source"}),
        )

        class Meta:
            model = ObjectDB
            fields = ["db_key", "db_location", "db_lock_storage"]
            labels = {
                "db_key": "Name",
                "db_location": "Room parent",
            }

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if self.instance and hasattr(self.instance, "db"):
                self.fields["desc"].initial = getattr(self.instance.db, "desc", "")

        def save(self, commit: bool = True):
            """Persist editable room fields through Evennia handlers."""
            obj = self.instance
            obj.key = self.cleaned_data.get("db_key", obj.key)
            obj.location = self.cleaned_data.get("db_location") or None
            obj.locks.clear()
            lockstring = self.cleaned_data.get("db_lock_storage") or ""
            if lockstring:
                obj.locks.add(lockstring)
            obj.db.desc = self.cleaned_data.get("desc", "")
            if commit:
                obj.save()
            return obj
else:

    class RoomForm(forms.Form):
        # Fallback form used during tests when ObjectDB is a dummy.
        db_key = forms.CharField(label="Name")
        db_location = forms.CharField(label="Room parent", required=False)
        db_lock_storage = forms.CharField(required=False)
        desc = forms.CharField(
            widget=forms.Textarea(attrs={"data-role": "ansi-preview-source"}),
            required=False,
        )


class EncounterSettingsForm(forms.Form):
    """Room-level encounter controls stored on ``room.db``."""

    allow_hunting = forms.BooleanField(label="Allow hunting", required=False)
    encounter_rate = forms.IntegerField(label="Encounter rate", min_value=0, max_value=100, initial=100)
    npc_chance = forms.IntegerField(label="NPC battle chance", min_value=0, max_value=100, initial=0)
    itemfinder_rate = forms.IntegerField(label="Itemfinder rate", min_value=0, max_value=100, initial=0)
    noitem = forms.BooleanField(label="Disable itemfinder", required=False)
    tp_cost = forms.IntegerField(label="Training point cost", min_value=0, initial=0)
    weather = forms.CharField(label="Weather", max_length=32, required=False, initial="clear")
    spawn_area_key = forms.CharField(label="Spawn area key", max_length=80, required=False)


class SpawnEntryForm(forms.Form):
    """One editable Pokemon spawn-table row."""

    species = forms.CharField(label="Species", max_length=80, required=False)
    frequency = forms.ChoiceField(label="Frequency", choices=FREQUENCY_CHOICES, initial=SpawnFrequency.COMMON.value)
    bands = forms.CharField(label="Bands", max_length=40, required=False, initial="1")
    enabled = forms.BooleanField(label="Enabled", required=False, initial=True)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("DELETE"):
            return cleaned

        species = (cleaned.get("species") or "").strip()
        bands_raw = cleaned.get("bands")
        if not species:
            cleaned["bands"] = []
            return cleaned

        bands = self._clean_bands(bands_raw)
        frequency = cleaned.get("frequency") or SpawnFrequency.COMMON.value
        if frequency == SpawnFrequency.SPECIAL.value and bands != ["T4"]:
            raise forms.ValidationError("Special spawns are limited to band 4.")

        cleaned["species"] = species
        cleaned["bands"] = bands
        return cleaned

    def _clean_bands(self, value: str | None) -> list[str]:
        parts = [part for part in re.split(r"[,\s]+", (value or "1").strip()) if part]
        if not parts:
            parts = ["1"]

        bands = []
        seen = set()
        for part in parts:
            try:
                band = normalize_band(part)
            except SpawnAdapterError as exc:
                raise forms.ValidationError(str(exc)) from exc
            tier = f"T{band}"
            if tier in seen:
                continue
            bands.append(tier)
            seen.add(tier)
        return bands


class SpawnPreviewForm(forms.Form):
    """Preview controls for spawn setup output."""

    preview_band = forms.ChoiceField(label="Preview band", choices=BAND_CHOICES, required=False)
    roll_band = forms.ChoiceField(label="Roll band", choices=BAND_CHOICES[1:], initial="1")
    roll_count = forms.IntegerField(label="Roll count", min_value=1, max_value=200, initial=100)
TRAVERSE_CHOICES = [
	("all()",            "Everyone"),
	("perm(Builder)",    "Builders"),
	("perm(Admin)",      "Admins"),
	("holds(key)",       "Holds a key item"),
	("expr",             "Custom expression (advanced)"),
]


class LockComposerForm(forms.Form):
	"""Form used to compose default lockstrings."""

	include_creator = forms.BooleanField(
		required=False,
		initial=True,
		help_text="Include the creating object id() in control/delete/edit",
	)
	traverse_choice = forms.ChoiceField(
		choices=TRAVERSE_CHOICES, required=True, initial="all()"
	)
	traverse_custom = forms.CharField(
		required=False, help_text="Only used if 'Custom' is selected."
	)
	# Raw textareas (advanced)
	room_lockstring = forms.CharField(
		widget=forms.Textarea(attrs={"rows":4}), required=False
	)
	exit_lockstring = forms.CharField(
		widget=forms.Textarea(attrs={"rows":4}), required=False
	)
