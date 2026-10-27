# Gimmighoul Coin qualification (#777)

## Selected rule, recorded before implementation

PF2 adopts an explicit **manual coin evolution equivalent**: exact native
**Gimmighoul (Chest Form)**, saved level **2–100**, uses
`+evolve <full-owned-id> Gimmighoul Coin` outside battle. Exactly **999 bag coins**
and the species/ability/type transition commit together. An explicit target,
if supplied, must be Gholdengo. No recent-level flag, quest/key, room prose,
staff override or nickname qualifies. This replaces the timing of a fresh
level-up with the existing explicit player evolution command; it does not grant
EXP, a level, moves or a stat-training overlay.

The [official connection guide](https://www.pokemon.com/us/pokemon-news/connect-pokemon-go-to-pokemon-scarlet-and-pokemon-violet)
describes 999 coins and a level-up for Scarlet/Violet Chest Gimmighoul, and a
separate Roaming evolution in GO. PF2 selects the Chest route and documents its
manual timing/minimum-level adaptation. **Gimmighoul-Roaming is deferred**;
its existence in local metadata does not enable the GO route or a form change.
No generated dex condition is edited to imply new behavior.

Gimmighoul Coin is a supplemental non-plot evolution collectible with full
normalized name, Evolution Items category and selected PF2 reference price 10
per coin. A deliberate optional Coin Counter may stock 999 units at that price,
finite stock/no automatic refill, using existing normal `+store` quantity input.
This is a reference acquisition recipe, not a grant or live stocking operation.
No capture, crafting, TM-material, held-combat or quest role is added.

## Ordinary flow and boundaries

At an explicitly configured source, use `+store`, Buy, then
`Gimmighoul Coin 999`. Inspect `+inventory`, `+itemdex Gimmighoul Coin` and
`+party 3`, then copy the complete ID into the evolution command. Use `+party 3`
again and reconnect to inspect Gholdengo and the remaining inventory. Buying
coins alone or equipping one does not activate evolution. `+use` is not a new
coin spender. A held coin is independent and never counted toward the 999.

The shared evolution service checks fresh owner, canonical placement, eggs,
reservations and battle locks. Require exact native Chest source and reviewed
Gholdengo dex metadata; reject transformed/suffixed/foreign species, nickname
spoofs, wrong targets, source/form drift and invalid native ability. Everstone
still blocks. Preserve identity, owner/placement, nickname, ordinary held item,
EXP/level, friendship, HP/status/sleep, genetics/Hyper Training, moves and PP.
Rattled's ordinary ability slot becomes **Good as Gold** and derived types become
Steel/Ghost through the existing transition writer.

Quantities 0/998 fail unchanged; 999 spends all; 1,000 leaves one. A failed or
partial 999-coin debit, post-transition save or outer transaction rolls the
entire result back. Completion receipts and locked current native species make
retries/competing requests idempotent; one bag of 999 cannot fund two targets.
Fresh SQL/cache reads must agree after success and failure. Arbitrary flags,
client coin counts and held-only copies cannot replace real trainer inventory.

Acceptance requires actual ordinary purchase/inventory/discovery/evolve/SQL
reload, level/form/owner/target/Everstone/stock negatives, rollback and genuine
contention. It remains local automated evidence until a separately released
build is walked in #782. No running-world stock, character, schema or service
changes are part of this implementation.
