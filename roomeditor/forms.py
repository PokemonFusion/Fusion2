# Tabs are intentional.
from __future__ import annotations

from django import forms
from evennia.objects.models import ObjectDB

from utils.build_utils import normalize_aliases


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
            """Persist desc to Attribute storage."""
            obj = super().save(commit=commit)
            obj.db.desc = self.cleaned_data.get("desc", "")
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
