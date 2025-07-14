from django import forms
from evennia.objects.models import ObjectDB


class RoomForm(forms.Form):
    name = forms.CharField(
        label="Name",
        max_length=80,
        widget=forms.TextInput(attrs={"size": 60}),
    )
    desc = forms.CharField(label="Description", widget=forms.Textarea, required=False)
    is_center = forms.BooleanField(label="Pokémon Center", required=False)
    is_shop = forms.BooleanField(label="Item Shop", required=False)
    has_hunting = forms.BooleanField(label="Allow Hunting", required=False)
    hunt_table = forms.CharField(
        label="Hunt Table", required=False,
        help_text="Format: name:rate, name:rate",
    )


class ExitForm(forms.Form):
    direction = forms.CharField(
        label="Direction",
        max_length=32,
        widget=forms.TextInput(
            attrs={
                "title": "Use Evennia color tags such as |gnorth|n to style the exit name.",
            }
        ),
    )
    dest_id = forms.ChoiceField(label="Destination Room", choices=())
    aliases = forms.CharField(
        label="Aliases",
        required=False,
        help_text="Separate aliases with commas or semicolons.",
    )
    exit_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = ObjectDB.objects.filter(
            db_location__isnull=True, db_typeclass_path__contains="rooms"
        )
        if hasattr(queryset, "order_by"):
            queryset = queryset.order_by("id")
        self.fields["dest_id"].choices = [
            (obj.id, f"{obj.id} - {getattr(obj, 'key', '')}") for obj in queryset
        ]

