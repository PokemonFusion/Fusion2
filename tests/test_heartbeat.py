from __future__ import annotations

import importlib
import sys
import types
from datetime import datetime, timezone

from world import heartbeat


class DummyScript:
    def __init__(self, key=heartbeat.HEARTBEAT_SCRIPT_KEY, typeclass_path=""):
        self.key = key
        self.db_typeclass_path = typeclass_path
        self.db = types.SimpleNamespace()
        self.is_active = False
        self.started = 0

    def start(self):
        self.started += 1
        self.is_active = True


class DummyCaller:
    def __init__(self):
        self.messages: list[str] = []

    def msg(self, text):
        self.messages.append(text)


def test_heartbeat_script_has_900_second_interval():
    script = DummyScript()

    heartbeat.configure_heartbeat_script(script)

    assert script.interval == 900
    assert script.start_delay is True
    assert script.repeats == 0
    assert script.persistent is True


def test_startup_helper_creates_heartbeat_once(monkeypatch):
    scripts: list[DummyScript] = []
    create_calls = []

    class FakeEvennia:
        @staticmethod
        def search_script(key):
            return [script for script in scripts if script.key == key]

        @staticmethod
        def create_script(typeclass, key):
            create_calls.append((typeclass, key))
            script = DummyScript(key=key, typeclass_path=typeclass)
            scripts.append(script)
            return script

    monkeypatch.setattr(heartbeat, "safe_import", lambda name: FakeEvennia)

    first = heartbeat.ensure_heartbeat_script()
    second = heartbeat.ensure_heartbeat_script()

    assert first is second
    assert len(scripts) == 1
    assert create_calls == [
        (heartbeat.HEARTBEAT_SCRIPT_TYPECLASS, heartbeat.HEARTBEAT_SCRIPT_KEY)
    ]
    assert scripts[0].interval == 900
    assert scripts[0].started == 1


def test_at_repeat_increments_tick_count():
    script = DummyScript()
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)

    result = heartbeat.run_heartbeat_tick(script, jobs=(), now=now)

    assert result["tick_count"] == 1
    assert script.db.tick_count == 1
    assert script.db.last_run == "2026-05-31T12:00:00+00:00"
    assert script.db.last_success == "2026-05-31T12:00:00+00:00"


def test_heartbeat_script_at_repeat_increments_tick_count(monkeypatch):
    fake_evennia = types.ModuleType("evennia")
    fake_scripts = types.ModuleType("evennia.scripts")
    fake_scripts_mod = types.ModuleType("evennia.scripts.scripts")

    class DefaultScript:
        def __init__(self):
            self.db = types.SimpleNamespace()
            self.is_active = False

    fake_scripts_mod.DefaultScript = DefaultScript
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)
    monkeypatch.setitem(sys.modules, "evennia.scripts", fake_scripts)
    monkeypatch.setitem(sys.modules, "evennia.scripts.scripts", fake_scripts_mod)
    sys.modules.pop("typeclasses.scripts", None)

    scripts_mod = importlib.import_module("typeclasses.scripts")
    script = scripts_mod.HeartbeatScript()

    script.at_script_creation()
    script.at_repeat()

    assert script.interval == 900
    assert script.db.tick_count == 1


def test_paused_heartbeat_does_not_run_jobs():
    script = DummyScript()
    script.db.paused = True
    calls = []

    def run_job(_context):
        calls.append("ran")

    result = heartbeat.run_heartbeat_tick(
        script,
        jobs=(heartbeat.HeartbeatJob("test_job", run_job),),
        now=datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc),
    )

    assert result["status"] == "paused"
    assert calls == []
    assert script.db.tick_count == 1


def test_failing_job_does_not_stop_later_jobs():
    script = DummyScript()
    calls = []

    def bad_job(_context):
        raise RuntimeError("boom")

    def good_job(_context):
        calls.append("good")
        return "finished"

    result = heartbeat.run_heartbeat_tick(
        script,
        jobs=(
            heartbeat.HeartbeatJob("bad_job", bad_job),
            heartbeat.HeartbeatJob("good_job", good_job),
        ),
    )

    assert calls == ["good"]
    assert result["status"] == "failed"
    assert "bad_job: RuntimeError: boom" in result["failures"]
    assert script.db.last_job_results[0]["status"] == "failed"
    assert script.db.last_job_results[1]["status"] == "ok"


def test_daily_maintenance_only_runs_once_per_date():
    script = DummyScript()
    first = heartbeat.HeartbeatContext(
        script=script,
        now=datetime(2026, 5, 31, 1, 0, tzinfo=timezone.utc),
    )
    second = heartbeat.HeartbeatContext(
        script=script,
        now=datetime(2026, 5, 31, 23, 0, tzinfo=timezone.utc),
    )

    first_message = heartbeat.daily_maintenance_check(first)
    second_message = heartbeat.daily_maintenance_check(second)

    assert "recorded for 2026-05-31" in first_message
    assert second_message == "daily maintenance already ran for 2026-05-31"
    assert script.db.last_daily_maintenance_date == "2026-05-31"
    assert script.db.last_daily_maintenance_run == "2026-05-31T01:00:00+00:00"


def test_admin_command_status_output_includes_key_fields(monkeypatch):
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)
    sys.modules.pop("commands.admin.cmd_heartbeat", None)
    cmd_mod = importlib.import_module("commands.admin.cmd_heartbeat")

    script = DummyScript(typeclass_path=heartbeat.HEARTBEAT_SCRIPT_TYPECLASS)
    script.is_active = True
    script.interval = 900
    script.db.tick_count = 7
    script.db.last_run = "2026-05-31T12:00:00+00:00"
    script.db.last_success = "2026-05-31T12:00:00+00:00"
    monkeypatch.setattr(cmd_mod, "get_heartbeat_script", lambda: script)

    cmd = cmd_mod.CmdHeartbeat()
    cmd.caller = DummyCaller()
    cmd.args = ""
    cmd.switches = ["status"]
    cmd.func()

    text = cmd.caller.messages[-1]
    assert "Exists: yes" in text
    assert "Active: yes" in text
    assert "Interval: 900 seconds" in text
    assert "Tick count: 7" in text
    assert "Last run: 2026-05-31T12:00:00+00:00" in text
    assert "activity_tick: enabled" in text
