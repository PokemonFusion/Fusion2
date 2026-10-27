# October consent trading verification (#725)

October 23, 2026 candidate based on `9ca0f11`. The [JSON evidence](october-trading-2026-10-23.json)
contains exact command replies, source and log fingerprints. This is local
automated acceptance with actual PostgreSQL models, accounts, User typeclasses
and public command classes. Outbound transport is captured; no live socket,
deployed-server or hosted-CI acceptance is claimed.

## Player and transaction evidence

| Criterion | Evidence |
| --- | --- |
| Explicit current consent | Recipient must inspect the sealed offer before accepting or countering. Same-account alts and the old offer's review cannot supply new consent. |
| Gifts and atomic swaps | Actual `+trade offer`, inspect, counter, accept, decline and cancel paths cover gapped party slots and boxed UUIDs. A fault after the first destination write rolls back both sides and approvals. |
| Durable outcome | Pending-first lists and sealed receipts survive Attribute cache discard/reconnect. Completed acceptance replays even after the asset is released, without resurrection. |
| Exact asset state | Immutable summaries and fingerprints bind ownership, genetics/training, held item, progression, moves and PP. Changed terms require a new offer. Transfers retain the same UUID and saved state. |
| Eligibility and authority | Real character identity, fresh ownership, battles, Fusion references, all shared reservation types and destination capacity are checked under the shared lock boundary. Raw accounts and facades with coincident integer IDs are rejected. |
| Contention | Independent connections race accepts, accept/cancel and move editing versus acceptance. One legal result is retained, with no duplicate transfer. |
| Expiry and cancellation | Fifteen-minute expiry blocks acceptance; either participant can cancel an expired offer to release claims. Decline/cancel/counter retains reason and closing character. |
| Retained move menus | Learning and moveset menus opened before reservation/transfer cannot inspect or edit a foreign/reserved source. Move-write rollback publishes no false notice or continuation. |

The actual saved-moveset command called a missing model method. `+moves/use` now
uses the existing saved-set service at a Pokemon Center, preserving its PP restore
behavior without granting field PP refill or HP healing. Real command tests cover
Center success, field rejection and reservation rejection. Player guidance and
the [operator contract](../operations/consent-trading.md) describe these limits.

## Final checks

- **236 cases pass across 11 PostgreSQL suites**, including 17
  dedicated trading cases, ownership/Fusion, field medicine/berries/abilities/PP,
  ordinary doubles and UI regressions.
- **19 focused tests pass** for trade safety, move learning/menus, saved sets and guide contracts.
- Three fresh mandatory suite orders: **4911, 4911, 4911 passed**, with **4,014 skipped** in
  each. Callback tests enabled; ambient pytest options cleared.
- Approved fresh-install, upgrade and guarded-invalid-data migration rehearsals pass.
  This cohort adds no migration.
- **1050 Python files** held fixed across the final checks; the Git-filtered
  staged-blob digest is added before committing. `git diff --check` passes.

Initial checks identified two outdated fixtures: a cloud-flow assertion still
expected disabled trading, and a move-learning stub replaced `pokemon.services`
with a non-package. Both fixtures now express the shipped behavior and the full
gate is rerun. Existing model reload/deprecation and Windows logging warnings
remain diagnostic limits; no warning-free operational claim is made.

Trades grant no fees, currency, EXP, healing or automatic evolution. Existing
manual trade-held evolution equivalents remain supported; other trade triggers
remain deferred. Plot-only assets, unrelated features and game service operations
are outside this change.
