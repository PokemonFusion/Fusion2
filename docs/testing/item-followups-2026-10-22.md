# Item follow-up closeout (#777–#781 and #813)

October 22, 2026. Source baseline: `335a3927761d4e2d79276879ae9fa8b47a88d5cc`. This is local
automated ordinary-command/session/SQL acceptance on a disposable database.
It does not certify live availability, hosted CI, main merge or deployment.

| Issue | Implemented bounded behavior | New PostgreSQL cases |
| --- | --- | --- |
| #777 | [Chest Gimmighoul coin equivalent](../gimmighoul-evolution.md): level 2–100, exactly 999 real bag coins, native/target guards, ability/types, atomic transition/receipt and retry/contention | 12 |
| #778 | [Rage Candy Bar/Hopo Berry](../recovery-equivalents.md): major-status cure / explicit selected active move +10 PP with boosted caps; shared field checks; field-only | 8 |
| #779 | [Potion finder](../hunt-item-sources.md): named opt-in room source, actual inventory credit, persistent attempt/cooldown, replay/partial-write/contention controls | 7 |
| #780 | [Wild Rattata/Oran source](../hunt-item-sources.md): explicit chance/default empty/noitem policy, persistent runtime/encounter/capture, no eaten/removed-item resurrection | 8 |
| #781 | [Supply Corner](../item-supply-route.md): six finite buy-only offers, ordinary exit/menu/effect routes, atomic/duplicate-safe install, no restock on retry | 11 |
| #813 | Atomic ordinary shop purchase: fresh stock/wallet/bag, post-credit/stock/debit/outer rollback and competing buyer/funds controls | 8 |

No plot-only/key/quest/story route, new capture mechanic, bulk wild catalog,
live stock or existing human character was changed. Coin timing is an explicit
PF2 manual equivalent; Roaming remains deferred. Hopo has no new held/lure
effect; both new recovery items reject manual battle input before an action.

## Evidence

- **54 new regressions / 810 total PostgreSQL checks passed**: 804 cases in 30
  independent guarded suites, plus six extra supply inventory walkthroughs.
  Regressions include existing field medicine/berries/foods, PP capacity, Rare
  Candy/training/ability/Hyper Training, Alcremie/trade-held/Peat/Crest/Kubfu
  evolution, battle items/recovery, capture/checkpoints, UI/doubles and incense.
- **1,062 focused tests passed** on the final audit/offline fixture tree.
- **Three mandatory fresh-process orders passed: 4,770 passed / 4,014 skipped each.**
  Exact command arrays, durations/log hashes and phase boundaries are in the
  [JSON receipt](item-followups-2026-10-22.json).

Every new source has a recorded purchase/hunt-to-inventory-to-use/equip/evolve
flow, independent SQL and reconnect/checkpoint checks. Source/target/wallet/stock
and correct one-copy or 999-copy consumption are explicit. Setup of tagged
owners, damaged targets, wallets, shops and capture balls is separate fixture
evidence; no bag grant is counted as source acquisition. Supply traversal uses
the real Exit command and SQL relocation with a transport adapter that disables
movement hooks; live movement and released runtime remain unaccepted in #782.

All six supply flows were additionally replayed with explicit ordinary
`+inventory` after purchase and before their unchanged useful effect. The
additional harness adds only that UI observation, substitutes no item effect,
and retains its exact source/transcripts in JSON. Runtime/test sources stayed
unchanged; this closes the player-visible inventory observation gap.

The shop baseline reproduced wallet 200000→200000, stock 1→1, bag 0→1 after a
post-credit fault. #813 replaces compensation with one transaction and keeps
legacy sales separate; the new source is buy-only. Evolution success/cache
publication also now follows the outermost commit, with a real parent-rollback
case proving that no temporary Gholdengo or success notice escapes.

## Qualification and historical boundaries

The first mandatory run exposed four offline parser fixtures calling the new
commit callback against an intentionally blocked offline database. Their entire
evolution service was mocked; the fixture now supplies the matching immediate
callback boundary. Production rollback assertions were not relaxed. One interim
qualification was stopped for audit reconciliation. Only the final three orders
are accepted; the initial failure is retained in JSON.

All production runtime sources are identical to those used by the 804 PostgreSQL
cases. Only the offline command fixture, audit fixture and audit generator changed
after that phase; their exact list is retained. The final 1,000-file Python tree
stayed frozen through focused/mandatory qualification. Historical #757/#772/#773
and #783 reports remain unchanged. Private schemas/public tables are absent and
the task-local PostgreSQL cluster is stopped; no migration runner was used.

The [fresh per-item index](item-followup-index-2026-10-22.json) accounts for 600
definitions / 454 scoped entries. It records the three new definitions and
conditional sources without inferring installed/live stock; all 454 availability
states remain unverified. Mega/Z/growing plans are unchanged, and metadata or
historical held proof is not relabeled as a fresh live replay.

## Remaining released acceptance (#782)

Read-only PF2-Dev checks find clean `b7637cb`, process startup October 16 and
recorded migration 0044; pre-existing staging gym migration 0045 is absent.
No release, migration, reload or live player batch was performed. The
[release/walkthrough plan](item-release-plan-2026-10-22.md) records this separate
approval/target dependency, exact operational command shape, deliberately
authored sources and fixture cleanup. #782 remains open until that evidence exists.
