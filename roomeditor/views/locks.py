"""Views for composing and validating default lockstrings."""
from __future__ import annotations

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render

from .. import forms
from ..utils.locks import compose_exit_default, compose_room_default, validate_lockstring


def _is_builder(user):
    """Determine if the user is allowed to edit lock defaults."""
    return user.is_superuser or user.has_perm("roomeditor.change_lockdefaults")


@login_required
@user_passes_test(_is_builder)
def edit_defaults(request: HttpRequest):
    """Compose and preview default lockstrings."""
    if request.method == "POST":
        form = forms.LockComposerForm(request.POST)
        if form.is_valid():
            include_creator = form.cleaned_data["include_creator"]
            traverse_choice = form.cleaned_data["traverse_choice"]
            traverse_custom = form.cleaned_data["traverse_custom"].strip()

            traverse = traverse_custom if traverse_choice == "expr" and traverse_custom else traverse_choice

            creator_id = request.user.id if include_creator else None
            composed_room = compose_room_default(request.user.id, creator_id)
            composed_exit = compose_exit_default(request.user.id, creator_id, traverse)

            room_final = form.cleaned_data["room_lockstring"].strip() or composed_room
            exit_final = form.cleaned_data["exit_lockstring"].strip() or composed_exit

            ok_r, msg_r = validate_lockstring(room_final)
            ok_e, msg_e = validate_lockstring(exit_final)

            return render(
                request,
                "roomeditor/locks_edit.html",
                {
                    "form": form,
                    "room_validation": (ok_r, msg_r),
                    "exit_validation": (ok_e, msg_e),
                    "composed_room": composed_room,
                    "composed_exit": composed_exit,
                },
            )
    else:
        creator_id = request.user.id
        composed_room = compose_room_default(request.user.id, creator_id)
        composed_exit = compose_exit_default(request.user.id, creator_id, "all()")
        form = forms.LockComposerForm(
            initial={
                "include_creator": True,
                "traverse_choice": "all()",
                "room_lockstring": composed_room,
                "exit_lockstring": composed_exit,
            }
        )

    return render(
        request,
        "roomeditor/locks_edit.html",
        {
            "form": form,
            "composed_room": composed_room,
            "composed_exit": composed_exit,
        },
    )


@login_required
@user_passes_test(_is_builder)
def api_validate_lockstring(request: HttpRequest):
    """Validate a lockstring via AJAX."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "message": "POST required"}, status=405)
    lockstring = (request.POST.get("lockstring") or "").strip()
    ok, message = validate_lockstring(lockstring)
    return JsonResponse({"ok": ok, "message": message})
