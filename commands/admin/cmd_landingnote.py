"""Wizard command for editing the public landing-page announcement."""

from __future__ import annotations

from evennia import Command

from utils.landing_announcement import (
    add_landing_bullet,
    clear_landing_bullets,
    get_landing_announcement,
    reset_landing_announcement,
    update_landing_announcement,
)


class CmdLandingNote(Command):
    """View or change the public landing-page announcement.

    Usage:
      @landingnote
      @landingnote/view
      @landingnote/label <label>
      @landingnote/title <title>
      @landingnote/body <text>
      @landingnote/bullet <text>
      @landingnote/clearbullets
      @landingnote/show
      @landingnote/hide
      @landingnote/reset
    """

    key = "@landingnote"
    aliases = ["landingnote"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def _usage(self):
        self.caller.msg(
            "Usage: @landingnote[/view|/label|/title|/body|/bullet|/clearbullets|/show|/hide|/reset] [text]"
        )

    def _show_current(self):
        note = get_landing_announcement()
        state = "visible" if note.visible else "hidden"
        source = "default" if note.is_default else "custom"
        bullets = "\n".join(f"  - {bullet}" for bullet in note.bullets) or "  (none)"
        updated = "Never"
        if note.updated_at or note.updated_by:
            updated = note.updated_at or "Unknown time"
            if note.updated_by:
                updated = f"{updated} by {note.updated_by}"

        self.caller.msg(
            f"Landing announcement ({source}, {state})\n"
            f"Label: {note.label}\n"
            f"Title: {note.title}\n"
            f"Body:\n{note.body}\n"
            f"Bullets:\n{bullets}\n"
            f"Last updated: {updated}"
        )

    def _require_text(self, switch: str) -> str | None:
        text = (self.args or "").strip()
        if not text:
            self.caller.msg(f"Usage: @landingnote/{switch} <text>")
            return None
        return text

    def func(self):
        """Display or update the landing announcement."""

        switches = [switch.lower() for switch in (self.switches or [])]
        switch = switches[0] if switches else "view"

        if switch == "view":
            self._show_current()
            return

        if switch == "label":
            label = self._require_text("label")
            if label is None:
                return
            note = update_landing_announcement(label=label, changed_by=self.caller)
            self.caller.msg(f"Landing announcement label set to: {note.label}")
            return

        if switch == "title":
            title = self._require_text("title")
            if title is None:
                return
            note = update_landing_announcement(title=title, changed_by=self.caller)
            self.caller.msg(f"Landing announcement title set to: {note.title}")
            return

        if switch == "body":
            body = self._require_text("body")
            if body is None:
                return
            update_landing_announcement(body=body, changed_by=self.caller)
            self.caller.msg("Landing announcement body updated.")
            return

        if switch == "bullet":
            bullet = self._require_text("bullet")
            if bullet is None:
                return
            try:
                note = add_landing_bullet(bullet, changed_by=self.caller)
            except ValueError as err:
                self.caller.msg(str(err))
                return
            self.caller.msg(f"Landing announcement bullet #{len(note.bullets)} added.")
            return

        if switch == "clearbullets":
            clear_landing_bullets(changed_by=self.caller)
            self.caller.msg("Landing announcement bullets cleared.")
            return

        if switch == "show":
            update_landing_announcement(visible=True, changed_by=self.caller)
            self.caller.msg("Landing announcement is now visible.")
            return

        if switch == "hide":
            update_landing_announcement(visible=False, changed_by=self.caller)
            self.caller.msg("Landing announcement is now hidden.")
            return

        if switch == "reset":
            reset_landing_announcement()
            self.caller.msg("Landing announcement reset to defaults.")
            return

        self._usage()
