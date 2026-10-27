# Permanent six-item source release proposal (2026-10-25)

#862 is the only remaining original #852 child. This is a **reviewable proposal**;
no PF2-Dev file, database, source or service has been changed.

The deliberately released and qualified candidate is
**ddc56bfaf32261e47551ad893e0592fca3e86311**. [Local acceptance](item-repair-released-player-2026-10-25.md)
passed716ordinarycommands/102effectchecks with complete disposable cleanup.
Its1,135Python sources passed6,153tests/4,028skips in each of three fresh orders.
The existing32-case item-availability PostgreSQL suite independently covers
all six purchase/effect routes, rollback, last-copy concurrency and installer retry.
These are separate from the proposed permanent shared-world walkthrough.

[Exact controllers, hashes, target, approval template and QA terms](item-source-release-plan-2026-10-25.json).
The new upgrade wrapper was rehearsed only on a fresh task-owned loopback schema:
0045→0058 plus post_migrate rolled back as one transaction after a deliberate
failure, then the same chain committed successfully. Its schema was dropped and
the task cluster stopped. This empty predecessor-schema probe does not certify
existing PF2-Dev data; real migration guards must still pass without data repair.

## Refreshed target and selected stock

Read-only preflight found clean af0eca6e63924c9108c3adbce389cc875be4c702 at
Pokemon0045, no enabled item shops/non-capture dispensers, and the reviewed public
Alpha Test Hub#31 from Limbo#2 (exit38 and return39, recorded public locks).
The actual entry aliases must be read in the ordinary client before acceptance.
Backup tools are /usr/bin/pg_dump and /usr/bin/pg_restore; the126,262,295-byte
database had12,837,265,408free bytes. The machine proposal binds the observed
database identity hash rather than exposing credentials.

Install the existing ItemSupplyRoute once at hub31. It creates only its room,
supplies entrance, back exit and hub marker. Preserve these exact finite,
buy-only, no-refill offers:

| Item | Price | Initial units |
| --- | ---: | ---: |
| Potion | 300 | 20 |
| Oran Berry | 80 | 20 |
| Fresh Water | 200 | 20 |
| Fire Stone | 3000 | 5 |
| Leftovers | 4000 | 2 |
| Smoke Ball | 4000 | 2 |

Installer retry cannot duplicate objects, replace a source or refill sold stock.

## Proposed exact operational sequence

Use /home/evennia/testing/evenv/bin/python3 -B and the existing Evennia CLI.
The new task directory is /home/evennia/testing/.item-source-862-20261025,
mode0700; reviewed controller files, the actual explicit approval record and
private receipts/backups stay there. No project source edit outside the reviewed
Git fast-forward is included.

1. Refresh HEAD/clean state, database fingerprint/migration, hub/exits/markers,
   space and live sessions. Refuse drift, unknown source conflicts, non-QA active
   battles/ownership tasks or an occupied maintenance window. Record protected
   existing-user/Pokemon/placement/trainer baselines without publishing their data.
2. After actual human approval, run backup.py --backup-approved from the game
   directory. It writes a new mode0600 custom dump, verifies pg_dump exit0,
   pg_restore --list, nonzero files and SHA256; it never restores a database.
   Do not continue without its backup receipt.
3. In /home/evennia/testing/fusion2 run the exact existing-instance command
   /home/evennia/testing/evenv/bin/evennia stop, then verify only that instance
   stopped. No PostgreSQL, nginx or machine restart is included.
4. Run git fetch origin staging, verify the candidate is a descendant of af0,
   then git merge --ff-only ddc56bfaf32261e47551ad893e0592fca3e86311.
   Refuse a dirty checkout or another HEAD; do not reset/rebase unrelated work.
5. Run the reviewed atomic_upgrade.py --apply-approved from the game directory.
   It wraps the normal migrate pokemon 0058_necrozma_integrity command and
   post_migrate in one PostgreSQL transaction. This is the full0046–0058 chain,
   including ownership/market/daycare/breeding integrity; there is no automatic
   legacy repair. Verify0058 and no pending target migration.
6. While this game is stopped, run install.py --install-approved. It binds
   the exact candidate/database, requires the AMP listener closed, installs the
   six-offer recipe at the exact named hub, and proves protected data unchanged.
   Record exact object IDs, marker, stock and source fingerprints.
7. Prepare only the separately reviewed tagged private QA rooms/counter/source
   charts in the machine terms, with name-specific access for ItemSupplyDuskd7cb66, ItemSupplyDawnd7cb66.
   These temporary sources are separate from the permanent public counter.
   Start this exact game with /home/evennia/testing/evenv/bin/evennia start;
   verify its process/source attribution, listeners and migration before testing.
8. Create/onboard the two named accounts through ordinary clients, preserving
   Player permissions. Separately label20,000/0 fixture wallets and HP0 only on
   a genuinely captured, currently owned out-of-battle Mew. Give no Pokemon,
   move, item effect, evolution or held item. Helper capture/revival copies are
   purchased normally from the private finite helper counter.
9. Walk ordinary Limbo→Alpha Hub→supplies→back, menu/funds/stock/positive integer
   handling and purchase→inventory conservation. The primary QA player buys
   exactly one of each public offer and proves useful Potion/Oran/Fresh Water
   +use, native capturedEevee+FireStone +evolve, real Leftovers recovery and
   SmokeBall +hold/+flee. The zero-wallet secondary player proves funds refusal;
   over-stock/zero/negative quantities refuse without changing resources.
   Reconnect and run install.py --retry-approved to verify same IDs/stock.
10. End all QA battles normally, recover reusable equipment, verify protected
    data and purchase ledgers, then remove only the new tagged QA accounts,
    characters/Pokemon and private fixtures. **Keep the public counter/entry
    and legitimate finite sales. Do not refund or restock.** Expected public
    remaining stock after the six one-copy QA purchases is19/19/19/4/1/1,
    unless separately recorded ordinary purchases explain a lower value.
    Publish the actual released-source/normal-player/cleanup receipt, then
    close#862 and update#852. Broader catalog availability remains unverified.

## Failure handling and authority

If the upgrade wrapper fails, verify the whole chain returned to0045 and
protected data matches. Only with that verified rollback and a clean candidate
checkout may git switch --detach af0eca6e63924c9108c3adbce389cc875be4c702 restore
the prior source and the exact old Evennia instance start again. Retain the
backup/error receipt; do not repair human rows automatically.

After a committed0058 upgrade, do not downgrade or restore the full database.
Pause on unexpected state/startup failure for review. An unused newly created
source may be removed only if its exact marker/IDs/initial stock match and no
non-QA occupant or purchase exists. After purchases, retain the content or
disable its entry pending review; never delete purchased items or reset wallets,
world stock or an entire database.

The repository AGENTS.md explicitly says Never run migrations without asking
first and prohibits PF2-Dev source changes/restarts without explicit approval.
The previous local-dev authorization covers the isolated local work already
completed; it does not approve this new PF2-Dev candidate, upgrade or permanent
world installation. Approval of this exact plan is still required before any
of the proposed mutations. Plot-only/CAP/clutter expansion and unrelated work
remain excluded.
