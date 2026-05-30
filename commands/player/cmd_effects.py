"""Command to display active battle field, side and Pokémon effects."""

from __future__ import annotations

from evennia import Command

from pokemon.battle.registry import REGISTRY
from pokemon.ui.battle_effects import render_effects_panel

# Simple helper: get current room's battles by checking sessions that have .room


def _battles_in_room(room):
    return [s for s in REGISTRY.all() if getattr(s, "room", None) == room]


def _current_battle_for_caller(caller):
    inst = getattr(getattr(caller, "ndb", None), "battle_instance", None)
    if inst and getattr(inst, "room", None) == getattr(caller, "location", None):
        return inst
    in_room = _battles_in_room(getattr(caller, "location", None))
    if len(in_room) == 1:
        return in_room[0]
    return None


def _session_title(s):
    a = getattr(getattr(s, "captainA", None), "name", "?")
    b = getattr(getattr(s, "captainB", None), "name", "?")
    enc = (getattr(getattr(s, "state", s), "encounter_kind", "") or "").lower()
    if enc == "wild":
        bmon = getattr(getattr(s, "captainB", None), "active_pokemon", None)
        b = f"Wild {getattr(bmon, 'name', 'Pokémon')}"
    turn = getattr(getattr(s, "state", s), "round", getattr(getattr(s, "state", s), "turn", 0))
    sid = getattr(s, "id", None) or getattr(s, "uuid", None) or str(id(s))
    return f"#{str(sid)[-3:]}  {a} – {b} (Turn {turn})"


class CmdEffects(Command):
    """Show battle status, field effects, and active Pokemon effects.

    Usage:
      +status [#id|@name|here] [brief] [me|opp] [list|next|prev]

    Examples:
      +status
      +status brief
      +status opp
      +status list

    Notes:
      Participants see full info for their own Pokemon. Watchers see revealed
      battle information.
    """

    key = "+status"
    aliases = ["+effects", "+bstate"]
    locks = "cmd:all()"
    switch_options = ()
    help_category = "Pokemon/Battle"

    def parse(self):
        self.flags = {
            "brief": False,
            "focus": None,
            "sel": None,
            "list": False,
            "next": False,
            "prev": False,
        }
        args = (self.args or "").strip()
        toks = [t for t in args.split() if t]
        for t in toks:
            lt = t.lower()
            if lt in ("brief", "-b", "--brief"):
                self.flags["brief"] = True
            elif lt in ("me", "mine"):
                self.flags["focus"] = "me"
            elif lt in ("opp", "opponent"):
                self.flags["focus"] = "opp"
            elif lt == "list":
                self.flags["list"] = True
            elif lt == "next":
                self.flags["next"] = True
            elif lt == "prev":
                self.flags["prev"] = True
            elif lt == "here":
                self.flags["sel"] = ("here", None)
            elif lt.startswith("#"):
                self.flags["sel"] = ("id", lt.lstrip("#"))
            elif lt.startswith("@"):
                self.flags["sel"] = ("name", lt.lstrip("@"))
            else:
                if lt.isdigit():
                    self.flags["sel"] = ("id", lt)
                else:
                    self.flags["sel"] = ("name", t)

    def _get_focus_list(self):
        return [
            getattr(s, "id", None) or getattr(s, "uuid", None) or str(id(s)) for s in REGISTRY.sessions_for(self.caller)
        ]

    def _get_sticky_focus(self):
        return self.caller.attributes.get("effects_focus_id", default=None)

    def _set_sticky_focus(self, ident):
        self.caller.attributes.add("effects_focus_id", ident)

    def func(self):
        caller = self.caller
        sessions = REGISTRY.sessions_for(caller)

        # cycling
        if self.flags["next"] or self.flags["prev"]:
            if not sessions:
                caller.msg("You're not in or watching any battles.")
                return
            ids = [str(getattr(s, "id", None) or getattr(s, "uuid", None) or id(s)) for s in sessions]
            cur = str(self._get_sticky_focus() or ids[0])
            if cur not in ids:
                cur = ids[0]
            idx = ids.index(cur)
            idx = (idx + (1 if self.flags["next"] else -1)) % len(ids)
            self._set_sticky_focus(ids[idx])
            caller.msg(f"Watch focus set to #{ids[idx][-3:]}.")
            return

        # list
        if self.flags["list"]:
            if not sessions:
                caller.msg("No battles found for you. Join a battle or watch one.")
                return
            lines = [f"{i + 1:>2}. {_session_title(s)}" for i, s in enumerate(sessions)]
            caller.msg("\n".join(lines))
            return

        # explicit selection
        target = None
        if self.flags["sel"]:
            mode, val = self.flags["sel"]
            if mode == "here":
                in_room = _battles_in_room(caller.location)
                if not in_room:
                    caller.msg("No battles found in this room.")
                    return
                if len(in_room) > 1:
                    caller.msg("Multiple battles here. Use +status list or +status #<id>.")
                    return
                target = in_room[0]
            elif mode == "id":
                target = REGISTRY.get_by_id(val)
            elif mode == "name":
                for s in REGISTRY.all():
                    a = getattr(getattr(s, "captainA", None), "name", None)
                    b = getattr(getattr(s, "captainB", None), "name", None)
                    if str(val).lower() in (str(a).lower(), str(b).lower()):
                        target = s
                        break
            if not target:
                caller.msg("Battle not found. Try +status list.")
                return
            self._set_sticky_focus(getattr(target, "id", None) or getattr(target, "uuid", None) or str(id(target)))
        else:
            participant = [
                s for s in sessions if caller in getattr(s, "teamA", []) or caller in getattr(s, "teamB", [])
            ]
            if participant:
                target = participant[0]
            elif len(sessions) == 1:
                target = sessions[0]
            else:
                sticky = self._get_sticky_focus()
                if sticky:
                    target = REGISTRY.get_by_id(sticky) or None
                if not target:
                    if not sessions:
                        caller.msg(
                            (
                                "You're not in a battle or watching one. "
                                "Try: +status #<id> / +status @<name> / +status here"
                            )
                        )
                        return
                    lines = [
                        "You're watching multiple battles. Try: +status #<id> or +status @Captain",
                        *[f"{i + 1:>2}. {_session_title(s)}" for i, s in enumerate(sessions)],
                    ]
                    caller.msg("\n".join(lines))
                    return

        panel = render_effects_panel(
            target,
            caller,
            total_width=78,
            brief=self.flags["brief"],
            focus=self.flags["focus"],
        )
        caller.msg(panel)


