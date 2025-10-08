"""Custom implementation of the ``look`` command."""

from __future__ import annotations

from typing import Iterable, List

from evennia import Command


class CmdLook(Command):
    """Look at the current location or a specific object.

    Usage:
        look
        look <obj>
        look *<account>
    """

    key = "look"
    aliases = ["l", "ls"]
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def func(self):
        """Execute the command."""
        caller = self.caller

        if not self.args:
            target = caller.location
            if not target:
                caller.msg("You have no location to look at!")
                return
            self._send_look(target)
            return

        target = self._resolve_target(self.args)
        if not target:
            return
        self._send_look(target)

    def _resolve_target(self, raw_search: str):
        """Find a target object using the provided search term.

        Args:
            raw_search: The user supplied search string.

        Returns:
            The matched object, or ``None`` if no unique match exists.
        """

        caller = self.caller

        matches = caller.search(raw_search, quiet=True)

        if matches:
            if not isinstance(matches, list):
                return matches

            if len(matches) == 1:
                return matches[0]

            narrowed = self._filter_partial_matches(raw_search, matches)
            if len(narrowed) == 1:
                return narrowed[0]

            caller.search(raw_search)
            return None

        candidates = self._gather_candidates()
        narrowed = self._filter_partial_matches(raw_search, candidates)
        if len(narrowed) == 1:
            return narrowed[0]
        if len(narrowed) > 1:
            caller.search(raw_search)
            return None

        caller.search(raw_search)
        return None

    def _gather_candidates(self) -> List:
        """Collect default candidates for partial matching."""

        caller = self.caller
        candidates: List = []

        location = getattr(caller, "location", None)
        if location:
            candidates.append(location)
            candidates.extend(location.contents)

        candidates.extend(caller.contents)

        unique: List = []
        seen: set[int] = set()
        for obj in candidates:
            if not obj:
                continue
            identifier = getattr(obj, "id", None)
            if identifier is None:
                identifier = id(obj)
            if identifier in seen:
                continue
            seen.add(identifier)
            unique.append(obj)

        return unique

    def _filter_partial_matches(self, raw_search: str, candidates: Iterable) -> List:
        """Filter candidates by case-insensitive partial matches."""

        term = raw_search.strip().lower()
        if not term:
            return []
        matches: List = []

        for obj in candidates:
            if not obj:
                continue
            aliases = getattr(obj, "aliases", None)
            alias_iterable = aliases.all() if hasattr(aliases, "all") else aliases or []
            names = [obj.key] + list(alias_iterable)
            if any(term in name.lower() for name in names if name):
                matches.append(obj)

        return matches

    def _send_look(self, target) -> None:
        """Send the formatted look output to the caller."""

        desc = self.caller.at_look(target)
        self.msg(text=(desc, {"type": "look"}), options=None)
