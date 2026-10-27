# Smoke Ball held escape — issue #759

Smoke Ball now resolves as a reusable held escape item. The existing `+hold`
interface equips it, and the living acting holder escapes eligible wild battles
through ordinary `+flee` / `+battle/flee`. The [item contract](../smoke-ball.md)
defines the selected PF2 policy and acquisition boundary.

The existing-item gate in #747 was satisfied before this addition; #752 and
#757 were freshly confirmed closed. This adds one supplemental definition,
with full normalized name lookup, description, Held Items category and the
existing CSV's 4000 reference price. It leaves the competitive ITEMDEX and the
historical #757 matrix unchanged. Shops/rewards may deliberately offer it using
existing configuration; this work does not grant inventory or stock live shops.

## Escape and capture behavior

The normal run-action consumer uses `EffectContext.item`. Smoke Ball bypasses
the flee route's Arena Trap, Shadow Tag and Magnet Pull restrictions. Klutz,
Magic Room, Embargo and explicit item suppression disable that guarantee.
Suppressed Klutz restores eligibility. Bag, benched, allied, foreign and opposing
copies do not supply the acting Pokemon's effect. Removing the item disables it.
Invalid/fainted actors are rejected and a completed result is not overwritten.

Trainer/NPC and PvP encounters remain restricted. Server-authored wild encounters
can set `battle.flee_allowed=False`; the existing checkpoint stores that policy,
and repeated session rebuilds retain it. Old snapshots default to the normal
wild flee policy. Explicit item/ability suppression flags also survive snapshots.
No migration, player policy override, new trap mechanic or universal escape route
is introduced. Existing Run Away and speed/formula escape retain their behavior.

Capture routing now requires canonical `isPokeball` metadata in commands,
current/legacy queues, restored declarations and final dispatch. A suffix is
insufficient. `+item Smoke Ball` directs the player to equip it and use `+flee`,
without queuing or debiting anything. A restored legacy item declaration cannot
capture or consume it. Real capture balls retain their route and debit behavior.

## Ordinary command/model walkthrough

The new suite runs three complete walkthroughs against real production models
and battle sessions, one for each trapping ability. Controlled setup creates
disposable ordinary characters, inventory and encounters separately. Session
transport and character lookup are adapted; commands, inventory, queues, engine
effects, checkpoint reconstruction and database writes are real.

```text
+inventory
+itemdex Smoke Ball
+hold 1=Smoke Ball
+party 1
[save, discard live references and rebuild the session checkpoint]
+flee
+hold 1=
```

Each flow confirms successful escape, normal session cleanup, a reusable held
copy after SQL reload and its return through normal removal. The spare bag copy,
capture balls, owner/identity, HP, EXP, moves/PP, placements and unrelated model
state remain unchanged. No capture receipt or additional owned Pokemon appears.

Other independently reported cases cover all four suppression mechanisms,
explicit removal, suppressed Klutz, bag/bench copies, trainer/PvP/no-flee after
rebuild, rejected item commands, restored legacy item actions and a real
`+item Master Ball` capture with one debit and correct owned placement. Unit
coverage adds foreign/fainted actors, other participants, canonical/partial name
classification and completed-battle retries.

## Validation

The [JSON report](smoke-ball-2026-10-21.json) retains exact commands, source and log
hashes, walkthrough outputs, final counts, preliminary diagnoses and cleanup.
The new [production-model suite](../../tests/integration/smoke_ball_cases.py) is
wired into lifecycle CI.

| Check | Passing result |
| --- | --- |
| PostgreSQL adventure lifecycle | 9 cases |
| PostgreSQL battle recovery | 36 cases |
| PostgreSQL capture ether | 21 cases |
| PostgreSQL capture pp item | 16 cases |
| PostgreSQL evolution | 28 cases |
| PostgreSQL player doubles | 10 cases |
| PostgreSQL remaining item | 8 cases |
| PostgreSQL smoke ball | 17 cases |
| Total PostgreSQL | 145 cases |
| Focused pytest | 157 tests |
| Mandatory combined, repeat and battle-first | 4,465 passed / 4,014 skipped in each process |

All checks passed. All 954 frozen Python source hashes stayed unchanged during the final gate. All isolated schemas were removed and the private test cluster stopped. Skipped tests are outside the enabled gate scope; existing warnings are retained.

The initial integration fixtures incorrectly expected a completed session to
retain its live engine, changed only runtime abilities before a model-backed
restore, assumed an incorrect removal message, and checked capture receipts
across other test owners. Those fixtures were corrected against the actual
lifecycle/model behavior. Three regression scripts initially received the
wrapper's filename as an unintended unittest selector; the local wrapper now
resets argv. These preliminary failures did not justify changing gameplay rules.
The final reruns are the qualifying evidence. An initial focused selection also
named a nonexistent test file; discovery was corrected before tests ran.

The local wrapper redirects only battle log destinations to task-specific paths;
the preliminary Windows error concerned rollover of a log open elsewhere. No
existing process or service was stopped. This is local automated ordinary-command
and model acceptance with captured transport, separate from a live player login,
hosted CI completion, main merge or deployment. The private PostgreSQL fixture
uses an explicit loopback DSN and isolated schemas, never the game database.
No migration runner, service restart, plot-only item or unrelated work is included.
