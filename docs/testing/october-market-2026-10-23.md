# October marketplace verification (#726)

October 23, 2026 candidate based on `3ad9fb4`. [JSON evidence](october-market-2026-10-23.json)
contains ordinary command replies, database assertions and source/log fingerprints.
Final evidence comes from the main checkout. Preparatory-copy results are not
included. These are local automated checks with actual User/Account models and
Player permission; outbound transport is captured. No live socket, deployment
or hosted-CI success is claimed.

## Supported flow and safety evidence

| Criterion | Evidence |
| --- | --- |
| Ordinary listing and purchase | Actual `+market list`, browse, inspect, buy, mine and cancel use per-character wallets and canonical party/box assets. Exact-term inspection is required before buying. |
| Atomic payment and ownership | Faults after destination, wallet and final receipt writes restore the active listing, source claim, source owner and both balances. |
| One buyer and one charge | Independent connections race two buyers, buy/cancel, buy/expiry and two purchases against one buyer wallet. Exactly one legal outcome commits; wallets cannot overdraw. |
| Replay and reconnect | Sold receipts survive Attribute cache discard, later asset release and repeated purchase. No repeated debit/credit, transfer or resurrection. Inspection shows historical destination and each participant's own post-sale balance. |
| Character authority | Self-purchase, foreign assets and same-account alt cancellation are rejected. Internal purpose `market` transfer receipts cannot be inspected/accepted/cancelled through public trade commands. |
| Eligibility and expiry | Eggs, invalid prices, insufficient funds, changed asset state, new battles and wallet overflow are rejected. Owner status and expired purchase attempts reclaim exact claims once. |
| Existing wallet compatibility | Stale Trainer instances use current row-locked balances. Credits racing settlement preserve both changes; stale debit cannot spend an earlier balance. Ordinary shop and reward rollback suites remain passing. |
| Database guarantees | Deferred listing/claim/custody agreement, immutable prices/snapshots/terminal receipts and known transfer purposes are enforced. Active claim deletion and price/receipt tampering fail. |

## Final checks

- **387 cases pass across 17 PostgreSQL suites**, including
  **16 dedicated marketplace cases**, consent trades, ownership/Fusion, ordinary
  shop purchases, battle rewards/recovery, progression, field item routes,
  ordinary doubles, production gym and UI.
- **29 focused checks pass** for guide availability, item-store behavior and legacy trade safety.
- One fresh full combined suite: **4913 passed / 4014 skipped**, with
  callbacks enabled and ambient pytest options cleared. The final October battle
  integration retains the three-order mandatory gate; this record claims one run.
- Approved isolated fresh, pre-ownership upgrade, invalid-reservation rollout and
  invalid-market rollout/rollback rehearsals pass, with no Pokemon model drift.
- **1057 Python sources** remain fixed across the final full suite; the staged
  Git-filtered source digest is added before commit. `git diff --check` passes.

See the [marketplace contract](../operations/marketplace.md) for price/fee, expiry,
reservation and recovery rules. Listings support hatched Pokemon and existing
held state, with no EXP, healing or automatic evolution. Existing currency only;
no fee, item-only market, auction or plot-only content. Generic future subsystem
claims remain that subsystem's responsibility; integrity recovery never invents
payment, consent or ownership.

Existing model-reload/deprecation and Windows battle-log rotation warnings remain
diagnostic limits. No unrelated service or logging changes are bundled here.

The initial full run identified a command-set fixture missing the new market
command stub and a runner basetemp inside the directory that the live-pilot
safety test explicitly expects to reject. The fixture now checks market command
registration in both alpha-gate modes, and the runner uses a separate project
temp directory. No live-pilot production code was changed. The full suite is
rerun on the final source. Final review also identified numeric input longer than
Python's integer-conversion limit but within Evennia's 6,000-character allowance.
Prices and shared party/UUID selectors now have bounded parsing; two ordinary
5,000-digit command inputs are rejected without writes. Marketplace/trade routes
and the full suite are rerun after that correction. Unaffected wallet/item/battle
scenarios retain their earlier successful results; their data/mutation paths did
not change.
