from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView

from utils.character_profiles import (
    ProfileError,
    delete_profile_field,
    field_key,
    get_profile_fields,
    set_profile_field,
)


def _as_list(value) -> list:
    if value is None:
        return []
    try:
        if hasattr(value, "all"):
            value = value.all()
        return list(value)
    except Exception:
        return []


def _character_id(character):
    for candidate in (character, getattr(character, "dbobj", None), getattr(character, "obj", None)):
        identifier = getattr(candidate, "id", None)
        if identifier is not None:
            return identifier
    return None


def account_profile_characters(account) -> list:
    try:
        return _as_list(account.characters)
    except Exception:
        return []


def character_label(character) -> str:
    return getattr(character, "key", None) or getattr(character, "name", None) or str(character)


def select_profile_character(account, character_id=None):
    characters = account_profile_characters(account)
    if not characters:
        return None

    if character_id:
        for character in characters:
            if str(_character_id(character)) == str(character_id):
                return character

    return characters[0]


def profile_field_rows(character) -> list[dict]:
    if not character:
        return []
    return [{"key": key, **field} for key, field in get_profile_fields(character).items()]


def profile_character_choices(account, selected_character=None) -> list[dict]:
    selected_id = _character_id(selected_character) if selected_character else None
    choices = []
    for character in account_profile_characters(account):
        ident = _character_id(character)
        choices.append(
            {
                "id": ident,
                "name": character_label(character),
                "selected": ident is not None and selected_id is not None and str(ident) == str(selected_id),
            }
        )
    return choices


def apply_profile_editor_action(character, post_data):
    action = (post_data.get("action") or "save").strip().lower()
    if action == "delete":
        label = post_data.get("field_key") or post_data.get("field_name") or ""
        if not delete_profile_field(character, label):
            raise ProfileError("No such profile field.")
        return "Profile field deleted."

    if action != "save":
        raise ProfileError("Unknown profile action.")

    old_key = post_data.get("field_key") or ""
    label = post_data.get("field_name") or old_key
    text = post_data.get("field_text") or ""
    private = bool(post_data.get("private"))
    field = set_profile_field(character, label, text, private=private)
    new_key = field_key(field["label"])
    if old_key and field_key(old_key) != new_key:
        delete_profile_field(character, old_key)
    return f"Profile field '{field['label']}' saved."


class ProfileEditorView(LoginRequiredMixin, TemplateView):
    """Edit profile fields for one of the logged-in account's characters."""

    template_name = "website/profile_editor.html"
    page_title = "Profile Editor"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected = select_profile_character(
            self.request.user,
            self.request.GET.get("character") or kwargs.get("character_id"),
        )
        context["page_title"] = self.page_title
        context["selected_character"] = selected
        context["selected_character_id"] = _character_id(selected) if selected else None
        context["character_choices"] = profile_character_choices(self.request.user, selected)
        context["profile_fields"] = profile_field_rows(selected)
        return context

    def post(self, request, *args, **kwargs):
        selected = select_profile_character(request.user, request.POST.get("character"))
        if not selected:
            messages.error(request, "No editable character was found.")
            return redirect("profile-editor")

        try:
            messages.success(request, apply_profile_editor_action(selected, request.POST))
        except ProfileError as err:
            messages.error(request, str(err))

        return redirect(f"{reverse('profile-editor')}?character={_character_id(selected)}")
