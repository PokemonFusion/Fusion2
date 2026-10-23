# Adventure PR: manual acceptance checklist

These steps test the Adventure changes against a running game. Run every in-game command separately and inspect the response before continuing. Do not paste a whole playthrough while a battle is waiting for input.

Record the exact code commit and its required migration leaf loaded by the test
game before beginning. This checklist does not perform deployment, migrations,
or reloads. The original Adventure participation prerequisite is
`0040_adventure_participation`; later code may require more migrations. Use the
chosen release's complete schema requirements rather than this original
checklist as a release plan. See the dated [branch validation record](../alpha-reliability-validation.md),
[gym recovery](../gym-recovery.md) and [September closeout](september-closeout-2026-10-23.md).

## 1. Prepare the test environment

Use a development/test game with **one regular, non-admin account containing two disposable characters: AdvTestA and AdvTestB**. Both characters must also have ordinary player permissions, completed character setup, a Trainer record, and a healthy, usable Pokemon party. This deliberately checks that two characters on the same account do not share Adventure rewards.

Keep a **separate staff account** connected in a second client window. That staff login needs `@py` permission for setup, diagnostics, and temporary failure hooks. **Every `@py` and `+adventureadmin` command below runs in the staff window; all gameplay commands run in the regular-player window.** Do not promote either test character to admin.

A second non-admin account is optional additional coverage for cross-account isolation; it is not needed for the initial A/B test.

Use the regular test account's character menu. If creating them there, the repository commands are `charcreate AdvTestA` / `charcreate AdvTestB`, `goic <name>` to enter, and `goooc` to return to the account menu. Complete any chargen/starter prompts before continuing. Character slots and permissions still apply.

Neither character should have completed Alpha Meadow before. In the STAFF window, select AdvTestA with this command (repeat with the name changed to AdvTestB when checking B):

```text
@py from evennia import search_object; matches = search_object("AdvTestA"); assert len(matches) == 1, "Expected exactly one matching test character"; me.ndb.adventure_test_target = matches[0]; me.msg("Selected test target: " + matches[0].key)
```

Then check the selected character from the STAFF window:

```text
@py from pokemon.models.adventures import AdventureSession as S; me.msg(list(S.objects.filter(leader=me.ndb.adventure_test_target, template_key="alpha_meadow", state="completed").values_list("id", flat=True)))
```

**Expected:** `[]`. If there are IDs, use a different fresh character and adjust the exact-name guards in the failure hooks. Do not delete completion records to reset eligibility.

Have a healthy party capable of defeating level-5 Rattata/Pidgey. Before capture tests, obtain Poke Balls through the normal test setup. Heal at an existing Pokemon Center between runs as needed. Avoid using Potions during the reward-count checks.

## 2. Confirm the running game has the changes

Enter this in the STAFF window on the test game:

```text
@py from django.db import connection; from django.db.migrations.recorder import MigrationRecorder; from pokemon.adventures.commands import CmdAdventure; me.msg({"retry_loaded": hasattr(CmdAdventure, "_retry"), "claim_loaded": hasattr(CmdAdventure, "_claim"), "migration_0040_applied": ("pokemon", "0040_adventure_participation") in MigrationRecorder(connection).applied_migrations()})
```

**Expected:** all three values are `True`.

If any value is false, STOP. The deployment/migration/reload prerequisite has not been met. Do not interpret later failures as acceptance-test results for the fixed code.

Run these as a staff character:

```text
+adventureadmin/validate all
+adventureadmin/preview alpha_meadow
```

**Expected:** `alpha_meadow: OK` and the Alpha Meadow information. Validation checks templates; it does not prove room provisioning or database health.

Travel to the EXISTING Adventure Hall through the normal map. Do not rerun `batchcommands adventure_hall` against a database where it has already been run: it creates duplicate rooms and exits. If no instance is available, inspect it with staff rather than running broad cleanup/reset commands.

## 3. AdvTestA: record the baseline

As **AdvTestA**, in Adventure Hall:

```text
+inventory
+adventure/claim
+adventure/retry
```

Record the number of Potions as **A0**; no Potion entry means zero.

