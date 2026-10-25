# Next nursery seed batch (#867)

Accepted design scope after repairs, reporting and source policy. Existing Oran growing
and Razz's independent snack remain accepted only for their documented routes.
This design adds no immediate seed, harvest, stock or completed live crop.

Select exactly **Cheri, Pecha, Rawst and Aspear Berry** as the next four seeds.
Each has an existing useful post-harvest `+use` status cure and held identity.
Do not enable all 77 berries, a flavor-food grower or new recovery effects.

Selected PF2 growth policy matches Oran: one private durable bed per trainer,
one real bag seed debit, four elapsed one-hour stages, distinct free watering
credits, and one harvest of 1–5 canonical berries. No decay; offline time counts.
Replant explicitly. Use server UTC and the saved cycle, never process timers,
client time or a reset-on-login schedule. No growth tools, story unlock, farming
currency, additional beds or auto-replant.

`BerryBed.berry` already stores a string and its existing constraints cover four
watering bits and a maximum yield of 5. A bounded seed registry plus service/
command changes should suffice; introduce no migration without an actual new
integrity need. Preserve valid legacy Oran cycles and receipts. `state` must
validate the saved berry against the reviewed registry and current cycle's
times. Plant binds the canonical seed before locking; harvest credits exactly
the berry saved on that cycle, not a supplied stale command name.

Reuse `BerryGrowing.locked`: fresh room→character→storage→trainer→bed ordering,
real nursery access and all battle guards. Plant/stock/cycle, watering bit and
harvest/bag/receipt writes remain atomic. One final seed can plant only once;
two harvest requests credit one total yield; old requests cannot water, harvest
or reset a replacement crop. Verify no success output/cache change after any
partial/outer rollback, changed room/owner/cycle or invalid saved state.

Discovery lists only accepted seeds, the current berry, stage, expected yield
and UTC ready time. Reuse `+berry plant <name>`, `water`, `status` and `harvest`.
A harvested cure must work normally through `+inventory`/`+use` with one useful
debit; a held berry remains an item rather than an implicit seed.

Keep the existing two-offer nursery recipe and its sold stock unchanged. Source
the four new seeds from a separate versioned optional Seed Counter: 100 each,
stock 5 each, buy-only, no automatic refill; an explicitly reviewed hub's `seeds`
exit returns via `back`. It may carry the same nursery-access flag, but cannot
duplicate or reset the original counter's markers or stock. This recipe and
its installation remain source work, not evidence of public availability.

Create one explicit four-seed registry/commands/atomic lifecycle issue and one
source/released acceptance issue. The first needs controlled-clock boundary,
replay/contention/rollback and ordinary command/SQL tests plus full Oran/Razz
regressions. The latter must perform ordinary purchase→plant→water→harvest→use,
including **four real elapsed hours** on an intentionally released build.
Clock advancement in tests is not proof of that timed walkthrough. Preserve
human data and distinguish tagged setup/cleanup from permanent nursery content.

The source audit checked `pokemon/models/berries.py::BerryBed` (40-character
berry field and existing watering/yield constraints),
`pokemon/services/berry_growing.py::state/locked/operate` (currently hardcoded
Oran identity), and `pokemon/services/item_counter.py::install` (current
recipe markers/offers cannot drift or refill on retry). These are exact
extension boundaries, not runtime acceptance of the four new seeds.
Implementation follows the linked issues below.
The [runtime seed delivery](../testing/nursery-seeds-2026-10-25.md) now has
controlled-clock command/SQL evidence for all four names and the old Oran/Razz
regressions. Optional source authoring is separate from #893's still-required
four-real-hour released ordinary-player acceptance.


## Implementation follow-ups

This closes the design/scoping deliverable only. Runtime effects, source installation,
migration/release operations and ordinary acceptance remain with these open issues.

| Issue | Exact delivery | Dependencies |
| --- | --- | --- |
| [#892](https://github.com/PokemonFusion/Fusion2/issues/892) | Grow Cheri, Pecha, Rawst and Aspear through the durable nursery | #867 |
| [#893](https://github.com/PokemonFusion/Fusion2/issues/893) | Deliver four seed sources and real elapsed nursery acceptance | #867, #892 |

Scope/source checks: [2026-10-25 decision receipt](../testing/item-scope-decisions-2026-10-25.md).
