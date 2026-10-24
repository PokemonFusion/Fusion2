"""Server-bound native pair reviews; confirmation revalidates all saved terms."""

from django.db import transaction
from django.utils import timezone

from pokemon.services.necrozma import NecrozmaService
from pokemon.services.necrozma_guards import NecrozmaError


def close_review(caller, menu):
    """Leave the review without synthesizing another player command."""


def node_review(caller, raw_string="", **kwargs):
    """Show exactly the server's current request, never client-supplied terms."""
    from pokemon.models.necrozma import NecrozmaOperation

    try:
        service = NecrozmaService(caller)
        operation = NecrozmaOperation.objects.get(pk=kwargs["request_id"], storage__user_id=service.actor_id)
        if operation.state != "pending" or operation.expires_at <= timezone.now():
            return "That native pair review is no longer pending. Start a fresh review with +necrozma.", None
        terms = operation.terms
        rows = {row["unique_id"]: row for row in terms["snapshot"]["sources"]}
        host, partner = rows[terms["host"]], rows[terms["companion"]]
        locations = {row["pokemon_id"]: row for row in terms["snapshot"]["placements"]}
        def describe(row):
            place = locations[row["unique_id"]]
            location = (f"party slot {place['slot']}" if place["location_type"] == "party" else
                        f"box {place['box_id']} position {place['box_position']}" if place["location_type"] == "box" else
                        "reserved native companion")
            return f"{row['nickname'] or row['species']} / {row['species']} — {row['unique_id']} ({location}); held {row['held_item'] or 'nothing'}"
        lines = [f"Review native Necrozma {operation.action} (free):", "Host: " + describe(host),
                 "Companion: " + describe(partner), f"Form: {terms['target']}; source {terms['source']} in move slot {terms['slot']}."]
        if operation.action == "combine":
            active = next((row for row in terms["snapshot"]["active"] if row["pokemon_id"] == terms["host"] and row["slot"] == terms["slot"]), None)
            if active:
                lines.append(f"Displaced slot: {active['move__name']}, saved PP {active['current_pp']} (inactive until separation).")
            else:
                lines.append("Displaced slot: empty; the same empty gap returns on separation.")
            resource = next((row for row in terms["snapshot"]["resources"] if row["host_id"] == terms["host"] and row["source"] == terms["source"]), None)
            lines.extend([f"Source PP: {resource['current_pp'] if resource else 5}; saved PP, including zero, persists across cycles.",
                "The unchanged companion is reserved and cannot battle, move, train, use items or transfer until separation."])
        lines.extend(["Separation retains current host health, status and progress; only the bound displaced slot returns. "
                      "A party companion returns to its old slot if free, then a free slot, then a box. "
                      "A boxed companion prefers its valid previous box. No occupant is evicted.",
                      "This exact review expires after five minutes. Confirm yes or no."])
        return "\n".join(lines), [
            {"key": ("yes", "y"), "desc": "Confirm these exact terms", "goto": (_confirm, {"request_id": str(operation.pk)})},
            {"key": ("no", "n", "cancel"), "desc": "Cancel without changes", "goto": (_cancel, {"request_id": str(operation.pk)})},
        ]
    except (NecrozmaOperation.DoesNotExist, KeyError, ValueError) as error:
        return (str(error) if isinstance(error, NecrozmaError) else "That native pair review is unavailable."), None


def _confirm(caller, raw_string, **kwargs):
    """Publish one correct success after the enclosing transaction commits."""
    try:
        result, applied = NecrozmaService(caller).commit(kwargs["request_id"])
        if result.get("error"):
            caller.msg(result["error"])
        elif applied:
            if result["action"] == "combine":
                message = (f"{result['old_name']} became {result['target']}. Native pair {result['lifecycle']}: "
                    f"host {result['host']}; companion {result['companion']} is safely reserved. "
                    f"{result['source']} occupies move slot {result['slot']} with {result['pp']} PP.")
            else:
                location = result["return"]
                destination = f"party slot {location['slot']}" if location["location"] == "party" else f"{location['box']}, position {location['position']}"
                message = (f"{result['old_name']} returned to Necrozma on the same host {result['host']}. "
                           f"Companion {result['companion']} returned to {destination}; current health and progress were retained.")
            transaction.on_commit(lambda: caller.msg(message), robust=True)
        else:
            caller.msg("That request was already completed. No effect was repeated.")
    except (ValueError, KeyError) as error:
        caller.msg(str(error))
    return "node_done"


def _cancel(caller, raw_string, **kwargs):
    """Retire only the current character's review, preserving both sources."""
    try:
        cancelled = NecrozmaService(caller).cancel(kwargs["request_id"])
        message = ("Native combination review cancelled. Neither Pokemon was changed." if cancelled else
                   "That review was already closed. No effect was repeated.")
        transaction.on_commit(lambda: caller.msg(message), robust=True)
    except ValueError as error:
        caller.msg(str(error))
    return "node_done"


def node_done(caller, raw_string="", **kwargs):
    """Exit without inserting a synthetic look or repeating a paid success."""
    return "", None
