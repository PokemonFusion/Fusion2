# Real abilities at item-form entry — October 25, 2026

Issue [#872](https://github.com/PokemonFusion/Fusion2/issues/872), found during
#857. Baseline `54275b1d67669a839b3cf6575a6d55d1d588bdf1`.

Species entries can contain display-only Ability objects with empty callback
data. `Pokemon.formeChange` installed those objects directly. Native Dialga's
held Adamant Crystal therefore produced Dialga-Origin without working Pressure
until checkpoint restoration resolved the stored ability name. The ordinary
owned-player pilot reproduced a one-PP/two-PP difference before/after restore.

Form installation now resolves its native ability against the real ability
dex. An unchanged ability's startup is left to normal entry, avoiding two
Crowned boosts. A changed ability uses the existing strict named-owner startup
boundary, so the opponent cannot occupy the callback's battle parameter.
Primordial Sea/Desolate Land End hooks accept proper event arguments and retain
their legacy two-argument interface, clearing only their real holder's weather.
Eligibility, required items, species data and source identities are unchanged.

The first full order found two existing display assertions after resolving the
real abilities: their dex keys spell `Desolateland`/`Primordialsea`. A shallow
battle-instance copy now retains the normal raw display name and the same real
callback data, without mutating the global dex. That failed order (6,043 passed,
4,028 skipped, two display failures) and its receipts remain immutable. All 46
existing runtime-hook tests then passed; the full gate is restarted from the
first order on the replacement frozen manifest.

The first nine regression tests all failed on baseline. Eleven final tests
check canonical callbacks for all seven forms, immediate real Pressure source
PP debit, native Primal weather and Crowned boosts, and weather cleanup when
the holder's ability changes. The #857 command suite additionally checks fresh
owned entry, correct Pressure cost, one Crowned boost, genuine Primal weather,
and unchanged ability/form/boost/weather state across durable reconstruction.

All 11 final ability regressions passed within 1,513 focused tests. All 46 existing
runtime-hook tests passed after the display correction. The final 237 owned
command cases and 556 compatibility cases passed, followed by all three fresh
full orders with 6,045 passed/ 4,028 skipped each and wrapper exit zero. The
task-only PostgreSQL fixture is stopped/clean, and 25 unrelated shared-worktree
paths remain unchanged. The [machine receipt](item-form-abilities-2026-10-25.json)
records the exact source methods and qualification commands.

The separate #872 commit and subsequent #857 commit are qualified together
against the frozen 1,128-file Python manifest; the combined gate does not certify
an untested intermediate commit alone. The
[#857 report](origin-primal-rusted-theft-2026-10-25.md) retains the shared
commands, failed pilots, full source manifest and acceptance boundaries.

No global species/ability data is regenerated. No new form, item, public source,
plot content, deployment, migration or human-character change is included.
