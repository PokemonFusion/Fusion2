# Capped operator replenishment (#876, 2026-10-25)

The explicit [operator API](../item-replenishment.md) adds a durable rolling
24-hour refill route for separately reviewed opted-in consumable sources.
The original Supply Corner stays finite and excluded. There is no source
installation, startup refill, scheduler, player refill command or live deployment.

**29 PostgreSQL cases passed**, including ordinary production `+store`/EvMenu
and `+inventory`/`+use` routes. Tagged stock, wallet, operator account, native
target and deterministic UTC clock are separate prerequisites. Items enter
the player bag only through the production purchase service. Captured client
transport is automated command acceptance, not an ordinary socket login.

The end-to-end route buys both last Potions, observes the sold-out refusal,
performs a separate eligible operator refill, buys another copy, and uses a
paid Potion on the current party target. HP rises from 1 to 21, one bag copy
is consumed, and the effect does not change wallet or source stock. SQL reload
preserves the ledger, purchased copies, HP and latest source sequence. Invalid
target/full-health controls preserve the acquired item.

The independent checks cover midnight and the microsecond before eligibility,
the exact 24-hour boundary, delayed refills without carryover, full-stock no-op,
duplicate requests after purchases and later refills, same-window new UUIDs,
clock rollback, untouched initial caps, retry without stock reset, absent
opt-in, source/version/price/count/item-set/flag drift, original source exclusion,
current SQL account permissions, stale elevation, invalid actors/request IDs,
duplicate markers, damaged/missing receipts, post-stock/post-receipt faults,
outer configure/refill rollback, and normal Attribute visibility after commit.
Independent SQL connections prove same-request idempotency, different-request
exclusion, purchase/refill stock conservation and two-buyer final-copy contention.

**52 focused tests passed** (31 new authoring/UTC checks and 21 existing source
index checks). **51 compatibility SQL cases passed**: 8 atomic shop purchases,
11 six-item Supply Corner routes and 32 existing acquire-to-effect routes.
The [machine receipt](item-replenishment-2026-10-25.json) retains individual
case names, actual windows/deltas, command examples and exact source identities.

All three fresh mandatory orders passed **6,318 passed / 4,028 skipped each**,
wrapper exit zero in 2,138.52 seconds. The immutable full copy contained
1,152 Python sources; the three published Python files match those identities.
The other 1,149 Python sources were unchanged in this qualified candidate.
All 25 unrelated shared dirty paths remain preserved.

The first diagnostic SQL run retained two failures and one error: directly
created receipt Attributes lacked Evennia's `db_model` field. Raw SQL could
read them while the ordinary Attribute handler could not see/remove them.
The creation path now supplies the object's actual model marker. All 29 final
cases pass, including both normal handler access and SQL-only validation.

The task-owned loopback database was stopped after all disposable schemas
were removed. No migration, existing game database, permanent stock, existing
human character or shared service was changed. PF2-Dev remains on its earlier
approved Supply Corner release. Source publication is separate from opting a
future counter into renewable supply; that still needs a concrete approved plan.
