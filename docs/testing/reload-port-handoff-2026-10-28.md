# Reload listener handoff verification — 2026-10-28

The Server now waits for its listening sockets to close before disconnecting
AMP. The Portal can then start the replacement Server without racing the old
internal HTTP listener. This uses Evennia's configured Server service extension;
it does not modify installed framework files or game data.

## Diagnosis

The preceding PF2-Dev update logged `CannotListenError` on `127.0.0.1:4005`
while reloading from `4347e76` to `f66982e`. The Portal remained running; the
old Server eventually released the port and the separately guarded retry
succeeded. That incident's backup, logs and preservation receipts remain in
the private `pf2-dev-position-label-release-20261027` artifact directory.

Inspection of the pinned Evennia 6.0.0 and Twisted 24.11.0 code identified a
reproducible ordering defect:

1. `MultiService.stopService` starts every child's shutdown concurrently.
2. A TCP listener can still own its socket while its close Deferred is pending.
3. AMP disconnect is the Portal's signal to launch the replacement Server.
4. Evennia's `WSGIWebServer.stopService` also discards the underlying TCP close
   Deferred, so merely awaiting the web service's return value is insufficient.

The regression uses the actual Evennia WSGI service, Twisted reactor, loopback
TCP sockets and AMP transports. With a deliberately delayed listener close,
the old service ordering reliably attempts the replacement bind too early.

## Change

`server.conf.server_service.ReloadSafeServerService` closes service-owned TCP
listeners and awaits their actual close Deferreds before delegating the ordinary
child-service shutdown. It clears the volatile port reference so the normal
TCP/WSGI shutdown does not close it twice. Thread-pool and AMP shutdown still
run normally; existing save, checkpoint and session-sync hooks are unchanged.
Multiple listeners must all finish. A close failure is propagated without
announcing a successful disconnect. There is no production sleep, retry loop,
process kill or port reassignment.

## Automated evidence

| Check | Result |
|---|---|
| Real lifecycle cases | 8 passed |
| Existing real AMP input/session-sync cases | 7 passed |
| Old-order real-socket reproduction | 1 expected bind conflict |
| Fixed-order real-socket repetitions | 5 successful handoffs; 0 conflicts |
| Fresh-process pytest wrappers, including existing AMP wrapper | 3 passed |
| Local mandatory gate, combined pass | 7,397 passed; 4,032 skipped; 846.62s |

The lifecycle cases cover delayed and out-of-order listener closes, the actual
WSGI return-value gap, failure propagation, partially started services, awaiting
asynchronous AMP shutdown, and the configured extension class. Database cursor
access is explicitly refused in both new integration scripts. Each socket test
uses ephemeral loopback ports, not any running game's ports.

Commands from the repository root, using the project's virtual environment:

```text
python -B tests/integration/server_shutdown_cases.py
python -B tests/integration/reload_socket_cases.py
python -B tests/integration/amp_reload_cases.py
python -B -m pytest -q tests/test_server_shutdown.py tests/test_amp_reload.py
python -B tools/run_mandatory_tests.py
```

The lifecycle-integrity GitHub workflow runs both new scripts directly, in
addition to the mandatory suite. The pull request records final repeat,
battle-first and hosted results; the combined result above was complete before
the source commit. Private local logs, source hashes and the machine receipt
are retained under `reload-port-handoff-20261028`.

## Activation and limits

This evidence qualifies isolated service/socket behavior, not a deployment or
live player session. No existing game database, account, character, Pokemon,
shop stock or service was changed during these checks. The local mandatory
gate has no PostgreSQL fixture configured; its skipped suites are not credited
as database or migration evidence.

The new service class is constructed when the Server next starts. A process
already running the old class still uses the old shutdown ordering during the
first transition. A rollout must therefore retain its approved backup, listener
and process checks, with a bounded recovery plan if that first transition
encounters the old race. Subsequent reloads use the close barrier. No migration
or Portal restart is required by this code change. Existing service restart
approval rules still apply.

The barrier prevents this shutdown-order race; it does not free a port owned by
an unrelated process. A failed close is an operational failure to investigate,
not permission to kill the owner, change ports or launch repeated replacements.
