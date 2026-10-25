# EV mochi contract (#870)

Accepted design scope after the repair/report gates; none of these new definitions is enabled.
The pinned RHH [item/effect tables](https://github.com/rh-hideout/pokeemerald-expansion/blob/44bc3e0473b85d8e254c8dbc9004ac2d7b0a5fb3/src/data/pokemon/item_effects.h)
and [effect constants](https://github.com/rh-hideout/pokeemerald-expansion/blob/44bc3e0473b85d8e254c8dbc9004ac2d7b0a5fb3/include/constants/item_effects.h)
bind the stat supplements to ten EVs and the reset to all six. They are a
primary implementation reference; PF2's transactions, HP and source policy
below are explicit project choices.

| Item | Effect |
| --- | --- |
| Health Mochi | HP EV +10 |
| Muscle Mochi | Attack EV +10 |
| Resist Mochi | Defense EV +10 |
| Genius Mochi | Special Attack EV +10 |
| Clever Mochi | Special Defense EV +10 |
| Swift Mochi | Speed EV +10 |
| Fresh-Start Mochi | Reset all six EVs to zero together |

Reuse `FieldTrainingUse` and the shared fresh field targets and locks. Require
exactly six valid nonnegative integer EVs within per-stat252/total510; reject
invalid stored arrays instead of repairing them by feeding. Supplements add
the useful minimum of10, remaining stat room and remaining total room. Consume
one copy only if the stored vector changes. Fresh-Start has one all-stat
operation, not six independently paid uses; all-zero targets are no-effect.

`+use <full name>=<current target>` is the only new activation route. No held
or manual battle effect, target-wide reset, extra friendship or nature effect.
Reject eggs, boxes, foreign/ambiguous/stale targets, non-current Fusion,
battles/pending battles and conflicting reservations. Combined companions stay
frozen; preserve any legitimate host training allowed by the existing contract.

Lock stock and current owned target once. One transaction contains one debit,
the complete EV vector and refreshed HP/stat persistence. Use project stat/HP
helpers and preserve absolute HP deficit, conscious minimum1 and fainted HP0.
Do not revive, change IVs/genetic Nature/Hyper Training/abilities/progression,
erase a status or install a new max-HP snapshot. Failure after debit, any EV
write, stat calculation, save or outer transaction must restore every field
and cache without success output. Competing requests on one final copy can
commit at most once; different-stat requests must retain both useful updates.

Create two bounded implementation issues: all six supplements, then the
Fresh-Start atomic reset. Both require actual `+use`, fresh SQL, cap/no-effect,
invalid/foreign/egg/box/current-Fusion/stale, partial-write/outer-rollback and
contention cases; reconnect and later battle stats must agree. Preserve vitamin,
feather, EV-berry and Hyper Training suites. Optional source prices are10000
per supplement/stock2, Fresh-Start20000/stock1, finite buy-only/no refill; they
are selected PF2 offers awaiting source/release work. No broad world grant.

Implementation follows the linked batches below; runtime qualification remains future work.


## Implementation follow-ups

This closes the design/scoping deliverable only. Runtime effects, source installation,
migration/release operations and ordinary acceptance remain with these open issues.

| Issue | Exact delivery | Dependencies |
| --- | --- | --- |
| [#905](https://github.com/PokemonFusion/Fusion2/issues/905) | Add six EV mochi through safe shared field training | #870 |
| [#906](https://github.com/PokemonFusion/Fusion2/issues/906) | Add Fresh-Start Mochi atomic reset and training acceptance | #870, #905 |

Scope/source checks: [2026-10-25 decision receipt](../testing/item-scope-decisions-2026-10-25.md).