**Expected:** no unclaimed rewards and no encounter results waiting to be retried. These commands should not create items or start a battle.

## 4. AdvTestA: normal wild-route completion

```text
+adventure/list
+adventure/info alpha_meadow
+adventure/start alpha_meadow
+adventure/look
+adventure/objectives
north
+adventure/choose wild
```

**Expected:** start at Meadow Entrance, move to Tall Grass Path, and enter a battle against a level-5 Rattata.

Win normally. `+attack /menu` lets you choose from the Pokemon's actual moves; do not assume it knows Tackle. Wait for each turn/result before choosing another action. Stop moving until the battle has ended.

```text
+adventure/objectives
```

**Expected:** `[x] Choose a route and resolve its encounter.`

Now finish the survey:

```text
north
+adventure/search
south
south
+adventure/objectives
+inventory
```

**Expected:** reach Old Tree, find fresh tracks, return to Meadow Entrance, and see all four objectives checked. Completion grants `First-clear reward: Potion x1.` Inventory should contain **A0 + 1** Potions.

```text
+adventure/leave
+adventure/look
+adventure/claim
+adventure/claim
+inventory
```

**Expected:** return to Adventure Hall; `+adventure/look` says you are not in an adventure. Both claims should grant nothing. Potion total remains **A0 + 1**.

## 5. AdvTestA: replay via trainer route and concede

Heal first if needed, then return to Adventure Hall:

```text
+adventure/start alpha_meadow
north
+adventure/choose trainer
```

**Expected:** Surveyor Mina with a level-5 Pidgey. When the battle is waiting for your action:

```text
+concede yes
+adventure/objectives
```

**Expected:** battle ends, the encounter resolves as `loss`, and the encounter objective is checked. Concession is expected to let the survey continue.

Finish the same `north`, `+adventure/search`, `south`, `south`, `+adventure/leave` sequence. Run `+adventure/claim` and `+inventory`.

**Expected:** no second first-clear reward; Potion count is still **A0 + 1**.

## 6. AdvTestA: reconnect while an Adventure is active

Start another run and go north to Tall Grass Path, but do not choose a route yet. Disconnect the game client, reconnect, and enter **AdvTestA** again if the account menu appears.

```text
+adventure/look
+adventure/objectives
```

**Expected:** still in the same run at Tall Grass Path, with its original objective state. Reconnect should not start a second run or grant a reward. Keep this run for the next test.

## 7. AdvTestA: force one character's result saves to fail

This is a deliberate, temporary test hook in the running Python process. It targets AdvTestA only and delegates other characters' results to the original function. Use it on the test game. Do not reload/restart the server while a hook is installed. The staff window owns the hook and its cleanup. Remove it with the cleanup command below before the player reconnects or switches characters.

Leave **AdvTestA** at Tall Grass Path in the PLAYER window. Install the hook once from the STAFF window; this command selects AdvTestA explicitly:

<!-- result-hook -->
```text
@py from evennia import search_object; matches = search_object("AdvTestA"); assert len(matches) == 1 and matches[0].key == "AdvTestA", "Expected exactly one AdvTestA character"; target = matches[0]; me.ndb.adventure_test_target = target; assert not getattr(me.ndb, "adventure_test_patches", None), "Clean up the existing test hook first"; from pokemon.adventures import progress; from unittest.mock import patch; original = progress.record_encounter_result; target_id = target.pk; hook = patch.object(progress, "record_encounter_result", lambda session, player, result, original=original, target_id=target_id: (_ for _ in ()).throw(RuntimeError("Adventure acceptance test: result save")) if player.pk == target_id else original(session, player, result)); me.ndb.adventure_test_patches = [hook]; hook.start(); me.msg("Result-save failure enabled for AdvTestA. Run cleanup after the failure checks.")
```

Choose `+adventure/choose trainer` and **win normally** using the attack menu. Wait until the battle ends.

**Expected:** a pending-result message mentioning `+adventure/retry`. The deliberate `Adventure acceptance test: result save` error in server logs is expected during this step.

```text
+adventure/objectives
+adventure/choose trainer
+adventure/retry
```

