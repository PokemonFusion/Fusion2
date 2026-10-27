# Receipt-preserving QA cleanup plan (October26, 2026)

**Proposal only; explicit approval required.** The previous approved logged-out
cleanup reached the game's immutable egg receipt trigger and rolled back.
Its approved refusal recovery restored healthy PF2-Dev on the same build:
**`4347e76b046d2c59bd8bcf1eabe3535ebeaa95a9`**, Pokemon0059, all1,188 source hashes, five listeners,
ordinary greeting/logins and protected original data/public sales. Four logged-out
QA accounts and25 owned Pokemon remain intact. Three approved maintenance cycles
have now been used; none of the eleven item issues has been closed early.

The item player checks, four actual nursery hours, real breeding/hatching waits
and all earlier effect observations remain passed. The remaining work is safe
teardown and final publication. No player command needs replaying.

## Exact replacement

Add only `cleanup_retained.py` to `/home/evennia/testing/.remaining-items-20261026-2259c9` with mode0600.
Keep every existing controller and approval file byte-identical. The new exact
UTF-8/LF SHA256 is **`03ac8a714785a0e191fa07dd36ee72d35e2f8dd59ac27fb5f279560247c66646`**. Its [complete source, thirteen-case receipt and
test/guard fixture sources](remaining-item-retained-cleanup-plan-2026-10-26.json)
are reviewable. Published approval is false until an actual new human response.

Retain the game's required sealed histories: **one closed breeding cycle, one
hatched egg receipt, one sold marketplace listing and four onboarding receipts**.
Never delete, rewrite or disable their seals. Deleting the exact QA-owned sources
and characters may clear only the existing nullable links listed below through
normal Django `SET_NULL` behavior. Historical UUIDs, origin IDs, trait plans,
genetics, payment terms, prices, receipts and timestamps remain unchanged.

| Receipt | Only permitted cleared fields |
| --- | --- |
| Closed breeding cycle | storage, parent_a, parent_b |
| Hatched egg | pokemon |
| Sold marketplace listing | seller, buyer, pokemon |
| Onboarding completion | character, pokemon |

Every old non-null link must point inside the exact QA deletion set; a foreign
link refuses. The collector must retain all seven rows. The complete row digest
normalizes only those explicitly listed links after verifying their old target
and requiring their final value to be NULL. **Every other field and row outside
the exact deletion set must stay identical.** Deferred constraints are forced
before success. Closed consent-transfer and native-operation rows may cascade
with their exact QA owners as previously reviewed; no external history is allowed.

All prior protections remain: exact names/IDs/tags/current SQL account state,
persistent roster ownership with no foreign roster reference, no privilege or
session, inactive consistent same-owner permanent forms only, no active native
pair/reservation/held item/battle/Daycare/breeding/market/ownership work, no
unfamiliar occupants, and exact collector/cascade checks. All pre-existing human
data, original source attributes, permanent markers and current finite sales stay
protected. No account or source field is rewritten to make a guard pass.

## Integrity-enabled isolated evidence

The earlier eight model-table cases missed the migration-installed receipt seals.
The new fixture uses **54 actual trigger definitions from the published repository
integrity SQL**, including placement, ownership, market, Daycare, breeding and
native pairs. It runs only in a new random schema on the task-owned loopback
PostgreSQL fixture. It uses no migration executor, live catalog export or game
database. Fixture functions are removed only after each isolated test; no live
trigger is removed or disabled. The cluster is stopped with no remaining test
schemas or public tables.

All **13 cases passed**: the previous controller reproduces the egg-seal refusal
and fully rolls back; market deletion and price rewrite refuse; exact cleanup
retains all seven receipts and every immutable field; missing/foreign/attached
account identity, foreign receipt links, unfamiliar occupants and foreign/active
forms refuse; ordinary unfuse permits its inactive owned form; injected partial
deletion and an unapproved retained-field edit roll back every row. The fixture
DDL SHA256 is `b7af33c5361a73823c8f57e30820ac3c590e1188a0d8c2bfa4242be69ea97d87`. This is integrity-enabled SQL evidence,
separate from the already completed released player walkthroughs.

## Exact commands after separate approval

Approval would authorize **one further guarded Evennia-only stop/start cycle**,
the fourth overall, on the same build/database. No migration, release, new stock,
refill, new account, source grant or player walkthrough is included.

1. Record the actual new response, candidate and new controller hash in private
   `retained-cleanup-approval.json`. Stage only the exact new controller. Original
   `atomic_upgrade.authorize()` validates the original build/database/plan and
   six old controllers; the new controller also validates its own approval/hash.
2. Before maintenance require exact build/clean checkout/0059/database identity,
   all1,188 hashes, private backup, original protected baselines, unchanged finite
   sales, four exact disconnected persistent rosters and no human sessions or
   active scripts/battles/open ownership work. Refuse drift without resetting it.
3. In `/home/evennia/testing/fusion2`, using the original reviewed virtualenv
   environment, run `/home/evennia/testing/evenv/bin/evennia stop`. Verify both
   exact processes ended and ports4000,4001,4002,4005,4006 are closed.
4. Run exactly:

   `/home/evennia/testing/evenv/bin/python3 -B /home/evennia/testing/.remaining-items-20261026-2259c9/cleanup_retained.py --cleanup-approved`

   Require its actual one-use cleanup receipt, exact four accounts/25 owned
   Pokemon/private-object removal, all seven retained audit rows, only the
   reviewed NULL links changed, identical normalized protected digests, no live
   tagged fixtures and unchanged permanent content/sales. Never invoke an old
   cleanup or disable a trigger as a fallback.
5. Run `/home/evennia/testing/evenv/bin/evennia start` once. Independently verify
   the same build/0059/all1,188 hashes/five listeners/ordinary greeting/logins,
   original data, public markers/stock, absence of live QA fixtures and preserved
   sealed audit receipts. Publish the final reports/index, commit/push and close
   only the satisfied eleven item issues and tracker#852.

If any cleanup guard refuses, the same approved cycle includes verifying full
rollback and restoring the unchanged candidate with that one `evennia start`,
then independently checking healthy service with QA retained. Keep the failure
evidence and stop for review. No fifth cycle, weakened seal, forged receipt,
automatic migration reversal, downgrade or database restore is authorized.

[AGENTS.md](../../AGENTS.md) says **"Do not restart Evennia, PostgreSQL, nginx, or
the server unless explicitly approved."** The previous approval pins a different
cleanup hash and its one cycle is used. This exact receipt-preserving replacement
and one further cycle therefore need approval. No sudo, PostgreSQL/nginx/host
restart, package, existing-human fixture, plot-only item or unrelated battle fix
is included. #918 stays separate and #915 remains untouched.
