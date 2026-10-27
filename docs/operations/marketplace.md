# Fixed-price Pokemon marketplace (#726)

The beta marketplace supports **hatched owned Pokemon**, including their existing
held item, through existing trainer money. Eggs use consent trading. Item-only
listings, auctions, bidding, new currencies and plot-only assets are excluded.

## Ordinary player flow

```text
Seller: +market list 3=100
Buyer:  +market
Buyer:  +market inspect LISTING_ID
Buyer:  +market buy LISTING_ID
Seller: +market mine
```

Use a canonical party slot or a unique owned UUID prefix of at least eight hex
characters for boxed Pokemon, as with `+trade`. No pre-list party move is needed.
The seller chooses an integer price from 1 to 1,000,000 trainer money. No listing
fee or sales tax is charged. A seller cannot buy their own listing. Character
money and authority remain separate even when characters share a login account.

Listings last 24 hours. Inspect displays the immutable asset summary and price;
the buying character must inspect those exact terms before purchasing. The seller
can `+market cancel LISTING_ID`. `+market mine` shows pending listings first and
reclaims expired claims; attempted purchase of an expired listing also releases
its claim. Status/cancellation/reclaim retries never move an asset or charge money.
An older listing without recorded shiny state must be cancelled and relisted by
its seller before purchase. The display says that state is unrecorded; it never
guesses that the Pokemon is ordinary or changes sealed terms in place.
Browse and own-list views show up to thirty records; use a saved listing UUID to
inspect or cancel an older record directly.

A sold listing retains its purchase identity. The same buyer can repeat `buy` to
recover that receipt after reconnect, even if the Pokemon was later released.
Inspection shows each participant their own saved post-sale balance and the
historical destination. This historical record does not promise that later
spending, storage moves or transfers leave that balance/location unchanged.

## Safety and custody

Listings reserve the source in its existing party or box. The listed Pokemon
cannot be used in battle, moved, released, fused, edited or offered to another
system until cancellation/expiry/sale. A boxed listing does not block battles
using other Pokemon, but buyer and seller must be out of battle at purchase.
Active/unlocked Fusion forms, breeding parents, eggs and conflicting claims are
rejected before publishing. No fee is charged for a rejected listing.

The final purchase locks both characters, storage and trainer wallets in the
shared order, then rechecks listing state, source ownership, the exclusive claim,
the advertised fingerprint, eligibility and funds. A seller wallet that cannot
receive the entire price is rejected; values never wrap or silently truncate.

Existing `Trainer.add_money` and `spend_money` writers also lock and read the
current wallet before changing it. A cached pre-sale Trainer cannot overwrite a
completed payment, spend more than the saved balance or introduce a negative
credit. Whole nonnegative amounts and the database wallet limit are enforced.

Buyer debit, seller credit, ownership, canonical placement and purchase receipt
commit in one outer transaction. The Pokemon transfer reuses `OwnershipTransfers`
with purpose `market`; public trade commands cannot inspect, approve, counter or
cancel those internal market settlements. The seller's sealed listing authorizes
the sale, while the named buyer's explicit purchase supplies buyer consent.

A free destination party slot is preferred; full parties use an existing owned
box under the current unbounded box policy. No member is evicted. UUID, original
trainer/provenance, HP/status/PP, held item, progression, friendship, genetics,
training and moves remain on the same Pokemon. Purchases never heal, grant EXP,
evolve a Pokemon, or mint money. A competing buyer/cancellation/expiry wins once;
losing attempts leave funds and assets unchanged.

## Inspection, migration and evidence

Durable listing states are active/sold/cancelled/expired. Price, advertised asset
and terminal receipts are sealed on PostgreSQL. Deferred checks require an active
listing to retain its matching claim and valid source custody, and a closed
listing to release its claim. Historical scalar character/asset IDs preserve the
receipt when nullable live references later disappear.

`audit_market_v1` is read-only and historical-model compatible. Integrity errors
ask staff to inspect the exact listing/claim; recovery never guesses a new owner,
approves somebody else's terms, fabricates payment or deletes a receipt. Generic
system reservations remain the responsibility of their owning subsystem.

The lifecycle CI includes real PostgreSQL command, payment rollback, destination,
replay and independent-buyer contention coverage. Dated test records distinguish
captured local command acceptance, live player sessions and deployment. Existing
game database migrations/restarts require their own explicit release approval.
