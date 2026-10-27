# Z-Crystal and berry-route design validation (#775/#776)

October 22, 2026. Inspected source baseline:
`4f0995b1b53e3b5a040d27092e48da05c67aa2d8`. These are two design closeouts,
with no runtime implementation or availability claim. #783's independently
scoped fixture correction is committed separately.

The [Z contract](../design/z-moves.md) selects reusable held Normalium Z and
the actual Tackle slot, proposed `+zmove` as one legal action, exact reviewed
damage/PP/prevention rules, team ledger, native/owner checks, Tera/Mega policy,
durable replay and cleanup. Fresh local enumeration gives **35** crystals:
18 generic, 17 signature. The [per-item plan](../design/z-crystals.md) maps 34
to #797–#808, keeping Ultranecrozium explicitly deferred behind an independent
Ultra native-form design. Zero ordinary Z routes are enabled; generic later
slices retain explicit partial move allowlists. Counts are fresh metadata
evidence, not a rewrite of the historical combined audit denominator.

The [berry contract](../design/berry-player-routes.md) selects a one-seed Oran
bed with four one-hour stages, once-per-stage watering, yield 1–5, no decay and
explicit new planting after harvest. It specifies unique ownership/cycle IDs,
atomic seed/harvest inventory, durable UTC/reconnect/retry/contention behavior
and safe optional nursery authoring. A separate Razz snack heals up to 10 HP
through shared field checks; this is an explicit PF2 equivalent rather than
invented contest support or a canonical Razz healing claim. #809–#812 separate
state, commands/content, snack and integrated acceptance. No model/migration
is implemented or run by this design task.

Catalog uniqueness/completeness, actual created issue mappings and local
Markdown targets were checked. Source inspection established that `BerryPlant`
remains an in-memory helper, ordinary Z declarations/ledger are absent, and
Tackle lacks an explicit Z-power field. Selected costs, yields, formats,
mechanic coexistence and command syntax are PF2 design choices. Primary Z
mechanics references are linked in the contract; newer external definitions
do not expand this local inventory.

The [JSON receipt](item-designs-2026-10-22.json) includes complete issue IDs,
catalog classification and source/design hashes. These checks do not prove
normal gameplay: implementation issues explicitly require complete turns,
ordinary commands, SQL/reconnect, actual sources, negative/failure/contention
coverage and relevant regression gates. No live login, released acceptance,
deployment, stock/character changes, service restart or migration occurred.
Existing #757/#772 historical reports remain unchanged.
