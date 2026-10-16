# Gym badge recovery

Gym victories are recorded in `GymVictory` before attempting badge delivery.
The record belongs to a character, independently of their account's other
characters and of the temporary battle room. A UUID stored in the battle result
keeps retries and rebuilt sessions attached to the same victory.

`+gym claim` retries the caller's unclaimed badges. It works outside the gym,
after disconnect/reconnect, and without a healthy party. It accepts no target
character or victory ID. It never starts another battle or grants money or XP.

Badge delivery and `claimed_at` use one database transaction. A failed write
rolls both back while leaving the earlier victory record available for retry.
Claims lock the character and victory rows, and an already-owned badge counts
as fulfilled. Claimed records are retained so replaying a callback cannot reset
them. Do not delete these records to retry an award.

The award uses the badge ID captured at encounter start. Disabling or
reconfiguring the gym does not redirect an existing award to a different badge.
A missing badge or trainer record leaves the victory pending for staff repair.
Legacy battle metadata without a badge ID still uses the existing gym-profile
lookup; it cannot preserve a badge identity that was never saved.

If the victory record itself cannot be saved, battle cleanup stops before
deleting the room's battle state. Staff must restore database availability and
retry normal battle finalization. `+gym claim` can only process victories that
have reached the ledger; it cannot infer a win from a missing record.

## Deployment prerequisite

Migration `0043_gym_victory` must be applied through the approved deployment
procedure before loading this code into a running game. It depends on
`0042_merge_adventure_placement`, which joins Adventure participation with the
canonical placement and ownership integrity migrations from main. This
implementation has not applied migrations, restarted services, or deployed code.
This change cannot reconstruct older victories whose result evidence was
already marked handled and deleted by the previous code.

Offline checks compare the migration's model state with the production model.
SQLite checks create isolated tables directly for transaction testing. The
standalone PostgreSQL recovery suite also tests overlapping claims on separate
connections and observes an actual character-row lock wait. These checks do
not apply deployment migrations or replace a fresh-install/upgrade rehearsal.

## Automated validation

From the `fusion2` directory:

```powershell
..\evenv\Scripts\python.exe -m pytest tests/test_gym_leaders.py tests/test_gym_command.py tests/test_gym_battle_results.py tests/test_gym_rewards_orm.py tests/test_battle_rebuild.py tests/test_adventure_battle_results.py
```

Coverage includes a real badge write followed by failure, claim-marker failure,
rollback, character isolation, a fresh character instance after reconnect,
repeat claims/rematches, immutable victory metadata, missing badge/trainer
records, one failing claim alongside a successful claim, restored battle
identity, and preservation through battle-room cleanup.

With `PF2_TEST_POSTGRES_DSN` explicitly set to an approved test connection:

```powershell
..\evenv\Scripts\python.exe tests/integration/recovery_cases.py
```

This creates and drops only a randomly named `pf2_recovery_test_` schema.
Every ORM connection, including worker threads, is restricted to that schema.
It uses the real character, account, inventory, badge, Adventure, and victory
models. Coverage includes overlapping claims for one victory and different
rematches, simultaneous Adventure first clears and reward retries, delivery
and claim-marker rollback, and isolation between characters on one account.
The PostgreSQL CI job runs this suite automatically.

After approval to run migrations, the same explicit test connection supports:

```powershell
..\evenv\Scripts\python.exe tests/integration/recovery_migrations.py
```

The rehearsal applies the complete graph in separate disposable schemas for
a fresh install, an upgrade from Adventure migration 0040, and an upgrade from
main's placement migration 0041. It checks model state and preservation of
existing inventory, earned badges, canonical placement, and unpaid Adventure
rewards. It does not migrate the running game's tables.

## Pending live acceptance

Use a development game with migration 0043 applied, two ordinary characters on
one non-admin account, and a separate staff login. Use fresh characters that do
not already hold the test badge. Run each command separately and inspect its
response before continuing. Failure injection belongs only in a controlled
test environment; staff must remove every temporary hook after its check.

1. As character A, run `+gym list`, then `+gym check <gym>` and
   `+gym challenge <gym>`. Win normally. Confirm one badge, a claimed ledger
   record owned by A, and normal battle cleanup.
2. Run `+gym claim` twice. Expected: no unclaimed gym badges and no extra badge.
3. Rematch and win. Expected: the existing badge remains a single award and
   the new victory is marked claimed. Lose or concede another rematch;
   neither outcome should create a victory record.
4. On fresh character B, staff temporarily makes badge delivery raise after
   its database write. Win. Expected: the battle cleans up, no badge remains
   from the failed transaction, and B has one unclaimed victory. The response
   directs B to `+gym claim`. Remove the failure hook immediately.
5. Switch to A and run `+gym claim`. Expected: A cannot claim B's badge.
   Reconnect as B, then run `+gym claim` twice. Expected: one badge, one claimed
   record, and no second award.
6. Separately inject failure while writing the claim marker. Expected: the
   badge addition also rolls back and the victory remains pending. Remove the
   hook, then retry with `+gym claim` and confirm exactly one award.
7. Interrupt a confirmed result before delivery, rebuild the battle, and
   retry finalization. Expected: the same victory UUID is reused and the
   original win is retained even if the winner object is unavailable.
8. Inject failure when saving the victory itself. Expected: finalization
   retains the battle state and does not clear the player's battle lock.
   Remove the hook, retry finalization with staff assistance, and verify the
   victory can be delivered without replaying the battle.
9. On PostgreSQL, issue overlapping claims for the same character, including
   separate wins awarding the same badge. Expected: one badge relation and
   correctly claimed receipts. Sequential commands and SQLite tests do not
   prove this locking behavior.

For a failure, remove hooks first, then record the command, response, character,
battle ID, victory UUID, and traceback. Preserve pending records and avoid
broad cleanup/reset commands. Any migration or service restart still requires
the repository's operational approval procedure.
