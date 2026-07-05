"""PF1-style character paging backed by Evennia messages."""

from __future__ import annotations

import shlex

try:  # pragma: no cover - Evennia can expose Command lazily in import-only tests
    from evennia import Command as _EvenniaCommand
    from evennia import search_object
except Exception:  # pragma: no cover
    _EvenniaCommand = None
    search_object = None

if _EvenniaCommand is None:  # pragma: no cover - import-only fallback
    try:
        from evennia.commands.command import Command as _EvenniaCommand
    except Exception:
        _EvenniaCommand = object

Command = _EvenniaCommand

from utils import character_mail


PAGE_TAG = "page"
PAGE_CATEGORY = "comms"
STAFF_PERMISSIONS = {"helper", "builder", "admin", "developer", "wizards", "wizard"}


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    try:
        return list(value)
    except TypeError:
        return [value]


def _db(obj):
    return getattr(obj, "db", None)


def _get_db(obj, name: str, default=None):
    db = _db(obj)
    if db is None:
        return default
    return getattr(db, name, default)


def _set_db(obj, name: str, value) -> None:
    db = _db(obj)
    if db is not None:
        setattr(db, name, value)


def _name(obj) -> str:
    return getattr(obj, "key", None) or getattr(obj, "name", None) or str(obj)


def _identity(obj) -> str:
    return _name(obj).casefold()


def _is_character(obj) -> bool:
    check = getattr(obj, "is_typeclass", None)
    if not callable(check):
        return False
    try:
        return bool(check("typeclasses.characters.Character", exact=False))
    except TypeError:
        return bool(check("typeclasses.characters.Character"))


def _permissions(obj) -> set[str]:
    found = set()
    for candidate in (obj, getattr(obj, "account", None)):
        perms = getattr(candidate, "permissions", None)
        if not perms:
            continue
        all_perms = getattr(perms, "all", None)
        if callable(all_perms):
            found.update(str(perm).casefold() for perm in all_perms())
        check = getattr(perms, "check", None)
        if callable(check):
            for perm in STAFF_PERMISSIONS:
                try:
                    if check(perm):
                        found.add(perm)
                except TypeError:
                    continue
        get = getattr(perms, "get", None)
        if callable(get):
            found.update(str(perm).casefold() for perm in _as_list(get()))
    return found


def _is_staff(obj) -> bool:
    checker = getattr(obj, "check_permstring", None)
    if callable(checker):
        for perm in STAFF_PERMISSIONS:
            try:
                if checker(perm):
                    return True
            except TypeError:
                continue
    return bool(_permissions(obj) & STAFF_PERMISSIONS)


def _is_online(obj) -> bool:
    sessions = getattr(obj, "sessions", None)
    count = getattr(sessions, "count", None)
    if callable(count):
        return bool(count())
    account = getattr(obj, "account", None)
    sessions = getattr(account, "sessions", None)
    count = getattr(sessions, "count", None)
    if callable(count):
        return bool(count())
    return True


def _search_characters(query: str) -> list:
    if not callable(search_object):
        return []
    try:
        matches = search_object(query, exact=False, typeclass="typeclasses.characters.Character")
    except TypeError:
        matches = search_object(query)
    return [match for match in _as_list(matches) if match and _is_character(match)]


def _ignored_names(character) -> set[str]:
    return {str(name).casefold() for name in _as_list(_get_db(character, "page_ignored", []))}


def _set_ignored_names(character, names: set[str]) -> None:
    _set_db(character, "page_ignored", sorted(names))


def _split_targets(raw: str) -> list[str]:
    raw = (raw or "").strip()
    if not raw:
        return []
    if len(_search_characters(raw)) == 1:
        return [raw]
    lexer = shlex.shlex(raw, posix=True)
    lexer.whitespace_split = True
    lexer.whitespace += ","
    try:
        return [part.strip() for part in lexer if part.strip()]
    except ValueError:
        return [part.strip() for part in raw.replace(",", " ").split() if part.strip()]


def _target_names(targets: list) -> list[str]:
    return [_name(target) for target in targets]


def _format_target_list(targets: list) -> str:
    names = _target_names(targets)
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return f"{', '.join(names[:-1])} and {names[-1]}"


