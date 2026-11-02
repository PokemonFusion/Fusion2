# Adventure Mode Operations

Adventure Mode provides short authored expeditions launched from Adventure
Hall. The current playable mission is `alpha_meadow` (Alpha Meadow Survey).

## Player Flow

Start in Adventure Hall. The original survey can be completed without a battle:

```text
+adventure/start alpha_meadow
north
north
+adventure/search
south
south
+adventure/leave
```

Reaching and searching the Old Tree, then returning to the entrance, completes
the survey. The route encounter is optional until chosen. Bring a battle-ready
party if you choose an encounter; once chosen, its result must resolve before
completion, including after a failed result save.

For either existing optional encounter:

```text
+adventure/list
+adventure/info alpha_meadow
+adventure/start alpha_meadow
north
+adventure/choose wild
```

At the Tall Grass Path, choose `wild` for a catchable Rattata or `trainer` for
Surveyor Mina's Pidgey. Finish the battle normally. Winning, losing, catching,
or fleeing resolves the encounter; ordinary setbacks do not restart the run.

Continue north, search the Old Tree, and return south to the entrance:

```text
north
+adventure/search
south
south
+adventure/leave
```

Useful commands during a run are `+adventure/look`, `+adventure/objectives`,
and `+adventure/leave`. A route choice is locked once its encounter begins.
If battle startup fails before a battle is created, repeat the same choice.

The first completed clear grants one Potion, whether or not an encounter was
chosen. A chosen route retains its original encounter result; a survey-only
clear invents no route or battle outcome. Later clears remain available for alternate outcomes,
catching, and roleplay but do not duplicate the first-clear reward.

If an encounter result cannot be saved, use `+adventure/retry`. This replays
the recorded outcome without starting another encounter. The original result
survives battle cleanup and reconnect; another route encounter is blocked
while that result is pending.

If a first-clear reward could not be delivered, use `+adventure/claim`.
This checks only your character's completed runs and works after leaving an
Adventure. Repeated claims do not grant extra items. An interrupted inventory
write or claim marker is rolled back together so the reward can be retried.

## Builder Setup

Run `batchcommands adventure_hall` once from the room that should link to
Adventure Hall. The batch file is intentionally non-idempotent and must not be
rerun against the same database.

Validate content and room setup with:

```text
+adventureadmin/validate all
+adventureadmin/preview alpha_meadow
+adventureadmin/cleanup
```

Use `+adventureadmin/list` and `+adventureadmin/info <session_id>` to inspect
sessions. Staff can abort a broken run or return a stranded player with the
documented Adventure admin commands.

The migration adding per-player result and reward tracking must be applied as
part of the normal deployment process before enabling this version.

## Current Boundaries

- Solo only; data is per-participant so party support can follow.
- One authored mission and one fixed difficulty.
- No weekly/monthly board goals or permanent milestone UI yet.
- No reputation, procedural generation, crafting loop, or player-authored maps.

## Exclusive solo instances (#833)

The reservation belongs to a **character**, independently of its account. Only
that character may enter or view its instance, select its battle through
`+status`, or register for battle observations. Other characters on the same
account have the same restrictions as any outsider. Developer permission is
the explicit staff inspection exception; Builder permission alone is insufficient.
Staff inspection is not ordinary-player acceptance.

`AdventureSession.holds_instance` records occupancy separately from completion.
Database constraints permit at most one occupied run per character and per room,
and require both identities on every occupied run. Completing a survey retains
the reservation until the owner leaves. Battle storage, pending original results
and failed return movement also retain it. After leaving, historical results and
unpaid first-clear rewards remain available without reserving the room.

Starts, returns and encounter-result writes acquire locks in battle order:
instance room, character, then session. A failed entry releases only its own
claim; a delayed leave/expiry cannot release a newer run. An expired owner still
inside must return successfully before the room becomes reusable. Expiry of an
owner already outside does not move that character. An unreserved room with a
character still physically inside is not offered as free capacity.

The existing fixed room pool remains in use. A full pool produces a retryable
message. Do not clear ownership attributes or rerun the Hall batch to bypass it.
Privacy checks apply at room admission, appearance, observation registration,
restoration and central battle output, including stale observer registrations.
Ordinary battles outside Adventure instances retain their existing policy.

### Schema preflight and activation