In the STAFF window, inspect AdvTestA's saved receipt:

```text
@py me.msg(dict(getattr(me.ndb.adventure_test_target.db, "pending_adventure_results", None) or {}))
```

**Expected:** encounter objective remains unchecked; choosing again is blocked without starting a new battle; retry still reports pending while the hook is active. The diagnostic shows one saved session ID mapped to `win`.

**Cleanup: run this now in the SAME STAFF window that installed the hook.** It restores all hooks installed by this checklist through that staff character. It is also the cleanup command to run if any test goes unexpectedly.

<!-- cleanup-hook -->
```text
@py [hook.stop() for hook in reversed(getattr(me.ndb, "adventure_test_patches", None) or [])]; me.ndb.adventure_test_patches = []; me.msg("Adventure test hooks removed.")
```

After the cleanup message, disconnect/reconnect and enter **AdvTestA** again. Then:

```text
+adventure/retry
+adventure/objectives
+adventure/retry
```

In the STAFF window, inspect AdvTestA's receipt again:

```text
@py me.msg(dict(getattr(me.ndb.adventure_test_target.db, "pending_adventure_results", None) or {}))
```

**Expected:** the original `win` is applied; the encounter objective becomes checked; the saved-result dictionary is `{}`; the second retry says nothing is waiting. No replacement battle should start.

Finish the survey and leave. Potion count remains **A0 + 1**, since this character already earned its first-clear reward.

## 8. AdvTestB: force reward delivery to fail after the item write

Switch to fresh **AdvTestB**, heal/setup its party, and go to Adventure Hall. Run `+inventory` and record Potions as **B0**.

Start Alpha Meadow, go north, choose `trainer`, and win or use `+concede yes`. Confirm the encounter objective is checked. Remain at Tall Grass Path.

Install this hook once from the STAFF window, while **AdvTestB** remains at Tall Grass Path in the PLAYER window, BEFORE returning to the entrance to complete the survey. It targets only AdvTestB's Potion additions. It calls the normal inventory write and then raises an error, specifically testing rollback of a partially delivered reward.

<!-- reward-hook -->
```text
@py from evennia import search_object; matches = search_object("AdvTestB"); assert len(matches) == 1 and matches[0].key == "AdvTestB", "Expected exactly one AdvTestB character"; target = matches[0]; me.ndb.adventure_test_target = target; assert not getattr(me.ndb, "adventure_test_patches", None), "Clean up the existing test hook first"; from pokemon.models.trainer import Trainer; from unittest.mock import patch; original = Trainer.add_item; target_id = target.pk; hook = patch.object(Trainer, "add_item", lambda trainer, item_name, amount=1, original=original, target_id=target_id: (original(trainer, item_name, amount), (_ for _ in ()).throw(RuntimeError("Adventure acceptance test: reward delivery")))[0] if trainer.user_id == target_id and item_name.lower() == "potion" else original(trainer, item_name, amount)); me.ndb.adventure_test_patches = [hook]; hook.start(); me.msg("Potion delivery failure enabled for AdvTestB. Run cleanup after the failure checks.")
```

Finish the survey:

```text
north
+adventure/search
south
south
+adventure/objectives
+inventory
+adventure/claim
+inventory
```

**Expected:** Adventure is completed with all objectives checked, but its reward remains unclaimed and the response mentions `+adventure/claim`. Inventory stays at **B0**, including after the failed claim. It must not increase despite the injected failure occurring AFTER the item write.

Run the cleanup command from step 7 **in the STAFF window now**. Then run `+adventure/leave` as AdvTestB in the PLAYER window.

## 9. Confirm isolation, then claim after leaving and reconnecting

Leave AdvTestB out of the Adventure. Switch to **AdvTestA**:

```text
+adventure/claim
+inventory
```

**Expected:** AdvTestA receives nothing and remains at **A0 + 1**. AdvTestB's unpaid reward must not be given to AdvTestA.

Switch back to **AdvTestB**, disconnect the client, reconnect, and enter AdvTestB again. You should be outside the Adventure. Then:

```text
+adventure/claim
+inventory
+adventure/claim
+inventory
```

