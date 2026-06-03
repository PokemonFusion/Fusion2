"""Staff command for starting gym leader proof-of-concept battles."""

from __future__ import annotations

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


if _EvenniaCommand is None:  # pragma: no cover - direct test/Django imports
    class Command:  # type: ignore[no-redef]
        """Lightweight command base used when Evennia is not configured."""

        pass
else:
    Command = _EvenniaCommand


class CmdGymBattle(Command):
    """Start a proof-of-concept gym leader battle.

    Usage:
      +gymbattle <leader name|gym_key>
      +gymbattle/list
      +gymbattle/list/all
      +gymbattle/check <leader name|gym_key>
    """

    key = "+gymbattle"
    aliases = ["@gymbattle"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def parse(self):
        parse = getattr(super(), "parse", None)
        if callable(parse):
            parse()
        self.switches = {switch.lower() for switch in getattr(self, "switches", [])}

    def func(self):
        if "list" in getattr(self, "switches", set()):
            self._list_leaders(include_disabled=self._include_disabled_list())
            return
        if "check" in getattr(self, "switches", set()):
            self._check_leader((self.args or "").strip())
            return

        identifier = (self.args or "").strip()
        if not identifier:
            self.caller.msg("Usage: +gymbattle <leader|gym_key> | +gymbattle/list | +gymbattle/check <leader|gym_key>")
            return

        check_in_battle = getattr(BattleSession, "ensure_for_player", None)
        if check_in_battle:
            try:
                if check_in_battle(self.caller):
                    self.caller.msg("You are already in a battle.")
                    return
            except Exception:
                pass

        if not has_usable_pokemon(self.caller):
            self.caller.msg("You don't have any Pokemon able to battle.")
            return

        try:
            encounter = generate_gym_leader_encounter(identifier, player=self.caller)
        except GymLeaderError as err:
            self.caller.msg(str(err))
            return

        session = BattleSession(self.caller)
        session.start_trainer_encounter(encounter)
        self.caller.msg(
            f"Started gym leader battle #{session.battle_id} against {encounter.display_name}."
        )

    def _include_disabled_list(self) -> bool:
        switches = getattr(self, "switches", set())
        args = (self.args or "").strip().lower()
        return "all" in switches or "disabled" in switches or args in {"all", "disabled"}

    def _list_leaders(self, *, include_disabled: bool = False):
        checks = list_gym_leaders(player=self.caller, include_disabled=include_disabled)
        if not checks:
            self.caller.msg("No gym leaders found." if include_disabled else "No enabled gym leaders found.")
            return
        lines = ["Gym leaders:" if include_disabled else "Enabled gym leaders:"]
        for check in checks:
            if not check.enabled:
                status = "disabled"
            else:
                status = "ready" if check.can_start_battle else "blocked"
            if getattr(check, "warnings", ()):
                status += " (warnings)"
            requirement = f"requires {check.required_badge_count} badge(s)"
            lines.append(
                "  "
                f"{check.gym_key or '<missing gym_key>'} - "
                f"{check.name} - "
                f"{check.badge_name} ({check.badge_key or '<missing badge_key>'}) - "
                f"{requirement} - "
                f"{check.template_count} Pokemon - "
                f"{status}"
            )
        self.caller.msg("\n".join(lines))

    def _check_leader(self, identifier: str):
        if not identifier:
            self.caller.msg("Usage: +gymbattle/check <leader|gym_key>")
            return
        check = check_gym_leader(identifier, player=self.caller)
        self.caller.msg(_format_check(check))


def _format_team_inline(check: GymLeaderCheck) -> str:
    return ", ".join(
        f"{template.species or '<missing species>'} Lv{template.level}"
        for template in check.templates
    ) or "no templates"


def _format_check(check: GymLeaderCheck) -> str:
    if not check.found:
        return check.issues[0] if check.issues else f"Gym leader '{check.name}' was not found."

    lines = [
        f"Gym leader check: {check.name}",
        "Found: yes",
        f"Enabled: {'yes' if check.enabled else 'no'}",
        f"Gym key: {check.gym_key or '<missing>'}",
        f"League key: {check.league_key or '<missing>'}",
        f"Badge: {check.badge_name} ({check.badge_key or '<missing>'})",
        f"Required badges: {check.required_badge_count}",
        f"Caller badges: {check.badge_count}",
        f"Eligible: {'yes' if check.eligible else 'no'}",
        f"Template Pokemon: {check.template_count}",
    ]
    for index, template in enumerate(check.templates, start=1):
        label = f"{template.species or '<missing species>'} Lv{template.level}"
        if template.template_key:
            label = f"{template.template_key}: {label}"
        status = "OK" if template.is_valid else "Issues: " + "; ".join(template.issues)
        if getattr(template, "warnings", ()):
            status += "; Warnings: " + "; ".join(template.warnings)
        lines.append(f"  {index}. {label} - {status}")
    lines.append(f"Team: {_format_team_inline(check)}")
    lines.append(f"Battle startup: {'should work' if check.can_start_battle else 'blocked'}")
    if check.issues:
        lines.append("Issues:")
        lines.extend(f"  - {issue}" for issue in check.issues)
    if getattr(check, "warnings", ()):
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in check.warnings)
    return "\n".join(lines)


__all__ = ["CmdGymBattle"]