def _compose_page_lines(sender, targets: list, message: str) -> tuple[str, str, str]:
    recipient_list = _format_target_list(targets)
    if message.startswith((":", ";")):
        pose = message[1:].strip()
        if pose and not pose.startswith(("'", ",")):
            pose = f" {pose}"
        stored = f"{_name(sender)}{pose}"
        return (
            f'You page-pose, "{stored}" (sent to {recipient_list}).',
            f"In a page-pose to you, {stored} (sent to {recipient_list}).",
            stored,
        )

    stored = message.strip()
    return (
        f'You page {recipient_list} with: "{stored}".',
        f'{_name(sender)} pages, "{stored}" (sent to {recipient_list}).',
        stored,
    )


def _mail_body(sender, message: str) -> str:
    if message.startswith((":", ";")):
        pose = message[1:].strip()
        if pose and not pose.startswith(("'", ",")):
            pose = f" {pose}"
        return f"{_name(sender)}{pose}"
    return f'{_name(sender)} says, "{message.strip()}"'


def _create_page_message(sender, targets: list, message: str) -> None:
    from evennia.utils import create

    create.create_message(sender, message, receivers=targets, tags=[(PAGE_TAG, PAGE_CATEGORY)])


def _page_history(character) -> list:
    try:
        from django.db.models import Q
        from evennia.comms.models import Msg
    except Exception:
        return []

    sent = Msg.objects.get_messages_by_sender(character).order_by("-db_date_created")
    got = Msg.objects.get_messages_by_receiver(character).order_by("-db_date_created")
    page_filter = Q(db_tags__db_key__iexact=PAGE_TAG, db_tags__db_category__iexact=PAGE_CATEGORY)
    sent = sent.filter(page_filter)
    got = got.filter(page_filter)
    pages = list(sent) + list(got)
    pages = [page for page in pages if page.access(character, "read", default=True)]
    return sorted(pages, key=lambda page: getattr(page, "date_created", None) or getattr(page, "db_date_created", None))


