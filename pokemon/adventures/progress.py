"""Durable Adventure participation, outcome, and reward helpers."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone as dt_timezone
from typing import Any

from django.db import transaction
from django.utils import timezone

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


def finalize_completion(session: Any) -> tuple[bool, str]:
    """Record completion and atomically grant an eligible first-clear item.

    Returns ``(claimed, message)``. A failed inventory delivery leaves the
    reward unclaimed so a later completion/recovery pass can retry it.
    """

    player = getattr(session, "leader", None)
    template = get_template(getattr(session, "template_key", ""))
    if player is None or template is None:
        return False, ""

    with transaction.atomic():
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
            return False, "Your first-clear reward is recorded and can be claimed after inventory is available."
        try:
            add_item(participation.reward_item, participation.reward_amount)
        except Exception:
            return False, "Your first-clear reward is recorded and remains unclaimed."

        participation.reward_claimed_at = _now()
        participation.save(update_fields=("reward_claimed_at",))
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
        return ""
