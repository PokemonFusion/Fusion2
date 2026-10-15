"""Durable Adventure participation, outcome, and reward helpers."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone as dt_timezone
from typing import Any

from django.db import transaction
from django.utils import timezone

from .constants import STATE_COMPLETED
from .templates import get_template


def _model():
    from pokemon.models.adventures import AdventureParticipation

    return AdventureParticipation


def _now():
    try:
        return timezone.now()
    except Exception:
        return datetime.now(dt_timezone.utc)


def ensure_participation(session: Any, player: Any):
    """Return the durable per-player row for ``session``."""

    participation, _created = _model().objects.get_or_create(session=session, player=player)
    return participation


def record_choice(session: Any, player: Any, *, route_key: str, outcome_key: str) -> None:
    """Persist a player's authored route selection."""

    participation = ensure_participation(session, player)
    participation.route_key = route_key
    participation.outcome_key = outcome_key
    participation.save(update_fields=("route_key", "outcome_key"))


def record_encounter_result(session: Any, player: Any, result: str) -> None:
    """Persist a terminal encounter result without granting completion rewards."""

    participation = ensure_participation(session, player)
    participation.encounter_result = result
    participation.save(update_fields=("encounter_result",))


def _lock_player(player: Any) -> None:
    """Serialize first-clear decisions across a character's different runs."""

    from evennia.objects.models import ObjectDB

    ObjectDB.objects.select_for_update().get(pk=player.pk)


def finalize_completion(session: Any) -> tuple[bool, str]:
    """Record completion and atomically grant an eligible first-clear item.

    Returns ``(claimed, message)``. A failed inventory delivery leaves the
    reward unclaimed so a later completion/recovery pass can retry it.
    """

    player = getattr(session, "leader", None)
    template = get_template(getattr(session, "template_key", ""))
    if player is None or template is None or getattr(session, "state", None) != STATE_COMPLETED:
        return False, ""

    with transaction.atomic():
        _lock_player(player)
        ensure_participation(session, player)
        participation = (
            _model().objects.select_for_update().get(session=session, player=player)
        )
        first_clear = not _model().objects.filter(
            player=player,
            session__template_key=template.key,
            completed_at__isnull=False,
        ).exclude(pk=participation.pk).exists()

        changed: list[str] = []
        if participation.completed_at is None:
            participation.completed_at = _now()
            changed.append("completed_at")
        if first_clear and not participation.reward_item:
            participation.reward_item = template.first_clear_item
            participation.reward_amount = max(1, int(template.first_clear_amount))
            changed.extend(("reward_item", "reward_amount"))
        if changed:
            participation.save(update_fields=tuple(changed))

        if not participation.reward_item or participation.reward_claimed_at is not None:
            return False, ""

        trainer = getattr(player, "trainer", None)
        add_item = getattr(trainer, "add_item", None)
        if not callable(add_item):
            return False, "Your first-clear reward is recorded. Use +adventure/claim after inventory is available."
        try:
            # A savepoint rolls back a partially delivered item as well as a
            # failed claim marker, while retaining the outer reward reservation.
            with transaction.atomic():
                add_item(participation.reward_item, participation.reward_amount)
                participation.reward_claimed_at = _now()
                participation.save(update_fields=("reward_claimed_at",))
        except Exception:
            participation.reward_claimed_at = None
            return False, "Your first-clear reward remains unclaimed. Use +adventure/claim to retry."

        return True, (
            f"First-clear reward: {participation.reward_item} "
            f"x{participation.reward_amount}."
        )


def safe_ensure_participation(session: Any, player: Any) -> None:
    """Create participation when Django is ready; pure unit harnesses may omit it."""

    try:
        ensure_participation(session, player)
    except Exception:
        return


def safe_finalize_completion(session: Any) -> str:
    """Finalize completion without breaking the Adventure on reward failure."""

    try:
        _claimed, message = finalize_completion(session)
        return message
    except Exception:
        return "Your Adventure is complete, but the reward could not be saved. Use +adventure/claim to retry."


def claim_completed_rewards(player: Any) -> str:
    """Retry completed runs belonging to this character, including after leaving."""

    from .sessions import _session_model

    sessions = _session_model().objects.filter(leader=player, state=STATE_COMPLETED).order_by("completed_at", "pk")
    messages = [message for session in sessions if (message := safe_finalize_completion(session))]
    return "\n".join(messages) or "No unclaimed Adventure rewards."
