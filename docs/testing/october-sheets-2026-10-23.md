# October sheet/profile implementation verification (#733)

October 23, 2026 candidate based on `37f1b04`. [JSON evidence](october-sheets-2026-10-23.json)
records source/log fingerprints and normal commands/request dispatch. **The live
browser/game comparison remains pending; #733 stays open.** Actual typed Player
characters/accounts, Django views/templates and saved rows are used. Game output
is captured; no browser/socket session or deployment is claimed.

## Repairs and evidence

| Area | Evidence |
| --- | --- |
| Profile privacy | A pre-fix PostgreSQL probe confirmed nested Saver fields became public after reload. Persisted private flags now survive; ordinary outsiders and colliding AccountDB/ObjectDB IDs cannot see them. The real User lookup works through +profile. |
| Account scope | Same-account alts are selectable; explicit foreign/removed IDs yield no editable character and cannot mutate the first own character. Anonymous views redirect. Saved roster authority is queried fresh. Profile HTML is escaped. |
| Custody | Slot 3 stays slot 3. Canonical boxes exclude Fusion/Daycare sources; trade/market claims retain labelled current locations. Actual Daycare deposit/retrieve and reviewed consent trade update the correct owner. |
| Read-only state | Actual incomplete User fixtures create no trainer, storage, boxes or Pokemon under hub, sheet, inventory and party reads. Missing placement and conflicting mirrors produce warnings/refusals without repairs. |
| Resources | Fresh saved wallet, badges, item quantities, traits, HP/status and moves appear under the correct owner. Real +use Potion=3 changes saved HP and inventory, then both view paths see the new state after cache discard. |
| Fusion compatibility | Active forms remain reserved and the existing battle-backed game sheet remains authoritative. Ordinary reload clears stale active-form annotations; #721/#814 stat/PP regressions remain in the full gate. |

## Final automated checks

- **225 cases pass across 15 PostgreSQL suites**, including
  **14 dedicated sheet/profile cases** plus communications, ownership, onboarding,
  trade, market, Daycare, breeding, gyms and existing player/UI routes.
- **59 focused checks pass**.
- One callback-enabled full suite: **4922 passed / 4014 skipped**.
- **1093 Python files** remain fixed across final checks; staged/committed
  Git-filtered source fingerprints are verified before publishing.
- No schema change or new migration rehearsal in this feature.

The [visibility/field contract](../operations/character-sheet-reads.md) identifies
overlapping fields and fields absent from the web hub. The incomplete fixture is
separately prepared after normal construction; saved-row update and damaged-state
fixtures are staff prerequisites, not ordinary gameplay claims. Initial request
fixtures lacked session context and are corrected. Existing Windows logging/model
reload diagnostics remain. No unrelated work or plot items are included.
