"""Staff command for starting static NPC trainer battles."""

from __future__ import annotations

try:
    from evennia import Command as _EvenniaCommand
except Exception:  # pragma: no cover - optional in lightweight tests
    _EvenniaCommand = None

from pokemon.battle.battleinstance import BattleSession
from pokemon.helpers.party_helpers import has_usable_pokemon
from pokemon.services.trainer_encounters import (
    StaticTrainerCheck,
    TrainerEncounterError,
    check_static_trainer,
    generate_static_trainer_encounter,
    list_static_trainers_with_templates,
)


if _EvenniaCommand is None:  # pragma: no cover - direct test/Django imports
    class Command:  # type: ignore[no-redef]
        """Lightweight command base used when Evennia is not configured."""

        pass
else:
    Command = _EvenniaCommand


class CmdNPCBattle(Command):
    """Start a battle against a static NPC trainer.

    Usage:
      +npcbattle <npc trainer name>
      +npcbattle/list
      +npcbattle/check <npc trainer name>
    """

    key = "+npcbattle"
    aliases = ["@npcbattle"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def parse(self):
        parse = getattr(super(), "parse", None)
        if callable(parse):
            parse()
        self.switches = {switch.lower() for switch in getattr(self, "switches", [])}

    def func(self):
        if "list" in getattr(self, "switches", set()):
            self._list_trainers()
            return
        if "check" in getattr(self, "switches", set()):
            self._check_trainer((self.args or "").strip())
            return

        trainer_name = (self.args or "").strip()
        if not trainer_name:
            self.caller.msg("Usage: +npcbattle <npc trainer name> | +npcbattle/list | +npcbattle/check <npc trainer name>")
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
            encounter = generate_static_trainer_encounter(trainer_name)
        except TrainerEncounterError as err:
            self.caller.msg(str(err))
            return

        session = BattleSession(self.caller)
        session.start_trainer_encounter(encounter)
        self.caller.msg(
            f"Started NPC trainer battle #{session.battle_id} against {encounter.display_name}."
        )

    def _list_trainers(self):
        checks = list_static_trainers_with_templates()
        if not checks:
            self.caller.msg("No static NPC trainers with template Pokemon found.")
            return
        lines = ["Static NPC trainers with templates:"]
        for check in checks:
            team = _format_team_inline(check)
            status = "ready" if check.can_start_battle else "needs check"
            lines.append(f"  {check.name} - {check.template_count} Pokemon - {status} - {team}")
        self.caller.msg("\n".join(lines))

    def _check_trainer(self, trainer_name: str):
        if not trainer_name:
            self.caller.msg("Usage: +npcbattle/check <npc trainer name>")
            return
        check = check_static_trainer(trainer_name)
        self.caller.msg(_format_check(check))


def _format_team_inline(check: StaticTrainerCheck) -> str:
    return ", ".join(
        f"{template.species or '<missing species>'} Lv{template.level}"
        for template in check.templates
    ) or "no templates"


def _format_check(check: StaticTrainerCheck) -> str:
    if not check.found:
        return check.issues[0] if check.issues else f"NPC trainer '{check.name}' was not found."

    lines = [
        f"Static NPC trainer check: {check.name}",
        "Found: yes",
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
    lines.append(f"Battle startup: {'should work' if check.can_start_battle else 'blocked'}")
    if check.issues:
        lines.append("Issues:")
        lines.extend(f"  - {issue}" for issue in check.issues)
    if getattr(check, "warnings", ()):
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in check.warnings)
    return "\n".join(lines)


__all__ = ["CmdNPCBattle"]
