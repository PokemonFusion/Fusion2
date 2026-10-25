# Permanent Supply Corner player acceptance (2026-10-25)

#862 is complete on deliberately released PF2-Dev candidate
**b13c43953451970cce68f2a47829e261ef9a7346**, under the explicitly approved
[replacement plan](item-source-retry-release-plan-2026-10-25.md). The permanent
six-item source remains installed after all tagged QA fixtures were removed.
This report adds released player evidence; it changes no gameplay code or source
policy and does not certify the broader catalog as stocked.

## Public route and dated stock

From Limbo, take `(A)lpha (H)ub` to **Alpha Test Hub #31**, then `supplies` to
**Item Supply Corner #105**. `back` returns to the hub; its `(E)xit` returns to
Limbo. These exits were traversed by ordinary Players. In the corner, use
`+store`, choose `1` (Buy items), enter the displayed full name and quantity,
then `back` and `q` before leaving the menu.

| Item | Price | Installed units | Remaining after acceptance |
| --- | ---: | ---: | ---: |
| Potion | 300 | 20 | 19 |
| Oran Berry | 80 | 20 | 19 |
| Fresh Water | 200 | 20 | 19 |
| Fire Stone | 3,000 | 5 | 4 |
| Leftovers | 4,000 | 2 | 1 |
| Smoke Ball | 4,000 | 2 | 1 |

The counter is **buy-only, finite and has no automatic refill**. Remaining
quantities are a dated observation, not a promise that later customers will find
stock. Reconnect and installer retry preserved the same room/exits and remaining
quantities. Cleanup retained the source and all six legitimate one-copy sales;
it did not refund wallets or replenish stock.

## Ordinary player evidence

Two fresh accounts completed self-service onboarding and retained only Player
permissions. **142 socket inputs /132 game commands** covered travel, menus,
refusals, purchases, capture, medicine, evolution, held effects and reconnect.
**71 evidence assertions**, including sixteen independent SQL observations,
verify responses, effects, conservation, protected-data preservation and cleanup.
The [machine receipt](item-source-released-player-2026-10-25.json) and
[QA-only command ledger](item-source-player-commands-2026-10-25.json) include
verified response fragments. Authentication, private identities and ambient
human output are omitted; original operational evidence remains private.

- A zero-wallet Player could not buy. Over-stock, zero, negative and malformed
  quantities were refused without changing either bag, wallet or source stock.
  The other Player bought exactly one of each public item and saw all six in
  `+inventory`. Public purchases totaled **11,580**. Separate purchased capture
  and revival prerequisites totaled **4,500**, leaving **3,920** from the labelled
  20,000 wallet. The SQL purchase observation was taken after both purchase
  groups; no intermediate 8,420 SQL balance is claimed.
- Both captured test Pokémon were obtained through ordinary `+hunt` and purchased
  `+item Master Ball` capture, with native species, moves and abilities. One
  separately approved operator prerequisite set only the currently owned,
  out-of-battle Mew's HP to zero. Ordinary purchased Revive restored **0→166/332**;
  `+use Potion=2`, `+use Oran Berry=2` and `+use Fresh Water=2` then restored
  **166→186→196→226/332**. Each useful action consumed one selected copy while
  preserving PP, ownership and other Pokémon fields. Revival is a labelled
  helper action, separate from the six-item public source.
- `+evolve <owned-Eevee-id> Fire Stone` produced
  **“SupplyEevee evolved into Flareon!”** and consumed one Fire Stone. The captured
  UUID, nickname, level, IVs, EVs, XP and ownership persisted; native ability
  changed from Run Away to Flash Fire. No evolution result was forced.
- `+hold 2=Leftovers`, a normal wild battle and `+attack Amnesia` produced the
  actual Leftovers message and useful **226→245/332** recovery despite the foe's
  Tackle. One real Amnesia PP was spent. The following ordinary flee turn also
  applied normal Leftovers recovery, ending at **265/332**. Unequipping returned
  the same reusable copy.
- `+hold 2=Smoke Ball`, an eligible wild battle and `+flee` ended the battle;
  unequipping returned one Smoke Ball and HP stayed **265/332**. The flee message
  is generic and does not name Smoke Ball. This released observation proves the
  equipped player route, escape, persistence and return; guarantee/suppression/
  restricted-battle controls are the separately qualified automated evidence.
- Reconnect preserved Pokémon, sparse party placements, PP, inventory, wallets
  and stock. All four battles ended normally and both reusable held copies returned
  before teardown. No item effect, battle result, native move or RNG was forced.

## Qualification, diagnosis and cleanup

The [source compatibility qualification](item-source-migration-compatibility-2026-10-25.md)
passed **6,188 tests /4,028 skipped in each of three fresh full orders**, plus
**28 isolated migration rehearsals** and **43 command/PostgreSQL acquisition
cases**. Concurrent last-copy purchases, conflicts and rollback were tested in
those disposable schemas, not induced in the shared world. No Python changed
after qualification; all **1,139** qualified source hashes matched the released
runtime before play and after final cleanup.

Original fixture failures are retained and diagnosed. An onboarding confirmation
arrived in the next read window; the completed onboarding receipt and ordinary
starter verified success without replaying creation. Smoke Ball expectations
incorrectly demanded an item-specific flee message and overlooked the preceding
Leftovers flee-turn recovery. Final logout expected different wording; both
clients actually received “Quitting. Hope to see you again, soon.” Read-only
observer/teardown preflights were corrected for actual primary keys and Evennia's
normal logged-out character relationships. These were fixture assumptions, not
reasons to change game mechanics or force results.

All original protected table columns and existing human Attributes/links remained
unchanged throughout the observations and final teardown. Only the two approved
QA accounts/characters, four QA-owned Pokémon, twelve private world objects and
their exclusive dependent data were removed. Clients and the owned tunnel exited.
Teardown ran while the approved instance was stopped so stale account caches
could not resurrect deleted fixtures. The same approved build then restarted;
independent checks verified actual process paths, five listeners, normal greeting,
enabled ordinary login, migration 0058, unchanged source stock and **zero tagged
QA residue**. Private backups remain retained.

Only the six named public offers gain this dated acquisition proof. Plot-only
items, unrelated work, further shops/families and existing human characters or
Pokémon were excluded. The twenty-five unrelated shared-worktree paths remain
unchanged. Earlier reports and source-only availability indices are historical
receipts and have not been rewritten.
