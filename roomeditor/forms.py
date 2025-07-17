from django import forms
from django.utils.safestring import mark_safe
from evennia.objects.models import ObjectDB
import pkgutil
import importlib
import inspect
import sys

try:
    from evennia.objects.objects import DefaultRoom as _DefaultRoom
except Exception:  # pragma: no cover - fallback when Evennia isn't available
    class _DefaultRoom:
        pass

DefaultRoom = _DefaultRoom
import typeclasses


def _collect_room_types() -> list[tuple[str, str]]:
    """Return list of (path, label) for all room typeclasses."""
    base = [
        ("typeclasses.rooms.Room", "Room"),
        ("typeclasses.rooms.FusionRoom", "Fusion Room"),
        ("typeclasses.battleroom.BattleRoom", "Battle Room"),
        ("typeclasses.maproom.MapRoom", "Map Room"),
    ]
    if not getattr(typeclasses, "__path__", None):
        return base
    # Ensure the Exit module is loaded so tests that stub it don't override it.
    if "typeclasses.exits" not in sys.modules:
        try:
            importlib.import_module("typeclasses.exits")
        except Exception:
            pass
    choices = list(base)
    for _, modname, ispkg in pkgutil.walk_packages(
        typeclasses.__path__, prefix="typeclasses."
    ):
        if ispkg or modname.endswith(".exits"):
            continue
        try:
            mod = importlib.import_module(modname)
        except Exception:
            continue
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if obj.__module__ != modname:
                continue
            try:
                if issubclass(obj, DefaultRoom) and obj is not DefaultRoom:
                    path = f"{obj.__module__}.{name}"
                    label = name.replace("_", " ")
                    if (path, label) not in choices:
                        choices.append((path, label))
            except Exception:
                continue
    choices.sort(key=lambda c: c[1].lower())
    return choices


class RoomForm(forms.Form):
    ROOM_CLASS_CHOICES = _collect_room_types()

    ROOM_CLASS_HELP = (
        "Room - standard room. "
        "Fusion Room - supports Pokémon centers, item shops and hunting. "
        "Battle Room - temporary space for battles. "
        "Map Room - displays a simple 2D map."
    )

    room_class = forms.ChoiceField(
        label="Room Class",
        choices=(),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["room_class"].choices = self.ROOM_CLASS_CHOICES


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