**Expected:** first claim grants one Potion; count becomes **B0 + 1**. Second claim grants nothing; count remains **B0 + 1**. Complete another run as AdvTestB if you want a second replay check; it must not add another first-clear Potion.

## 10. Check the stored records

In the STAFF window, use the selection command in step 1 to select AdvTestA, then run these read-only diagnostics. Repeat after selecting AdvTestB:

```text
@py from pokemon.models.adventures import AdventureSession as S; me.msg(list(S.objects.filter(leader=me.ndb.adventure_test_target, template_key="alpha_meadow").order_by("-id").values("id", "state", "metadata", "objective_progress")[:3]))
```

```text
@py from pokemon.models.adventures import AdventureParticipation as P; me.msg(list(P.objects.filter(player=me.ndb.adventure_test_target, session__template_key="alpha_meadow").order_by("id").values("session_id", "route_key", "outcome_key", "encounter_result", "completed_at", "reward_item", "reward_amount", "reward_claimed_at")))
```

**Expected:** completed sessions remain completed after leaving; the relevant encounter results are `win` or `loss` as tested; the recovered win remains `win`. Each character has exactly one first-clear Potion grant/claim, not one per replay. Successful claimed records have a non-null `reward_claimed_at`. Replays can have a completion timestamp but no reward item.

## 11. Cover capture and fleeing

These are separate short wild-route replays on a character that has already cleared the Adventure. Heal and return to Adventure Hall between runs.

- **Capture:** start, go north, choose `wild`, weaken Rattata if necessary, and use `+battle/item Poke Ball` when prompted for an action. Have Poke Balls available first. A failed throw is not a failed test; repeat until a capture succeeds. Confirm the caught Pokemon is actually kept through the normal capture flow, the encounter objective is checked, and the stored result is `capture`.
- **Flee:** start another run, go north, choose `wild`, and use `+flee` when prompted. Flee attempts can fail; wait for a successful escape. Confirm the encounter objective is checked and the stored result is `flee`.

Finish and leave each survey normally. Neither replay grants an extra first-clear Potion. Use the stored-record commands in step 10 to verify the outcomes.

## 11a. Survey without an encounter

On a character that already earned its first-clear Potion, return to Adventure
Hall and run each command separately:

```text
+adventure/start alpha_meadow
north
north
+adventure/search
south
south
+adventure/objectives
+adventure/leave
+adventure/claim
+inventory
```

**Expected:** the survey completes with reach/search/return checked. The
encounter is visibly optional and remains unchecked; no battle starts and no
encounter outcome is invented. The character returns to Adventure Hall and
receives no repeat first-clear Potion. Choosing an encounter in other runs
still requires its result to resolve before completion. This route requires
the October 23 non-combat repair; older loaded builds are not proof of it.

## 12. Finish and report

Run the cleanup command from step 7 once in the STAFF window, even if you believe the hooks were already removed. Finish/leave their Adventures so the instance room is available again. Do not delete reward history or manually clear pending-result data to make a failed test pass.

Record these results:

| Check | Pass/fail and notes |
|---|---|
| Running code and migration prerequisites | |
| Wild victory and first-clear Potion | |
| Trainer concession continues the survey | |
| Replay does not grant another Potion | |
| Active Adventure survives reconnect | |
| Failed result retained, replay blocked, original win recovered | |
| Failed reward rolls back the item and remains claimable | |
| Reward can be claimed after leaving/reconnect | |
| Other character cannot claim the unpaid reward | |
| Repeated claims do not duplicate the item | |
| Capture stored as capture and caught Pokemon retained | |
| Successful flee stored as flee | |
| All staff-installed test hooks removed | |

For a failure, save the exact command, response, character, session ID, and server traceback/time if available. Run hook cleanup first, then stop at that step and share the output. Do not run broad Adventure cleanup, reset records, or rerun the room batch as a workaround.

This checklist verifies live single-player and sequential two-character behavior. PostgreSQL simultaneous-claim behavior is covered separately by `tests/integration/recovery_cases.py`; sequential manual claims and SQLite rollback tests do not prove that locking behavior.
