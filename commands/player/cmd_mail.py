from evennia import Command, search_object
from evennia.objects.objects import DefaultCharacter
from evennia.utils.evtable import EvTable

from utils import character_mail


def _is_character(obj) -> bool:
    check = getattr(obj, "is_typeclass", None)
    return bool(callable(check) and check(DefaultCharacter, exact=False))


def _search_character(query: str) -> list:
    matches = search_object(query, exact=False, typeclass="typeclasses.characters.Character")
    return [match for match in matches if _is_character(match)]


def _format_date(value) -> str:
    formatter = getattr(value, "strftime", None)
    if callable(formatter):
        return formatter("%Y-%m-%d %H:%M")
    return str(value or "-")


def _preview(text: str, width: int = 42) -> str:
    clean = " ".join(str(text or "").split())
    if len(clean) <= width:
        return clean
    return f"{clean[: width - 3].rstrip()}..."


def _split_subject_body(raw: str) -> tuple[str, str]:
    if "/" not in (raw or ""):
        return "", ""
    subject, body = raw.split("/", 1)
    return subject.strip(), body.strip()


class CmdMail(Command):
    """Send and read character mail.

    Usage:
      +mail
      +mail/send <character>=<subject>/<message>
      +mail/read <id>
      +mail/reply <id>=<message>
      +mail/delete <id>
      +mail/unread <id>

    Aliases:
      mail
    """

    key = "+mail"
    aliases = ["mail"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        switches = {switch.lower() for switch in getattr(self, "switches", []) or []}
        if "help" in switches or (self.args or "").strip().lower() in {"help", "#help"}:
            self._show_help()
            return

        if "send" in switches or "compose" in switches:
            self._send_mail()
            return

        if "read" in switches or "show" in switches:
            self._read_mail()
            return

        if "reply" in switches:
            self._reply_mail()
            return

        if "delete" in switches or "del" in switches or "archive" in switches:
            self._delete_mail()
            return

        if "unread" in switches:
            self._mark_unread()
            return

        if (self.args or "").strip():
            self._read_mail()
            return

        self._list_mail()

    def _show_help(self):
        self.caller.msg(
            "Usage: +mail | +mail/send <character>=<subject>/<message> | "
            "+mail/read <id> | +mail/reply <id>=<message> | +mail/delete <id>"
        )

    def _resolve_recipient(self, query: str):
        matches = _search_character(query)
        if not matches:
            self.caller.msg("No matching character found.")
            return None
        if len(matches) > 1:
            names = ", ".join(character_mail.character_name(match) for match in matches[:8])
            if len(matches) > 8:
                names += ", ..."
            self.caller.msg(f"Multiple characters match: {names}")
            return None
        return matches[0]

    def _list_mail(self):
        rows = character_mail.list_character_mail(self.caller)
        if not rows:
            self.caller.msg("Your mailbox is empty.")
            return

        table = EvTable("ID", "From", "Subject", "Sent", "Status")
        for message in rows:
            table.add_row(
                character_mail.mail_id(message),
                character_mail.sender_name(message),
                _preview(character_mail.mail_subject(message)),
                _format_date(character_mail.mail_date(message)),
                "Unread" if character_mail.is_unread(message) else "Read",
            )
        self.caller.msg(f"Mailbox for {character_mail.character_name(self.caller)}:\n{table}")

    def _send_mail(self):
        if not getattr(self, "lhs", "") or not getattr(self, "rhs", ""):
            self.caller.msg("Usage: +mail/send <character>=<subject>/<message>")
            return

        recipient = self._resolve_recipient(self.lhs)
        if not recipient:
            return

        subject, body = _split_subject_body(self.rhs)
        if not subject or not body:
            self.caller.msg("Usage: +mail/send <character>=<subject>/<message>")
            return

        try:
            message = character_mail.send_character_mail(self.caller, recipient, subject, body)
        except character_mail.CharacterMailError as err:
            self.caller.msg(str(err))
            return

        self.caller.msg(f"Mail #{character_mail.mail_id(message)} sent to {character_mail.character_name(recipient)}.")

    def _read_mail(self):
        mail_id = (self.args or "").strip()
        if not mail_id:
            self.caller.msg("Usage: +mail/read <id>")
            return

        try:
            message = character_mail.read_character_mail(self.caller, mail_id)
        except character_mail.CharacterMailError as err:
            self.caller.msg(str(err))
            return

        self.caller.msg(
            f"Mail #{character_mail.mail_id(message)}\n"
            f"From: {character_mail.sender_name(message)}\n"
            f"Sent: {_format_date(character_mail.mail_date(message))}\n"
            f"Subject: {character_mail.mail_subject(message)}\n\n"
            f"{character_mail.mail_body(message)}"
        )

    def _reply_mail(self):
        if not getattr(self, "lhs", "") or not getattr(self, "rhs", ""):
            self.caller.msg("Usage: +mail/reply <id>=<message>")
            return

        try:
            message = character_mail.reply_to_character_mail(self.caller, self.lhs, self.rhs)
        except character_mail.CharacterMailError as err:
            self.caller.msg(str(err))
            return

        self.caller.msg(f"Reply sent as mail #{character_mail.mail_id(message)}.")

    def _delete_mail(self):
        mail_id = (self.args or "").strip()
        if not mail_id:
            self.caller.msg("Usage: +mail/delete <id>")
            return

        try:
            message = character_mail.archive_character_mail(self.caller, mail_id)
        except character_mail.CharacterMailError as err:
            self.caller.msg(str(err))
            return

        self.caller.msg(f"Mail #{character_mail.mail_id(message)} archived.")

    def _mark_unread(self):
        mail_id = (self.args or "").strip()
        if not mail_id:
            self.caller.msg("Usage: +mail/unread <id>")
            return

        try:
            message = character_mail.get_character_mail(self.caller, mail_id)
        except character_mail.CharacterMailError as err:
            self.caller.msg(str(err))
            return

        character_mail.mark_unread(message)
        self.caller.msg(f"Mail #{character_mail.mail_id(message)} marked unread.")
