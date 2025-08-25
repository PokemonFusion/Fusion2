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


if hasattr(ObjectDB, '_meta'):
	class RoomForm(forms.ModelForm):
		"""Minimal form for editing room attributes."""

		class Meta:
			model = ObjectDB
			fields = ['db_key', 'db_desc']
			widgets = {
				'db_desc': forms.Textarea(attrs={'data-role': 'ansi-preview-source'})
			}
else:
	class RoomForm(forms.Form):
		# Fallback form used during tests when ObjectDB is a dummy.
		db_key = forms.CharField(label='Key')
		db_desc = forms.CharField(widget=forms.Textarea(attrs={'data-role': 'ansi-preview-source'}), required=False)