class CmdEffectsAdminReveal(Command):
    """Toggle admin-only ability reveal for the current battle.

    Usage:
      +effects/adminreveal
      +effects/adminreveal on
      +effects/adminreveal off
      +effects/adminreveal toggle
    """

    key = "+effects/adminreveal"
    aliases = ["+effects/adminreveal"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        inst = _current_battle_for_caller(caller)
        if not inst:
            in_room = _battles_in_room(getattr(caller, "location", None))
            if len(in_room) > 1:
                caller.msg("Multiple battles are active here. Join the battle you want to change first.")
            else:
                caller.msg("No active battle found in this room.")
            return

        arg = (self.args or "").strip().lower()
        current = True
        getter = getattr(inst, "get_admin_ability_reveal", None)
        if callable(getter):
            current = bool(getter())
        else:
            data = getattr(getattr(inst, "logic", None), "data", None)
            current = bool(getattr(data, "admin_ability_reveal", True))

        if arg in {"", "toggle"}:
            enabled = not current
        elif arg in {"on", "enable", "enabled", "true", "yes"}:
            enabled = True
        elif arg in {"off", "disable", "disabled", "false", "no"}:
            enabled = False
        else:
            caller.msg("Usage: +effects/adminreveal [on|off|toggle]")
            return

        setter = getattr(inst, "set_admin_ability_reveal", None)
        if callable(setter):
            setter(enabled)
        else:
            data = getattr(getattr(inst, "logic", None), "data", None)
            if data is not None:
                data.admin_ability_reveal = bool(enabled)
            battle = getattr(getattr(inst, "logic", None), "battle", None) or getattr(inst, "battle", None)
            if battle is not None:
                setattr(battle, "admin_ability_reveal", bool(enabled))
            storage = getattr(inst, "storage", None)
            if storage is not None and data is not None:
                storage.set("data", data.to_dict())

        state = "ON" if enabled else "OFF"
        caller.msg(f"Admin ability reveal for this battle is now {state}.")
