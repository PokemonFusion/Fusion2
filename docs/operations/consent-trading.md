# Consent-based Pokémon trades (#725)

The ordinary `+trade` command uses the shared [ownership service](pokemon-transfers.md).
There is no immediate gift/owner reassignment shortcut. A player can offer one
owned party or boxed Pokémon, or negotiate a one-for-one swap. No new currency,
fee, EXP, healing, capture credit or automatic evolution is granted.

## Player flow

```text
Ash:   +trade offer Misty=3
Misty: +trade inspect OFFER_ID
Misty: +trade accept OFFER_ID
```

For a swap, Misty inspects that offer and counters with her own asset:

```text
Misty: +trade counter OFFER_ID=HER_POKEMON_ID
Ash:   +trade inspect NEW_OFFER_ID
Ash:   +trade accept NEW_OFFER_ID
```

Use an exact character name or `#character_id` for the recipient. Pokémon selectors
are canonical party slots 1–6 (`3`, `slot3`) or a complete/unique ID prefix of at
least eight hex characters from `+box`/`+pokemon`. Boxed assets do not need to
enter the party first. Eggs retain their existing identity/state and can be traded;
this route never hatches them or grants their contents again.

`+trade` lists up to thirty outcomes, pending first. Inspect shows the sealed
asset summary, participants, deadline and receipt. Each recipient must inspect
the exact offer before acceptance or countering. Reviews are character-bound
digests in the `trade_reviews` Attribute category. Sharing an account, inspecting
another offer or inspecting the old terms cannot supply consent for a new one.

`+trade decline ID` is for the intended recipient. `+trade cancel ID` is for either
participant. A counteroffer atomically closes the original and creates a new
immutable operation requiring fresh inspection and consent; its original receipt
links the replacement. A rejected replacement leaves the original pending claim
intact. Changing a counteroffer again requires another new operation/consent.

Offers expire after fifteen server-clock minutes. Expiry immediately prevents
acceptance. Claims remain inspectable until either participant cancels the expired
offer; no timer transfers or discards an asset. Close pending offers to expose older
entries in the thirty-entry list. Disconnects do not erase offers or outcomes.

## Exact terms and commit behavior

The proposer reserves only their own asset. A requested counterparty asset is
reserved only when that owner accepts. Immutable snapshots bind the existing
Pokémon UUID and stored genetic/progression/held/move/PP state. Changed state is
rejected rather than accepted against an earlier display. A counter checks the
original offered snapshot before proposing replacement terms.

Shiny summaries read the saved `is_shiny` boolean. Older pending offers that did
not record that value must be cancelled and reissued before acceptance or a
counteroffer. Their terms are never silently rewritten or filled from a later
owner's live Pokemon. Completed receipts still replay without a new transfer.

The final commit rechecks both characters, source custody, battles, Fusion
references, all system claims and destination allocation under shared locks.
Both sides save or neither does. A free party slot is preferred, then the first
owned box under the existing unbounded box policy. Explicit party-only service
requests still fail atomically when full. No player/member is evicted.

UUID, original trainer/provenance, nickname, held item, HP/status, EXP, friendship,
genetic IVs/EVs, Hyper Training and move/PP rows remain on the same owned Pokémon.
Final receipts survive later moves or release. Repeating acceptance returns the
historical result without payment, transfer or resurrection. Cancellation/decline
records retain the closing character and reason. Notices publish after commit;
offline participants can inspect their own persisted list after reconnect.

Trades never trigger automatic evolution. Existing documented
[manual trade-held item equivalents](../trade-held-evolution.md) remain supported.
Other non-item/partner-species trade triggers remain deferred; this feature does
not silently grant them.

## Shared mutation guards

Party sources reserved by an offer cannot enter battle until cancelled. Boxed
offers do not prevent using other party members, but both characters must be out
of battle to commit. Active/unlocked Fusion forms and marketplace/Daycare/breeding
claims cannot be offered. Storage, release, field item/evolution and moves/menu
routes validate reservations and current ownership.

`MoveEdits` protects caller-bound learning and retained moveset/replacement menu
sources. A menu opened before a transfer cannot edit the new owner's Pokémon.
Learning notices, continuation callbacks and prompts publish after commit, and
rollback discards cached model state. Automatic server learning without a caller
retains its existing enclosing lifecycle transaction contract.

The old `+moves/use` called a model method that did not exist. Its real player path
now uses a guarded saved-set activation at a Pokémon Center. Center-only activation
preserves the existing PP restoration behavior without adding free field PP refill;
it does not heal HP. The moveset manager rechecks Center/owner/reservation state on
each reply. Existing pure test/engine stand-ins retain their lightweight adapters.

## Verification and operations

`tests/integration/trade_cases.py` runs actual User/Account models and commands in
an explicit isolated PostgreSQL schema, including review/consent, same-account
authority, party/box swaps, rollback, replay, expiry, competing accepts and old
menu/edit races. Source and log fingerprints belong in the dated test report.
Captured command transport is automated local acceptance, separately labelled
from a live socket walkthrough, hosted CI and deployment.

Use `audit_pokemon_transfers --pending` for read-only staff inspection. Cancel a
known pending operation through its participant-bound service; do not edit owners,
manufacture approvals or delete terminal receipts. Existing game deployment,
migrations and service operations require their own authorization. No plot-only
item route or unrelated battle feature is added here.