class CmdPage(Command):
    """Send PF1-style private pages between characters.

    Usage:
      page <character>[ <character>...]=<message>
      page <character> <message>
      page <message>
      page #r=<message>
      page #R=<message>
      page #mail <character>=<message>
      page #ignore <character>
      page #!ignore <character>
      page #haven
      page #!haven

    Staff:
      page #lock <character>
      page #!lock <character>

    Aliases:
      @page, tell
    """

    key = "page"
    aliases = ["@page", "tell"]
    locks = "cmd:all()"
    help_category = "Comms"

    def func(self):
        switches = {switch.lower() for switch in getattr(self, "switches", []) or []}
        args = (self.args or "").strip()

        if "help" in switches or args.lower() in {"#help", "help"}:
            self._show_help()
            return
        if "last" in switches:
            self._show_last()
            return
        if "list" in switches:
            self._show_history()
            return

        lowered = args.lower()
        if lowered == "#haven":
            self._set_haven(True)
            return
        if lowered == "#!haven":
            self._set_haven(False)
            return
        if lowered.startswith("#ignore "):
            self._set_ignore(args[8:].strip(), True)
            return
        if lowered.startswith("#!ignore "):
            self._set_ignore(args[9:].strip(), False)
            return
        if lowered.startswith("#lock "):
            self._set_lock(args[6:].strip(), True)
            return
        if lowered.startswith("#!lock "):
            self._set_lock(args[7:].strip(), False)
            return
        if args.startswith("#R"):
            self._reply_all(self._message_after_reply_prefix(args, "#R"))
            return
        if lowered.startswith("#mail "):
            self._send_page_mail(args[6:].strip())
            return
        if lowered.startswith("#r"):
            self._reply_sender(self._message_after_reply_prefix(args, "#r"))
            return

        if args.isdigit():
            self._show_history(int(args))
            return
        if not args:
            self._show_history()
            return

        target_text = (getattr(self, "lhs", "") or "").strip()
        message = (getattr(self, "rhs", "") or "").strip()
        if target_text and message:
            self._send_to_target_text(target_text, message)
            return

        target_text, message = self._split_space_syntax(args)
        if target_text and message:
            self._send_to_target_text(target_text, message)
            return

        self._reply_last(args)

    def _show_help(self):
        self.caller.msg(
            "Usage: page <character>[ <character>...]=<message> | page <character> <message> | "
            "page <message> | page #r=<message> | page #R=<message> | page #mail <character>=<message>. "
            "Controls: page #haven, page #!haven, page #ignore <character>, page #!ignore <character>."
        )

    def _message_after_reply_prefix(self, args: str, prefix: str) -> str:
        rest = args[len(prefix) :].strip()
        if rest.startswith("="):
            rest = rest[1:].strip()
        return rest

    def _split_space_syntax(self, args: str) -> tuple[str, str]:
        if args.startswith(('"', "'")):
            lexer = shlex.shlex(args, posix=True)
            lexer.whitespace_split = True
            try:
                target_text = next(lexer)
            except (StopIteration, ValueError):
                return "", ""
            message = args[lexer.instream.tell() :].strip()
            if target_text and message and self._resolve_targets([target_text], quiet=True):
                return target_text, message

        target_text, _, message = args.partition(" ")
        if not target_text or not message:
            return "", ""
        matches = self._resolve_targets([target_text], quiet=True)
        if not matches:
            return "", ""
        return target_text, message.strip()

    def _resolve_one(self, query: str, quiet: bool = False):
        matches = _search_characters(query)
        if not matches:
            if not quiet:
                self.caller.msg(f"I don't know who {query} is.")
            return None
        if len(matches) > 1:
            if not quiet:
                names = ", ".join(_name(match) for match in matches[:8])
                if len(matches) > 8:
                    names += ", ..."
                self.caller.msg(f"Multiple characters match {query}: {names}")
            return None
        return matches[0]

    def _resolve_targets(self, queries: list[str], quiet: bool = False) -> list:
        targets = []
        seen = set()
        for query in queries:
            target = self._resolve_one(query, quiet=quiet)
            if not target:
                return []
            ident = _identity(target)
            if ident not in seen:
                seen.add(ident)
                targets.append(target)
        return targets

    def _send_to_target_text(self, target_text: str, message: str):
        targets = self._resolve_targets(_split_targets(target_text))
        if not targets:
            return
        self._send_page(targets, message)

    def _send_page(self, targets: list, message: str):
        message = (message or "").strip()
        if not message:
            self.caller.msg("Please input text.")
            return

        allowed = []
        for target in targets:
            if self._can_page(target):
                allowed.append(target)
        if not allowed:
            return

        sender_line, receiver_line, stored = _compose_page_lines(self.caller, allowed, message)
        _create_page_message(self.caller, allowed, stored)

        offline = []
        for target in allowed:
            if _is_online(target):
                target.msg(receiver_line)
            else:
                offline.append(_name(target))
        if offline:
            self.caller.msg(
                f"{', '.join(offline)} is offline. They will see your page when they list pages later."
            )
        self.caller.msg(sender_line)

        allowed_names = _target_names(allowed)
        _set_db(self.caller, "page_last_paged", allowed_names)
        for target in allowed:
            _set_db(target, "page_last_sender", _name(self.caller))
            _set_db(target, "page_reply_group", allowed_names)

    def _can_page(self, target) -> bool:
        if target is self.caller:
            self.caller.msg("You cannot page yourself.")
            return False
        if _is_staff(self.caller):
            return True

        if _get_db(self.caller, "page_locked", False) and not _is_staff(target):
            self.caller.msg(f"{_name(target)} cannot receive your page while you are locked from page.")
            return False
        if _get_db(target, "page_haven", False):
            self.caller.msg(f"{_name(target)} is not receiving pages.")
            return False
        if _identity(self.caller) in _ignored_names(target):
            self.caller.msg(f"{_name(target)} is ignoring your pages.")
            return False
        if _get_db(target, "page_locked", False):
            self.caller.msg(f"{_name(target)} is locked from page.")
            return False

        access = getattr(target, "access", None)
        if callable(access) and not access(self.caller, "msg", default=True):
            self.caller.msg(f"You are not allowed to page {_name(target)}.")
            return False
        return True

    def _reply_last(self, message: str):
        names = _as_list(_get_db(self.caller, "page_last_paged", []))
        if not names:
            self.caller.msg("You haven't paged anyone yet.")
            return
        targets = self._resolve_targets([str(name) for name in names])
        if targets:
            self._send_page(targets, message)

    def _reply_sender(self, message: str):
        sender = _get_db(self.caller, "page_last_sender", "")
        if not sender:
            self.caller.msg("No one has paged you yet.")
            return
        targets = self._resolve_targets([str(sender)])
        if targets:
            self._send_page(targets, message)

    def _reply_all(self, message: str):
        sender = _get_db(self.caller, "page_last_sender", "")
        group = [str(name) for name in _as_list(_get_db(self.caller, "page_reply_group", []))]
        names = []
        if sender:
            names.append(str(sender))
        names.extend(name for name in group if name.casefold() != _identity(self.caller))
        if not names:
            self.caller.msg("No page group to reply to.")
            return
        targets = self._resolve_targets(names)
        if targets:
            self._send_page(targets, message)

    def _set_haven(self, enabled: bool):
        _set_db(self.caller, "page_haven", enabled)
        if enabled:
            self.caller.msg("You are now stopping all pages.")
        else:
            self.caller.msg("You are now receiving pages.")

    def _set_ignore(self, target_query: str, enabled: bool):
        target = self._resolve_one(target_query)
        if not target:
            return
        ignored = _ignored_names(self.caller)
        ident = _identity(target)
        if enabled:
            if ident in ignored:
                self.caller.msg(f"{_name(target)} is already on your page ignore list.")
                return
            ignored.add(ident)
            _set_ignored_names(self.caller, ignored)
            self.caller.msg(f"{_name(target)} is now on your page ignore list.")
            return

        if ident not in ignored:
            self.caller.msg(f"{_name(target)} is not on your page ignore list.")
            return
        ignored.remove(ident)
        _set_ignored_names(self.caller, ignored)
        self.caller.msg(f"{_name(target)} is now off your page ignore list.")

    def _set_lock(self, target_query: str, enabled: bool):
        if not _is_staff(self.caller):
            self.caller.msg("Only staff can lock or unlock page access.")
            return
        target = self._resolve_one(target_query)
        if not target:
            return
        _set_db(target, "page_locked", enabled)
        if enabled:
            self.caller.msg(f"{_name(target)} is now locked from page.")
        else:
            self.caller.msg(f"{_name(target)} is now unlocked from page.")

    def _send_page_mail(self, raw: str):
        target_text, sep, message = (raw or "").partition("=")
        if not sep:
            self.caller.msg("Usage: page #mail <character>=<message>")
            return
        target = self._resolve_one(target_text.strip())
        if not target:
            return
        if not self._can_page(target):
            return
        message = message.strip()
        if not message:
            self.caller.msg("Please input text.")
            return
        subject = f"Page-Mail from {_name(self.caller)}"
        try:
            mail = character_mail.send_character_mail(self.caller, target, subject, _mail_body(self.caller, message))
        except character_mail.CharacterMailError as err:
            self.caller.msg(str(err))
            return
        self.caller.msg(f"Page-mail #{character_mail.mail_id(mail)} sent to {_name(target)}.")

    def _show_last(self):
        names = _as_list(_get_db(self.caller, "page_last_paged", []))
        if not names:
            self.caller.msg("You haven't paged anyone yet.")
            return
        self.caller.msg(f"You last paged {', '.join(str(name) for name in names)}.")

    def _show_history(self, number: int | None = None):
        pages = _page_history(self.caller)
        if number is not None:
            pages = pages[-number:]
        if not pages:
            self.caller.msg("You haven't sent or received any pages yet.")
            return

        lines = []
        for page in pages:
            senders = ", ".join(_name(sender) for sender in _as_list(getattr(page, "senders", []))) or "Unknown"
            receivers = ", ".join(_name(receiver) for receiver in _as_list(getattr(page, "receivers", []))) or "Unknown"
            marker = "to" if self.caller in _as_list(getattr(page, "senders", [])) else "from"
            if marker == "to":
                lines.append(f"to {receivers}: {getattr(page, 'message', getattr(page, 'db_message', ''))}")
            else:
                lines.append(f"from {senders}: {getattr(page, 'message', getattr(page, 'db_message', ''))}")
        self.caller.msg("Your latest pages:\n " + "\n ".join(lines))
