from django import forms


class RoomForm(forms.Form):
    name = forms.CharField(label="Name", max_length=80)
    desc = forms.CharField(label="Description", widget=forms.Textarea, required=False)
    is_center = forms.BooleanField(label="Pokémon Center", required=False)
    is_shop = forms.BooleanField(label="Item Shop", required=False)
    has_hunting = forms.BooleanField(label="Allow Hunting", required=False)
    hunt_table = forms.CharField(
        label="Hunt Table", required=False,
        help_text="Format: name:rate, name:rate",
    )


class ExitForm(forms.Form):
    direction = forms.CharField(label="Direction", max_length=32)
    dest_id = forms.IntegerField(label="Destination Room ID")
