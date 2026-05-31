"""Global heartbeat runner and small heartbeat jobs for Fusion2."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from utils.safe_import import safe_import


HEARTBEAT_INTERVAL_SECONDS = 900
HEARTBEAT_SCRIPT_KEY = "WorldHeartbeat"
HEARTBEAT_SCRIPT_TYPECLASS = "typeclasses.scripts.HeartbeatScript"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HeartbeatContext:
    """Runtime context passed to each heartbeat job."""

    script: Any
    now: datetime
    forced: bool = False


HeartbeatCallable = Callable[[HeartbeatContext], str | None]


@dataclass(frozen=True)
class HeartbeatJob:
    """One isolated heartbeat job."""

    name: str
    run: HeartbeatCallable
    enabled: bool = True
    description: str = ""


def _db(script: Any) -> Any:
    return getattr(script, "db", None)


def _get_db(script: Any, name: str, default: Any = None) -> Any:
    db = _db(script)
    if db is None:
        return default
    try:
        value = getattr(db, name)
    except Exception:
        return default
    return default if value is None else value


def _set_db(script: Any, name: str, value: Any) -> None:
    db = _db(script)
    if db is None:
        return
    setattr(db, name, value)


def _set_default(script: Any, name: str, value: Any) -> None:
    if _get_db(script, name, None) is None:
        _set_db(script, name, value)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_now(now: datetime | None = None) -> datetime:
    value = now or _utc_now()
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _timestamp(now: datetime) -> str:
    return _normalize_now(now).replace(microsecond=0).isoformat()


def initialize_heartbeat_state(script: Any) -> None:
    """Ensure persistent heartbeat attributes exist."""

    _set_default(script, "enabled", True)
    _set_default(script, "paused", False)
    _set_default(script, "tick_count", 0)
    _set_default(script, "last_run", "")
    _set_default(script, "last_success", "")
    _set_default(script, "last_error", "")
    _set_default(script, "last_job_results", [])
    _set_default(script, "last_daily_maintenance_date", "")
    _set_default(script, "last_daily_maintenance_run", "")


def _set_script_field(script: Any, name: str, value: Any) -> None:
    try:
        setattr(script, name, value)
        return
    except Exception:
        pass
    try:
        setattr(script, f"db_{name}", value)
    except Exception:
        pass


def configure_heartbeat_script(script: Any, *, start: bool = False) -> Any:
    """Apply the standard persistent script configuration."""

    _set_script_field(script, "interval", HEARTBEAT_INTERVAL_SECONDS)
    _set_script_field(script, "start_delay", True)
    _set_script_field(script, "repeats", 0)
    _set_script_field(script, "persistent", True)
    initialize_heartbeat_state(script)

    if start and not bool(getattr(script, "is_active", False)):
        starter = getattr(script, "start", None)
        if callable(starter):
            try:
                starter()
            except Exception:
                logger.exception("Failed to start heartbeat script.")
    return script


def _script_typeclass(script: Any) -> str:
    return str(
        getattr(script, "db_typeclass_path", None)
        or getattr(script, "typeclass_path", None)
        or ""
    )


def _pick_heartbeat_script(scripts: Iterable[Any]) -> Any | None:
    choices = list(scripts or [])
    for script in choices:
        if _script_typeclass(script) == HEARTBEAT_SCRIPT_TYPECLASS:
            return script
    return choices[0] if choices else None


def get_heartbeat_script() -> Any | None:
    """Return the configured heartbeat script if Evennia can find it."""

    try:
        evennia = safe_import("evennia")
        return _pick_heartbeat_script(evennia.search_script(HEARTBEAT_SCRIPT_KEY))
    except Exception:
        return None


def ensure_heartbeat_script() -> Any | None:
    """Create or update the global heartbeat script without duplicating it."""

    try:
        evennia = safe_import("evennia")
        script = _pick_heartbeat_script(evennia.search_script(HEARTBEAT_SCRIPT_KEY))
        if script is None:
            script = evennia.create_script(
                HEARTBEAT_SCRIPT_TYPECLASS,
                key=HEARTBEAT_SCRIPT_KEY,
            )
        return configure_heartbeat_script(script, start=True)
    except Exception:
        logger.exception("Could not ensure heartbeat script.")
        return None


def activity_tick(context: HeartbeatContext) -> str:
    """Record that the activity tick ran without granting progression."""

    _set_db(context.script, "last_activity_tick", _timestamp(context.now))
    return "activity tick recorded; no progression rewards are configured yet"


def daily_maintenance_check(context: HeartbeatContext) -> str:
    """Run once per UTC calendar day and leave extension points for resets."""

    today = _normalize_now(context.now).date().isoformat()
    if _get_db(context.script, "last_daily_maintenance_date", "") == today:
        return f"daily maintenance already ran for {today}"

    _set_db(context.script, "last_daily_maintenance_date", today)
    _set_db(context.script, "last_daily_maintenance_run", _timestamp(context.now))
    return (
        f"daily maintenance recorded for {today}; reset hooks are not configured yet"
    )


def battle_cleanup_tick(context: HeartbeatContext) -> str:
    """Conservative battle cleanup hook with no active-battle termination."""

    try:
        from pokemon.battle.handler import battle_handler
    except Exception as err:
        return f"battle handler unavailable: {err}"

    instances = getattr(battle_handler, "instances", {}) or {}
    cleanup = getattr(battle_handler, "gc", None)
    if callable(cleanup):
        cleanup()
        return f"battle cleanup hook ran; active battles now {len(instances)}"
    return (
        f"observed {len(instances)} active battle(s); no stale-battle policy configured"
    )


def get_heartbeat_jobs() -> tuple[HeartbeatJob, ...]:
    """Return the registered heartbeat jobs in execution order."""

    return (
        HeartbeatJob(
            name="activity_tick",
            run=activity_tick,
            description="Records a safe activity tick without granting rewards.",
        ),
        HeartbeatJob(
            name="daily_maintenance_check",
            run=daily_maintenance_check,
            description="Records once-per-day maintenance state.",
        ),
        HeartbeatJob(
            name="battle_cleanup_tick",
            run=battle_cleanup_tick,
            description="Observes battle state without ending active battles.",
        ),
    )


def run_heartbeat_tick(
    script: Any,
    *,
    jobs: Iterable[HeartbeatJob] | None = None,
    now: datetime | None = None,
    forced: bool = False,
) -> dict[str, Any]:
    """Run one heartbeat tick and persist status on the script."""

    initialize_heartbeat_state(script)
    current_time = _normalize_now(now)
    current_stamp = _timestamp(current_time)
    tick_count = int(_get_db(script, "tick_count", 0) or 0) + 1

    _set_db(script, "last_run", current_stamp)
    _set_db(script, "tick_count", tick_count)

    if not bool(_get_db(script, "enabled", True)):
        result = {
            "status": "disabled",
            "tick_count": tick_count,
            "results": [],
            "failures": [],
        }
        _set_db(script, "last_job_results", [])
        return result

    if bool(_get_db(script, "paused", False)):
        result = {
            "status": "paused",
            "tick_count": tick_count,
            "results": [],
            "failures": [],
        }
        _set_db(script, "last_job_results", [])
        return result

    context = HeartbeatContext(script=script, now=current_time, forced=forced)
    results: list[dict[str, str]] = []
    failures: list[str] = []

    for job in jobs if jobs is not None else get_heartbeat_jobs():
        if not job.enabled:
            results.append({"name": job.name, "status": "skipped", "message": "disabled"})
            continue
        try:
            message = job.run(context) or "ok"
        except Exception as err:
            message = f"{type(err).__name__}: {err}"
            failures.append(f"{job.name}: {message}")
            results.append({"name": job.name, "status": "failed", "message": message})
            logger.exception("Heartbeat job failed: %s", job.name)
            continue
        results.append({"name": job.name, "status": "ok", "message": str(message)})

    _set_db(script, "last_job_results", results)
    if failures:
        _set_db(script, "last_error", "; ".join(failures))
        status = "failed"
    else:
        _set_db(script, "last_error", "")
        _set_db(script, "last_success", current_stamp)
        status = "ok"

    return {
        "status": status,
        "tick_count": tick_count,
        "results": results,
        "failures": failures,
    }


def set_heartbeat_paused(script: Any, paused: bool) -> None:
    """Pause or resume job execution while preserving heartbeat state."""

    initialize_heartbeat_state(script)
    _set_db(script, "paused", bool(paused))


def _value_or_unknown(value: Any) -> str:
    return str(value) if value not in (None, "") else "never"


def format_heartbeat_jobs() -> str:
    """Return a readable list of registered jobs."""

    lines = ["Heartbeat jobs:"]
    for job in get_heartbeat_jobs():
        state = "enabled" if job.enabled else "disabled"
        desc = f" - {job.description}" if job.description else ""
        lines.append(f"- {job.name}: {state}{desc}")
    return "\n".join(lines)


def format_heartbeat_status(script: Any | None) -> str:
    """Return a readable admin status report."""

    lines = ["Heartbeat status:"]
    if script is None:
        lines.append("Exists: no")
        lines.append(format_heartbeat_jobs())
        return "\n".join(lines)

    initialize_heartbeat_state(script)
    lines.extend(
        [
            "Exists: yes",
            f"Active: {'yes' if bool(getattr(script, 'is_active', False)) else 'no'}",
            f"Interval: {getattr(script, 'interval', getattr(script, 'db_interval', 'unknown'))} seconds",
            f"Enabled: {'yes' if bool(_get_db(script, 'enabled', True)) else 'no'}",
            f"Paused: {'yes' if bool(_get_db(script, 'paused', False)) else 'no'}",
            f"Last run: {_value_or_unknown(_get_db(script, 'last_run', ''))}",
            f"Last success: {_value_or_unknown(_get_db(script, 'last_success', ''))}",
            f"Last error: {_value_or_unknown(_get_db(script, 'last_error', ''))}",
            f"Tick count: {int(_get_db(script, 'tick_count', 0) or 0)}",
            format_heartbeat_jobs(),
        ]
    )
    return "\n".join(lines)
