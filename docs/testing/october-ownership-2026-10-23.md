# October ownership foundation verification (#722)

Local candidate based on `43d821e`, October 23, 2026. The accompanying
[machine-readable report](october-ownership-2026-10-23.json) pins Python sources,
commands, counts and log SHA-256 fingerprints. This is implementation/local test
evidence; no existing game deployment, hosted CI success or socket walkthrough is
claimed. The consent trading UI remains disabled pending #725.

## Behavior and criteria

| Requirement | Evidence |
| --- | --- |
| One owner, one valid destination for party and boxed assets | Real canonical party/box swap; ownership/placement/mirror audit after every scenario; PostgreSQL deferred constraints remain installed. |
| Fresh authority, source and destination state | Locked acting character IDs, owners/storage/trainers/Pokémon; SQL reads bypass identity/Attribute caches. Foreign acting character cannot prepare another owner's assets, approve, commit or cancel. Account ownership grants no additional authority. |
| Shared battle/Fusion/system reservations | Active/unlocked Fusion references, saved/runtime battle references and competing trade/market/Daycare/breeding claims reject before writes. Storage/release/Fusion and field `+use` reuse the same fresh reservation boundary. |
| Atomicity and retries | Both approvals required; immutable exact terms, terminal receipts and source UUIDs. Duplicate prepare/commit, retry after release, second destination failure and outer rollback preserve custody and do not repeat transfer. |
| Concurrent writers and capacity | Independent connections race duplicate commits, offers to different destinations, release/deposit/withdraw/cancel, battle admission and the last party slot. Full-party auto placement boxes safely; explicit-party failure rolls back; full-party swaps free both outgoing slots first. |
| Provenance and persistent state | Same owned UUID and original trainer/name, nickname, held item, HP/status/EXP/IV/EV fields; learned move, active move PP and PP boost rows retain identity and values. |
| Schema and operations | Approved fresh/upgrade/invalid-data rehearsals preserve existing progression and detect model drift. Versioned read-only audit reports custody/claim problems and pending expired offer identities; no owner guesses or automatic repairs. |

The battle-admission race exposed a real lock-order defect during development.
Character locks now precede storage locks; `NO KEY UPDATE` permits the foreign-key
key-share locks used by storage-first Attribute writers. The dedicated race passes
after the repair. The invalid-data migration rehearsal also caught a runner issue:
the executor must refresh its applied-migration state after installing a baseline.
The final three scenarios pass with the corrected runner.

## Final local checks

- Eleven affected real PostgreSQL suites: **248 passing cases**. The final
  23-case ownership run supersedes its initial 22-case development run. Other
  suites cover canonical placement, evolution, field medicine/berries/abilities,
  trade-held equivalents, ordinary doubles, production gyms, battle recovery and
  cloud gameplay.
- Approved `ownership_migrations.py`: fresh install, upgrade from `0046`, and
  deliberate invalid reservation before `0048` followed by inspected QA-row
  removal and a successful retry. Existing badges, inventory, ownership and
  recovery progression remain intact; no Pokémon model drift.
- `tools/run_mandatory_tests.py`: combined, repeat and battle-first processes,
  **4,908 passed / 4,014 skipped in each**. Callback tests enabled and ambient
  pytest options cleared. The new ownership subprocess is included with the
  explicit test DSN.
- Source held fixed across the gate: **1,043 Python files**; exact hashes in JSON.
- `git diff --check` passes. Existing test/import and Evennia deprecation warnings
  remain visible in logs; warning-free operational behavior is not claimed.

The private cluster uses only loopback and generated isolated schemas; test
connections reject any other schema. No live characters, inventory, Adventure
rooms, game migrations or existing services were changed.

## Remaining boundaries

This is the common transfer/reservation layer, not acceptance of #725–#728.
No money, prices, EXP or automatic trade evolution is granted. Current manual
trade-held evolution equivalents remain supported. Automatic placement inherits
the existing unbounded box policy, documented in the
[write contract](../operations/pokemon-transfers.md).

The subsequent #723 cohort must cover older party-placed permanent Fusion starters
and atomic form transitions before October's combined player readiness is claimed.
Foreign/missing Fusion references require inspection rather than invented ownership.
Plot-only assets and unrelated work are outside this change.
