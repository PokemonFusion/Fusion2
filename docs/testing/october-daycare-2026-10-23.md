# October Daycare verification (#727)

October 23, 2026 candidate based on `5ca3511`. [JSON evidence](october-daycare-2026-10-23.json)
contains exact ordinary commands, assertions and source/log fingerprints. These
are local automated checks with actual User/Account models and Player permission,
using only task-owned PostgreSQL schemas. Outbound transport is captured; no live
socket, deployment or hosted-CI success is claimed.

## Acceptance evidence

| Criterion | Evidence |
| --- | --- |
| Normal custody route | Actual `+daycare deposit`, status, reconnect/cache discard and retrieve preserve the exact owned UUID and all saved genetics, progression, held/HP/status/move/PP state. |
| Canonical reservation | A deposited Pokemon retains its trainer and one `daycare` placement, with no party/box mirrors and an exclusive entry-bound claim. Battle roster helpers exclude it; storage/release/trade/market and other claims cannot take it. |
| Atomic fees and capacity | Two places, one 100-money fee per stay, free retrieval and no cooldown. Foreign/same-account sources, eggs, battles, Fusion references, other claims, insufficient funds and full capacity fail before a fee. |
| Replay and full party | Duplicate UUID deposit/retrieval and independent connection retries charge once. Retrieval prefers the previous party slot, then another free slot, then a box; later release does not turn replay into resurrection. |
| Faults and contention | Independent connections race same deposit/retrieve, three deposits against two places, and retrieval against trade/listing creation. Faults after real fee or retrieval destination writes roll back custody, claim, receipt and money together. |
| Staff inspection/recovery | Read-only `audit_pokemon_daycare --entry ID`, current placement/transfer audits and the owning character's idempotent retrieval route expose exact records without inventing ownership or deleting receipts. |
| Schema and rollout | Versioned placement/ownership audits preserve historical v1 migration behavior. Deferred checks reject orphan Daycare placements, missing active claims and closed entries retaining custody. |

## Final checks

- **246 cases pass across 13 PostgreSQL suites**, including
  **11 dedicated Daycare cases**, canonical placement, ownership/Fusion, trades,
  marketplace, field item routes, ordinary doubles and UI.
- **30 focused checks pass**, including command registration with both
  alpha-gate settings, guidance and existing shop/trade/pilot safety contracts.
- One fresh callback-enabled full combined suite: **4915 passed / 4014
  skipped**. Final integrated October battle work retains the three-order gate.
- Five approved isolated migration rehearsals pass: fresh install, upgrade,
  invalid reservation, invalid marketplace and invalid Daycare rollout/rollback.
  Invalid entries block without partial checks or guessed repairs; model drift is empty.
- **1065 Python sources** remain fixed across the checks, with a staged
  Git-filtered blob fingerprint added before commit. `git diff --check` passes.

See [Daycare rules](../operations/daycare.md) for costs, overflow, expiry-free
custody, cooldown and recovery behavior. No passive EXP, HP/PP restoration,
friendship, evolution, breeding production or plot-only content is added. #728
owns eggs/inheritance and remains separate. Preparatory-copy breeding work is not
part of this candidate or its acceptance evidence.

Existing model-reload/deprecation and Windows logging diagnostics remain. No
unrelated service, logging, live character or Adventure-room changes are included.
