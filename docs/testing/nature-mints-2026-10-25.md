# Nature mint qualification (#897–#904)

**October26 released acceptance update:** Later approved PF2-Dev player checks,
actual crop/breeding waits, receipt-preserving QA teardown and independent
same-build health are complete. See the [released report](remaining-item-released-player-2026-10-26.md)
and [dated availability index](item-availability-released-index-2026-10-26.json).
The October25 source-only receipts and then-pending limits below remain
historical records. Temporary QA helpers do not certify permanent stock.

Local automated command/SQL and consumer qualification is complete for21 exact
mints. Actual migration rehearsals and deliberately released acceptance are
separate gates; see the machine report for their current status. No existing
game database or shared-world source was changed. [Player guide](../nature-mints.md),
[machine receipts and observations](nature-mints-2026-10-25.json),
[isolated migration plan](nature-mint-migration-plan-2026-10-25.md).

The trained stat preference is separate nullable owned state. Genetic Nature
stays unchanged. Stat helpers/builders, raw fallback, constructor/checkpoint,
native/Mega/Fusion recalculation and caches use the effective preference;
inspection/custody labels both. Existing breeding/Everstone, capture generation,
Toxtricity evolution and flavor confusion keep genetics. Invalid training is
visible before broad stat fallback. Existing blank legacy genetics retain their
old neutral untrained stat reads; a mint refuses such a paid target.

**191 PostgreSQL cases** passed on the exact immutable candidate:59 field/source,
17 native pairs,21 trade,20 marketplace,30 vitamin/feather,31 Hyper Training,
13 breeding. Every mint has a paid +use, useful stat outcome, invalid target,
partial-debit and containing rollback, no-effect/repeat, fresh connection/context,
later actual battle and separate-connection final-copy race. Additional controls
cover stale ownership/Fusion/eggs/boxes/battles/selectors/HP/genetics, allneutral
equivalence, immutable move/PP/IV/EV/status/progression, actual source Exits/menu,
legacy owned checkpoints, trained companions/both native pairs/separation,
actual evolution, Everstone inheritance, and trade/market review and transfer.

**159 focused tests** passed, including exact non-HP modifiers and allfive actual
flavor-berry callbacks under opposite minted/genetic preferences. The mandatory
combined/repeat/battle-first runs each passed **6,592 /4,028 skipped**, exit0.
The final1,179-file Python map after the separate renewable and mint commits
must match this frozen cohort; later Ultra WIP remains excluded and all25
unrelated shared dirty paths are protected.

Schema0059 adds only a nullable/empty validated overlay and its constraint,
without backfill or grants. Reverse refuses nonblank training before dropping
the field. A migration rehearsal is never inferred from direct model-table
SQL tests or a Python/full-suite pass. Allsix approved guarded random-schema
loopback rehearsals passed, including fresh/upgrade/active-pair, reverse/reapply,
paid reversal refusal and injected post-DDL rollback/reapplication. The initially
incomplete fixture/audit/loader diagnostics are retained; the migration remained
unchanged. No game migration/restart is authorized by this rehearsal.
Issue#904 released sockets remain a separate required gate.

The optional21-offer counter has finite one-copy20,000 prices, buy-only through
`mints`/`back`, without implicit refill. The source index preserves472 prior
definition fingerprints and records641 definitions/493 scoped entries, all
world availability unverified. Captured transport is not a socket reconnect,
deployment, hosted CI, permanent source or shared installation claim.
