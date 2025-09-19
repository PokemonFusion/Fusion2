"""Temporary developer command to inflict status conditions."""

from evennia import Command


class CmdStatusDev(Command):
        """Inflict common status conditions for quick testing."""

        key = "statusdev"
        locks = "cmd:perm(Developer)"

        def parse(self):
                self.args = (self.args or "").split()

        def func(self):
                if len(self.args) < 2:
                        self.caller.msg("Usage: statusdev <brn|psn|tox|par|slp|frz> <target>")
                        return
                status_key = self.args[0].lower()
                target_name = " ".join(self.args[1:])
                target = self.caller.search(target_name)
                if not target:
                        return
                status_map = {
                        "brn": "brn",
                        "psn": "psn",
                        "tox": "tox",
                        "par": "par",
                        "slp": "slp",
                        "frz": "frz",
                }
                status = status_map.get(status_key)
                if not status:
                        self.caller.msg("Unknown status identifier.")
                        return
                inflict = getattr(target, "inflict_status", None)
                if not callable(inflict):
                        ok = target.setStatus(status)
                else:
                        ok = inflict(status, source=self.caller)
                self.caller.msg(f"Inflict {status.upper()} => {'ok' if ok else 'blocked'} on {target.key}.")
