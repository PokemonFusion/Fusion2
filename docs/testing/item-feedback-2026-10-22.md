# Item feedback repair (#814)

**Fixed:** full and moves party sheets now show saved boosted PP capacity, and
evolution notices use the original species/name or nickname before the destination.
The [JSON receipt](item-feedback-2026-10-22.json) retains exact production commands,
SQL before/after, failures/rollback, test results and 1,001 frozen Python hashes.

## Behavior and scope

After buying PP Up and PP Max through the real finite store menu, the ordinary
player uses `+use PP Up=3` → `+use Water Gun` and `+use PP Max=3` → `+use 1`.
Both `+party 3` and `+party/moves 3` show **Watergun (30/30 PP)** and
**Tackle (56/56 PP)**, including after closing SQL connections, flushing model
identity caches and binding a fresh player transport. The target party and move
slots deliberately have gaps. Displaying the sheets changes no saved rows.

The display calls the existing owned `get_max_pp` helper used by field PP rules.
It preserves spent/zero PP, handles null-current presentation without saving a
refill, and reads an existing noncanonical raw bonus without silently migrating
it. Non-model adapters keep their runtime `pp_bonuses` fallback. No PP policy,
inventory debit, move-slot writer, genetics or progression code changed.

After buying Fire Stone, `+evolve <full-Vulpix-id> Fire Stone` now reports
**Vulpix evolved into Ninetales!** A nicknamed target reports **Ember Fox evolved
into Ninetales!** and retains that nickname. The command captures its original
display name before the service publishes refreshed state; the existing robust
`transaction.on_commit` callback and Alcremie appearance suffix remain in place.
Successful outer commit notifies once; outer rollback or a real post-save failure
produces no evolution success. Fresh-SQL retry/replay never double-debits or
repeats success. The evolution service itself is unchanged.

## Validation

Nine new guarded PostgreSQL regressions cover acquisition, both sheet modes,
gapped slots, reduced/zero/null PP, compatible saved raw bonuses, original-name
and nickname evolution, fresh SQL/transport, post-save failure, outer commit,
outer rollback and replay. Related existing suites preserve evolution variants,
Alcremie appearance, coin behavior, native names and other sheet consumers.

| Guarded PostgreSQL suite | Passed |
| --- | ---: |
| item_feedback | 9 |
| pp_capacity | 37 |
| evolution | 28 |
| gimmighoul_coin | 12 |
| alcremie | 76 |
| name_resolution | 8 |
| ui | 14 |
| item_availability | 32 |
| **Total** | **216** |

Focused display/command/PP/evolution/party/battle-PP tests: **183 passed**.
Mandatory fresh-process combined, repeat and battle-first orders:
**4,775 passed / 4,014 skipped each**. All 1,001 Python sources stayed
frozen across qualification. Existing model-reregistration warnings are retained;
no failed test run was accepted or hidden.

These are automated production-command/menu/model checks with captured client
transport. The fresh transport is **not an actual socket reconnect or live login**.
The earlier [released-build walkthrough](item-live-2026-10-22.md) remains immutable
evidence of the defects on its pinned build, separate from this later repair.
No new PF2-Dev deployment, migration, reload, staff setup or human-data change was
performed. Hosted CI, main merge and deployed acceptance are not claimed.

All disposable schemas were removed, the task database has no public tables,
and the private PostgreSQL cluster is stopped. No plot content or unrelated work
is included. The wider store-hint/onboarding work remains in #731; the deferred
Mega/Z/berry systems remain their separate implementation issues.
