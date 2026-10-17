"""Player-facing gym command."""

from __future__ import annotations

import logging

try:
    from evennia import Command as _EvenniaCommand
except Exception:  # pragma: no cover - optional in lightweight tests
    _EvenniaCommand = None

from pokemon.battle.battleinstance import BattleSession
from pokemon.helpers.party_helpers import has_usable_pokemon
from pokemon.services.gym_leaders import (
    GymLeaderCheck,
    GymLeaderError,
    check_gym_leader,
    generate_gym_leader_encounter,
    list_gym_leaders,
)
from pokemon.services.gym_rewards import PENDING_MESSAGE, GymVictoryRewards

logger = logging.getLogger(__name__)


if _EvenniaCommand is None:  # pragma: no cover - direct test/Django imports
    class Command:  # type: ignore[no-redef]
        """Lightweight command base used when Evennia is not configured."""

        pass
else:
    Command = _EvenniaCommand


class CmdGym(Command):
    """Find and challenge available gyms.

    Usage:
      +gym list
      +gym check <gym>
      +gym challenge <gym>
      +gym claim

    Examples:
      +gym list
      +gym check tempo_gym
      +gym challenge tempo_gym

    Notes:
      Gym badges are awarded once. You may rematch a gym leader after earning
      the badge, but the rematch will not award another copy.
      Use +gym claim to retry a pending badge award, including after reconnecting.
    """

    key = "+gym"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        subcommand, rest = _split_subcommand(self.args)
        if subcommand in {"", "help"}:
            self.caller.msg(_usage())
            return
        if subcommand == "list":
            self._list_gyms()
            return
        if subcommand == "check":
            self._check_gym(rest)
            return
        if subcommand == "challenge":
            self._challenge_gym(rest)
            return
        if subcommand == "claim":
            self._claim_badges(rest)
            return
        self.caller.msg(_usage())

    def _claim_badges(self, args: str):
        """Claim only the caller's saved victories, without starting a battle."""
        if args:
            self.caller.msg("Usage: +gym claim")
            return
        try:
            results = GymVictoryRewards(self.caller).claim_pending()
        except Exception:
            logger.exception("Could not load pending gym victories")
            self.caller.msg(PENDING_MESSAGE)
            return
        if not results:
            self.caller.msg("No unclaimed gym badges.")
            return
        for result in results:
            self.caller.msg(result.message)

    def _list_gyms(self):
        checks = [
            check
            for check in list_gym_leaders(player=self.caller, include_disabled=False)
            if _is_player_visible(check)
        ]
        if not checks:
            self.caller.msg("No gyms are available right now.")
            return

        lines = ["Available gyms:"]
        for check in checks:
            lines.append(
                "  "
                f"{_gym_label(check)} | "
                f"Leader: {check.name or 'Unknown'} | "
                f"Requires: {check.required_badge_count} badge(s) | "
                f"Qualifies: {_yes_no(check.eligible)} | "
                f"Badge earned: {_yes_no(check.has_badge)}"
            )
        self.caller.msg("\n".join(lines))

    def _check_gym(self, identifier: str):
        if not identifier:
            self.caller.msg("Usage: +gym check <gym>")
            return
        check = check_gym_leader(identifier, player=self.caller)
        if not _is_player_visible(check):
            self.caller.msg(_missing_or_unavailable_message(identifier))
            return
        self.caller.msg(_format_check(check))

    def _challenge_gym(self, identifier: str):
        if not identifier:
            self.caller.msg("Usage: +gym challenge <gym>")
            return

        check_in_battle = getattr(BattleSession, "ensure_for_player", None)
        if callable(check_in_battle):
            try:
                if check_in_battle(self.caller):
                    self.caller.msg("You are already in a battle.")
                    return
            except Exception:
                pass

        if not has_usable_pokemon(self.caller):
            self.caller.msg("You don't have any Pokemon able to battle.")
            return

        check = check_gym_leader(identifier, player=self.caller)
        if not _is_player_visible(check):
            self.caller.msg(_missing_or_unavailable_message(identifier))
            return
        if not check.eligible:
            self.caller.msg(_eligibility_message(check))
            return
        if not check.can_start_battle:
            self.caller.msg(_configuration_message(check))
            return

        if check.reward_policy == "badge_only":
            from pokemon.services.gym_challenges import GymChallenge

            try:
                session, encounter = GymChallenge(self.caller, identifier).start()
            except GymLeaderError as error:
                self.caller.msg(str(error))
                return
            except Exception:
                logger.exception("Production gym startup failed and was rolled back")
                self.caller.msg("The gym challenge could not start. No reward or cooldown was consumed; try again.")
                return
            mode = encounter.metadata["challenge_mode"].replace("_", " ")
            self.caller.msg(f"Started {mode} gym challenge #{session.battle_id} against {encounter.display_name}.")
            return

        if check.has_badge:
            self.caller.msg(
                f"You already have the {check.badge_name}. This rematch will not award another badge."
            )

        try:
            encounter = generate_gym_leader_encounter(identifier, player=self.caller)
        except GymLeaderError as err:
            self.caller.msg(str(err))
            return

        session = BattleSession(self.caller)
        session.start_trainer_encounter(encounter)
        self.caller.msg(
            f"Started gym challenge #{session.battle_id} against {encounter.display_name}."
        )


def _split_subcommand(args: str | None) -> tuple[str, str]:
    text = (args or "").strip()
    if not text:
        return "", ""
    subcommand, _, rest = text.partition(" ")
    return subcommand.lower(), rest.strip()


def _usage() -> str:
    return "Usage: +gym list | +gym check <gym> | +gym challenge <gym> | +gym claim"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _gym_label(check: GymLeaderCheck) -> str:
    return check.gym_key or check.identifier or check.name or "Unknown Gym"


def _is_player_visible(check: GymLeaderCheck) -> bool:
    return bool(check.found and check.enabled and check.content_stage == "production")


def _missing_or_unavailable_message(identifier: str) -> str:
    label = identifier.strip() or "that gym"
    return f"Gym '{label}' is not available right now. Use +gym list to see available gyms."


def _format_check(check: GymLeaderCheck) -> str:
    lines = [
        f"Gym: {_gym_label(check)}",
        f"Leader: {check.name or 'Unknown'}",
        f"Badge awarded: {check.badge_name or 'Unknown Badge'}",
        f"Required badges: {check.required_badge_count}",
        f"Your badges: {check.badge_count}",
        f"Qualifies: {_yes_no(check.eligible)}",
        f"Already earned: {_yes_no(check.has_badge)}",
        f"Format: {check.battle_format}",
    ]
    if check.rules_text:
        lines.append(check.rules_text)
    if check.availability_message:
        lines.append(check.availability_message)
    elif check.has_badge:
        lines.append("Rematch available. No additional badge will be awarded.")
    elif check.can_start_battle:
        lines.append("Challenge available.")
    elif not check.eligible:
        lines.append(_eligibility_message(check))
    else:
        lines.append(_configuration_message(check))
    return "\n".join(lines)


def _eligibility_message(check: GymLeaderCheck) -> str:
    if check.availability_message:
        return check.availability_message
    for issue in check.issues:
        if issue.startswith("Requires at least") or "trainer progression record" in issue:
            return issue
    return "You do not qualify for this gym yet."


def _configuration_message(check: GymLeaderCheck) -> str:
    issue_text = "; ".join(check.issues)
    if issue_text:
        return f"That gym is not ready for challenges yet: {issue_text}"
    return "That gym is not ready for challenges yet."


__all__ = ["CmdGym"]
