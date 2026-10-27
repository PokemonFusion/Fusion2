# Shared ownership transfers and reservations (#722)

This foundation supplies transactional services. The ordinary `+trade` route uses
the [consent UI](consent-trading.md) in #725. Marketplace, Daycare and
breeding remain separate implementation/acceptance work. These services grant
no money, items, evolution, EXP or automatic repairs.

## Custody and write contract

`OwnedPokemon.trainer` remains the owner and `PokemonPlacement` remains canonical.
Existing same-owner writers use `PlacementService` (storage then Pokémon locks).
Compound writers acquire sorted character IDs, storage IDs and trainer IDs, then
the operation row, sorted Pokémon UUIDs and reservation rows. They must not acquire
a character lock after storage. Character locks use PostgreSQL `NO KEY UPDATE`
so storage-first Attribute writes can acquire their foreign-key key-share locks.

`OwnershipTransfers(actor).prepare(recipient_id, movements, request_id=uuid)`
accepts one to twelve unique Pokémon UUIDs moving between exactly those two
characters. Each movement binds `pokemon`, `source`, `destination`, and placement
`mode` (`auto`, `party`, `box`), with an optional exact party `slot`. The proposer
must offer their own asset. Recipient assets are not reserved before consent.
No account-level permission grants an alternate character's approval.

The resulting `OwnershipTransfer` has immutable terms, two named characters,
character-specific approvals, a fifteen-minute deadline and a durable UUID.
`approve(id)` validates current custody, battle/Fusion state and competing claims
again and reserves the consenting assets. `commit(id)` requires both approvals,
locks the same owners and rechecks every asset and destination before writing.
`cancel(id)` is safe for either participant, including expired offers; it releases
only that offer's claims. Pending expiry prevents approval/commit immediately;
claims remain inspectable until cancellation. No timer silently transfers assets.

A successful batch atomically frees outgoing slots, moves owners and the existing
canonical rows, rebuilds legacy mirrors, releases claims and seals one receipt.
All outgoing members are freed before allocating incoming members, so full-party
swaps work. Automatic placement uses a free slot 1–6, otherwise the existing box
policy (first owned box; eight default boxes can be created). There is currently
no box-size limit. Explicit party placement fails atomically when unavailable;
it never evicts another member. No transient unplaced state can commit.

Only `trainer_id` changes on the owned Pokémon. UUID, original trainer/name,
acquisition provenance, nickname, held item, HP/status, EXP, friendship, IVs/EVs,
Hyper Training and moves/PP stay attached to the same row. No trade evolution is
triggered by this foundation. The supported manual trade-held equivalents remain
in [trade-held evolution](../trade-held-evolution.md).

The original receipt is returned on exact retries, even after subsequent storage
moves or release; replay cannot resurrect or move the asset again. A request UUID
cannot be reused with different terms. Database errors roll back the entire batch
and keep its pending consent/claims available for deliberate retry/cancellation.
Identity-map fields are refreshed for validation, flushed inside outer transactions
and published again only after commit. Callers must likewise discard their runtime
snapshots when rolling back their own larger transactions.

## Shared reservations and battles

`PokemonReservation` exclusively claims one owned Pokémon while retaining custody
and canonical placement. Trade claims bind the matching pending operation and an
approved source owner. `PokemonReservations(actor).claim(kind, ids, token)` and
`.release(kind, token)` provide atomic owner/kind/cycle-bound hooks for marketplace,
Daycare and breeding. Those systems must persist their own lifecycle/payment
receipt and must not expose arbitrary token cancellation as a player capability.
The hooks alone implement none of those player systems.

`PlacementService` rejects conflicting claims for storage, release, Fusion and the
field item/evolution services that reuse its fresh-target boundary. Transfer also
rejects saved or runtime battles, a pending PvP lobby, active/unlocked Fusion IDs
(even when inconsistent with placement) and legacy breeding flags. Missing or
conflicting custody fails closed for staff review.

Battle admission claims the saved battle lock under character/storage locks and
checks the canonical party and active Fusion before building snapshots. An offered
party member must be cancelled/unreserved before battling. A boxed claim does not
prevent battling with other party members. The saved lock prevents transfer until
battle cleanup. A stale lock is not automatically assumed safe to erase.

## Database guarantees and rollout

Migrations `0047` and `0048` add the tables, state/shape constraints, immutable
consent/terminal receipts and deferred PostgreSQL reservation/custody checks.
The second migration locks affected tables and runs the versioned audit first.
Invalid existing data blocks rollout without guesses or repairs. Existing `0041`
deferred placement checks continue to require exactly one owner-matching placement.
SQLite does not provide the cross-table or row-lock guarantees.

Existing game deployment/migrations/restarts require separate operator approval
under [AGENTS.md](../../AGENTS.md). The approved local October migration rehearsals
do not authorize deployment to any existing game environment.

Read-only inspection in the selected environment:

```text
python -m django audit_pokemon_transfers --settings=server.conf.settings --pending
```

An audit problem reports a Pokémon UUID and reservation/transfer reference. Exit
status is nonzero for inconsistent data. A pending expired operation is labelled
for cancellation. Staff should inspect both characters and the exact terms; use
the authorized participant-bound cancellation service for a known pending offer.
Never change the owner, fabricate consent or delete a receipt to make an audit pass.

## Reproducible local verification

Set `PF2_TEST_POSTGRES_DSN` only to an isolated test PostgreSQL database. Never use
a game database. Each runner creates and drops a randomly named protected schema.

- `python -B tests/integration/ownership_cases.py`: real model custody, consent,
  guard/field-command behavior, write failures, receipts and independent-connection
  transfer/storage/release/battle-admission/capacity races; builds model tables and
  constraint functions directly, without deployment migrations.
- `python -B tests/integration/ownership_migrations.py`: **approval required**;
  fresh install, upgrade from `0046`, guarded invalid-data failure from `0047`,
  preserved progression, current model state and transfer/replay after migration.
- `python -B tools/run_mandatory_tests.py`: fresh combined, repeat and battle-first
  suites. With an explicit DSN these also run the transfer subprocess tests.

CI provisions its own PostgreSQL service. Local tests, hosted CI, ordinary socket
acceptance and deployment are separate evidence; a service test does not certify
the later consent UI or live readiness.
