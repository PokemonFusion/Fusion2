# Native Necrozma integrity and release boundary

The [player guide](../necrozma.md) and [reviewed contract](../design/necrozma-combination.md)
define the two native pairs. This is not trainer/Pokémon Fusion or a new owner
transfer implementation. `OwnedPokemon.trainer` and `PokemonPlacement` remain
authoritative; the companion uses `combined`, never a hidden box or `fusion`.

Migration 0057 locks and audits legacy owned forms/source exposure **before its
first schema write**. Ambiguous directly granted fused rows or base Necrozma
with unexplained form-only moves stop the upgrade. It does not invent a partner,
delete sources or automatically separate anything. Migration 0058 audits the
new final state before installing deferred pair/ownership/source/PP checks,
frozen companion/slot boundaries and immutable requests/receipts.

The current read-only `audit_pokemon_placements` includes version 3 native
custody, source bindings and historical PP resources. Historical v1/v2 audits
remain unchanged for older migrations. Audit findings require deliberate staff
review. Do not treat an invalid pair as permission to repair or delete it.

`NecrozmaService` locks character → storage → trainer → UUID-ordered sources →
placements/pair/resources. It uses detached owned instances; caches refresh only
after transaction publication. Confirmation binds current SQL terms, the exact
lifecycle and version, and a five-minute expiry. Committed receipts retain UUIDs
without protective source foreign keys, so later legitimate release remains
possible and receipt replay cannot recreate a source.

Storage-first eligibility hooks never acquire a later character lock. Ownership,
placement, field, move, trainer-Fusion and battle entry share that boundary.
Battle admission and native full turns/synchronization serialize through the
same owner/storage/source order. Reserved companions never join a roster.
Battle snapshots bind both sources and lifecycle; reconstruction validates after
controllers have been restored, before accepting further input or final writes.

The actual active move slot is the live PP authority. A transactional PostgreSQL
trigger mirrors that bound slot into its persistent form resource, including bulk
updates. Attack/Z debits, PP drains, recovery, PP capacity and healing therefore
commit together. No second debit is added. Dormant resources are not active
healing targets. Missing prior history fails closed. Separation removes only
temporary source exposure and restores the exact displaced slot.

All pair/form/slot/placement/mirror/receipt writes share one transaction.
Failures, no return destination or outer rollback retain the valid previous
state and suppress success. Live links protect both owned rows. Rollback of an
unused feature is rehearsed; reversing migration 0058 after pair/resource or
completed operation data exists refuses before removing checks. Keep a used
schema intact until a separately reviewed data-preserving recovery plan exists.

## Operator approval

`AGENTS.md` requires separate approval for migrations, existing-service restarts
and game-data operations. The current approval covers only the explicit
`tests/integration/necrozma_migrations.py` runner in task-owned loopback PostgreSQL
and random disposable schemas. It does not authorize a game deployment.

Before #831, publish the exact tested implementation SHA, inspect the chosen
environment/source/schema read-only, and prepare exact deployment, migration,
reload and tagged-source/player setup commands. Obtain separate approval for
unapproved operations. Preserve existing human characters, Pokémon and sessions.
Do not install permanent stock or default sources for this feature.

The released walkthrough must acquire both native sources through ordinary
configured routes, then exercise actual Center movement, review/confirmation,
inspection, held crystal, ordinary and Z actions, source PP, field use,
reconnect, separation and party/box fallback for both forms. Separate setup and
staff observations from ordinary socket input. Retain command/SQL/protected-row
baselines and exact cleanup receipts. Local automation, CI, publication and live
release remain separate evidence categories.
