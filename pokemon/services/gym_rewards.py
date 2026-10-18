"""Durable, retryable badge delivery for confirmed gym victories."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from pokemon.services.gym_leaders import grant_gym_badge_for_victory

logger = logging.getLogger(__name__)
PENDING_MESSAGE = "Your gym badge award is pending. Use +gym claim to retry it."


def _metadata_snapshot(value):
    """Detach nested Evennia Saver containers before writing a JSON victory row."""
    if isinstance(value, Mapping):
        return {key: _metadata_snapshot(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_metadata_snapshot(item) for item in value]
    return value


@dataclass(frozen=True)
class GymClaimResult:
    """Report whether a saved victory's badge has been delivered."""

    completed: bool
    message: str
    awarded: bool = False
    award_kind: str = ""


class GymVictoryRewards:
    """Record victories and claim awards only for the supplied character."""

    def __init__(self, player):
        """Use the persistent character behind an optional session transport."""
        from pokemon.services.battle_rewards import BattleRewards

        self.player = BattleRewards.character(player)

    def record(self, victory_id, metadata):
        """Save the first victory snapshot before attempting badge delivery.

        The UUID is also saved in the battle result, so rebuilds reuse the same
        record even if numeric battle IDs are later reused. Existing records,
        including claimed ones, must never be reset by a replayed callback.
        """
        if metadata.get("source_type") != "gym_leader":
            raise ValueError("Only confirmed gym victories can be recorded.")
        victory, _created = self._model().objects.get_or_create(
            pk=UUID(str(victory_id)),
            defaults={"player": self.player, "metadata": _metadata_snapshot(metadata)},
        )
        if victory.player_id != self.player.pk:
            raise ValueError("This gym victory belongs to another character.")
        return victory

    def claim(self, victory_id) -> GymClaimResult:
        """Commit the badge and claim marker together, retaining failed claims."""
        from django.db import transaction
        from django.utils import timezone

        model = self._model()
        with transaction.atomic():
            # Serialize claims for different victories of the same character,
            # including two rematches awarding the same badge.
            player_model = model._meta.get_field("player").remote_field.model
            player_model.objects.select_for_update().get(pk=self.player.pk)
            victory = model.objects.select_for_update().get(pk=victory_id, player=self.player)
            if victory.claimed_at is not None:
                return GymClaimResult(True, "This gym victory has already been claimed.", award_kind=victory.award_kind)
            result = grant_gym_badge_for_victory(self.player, victory.metadata)
            if result is None or not (result.awarded or result.already_had):
                detail = f"{result.message} " if result and result.message else ""
                return GymClaimResult(False, detail + PENDING_MESSAGE)
            victory.claimed_at = timezone.now()
            victory.award_kind = "first_clear" if result.awarded else "rematch"
            victory.save(update_fields=("claimed_at", "award_kind"))
        message = result.message
        if victory.metadata.get("reward_policy") == "badge_only":
            message = (f"First clear complete: you earned the {result.badge_name}!" if result.awarded else
                       "Rematch complete. Your existing badge is unchanged; no repeat rewards are awarded.")
        return GymClaimResult(True, message, awarded=result.awarded, award_kind=victory.award_kind)

    def claim_pending(self) -> tuple[GymClaimResult, ...]:
        """Retry this character's unclaimed victories independently."""
        victory_ids = list(
            self._model().objects.filter(player=self.player, claimed_at__isnull=True)
            .values_list("pk", flat=True)
        )
        results = []
        for victory_id in victory_ids:
            try:
                results.append(self.claim(victory_id))
            except Exception:
                logger.exception("Could not claim gym victory %s", victory_id)
                results.append(GymClaimResult(False, PENDING_MESSAGE))
        return tuple(results)

    @staticmethod
    def _model():
        """Load the production model only when persistence is needed."""
        from pokemon.models.gym import GymVictory

        return GymVictory