This change requires `0060_adventure_occupancy`. **Migration execution and shared
game activation require separate approval.** Prepare a verified backup and a
quiescent deployment window using the normal operational procedure. From the
intended deployment checkout with its existing database settings, inspect first:

```powershell
..\evenv\Scripts\python.exe -B tools/audit_adventure_occupancy.py
```

The read-only preflight works against the legacy schema. It lists retained
session IDs and exact conflicting identities; it never guesses a winner or
repairs data. The migration repeats that preflight transactionally, preserving
active runs, completed occupancy, original-result receipts and battle identities.
Ambiguous ownership, missing identities or invalid receipts stop the migration.
Session histories, participation, encounter outcomes and unpaid rewards are not
rewritten. Resolve any reported ambiguity through separately reviewed recovery.

Before approval to deploy, rehearse fresh installation, a legacy upgrade with
held/completed/unpaid runs, and rejected conflicting claims on a disposable
PostgreSQL fixture. The guarded runner is:

```powershell
# Only after explicit approval, with PF2_TEST_POSTGRES_DSN set to a test fixture:
..\evenv\Scripts\python.exe -B tests/integration/adventure_migration_cases.py --approved
```

This rehearsal is separate from model-table tests. Do not point it at a game
database. Do not reverse/delete participation history as a rollback shortcut.
Rollback across 0060 must coordinate code and schema: older Adventure inserts
do not populate the new required occupancy column. Keep admissions quiescent
until a separately approved rollback plan preserves all held runs and receipts;
reverting only Python source is insufficient.

### Regression and socket checks

`tests/integration/adventure_privacy_cases.py` covers independent-connection
same-room/same-character starts, release/reuse, stale markers, failed movement,
database uniqueness, actual admission/observation commands and the staff exception.
The lifecycle CI runs this alongside the retained Adventure player/recovery suites.

`tests/integration/adventure_socket_cases.py` starts a task-owned Portal and
Server against an explicit disposable PostgreSQL schema. It tests real Telnet
login and commands with two Player accounts and two characters on one account,
then stops its processes and removes its schema. It creates fixture model tables
without migrations and records command-level evidence under `.codex-artifacts`.
It does not establish shared-world deployment, migration readiness, or injected
failure acceptance. The command/SQL suites retain pending-outcome and failure
coverage separately.

The [September closeout](testing/september-closeout-2026-10-23.md) records the
retained integration, non-combat route repair, current command/SQL checks and
deferred November work. `tests/integration/adventure_player_cases.py` exercises
the real player typeclass, persisted room pool, cardinal commands, reconnect
seam, leave/expiry, reward recovery and the existing optional wild route.

## Recovery Change Validation

The recovery changes use existing character attributes and Adventure tables;
they add no migration beyond the branch's required `0040_adventure_participation`.
Reload the game through the normal approved deployment procedure after that
migration has been applied. No running service or game database is changed by
the automated recovery tests.

Manual checks on a test server:

1. Finish each route normally and confirm its recorded outcome and objectives.
2. Simulate a temporary result-save failure in a controlled test environment.
   Confirm the battle ends once its retry receipt is saved; reconnect and use
   `+adventure/retry`. Verify the original outcome is applied once and a new
   encounter cannot start while it is pending.
3. Interrupt reward delivery on a new character's first clear. Leave the run,
   reconnect, and use `+adventure/claim` twice. Confirm exactly one Potion is
   granted and a different character cannot claim that reward.
4. Complete a second run and confirm it does not grant another first-clear item.

For production-model PostgreSQL checks, explicitly set `PF2_TEST_POSTGRES_DSN`
to an approved test connection and run:

```powershell
..\evenv\Scripts\python.exe tests/integration/recovery_cases.py
```

The standalone suite builds and removes a disposable schema without running
migrations. It exercises simultaneous completion of one run, overlapping
first clears, overlapping recovery claims, actual inventory-write and
claim-marker rollback, and two characters sharing one account. It also
covers gym badge recovery and runs in the PostgreSQL CI job. Migration
rehearsal instructions are in [Gym badge recovery](gym-recovery.md).

For rollback, first resolve pending results and claim unpaid rewards, then
restore the previous code and reload through the approved deployment process.
Do not delete participation records or reverse migration 0040: the older
branch code also uses those tables, and the records prevent duplicate rewards.
