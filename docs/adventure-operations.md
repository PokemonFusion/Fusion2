# Adventure Mode Operations

Adventure Mode provides short authored expeditions launched from Adventure
Hall. The current playable mission is `alpha_meadow` (Alpha Meadow Survey).

## Player Flow

The player must be in Adventure Hall and have a battle-ready party.

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

The first completed clear records the chosen route and encounter result and
grants one Potion. Later clears remain available for alternate outcomes,
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
