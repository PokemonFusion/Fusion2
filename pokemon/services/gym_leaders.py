"""Gym leader encounter and badge progression helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from typing import Any

from pokemon.services.trainer_encounters import (
    StaticTrainerCheck,
    StaticTrainerTemplateCheck,
    TrainerEncounter,
    TrainerEncounterError,
    check_static_trainer,
    generate_static_trainer_encounter,
)


GYM_LEADER_SOURCE_TYPE = "gym_leader"


@dataclass(frozen=True)
class GymLeaderCheck:
    """Read-only validation summary for a gym leader battle."""

    identifier: str
    found: bool
    name: str = ""
    enabled: bool = False
    eligible: bool = False
    league_key: str = ""
    gym_key: str = ""
    badge_key: str = ""
    badge_name: str = ""
    required_badge_count: int = 0
    badge_count: int = 0
    templates: tuple[StaticTrainerTemplateCheck, ...] = ()
    issues: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    profile: Any = None

    @property
    def template_count(self) -> int:
        return len(self.templates)

    @property
    def can_start_battle(self) -> bool:
        return (
            self.found
            and self.enabled
            and self.eligible
            and bool(self.templates)
            and not self.issues
        )


@dataclass(frozen=True)
class GymBadgeGrantResult:
    """Result of applying a gym badge reward after battle victory."""

    awarded: bool
    already_had: bool
    badge_name: str
    message: str = ""


class GymLeaderError(ValueError):
    """Base error for gym leader encounter failures."""


class GymLeaderNotFoundError(GymLeaderError):
    """Raised when a gym leader profile cannot be found."""


class GymLeaderDisabledError(GymLeaderError):
    """Raised when a gym leader profile is disabled."""


class GymLeaderEligibilityError(GymLeaderError):
    """Raised when a player is not eligible for a gym battle."""


class GymLeaderTeamError(GymLeaderError):
    """Raised when the linked static trainer cannot start a battle."""


def list_gym_leaders(player=None, *, include_disabled: bool = False) -> list[GymLeaderCheck]:
    """Return gym leader profiles with current startup checks."""

    checks: list[GymLeaderCheck] = []
    for profile in _all_profiles():
        check = check_gym_leader(profile, player=player)
        if include_disabled or check.enabled:
            checks.append(check)
    return checks


def check_gym_leader(identifier, *, player=None) -> GymLeaderCheck:
    """Validate whether ``identifier`` can start a gym leader battle."""

    identifier_text = _text(identifier, "")
    try:
        profile = _resolve_gym_leader_profile(identifier)
    except GymLeaderNotFoundError:
        label = identifier_text or "<missing>"
        return GymLeaderCheck(
            identifier=identifier_text,
            found=False,
            name=label,
            issues=(f"Gym leader '{label}' was not found.",),
        )

    static_check = check_static_trainer(getattr(profile, "npc_trainer", None))
    required_badge_count = max(0, _int(getattr(profile, "required_badge_count", 0), 0))
    trainer = _trainer_for_player(player) if player is not None else None
    badge_count = _trainer_badge_count(trainer)
    enabled = bool(getattr(profile, "is_enabled", True))
    eligible = player is None or (
        trainer is not None and badge_count >= required_badge_count
    )

    issues = list(static_check.issues)
    warnings = list(static_check.warnings)
    if not enabled:
        issues.append("Gym leader profile is disabled.")
    if player is not None and trainer is None:
        issues.append("Player has no trainer progression record.")
    elif not eligible:
        issues.append(
            f"Requires at least {required_badge_count} badge(s); you have {badge_count}."
        )

    return GymLeaderCheck(
        identifier=identifier_text,
        found=True,
        name=static_check.name,
        enabled=enabled,
        eligible=eligible,
        league_key=_text(getattr(profile, "league_key", None), ""),
        gym_key=_text(getattr(profile, "gym_key", None), ""),
        badge_key=_text(getattr(profile, "badge_key", None), ""),
        badge_name=_badge_name(getattr(profile, "badge", None)),
        required_badge_count=required_badge_count,
        badge_count=badge_count,
        templates=static_check.templates,
        issues=tuple(issues),
        warnings=tuple(warnings),
        profile=profile,
    )


def generate_gym_leader_encounter(identifier, *, player=None) -> TrainerEncounter:
    """Build a battle-ready gym leader encounter from a static NPC trainer."""

    check = check_gym_leader(identifier, player=player)
    if not check.found:
        raise GymLeaderNotFoundError(check.issues[0])
    if not check.enabled:
        raise GymLeaderDisabledError("Gym leader profile is disabled.")
    if not check.eligible:
        raise GymLeaderEligibilityError(_eligibility_issue(check))
    if not check.templates or check.issues:
        raise GymLeaderTeamError(
            "; ".join(check.issues) or f"Gym leader '{check.name}' has no usable team."
        )

    profile = check.profile
    try:
        encounter = generate_static_trainer_encounter(getattr(profile, "npc_trainer", None))
    except TrainerEncounterError as err:
        raise GymLeaderTeamError(str(err)) from err

    metadata = dict(getattr(encounter, "metadata", None) or {})
    metadata.update(_profile_metadata(profile))
    return replace(
        encounter,
        source_type=GYM_LEADER_SOURCE_TYPE,
        metadata=metadata,
    )


def grant_gym_badge_for_victory(player, metadata: Mapping[str, Any] | None) -> GymBadgeGrantResult | None:
    """Grant a gym badge once when a player wins a gym leader battle."""

    if not isinstance(metadata, Mapping):
        return None
    if metadata.get("source_type") != GYM_LEADER_SOURCE_TYPE:
        return None

    try:
        profile = _resolve_profile_from_metadata(metadata)
    except GymLeaderNotFoundError:
        return GymBadgeGrantResult(
            awarded=False,
            already_had=False,
            badge_name="",
            message="Gym badge could not be resolved for this victory.",
        )

    badge = getattr(profile, "badge", None)
    badge_name = _badge_name(badge)
    trainer = _trainer_for_player(player)
    if trainer is None:
        return GymBadgeGrantResult(
            awarded=False,
            already_had=False,
            badge_name=badge_name,
            message="Badge could not be awarded because no trainer record was found.",
        )

    if _trainer_has_badge(trainer, badge):
        return GymBadgeGrantResult(
            awarded=False,
            already_had=True,
            badge_name=badge_name,
            message=f"You already have the {badge_name}.",
        )

    _add_badge(trainer, badge)
    return GymBadgeGrantResult(
        awarded=True,
        already_had=False,
        badge_name=badge_name,
        message=f"You earned the {badge_name}!",
    )


def _profile_metadata(profile) -> dict[str, object]:
    npc_trainer = getattr(profile, "npc_trainer", None)
    badge = getattr(profile, "badge", None)
    return {
        "source_type": GYM_LEADER_SOURCE_TYPE,
        "gym_leader_profile_id": _object_id(profile),
        "npc_trainer_id": _object_id(npc_trainer),
        "league_key": _text(getattr(profile, "league_key", None), ""),
        "gym_key": _text(getattr(profile, "gym_key", None), ""),
        "badge_id": _object_id(badge),
        "badge_key": _text(getattr(profile, "badge_key", None), ""),
        "required_badge_count": max(0, _int(getattr(profile, "required_badge_count", 0), 0)),
    }


def _eligibility_issue(check: GymLeaderCheck) -> str:
    for issue in check.issues:
        if issue.startswith("Requires at least") or "trainer progression record" in issue:
            return issue
    return f"Gym leader '{check.name}' is not currently available."


def _resolve_gym_leader_profile(identifier):
    if _looks_like_profile(identifier):
        return identifier

    text = _text(identifier, "")
    if not text:
        raise GymLeaderNotFoundError("Usage: +gymbattle <leader|gym_key>")

    for profile in _all_profiles():
        if _profile_matches(profile, text):
            return profile
    raise GymLeaderNotFoundError(f"Gym leader '{text}' was not found.")


def _resolve_profile_from_metadata(metadata: Mapping[str, Any]):
    profile_id = metadata.get("gym_leader_profile_id")
    gym_key = _text(metadata.get("gym_key"), "")
    league_key = _text(metadata.get("league_key"), "")
    npc_trainer_id = metadata.get("npc_trainer_id")

    for profile in _all_profiles():
        if profile_id is not None and _same_id(profile, profile_id):
            return profile
        if gym_key and _text(getattr(profile, "gym_key", None), "").lower() == gym_key.lower():
            if not league_key or _text(getattr(profile, "league_key", None), "").lower() == league_key.lower():
                return profile
        npc_trainer = getattr(profile, "npc_trainer", None)
        if npc_trainer_id is not None and _same_id(npc_trainer, npc_trainer_id):
            return profile

    label = gym_key or _text(profile_id, "")
    raise GymLeaderNotFoundError(f"Gym leader '{label}' was not found.")


def _profile_matches(profile, text: str) -> bool:
    needle = text.strip().lower()
    if not needle:
        return False
    if _same_id(profile, text):
        return True
    for value in (
        getattr(profile, "gym_key", None),
        getattr(profile, "badge_key", None),
        getattr(getattr(profile, "npc_trainer", None), "name", None),
        getattr(getattr(profile, "npc_trainer", None), "display_name", None),
    ):
        if _text(value, "").lower() == needle:
            return True
    return False


def _all_profiles() -> list[Any]:
    model = _gym_leader_profile_model()
    manager = getattr(model, "objects", None)
    if manager is None:
        return []

    all_func = getattr(manager, "all", None)
    queryset = all_func() if callable(all_func) else getattr(manager, "rows", [])
    if queryset is None:
        return []
    if hasattr(queryset, "select_related"):
        queryset = queryset.select_related("npc_trainer", "badge")
    if hasattr(queryset, "order_by"):
        queryset = queryset.order_by("sort_order", "league_key", "gym_key")
    return list(queryset)


def _gym_leader_profile_model():
    from pokemon.models.trainer import GymLeaderProfile

    return GymLeaderProfile


def _looks_like_profile(value) -> bool:
    return (
        value is not None
        and not isinstance(value, str)
        and hasattr(value, "npc_trainer")
        and hasattr(value, "gym_key")
        and hasattr(value, "badge")
    )


def _trainer_for_player(player):
    if player is None:
        return None
    trainer = getattr(player, "trainer", None)
    if trainer is not None:
        return trainer
    trainer_func = getattr(player, "get_trainer", None)
    if callable(trainer_func):
        try:
            return trainer_func()
        except Exception:
            return None
    return None


def _trainer_badge_count(trainer) -> int:
    if trainer is None:
        return 0
    badges = getattr(trainer, "badges", None)
    if badges is None:
        return 0
    count_func = getattr(badges, "count", None)
    if callable(count_func):
        try:
            return int(count_func())
        except TypeError:
            pass
        except Exception:
            return 0
    rows = _badge_rows(badges)
    return len(rows)


def _trainer_has_badge(trainer, badge) -> bool:
    if trainer is None or badge is None:
        return False
    badges = getattr(trainer, "badges", None)
    if badges is None:
        return False

    badge_id = _object_id(badge)
    filter_func = getattr(badges, "filter", None)
    if callable(filter_func) and badge_id is not None:
        for key in ("pk", "id"):
            try:
                queryset = filter_func(**{key: badge_id})
                exists = getattr(queryset, "exists", None)
                if callable(exists):
                    return bool(exists())
                if list(queryset):
                    return True
            except Exception:
                continue

    for owned in _badge_rows(badges):
        if owned is badge or _same_id(owned, badge_id):
            return True
    return False


def _add_badge(trainer, badge) -> None:
    add_badge = getattr(trainer, "add_badge", None)
    if callable(add_badge):
        add_badge(badge)
        return
    badges = getattr(trainer, "badges", None)
    add_func = getattr(badges, "add", None)
    if callable(add_func):
        add_func(badge)


def _badge_rows(badges) -> list[Any]:
    rows = badges
    all_func = getattr(badges, "all", None)
    if callable(all_func):
        try:
            rows = all_func()
        except Exception:
            rows = []
    if isinstance(rows, Iterable) and not isinstance(rows, (str, bytes)):
        return list(rows)
    return []


def _badge_name(badge) -> str:
    return _text(getattr(badge, "name", None), "Gym Badge")


def _same_id(obj, other) -> bool:
    if obj is None or other is None:
        return False
    other_text = str(other)
    for attr in ("pk", "id"):
        value = getattr(obj, attr, None)
        if value is not None and str(value) == other_text:
            return True
    return False


def _object_id(obj):
    if obj is None:
        return None
    return getattr(obj, "pk", getattr(obj, "id", None))


def _text(value, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


__all__ = [
    "GYM_LEADER_SOURCE_TYPE",
    "GymBadgeGrantResult",
    "GymLeaderCheck",
    "GymLeaderDisabledError",
    "GymLeaderEligibilityError",
    "GymLeaderError",
    "GymLeaderNotFoundError",
    "GymLeaderTeamError",
    "check_gym_leader",
    "generate_gym_leader_encounter",
    "grant_gym_badge_for_victory",
    "list_gym_leaders",
]
