# Durable Oran growing and Razz snack acceptance (#809–#812)

Implemented one private Oran bed and the independent PF2 Razz HP snack through
ordinary `+berry` commands. The [JSON receipt](berry-player-routes-2026-10-22.json)
retains exact command/output/SQL observations, timestamps/cycles, all test results,
diagnoses and 1,009 frozen Python source hashes. See the [player guide](../berry-nursery.md).

## Accepted bounded behavior

`+store` → Buy → `Oran Berry 1` costs exactly 100 and reduces five-copy stock by
one. `+inventory` observes the real bag. `+berry plant Oran Berry` spends that
seed, with a server-created immutable cycle UUID and UTC ready time 14,400 seconds
later. Four 3,600-second stages each accept one free watering. All 16 watering
masks yield exactly 1–5 Oran Berries. Status and readiness derive from persisted
SQL timestamps after connection teardown; ready crops have no decay.

The reviewed recipe is tested through a real `nursery` Exit command and saved
`move_to` destination, ordinary finite shop menu, planting/watering/harvest and
`+use Oran Berry=3`. Movement transport disables ancillary move hooks in this
isolated harness. Competing installers create one source; reinstalling preserves
sold stock. Disabled shops, funds, stock, wrong hubs and post-create faults do
not grant copies or duplicate content. No running-world source was installed.

Plant seed/cycle, stage bit, and harvest inventory/receipt/empty reset are atomic.
Lock order is room → character → storage → trainer → bed. The request captures
the current cycle before waiting for mutation locks; a stale harvest cannot clear
a new planting. Final-seed, same-stage watering, two-harvest, ready-water/harvest
and three-way water/harvest/replant contention use separate PostgreSQL connections.
Post-debit/post-credit/post-save and outer rollback restore all rows and suppress
success notices. Messages and inventory caches follow the outer commit.

`+store` → `Razz Berry 1` → `+inventory` → `+berry snack Razz Berry=3` spends one
bag copy for up to 10 useful HP, independently of a nursery or crop. Current
Fusion, clamped healing, fresh target/placement, no-effect/full/faint/egg/box,
foreign/ambiguous/inactive Fusion, battle and held-only guards retain existing
field rules. Partial debit, post-save, parent rollback, final-copy and overheal
contention are covered. Status, PP, held items and progression are unchanged.
Razz is a selected PF2 equivalent, with no implicit `+use`/battle/held alias.

| Slice | Accepted local support | Remaining limits |
| --- | --- | --- |
| Oran growing | Private persisted bed, UTC stages, water and one-time harvest | One species; deploy/migration/source installation and timed live acceptance separate |
| Oran feeding | Harvested copies reach existing `+use`; field/EV/held regressions pass | Existing effect rules remain authoritative |
| Razz snack | `+berry snack` useful 10-HP maximum, real bag debit, current party/Fusion | No `+use`, held or battle alias; no contest/lure/friendship |
| Nursery source | Explicit duplicate-safe recipe, finite Oran/Razz offers, ordinary local purchase | No automatically populated public source or refill |
| Other berries/agriculture | Existing field/held effects retained | No additional growing species, shared beds, cooking or contests |

## Qualification and schema review

| Disposable PostgreSQL suite | Passed |
| --- | ---: |
| berry_growing | 44 |
| field_berry | 26 |
| legacy_berry | 26 |
| field_food | 70 |
| field_item | 23 |
| field_training | 30 |
| shop_purchase | 8 |
| item_supply | 11 |
| item_availability | 32 |
| item_feedback | 9 |
| **Total** | **279** |

The new suite has **44 SQL cases**, including five exact stage boundaries and
16 watering masks. Focused commands, clock/corruption, field food, inventory,
help and import isolation: **58 passed**. Mandatory combined, repeat and
battle-first orders: **4,788 passed / 4,014 skipped each**. Python sources were
unchanged throughout accepted qualification.

The migration file `0046_berry_bed` matches the registered model in a read-only
migration-state review. The trainer OneToOne and bounded mask/yield constraints
are present. Tests create production tables directly in disposable schemas;
**no migration was run**. All test schemas were removed and the private fixture
database has no public tables; its empty local cluster is retained for the next
item chunks. No game database or human data was used.

Initial failures are retained in the JSON diagnosis: a stale Evennia location
guard was corrected to use the locked SQL row; the new source fixture needed
standard ContentType initialization; the mandatory command-set fixture needed
the new CmdBerry import stub. A focused test invocation also needed its filename
corrected and a fresh Windows temporary directory. Only the frozen successful
runs above count as acceptance.

## Release and remaining limits

These are automated production-command/SQL checks with captured transport and
controlled server time. They establish neither real socket reconnect nor four
hours of live timed growth. The previous [#782 released walkthrough](item-live-2026-10-22.md)
remains separate historical proof; it did not include this feature. No deployment,
live migration, reload, stock grant, human/session or Adventure change occurred.
Hosted CI and main merge are not claimed.

The checked-in optional nursery offers Oran/Razz at 100 with stock five each,
no refill/resale. It does not change #781's six-item Supply Corner or establish
permanent public availability. Applying the migration, deploying the commands,
installing public content and real timed acceptance remain release steps.
Other growing species, contests, shared beds, cooking, plot items and broad
agriculture remain outside these completed slices.
