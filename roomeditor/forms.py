from django import forms
from django.utils.safestring import mark_safe
from evennia.objects.models import ObjectDB


class RoomForm(forms.Form):
    ROOM_CLASS_CHOICES = [
        ("typeclasses.rooms.Room", "Room"),
        ("typeclasses.rooms.FusionRoom", "Fusion Room"),
        ("typeclasses.rooms.BattleRoom", "Battle Room"),
        ("typeclasses.rooms.MapRoom", "Map Room"),
    ]

    ROOM_CLASS_HELP = (
        "Room - standard room. "
        "Fusion Room - supports Pokémon centers, item shops and hunting. "
        "Battle Room - temporary space for battles. "
        "Map Room - displays a simple 2D map."
    )

    room_class = forms.ChoiceField(
        label="Room Class",
        choices=ROOM_CLASS_CHOICES,
        help_text=ROOM_CLASS_HELP,
        widget=forms.Select(attrs={"title": ROOM_CLASS_HELP}),
    )
    name = forms.CharField(
        label="Name",
        max_length=80,
        widget=forms.TextInput(attrs={"size": 60}),
    )
    desc = forms.CharField(
        label="Description",
        widget=forms.Textarea,
        required=False,
        help_text=mark_safe('Use Evennia color codes. <a href="/ansi/" target="_blank">ANSI reference</a>'),
    )
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
    desc = forms.CharField(
        label="Description",
        widget=forms.Textarea,
        required=False,
        help_text=mark_safe('Use Evennia color codes. <a href="/ansi/" target="_blank">ANSI reference</a>'),
    )
    err_traverse = forms.CharField(
        label="Failure Message",
        required=False,
        help_text="Message shown when traversal fails.",
    )
    locks = forms.CharField(label="Lockstring", required=False)
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

