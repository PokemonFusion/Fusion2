# Logged-out QA cleanup plan (2026-10-26)

**Proposal only; explicit approval is still required.** All eleven item player
routes, including the four actual nursery hours, have passed on PF2-Dev build
**`4347e76b046d2c59bd8bcf1eabe3535ebeaa95a9`** at Pokemon0059. The original two approved Evennia
stop/start cycles have been used. The second cleanup refused **before deletion**:
normal logout clears `ObjectDB.db_account_id`, while the approved Fusion cleanup
expected that transient attachment to remain. Its transaction rolled back.

The already approved second start restored the same game. Independent checks
passed all1,188 Python identities,0059, five listeners, ordinary greeting/logins
and protected original data. All four tagged QA accounts and25 owned Pokemon
remain intact. No cleanup receipt was forged, no account link was rewritten,
and no game code, migration, stock, refill or human fixture was changed.
The item issues remain open for final teardown/health and publication.

## Exact replacement and evidence

Keep all six original controllers and the prior Fusion controller byte-identical.
Add only `cleanup_logged_out.py` under `/home/evennia/testing/.remaining-items-20261026-2259c9`.
Its exact UTF-8/LF SHA256 is **`1e495f7c7d0d5c73b3b8a7c4fb1acbb13b71286007cabef4f401676fdffee10a`**. The
[complete controller and eight-case receipt](remaining-item-logout-cleanup-plan-2026-10-26.json)
also records the actual recovery checkpoint.

The replacement requires the exact receipted names, IDs and tags, no connected
account, and **no active account FK read directly from current SQL**. Only the
matching persistent `_playable_characters` roster containing exactly that one
QA character can establish ownership; a reference from any other account
refuses. Current connection and superuser state also come directly from SQL.
Missing, mismatched, foreign, attached or privileged identities refuse.
Do not attach, log in, elevate or rewrite a QA character to make cleanup pass.

All previous inactive-Fusion/owned placement, companion/reservation, held item,
closed Daycare/breeding/market/ownership, unfamiliar occupant, exact collector
deletion-set and **every-other-row digest** protections remain unchanged.
No active or foreign form is accepted. Permanent source markers, current finite
sales, original Oran/Razz/Supply Corner and all existing human data are protected.

Eight fresh disposable local PostgreSQL cases passed: exact disconnected cleanup;
missing roster refusal; foreign-account roster refusal; still-attached refusal;
unfamiliar occupant refusal; active Fusion refusal then ordinary unfuse/inactive
cleanup; foreign form refusal; and injected partial deletion with full rollback.
The first proposed replacement exposed stale FK identity caching; the final
controller uses fresh SQL and all eight pass. The failed cohort is retained.
These are model-table tests with no migrations or shared-game deletion. The
task-owned loopback cluster is stopped with zero disposable schemas/public tables.

## Commands after separate explicit approval

The approved scope would be **one additional guarded Evennia-only maintenance
cycle**, on the same build/database. No migration, source release, new stock,
refill, account creation, capture, walkthrough replay or clock change is needed.

1. Record the actual new human approval, exact candidate and controller hash in
   private `logout-cleanup-approval.json`; its published template remains false.
   Stage only the exact new controller with mode0600 in the existing mode0700
   task directory. Original approval files, controllers and game checkout remain
   unchanged. Original `atomic_upgrade.authorize()` and the new controller's
   own approved hash must both validate.
2. Verify exact candidate,0059/database identity, clean checkout, all1,188 hashes,
   private backup presence, protected original baselines, all four disconnected
   exact roster identities and no human sessions, active scripts/battles or open
   ownership work. Refuse before maintenance on any drift; never reset data.
3. In `/home/evennia/testing/fusion2`, with the original reviewed virtualenv
   environment, run `/home/evennia/testing/evenv/bin/evennia stop`. Verify the
   receipted processes have ended and ports4000,4001,4002,4005,4006 are all closed.
4. Run exactly:

   `/home/evennia/testing/evenv/bin/python3 -B /home/evennia/testing/.remaining-items-20261026-2259c9/cleanup_logged_out.py --cleanup-approved`

   Require the actual one-use `qa-cleanup-receipt.json`, identical protected
   before/after digest, no tagged accounts/objects/owned sources, and preserved
   permanent stock/sales. Never invoke either old cleanup as a fallback.
5. Run `/home/evennia/testing/evenv/bin/evennia start` once. Independently verify
   the same build,0059, all1,188 hashes, five listeners, ordinary greeting/logins,
   original data, exact public markers/quantities and no remaining QA fixtures.
   Update the released reports/index, commit/push, then close only the satisfied
   eleven item issues and tracker#852.

If a cleanup guard refuses, its transaction must roll back. This same approved
cycle includes restoring the unchanged candidate with that one `evennia start`
and independently verifying healthy service with QA retained; report the refusal
and stop for review. Never forge a cleanup receipt, weaken a guard, repeat a
partial mutation, add a fourth cycle, reverse0059, downgrade source or restore
the database automatically. Startup/data failures retain evidence for review.

[AGENTS.md](../../AGENTS.md) says **"Do not restart Evennia, PostgreSQL, nginx, or
the server unless explicitly approved."** The prior plans pin their controller
hashes and their two cycles are already used. This replacement hash and one
additional cycle therefore need explicit approval. No sudo, PostgreSQL/nginx/host
restart, packages, existing-human fixture, plot-only item or unrelated battle
repair is included. Separate battle#918 is filed; #915 remains untouched.
