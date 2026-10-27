# Replacement Supply Corner release proposal (2026-10-25)

This is a new reviewable proposal for #862, not an executed release. The earlier
[plan](item-source-release-plan-2026-10-25.md) approves a different source build.
The replacement candidate is **b13c43953451970cce68f2a47829e261ef9a7346**. No new candidate will be deployed
without explicit approval of this plan.

The candidate includes the three shared ObjectDB dependency corrections,
previously published thirteen flavor snacks and six Special Z source mappings.
It adds no other world offer or acquisition policy. Its **1,139 Python sources**
passed **6,188 tests /4,028 skipped** in each of three fresh full orders, plus
28 isolated migration rehearsals and 43 acquisition command/SQL cases. The
[compatibility receipt](item-source-migration-compatibility-2026-10-25.md) records
their scope and retained fixture diagnosis. Prior released local walkthroughs
remain separate evidence, not acceptance of this replacement on a shared game.

## Exact unchanged source

Start only from clean `af0eca6e63924c9108c3adbce389cc875be4c702` in
`/home/evennia/testing/fusion2`, at Pokémon 0045. Refuse different source, database,
occupancy, markers or conflicting stock. Use the reviewed public Alpha Test
Hub #31, ordinary Limbo #2 entry/return exits #38/#39, and the existing recipe.

| Item | Price | Initial finite units |
| --- | ---: | ---: |
| Potion | 300 | 20 |
| Oran Berry | 80 | 20 |
| Fresh Water | 200 | 20 |
| Fire Stone | 3000 | 5 |
| Leftovers | 4000 | 2 |
| Smoke Ball | 4000 | 2 |

Supply Corner is permanent, buy-only and has no automatic refill. `supplies`
enters from hub31 and `back` returns. Retry must preserve IDs and remaining stock.
[Exact target, stock, controller sources/hashes and QA terms](item-source-retry-release-plan-2026-10-25.json).
The three controller functions are unchanged from the original reviewed plan;
only their candidate and new private task-directory constants differ.

## Exact operation sequence after approval

Use a new mode0700 private directory `/home/evennia/testing/.item-source-862-retry-20261025`. Preserve the earlier private
receipts/backups. Place the exact reviewed controllers and the actual approval
record there. In the game directory, prepend
`/home/evennia/testing/evenv/bin` to PATH for both Evennia commands below, so the
launcher resolves its own `twistd` executable. No package installation is included.

1. Refresh clean HEAD, fingerprinted database/Pokémon0045, free space, hub/exits,
   source markers and all active players/battles/ownership work. Require an empty
   maintenance window and ordinary Player registration/login policy. Validate
   the common ObjectDB0013 file and candidate
   dependencies against actual installed files. Record a private existing-account
   and Pokémon/trainer/placement/move/inventory baseline, including original
   columns/row IDs. Do not publish private records or credentials.
2. Run `backup.py --backup-approved` using
   `/home/evennia/testing/evenv/bin/python3 -B`. Require a new mode0600 custom
   dump, successful pg_dump, pg_restore --list, nonempty TOC and SHA receipt.
3. Run `/home/evennia/testing/evenv/bin/evennia stop` with the PATH prefix above.
   Verify only that exact instance stopped and its listeners closed. Compare
   the private baseline again; refuse unexplained added/deleted/changed existing
   rows without editing them. No other service is stopped.
4. Run `git fetch origin staging`, verify ancestry, then exactly
   `git merge --ff-only b13c43953451970cce68f2a47829e261ef9a7346`. Require that exact clean HEAD. Construct
   the actual Django migration graph before attempting the upgrade.
5. Run `atomic_upgrade.py --apply-approved` with the exact Python above. This
   applies the full Pokémon0046–0058 chain and post_migrate in one transaction.
   Require0058 and no pending target migration. Compare original protected
   columns and separately check intended new null/default columns. No legacy
   repair, migration fake or framework-package file edit is allowed.
6. While AMP is closed, run `install.py --install-approved`. Record source IDs,
   marker, six-offer stock and protected-data equality. Prepare only the named
   tagged private QA fixtures below, with name-specific access locks.
7. Run `/home/evennia/testing/evenv/bin/evennia start` with the same PATH prefix.
   Independently require correct process paths/candidate, Pokémon0058, ports
   4000/4001/4002/4005/4006 and an ordinary-client greeting. Launcher exit zero
   alone is insufficient. Do not restart PostgreSQL, nginx or the host.
8. Onboard both ordinary named Players through clients. Label only their
   20,000/0 fixture wallets and the approved captured-owned-Mew HP0 prerequisite.
   Walk Limbo→Alpha Hub→supplies→back. Test menu discovery, zero-wallet refusal,
   over-stock/zero/negative quantities and purchase→inventory/wallet/stock.
9. Buy exactly one public copy each. Prove useful Potion/Oran/FreshWater +use,
   native captured Eevee/FireStone +evolve, Leftovers +hold/battle recovery and
   SmokeBall +hold/+flee. Use normal source capture/learning/party routes, with
   operator prerequisites and ordinary inputs recorded separately. Reconnect;
   run `install.py --retry-approved` and require unchanged IDs/remaining stock.
10. End battles normally and recover reusable held copies. Compare protected
    existing data and exact purchase ledgers. Remove only this newly tagged QA
    setup. Keep permanent public source and legitimate sales: expected remaining
    stock19/19/19/4/1/1 after six one-copy QA purchases, adjusted only for separately
    evidenced ordinary sales. Never refund/reset wallets or refill stock. Publish
    only approved nonprivate acceptance evidence; close#862/update#852 after success.

## Separate tagged ordinary QA

Reuse the exact two as-yet-unused planned names ItemSupplyDuskd7cb66 and
ItemSupplyDawnd7cb66, tag `item-source-862-4b17eea80a4a443dbdb091253ed7cb66`. They retain Player permissions
and are never elevated. Temporary Center/helper counter stock is MasterBall1000×4
and Revive1500×2, with private Mew100/Eevee5/Magikarp5 charts. Traverse locks permit
only those exact names. No human source/character/Pokémon is a fixture.

All Pokémon, moves and items must be obtained through ordinary capture, native
learning and purchases. The only labelled status prerequisite is HP0 on a newly
captured, currently owned, out-of-battle Mew, followed by ordinary purchased
Revive. No item effect, evolution, battle result or RNG is forced. Clean only
the exact new tagged accounts/characters/Pokémon/private objects. Public source
and legitimate finite sales remain; private backups are retained.

## Failure handling and authority

If graph/upgrade fails, prove Pokémon0045, no partial chain and preserved existing
data. Only then may clean source return with
`git switch --detach af0eca6e63924c9108c3adbce389cc875be4c702` and the same exact prior Evennia start,
including virtualenv PATH and independent listeners/process verification.
Do not repair/delete unexpected rows. Retain private error and backup receipts.
After a committed0058 upgrade, never downgrade or automatically restore the dump.
Pause on unexpected data/startup state. After purchases, retain content or disable
its entry for review; do not remove human-purchased items, reset money or replenish
stock. The separately approved tagged QA teardown remains limited to its own rows.
An unused source can be removed only under the original exact-ID/marker/stock,
no-human-occupant/no-sale rollback conditions.

AGENTS.md says **"Never run migrations without asking first"** and
**"Do not restart Evennia, PostgreSQL, nginx, or the server unless explicitly
approved."** The earlier approval names another candidate; this replacement
requires its own explicit approval. It includes no sudo, package upgrade,
database-wide restore, unrelated feature, plot-only item or additional shop stock.
