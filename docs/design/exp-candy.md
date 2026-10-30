# Non-plot EXP Candy contract (#868)

Accepted design scope after #853–#859. This design does not enable runtime
items, change Rare Candy, populate a shop or certify released gameplay.

## Reference and selected rules

The Pokémon Company's [training announcement](https://swordshield.pokemon.com/en-au/gameplay/features-raise-pokemon/)
establishes direct EXP feeding. The pinned RHH implementation at
`44bc3e0473b85d8e254c8dbc9004ac2d7b0a5fb3`,
[items table](https://github.com/rh-hideout/pokeemerald-expansion/blob/44bc3e0473b85d8e254c8dbc9004ac2d7b0a5fb3/src/data/items.h)
and [EXP table](https://github.com/rh-hideout/pokeemerald-expansion/blob/44bc3e0473b85d8e254c8dbc9004ac2d7b0a5fb3/src/pokemon.c),
records XS=100, S=800, M=3,000, L=10,000 and XL=30,000 EXP. RHH is a primary
implementation reference, not an official PF2 economy or its policy authority.

Canonical names: Exp. Candy XS, Exp. Candy S, Exp. Candy M, Exp. Candy L and
Exp. Candy XL. Exactly one copy per `+use <item>=<current target>`; no quantity
loop or battle/held effect. Discover through the ordinary itemdex/use help.
Use the existing species growth curve; reject invalid noninteger level/EXP,
negative EXP, level/EXP contradictions, unknown curves and levels outside1–100.
Reject level100 and zero useful gain without a debit. Cap useful EXP at the
species' level100 threshold; a partial final gain consumes one copy.

Reuse fresh field target resolution and character/storage/trainer/owned-row
locking, including canonical party gaps and current Fusion. Reject eggs,
boxed/foreign/ambiguous/stale targets, battles/pending battles and conflicting
reservations. Combined companions remain frozen. A legitimate Necrozma host
follows its existing progression/deferred-learning contract; no active-source
slot or companion PP can change through candy.

One transaction includes the one-copy debit, total EXP, final level, every
crossed-level learned-move record and calculated HP/stat persistence. Preserve
absolute HP deficit with living minimum1 and fainted HP0 (selected PF2 policy;
this route is not a revival substitute). Preserve IVs/EVs/nature, Hyper Training,
held items, friendship, statuses/sleep and ownership. Evolving remains a separate
ordinary decision; candy must not silently spend an evolution item.

Record crossed-level knowledge in stable level/move order, deduplicated by real
owned identity. Offer eligible active-slot choices only after outer commit;
busy/disconnected players retain durable pending learning. Cancellation may
decline a replacement, never undo or replay paid EXP. A learned-move write,
stat save or outer transaction failure rolls back EXP/level/item/knowledge and
emits no success/menu. Retries must not recreate stale pending choices; two
last-copy users can produce at most one committed effect. Preserve Rare Candy's
existing semantics rather than routing it through new assumptions.

## Delivery boundaries

Create separate implementation issues for: five definitions plus atomic
progression; multi-level learning/prompt/reconnect integration; and bounded
optional acquisition plus ordinary buy→inventory→use→battle/evolve acceptance.
Each depends on the repaired field baseline. Optional reference offers are a
future finite buy-only progression counter: XS100/stock10, S800/stock10,
M3000/stock 5, L10000/stock2, XL30000/stock1. These are selected PF2 prices,
with no auto-refill, resale or automatic world installation.

Required proof: each size, same-level and multiple-level gains, cap truncation,
invalid saved states, living/fainted HP, source and companion preservation,
fresh target changes, failure after each partial write/learning/outer commit,
two-player last-copy contention, quiet rollback, pending-learning reconnect,
real normal command and subsequent battle stats. Keep disposable PostgreSQL,
required fresh full gates and intentionally released socket evidence distinct.

Implementation follows the linked batches below; source/reference audit is recorded above.


## Implementation follow-ups

This closes the design/scoping deliverable only. Runtime effects, source installation,
migration/release operations and ordinary acceptance remain with these open issues.

| Issue | Exact delivery | Dependencies |
| --- | --- | --- |
| [#894](https://github.com/PokemonFusion/Fusion2/issues/894) | Add five EXP Candy definitions and atomic field progression | #868 |
| [#895](https://github.com/PokemonFusion/Fusion2/issues/895) | Preserve crossed-level EXP Candy learning and reconnect choices | #868, #894 |
| [#896](https://github.com/PokemonFusion/Fusion2/issues/896) | Qualify EXP Candy acquisition, multi-level use and later gameplay | #868, #895 |

Runtime/learning implementation and local qualification for #894/#895:
[player guide](../exp-candy.md), [dated evidence](../testing/exp-candy-2026-10-25.md).
The optional finite counter and captured-command flows are qualified locally;
#896 retains the installation/released acceptance boundary.

Scope/source checks: [2026-10-25 decision receipt](../testing/item-scope-decisions-2026-10-25.md).
