# Link Cord trade-only evolutions (#939)

An ordinary owner uses `+evolve <pokemon-id> Link Cord` outside battle. One
successful evolution consumes exactly one Link Cord from trainer inventory and
retains ownership, identity and party/box placement. A held-only copy cannot
activate this route. An optional `=<exact target>` must match the current source.

## Exact supported mappings

| Source | Target |
| --- | --- |
| Kadabra | Alakazam |
| Machoke | Machamp |
| Graveler | Golem |
| Graveler-Alola | Golem-Alola |
| Haunter | Gengar |
| Boldore | Gigalith |
| Gurdurr | Conkeldurr |
| Phantump | Trevenant |
| Pumpkaboo | Gourgeist |
| Pumpkaboo-Small | Gourgeist-Small |
| Pumpkaboo-Large | Gourgeist-Large |
| Pumpkaboo-Super | Gourgeist-Super |
| Karrablast | Escavalier |
| Shelmet | Accelgor |

These are 14 exact native source/target pairs. Alolan form and Pumpkaboo size
are preserved; the unsuffixed Pumpkaboo and Gourgeist are Average Size. A room
in Alola is not required to evolve an already Alolan Graveler. Ordinary
Graveler cannot select Alolan Golem, nor can Pumpkaboo select another size.

Karrablast and Shelmet each evolve independently, without owning, supplying or
having the other species in the party. One use evolves only the selected
Pokemon; evolving both takes two uses and two cords. This deliberately replaces
the main-series paired-trade requirement with PF2's bag-item equivalent.

Existing [trade-held item equivalents](trade-held-evolution.md) are unchanged:
their own held item is consumed through `+hold` then `+evolve`, without any
additional Link Cord. A cord cannot replace Metal Coat, King's Rock or another
required trade-held item. Ordinary consent trading still does not trigger
automatic evolution. Unlisted pairs, including CAP/fan species, remain closed.

## Player flow and item availability

```text
+inventory
+itemdex Link Cord
+party 3
+evolve <full ID copied from +party 3> Link Cord
+party 3
```

The item has complete normalized name lookup, an Evolution Items category and
a reference price of 10000, matching PF2's other supplemental single-use
evolution items. The optional `world/link_cord_counter.json` authors a finite
buy-only counter: 10,000 each, 20 initial cords, `linkcord` entrance and `back`
return. Explicit installation requires a selected hub; retry never refills sold
stock. No shared-world shop, reward or encounter table is changed here. The supported bag action is `+evolve`; `+use` and merely
holding the cord do not activate it. If a held cord and a bag cord both exist,
only the bag copy is consumed and the held copy remains.

## Integrity and verification

`LinkCordEvolution` in `pokemon/evolution_items.py` owns the exact allowlist,
reviewed form metadata and replacement trade conditions. Both the source's
successors and the target's predecessor must match. Unknown conditions or forms
fail closed. Stored levels must be integers from 1 through 100, and any dex
level/gender/region restrictions still apply. Everstone, egg, battle, ownership,
placement and reservation checks remain in the shared evolution path.

`EvolutionService` atomically debits one bag copy and saves the existing Pokemon
under its storage/trainer/Pokemon locks and retry receipt. Failed saves roll
back species, inventory and cached state. Repeated/competing requests cannot
consume an extra copy. Ability slots and types follow the target; nickname,
held item, HP/status, EXP, IVs/EVs, moves/PP and placement retain the existing
evolution policy. No schema change, migration or automatic trade hook is added.

- `tests/test_link_cord_evolution.py` covers the complete dex allowlist, exact
  form/size selection, independent paired-species equivalents and rule guards.
- `tests/integration/link_cord_cases.py` uses an explicit disposable PostgreSQL
  DSN for ordinary commands, all 14 mappings, bag consumption, persisted state,
  stale data, reservations, rollback and concurrent last-copy requests.
- `tools/run_mandatory_tests.py` runs the repository suites in three fresh
  processes, including reversed suite order.

Automated command transport and disposable database tests are separate from a
logged-in live walkthrough, hosted CI, merge and deployment.

Local results and the Emergency Exit fixture repair are recorded in the
[October 29 commit verification](testing/link-cord-2026-10-29.md), with the
original PostgreSQL evidence retained in the linked October 28 report.
The later [remaining-item receipt](testing/remaining-item-delivery-2026-10-29.md)
records finite-source purchase, all 14 exact evolutions and reconnect through
actual ordinary sockets in a task-owned private game. It does not establish
existing-world installation or deployment.
