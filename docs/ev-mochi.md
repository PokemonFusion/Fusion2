# EV mochi

Use one owned bag copy outside battle with `+use <full item name>=<current
party slot, unique name, full ID or fusion>`. `+inventory` lists your copies;
`+itemdex <name>` describes them. Mochi have no held or manual `+item` effect.

| Item | Useful effect |
| --- | --- |
| Health Mochi | HP EVs, up to +10 |
| Muscle Mochi | Attack EVs, up to +10 |
| Resist Mochi | Defense EVs, up to +10 |
| Genius Mochi | Special Attack EVs, up to +10 |
| Clever Mochi | Special Defense EVs, up to +10 |
| Swift Mochi | Speed EVs, up to +10 |
| Fresh-Start Mochi | Reset all six valid EVs to zero together |

Supplements share vitamin limits: 252 per stat and 510 total. A copy adds only
the useful remaining room. A capped supplement or all-zero reset consumes
nothing. Malformed saved EVs require investigation; feeding does not repair them.
Eggs, boxes, foreign/stale/ambiguous targets, inactive Fusion, battle locks and
reserved companions cannot use a copy. There is no move or stat selector.

Training preserves genetic Nature, IVs, Hyper Training, ability, status,
friendship, progression, moves/PP and held items. Calculated HP preserves its
absolute deficit, with a conscious minimum of one HP and fainted HP remaining
zero. One atomic operation contains the debit, whole EV vector and HP/stat
update. Success and shared cache updates wait for the outer transaction commit.

Both native Necrozma hosts can use ordinary training while their companions
stay frozen. Training does not unlock a temporary move slot, refill its source
PP or spend a companion's resources. Separation retains the current host's
training and the companion's original state.

The optional `world/ev_mochi_counter.json` offers supplements at 10,000 each,
two copies each, and Fresh-Start at 20,000, one copy. Its `mochi`/`back` route
is finite, buy-only and no-refill. An operator must separately review/approve
installation before calling `ItemCounter("world/ev_mochi_counter.json").install(hub)`.
The recipe does not establish current-game availability.

The [dated evidence](testing/ev-mochi-2026-10-25.md) separates production
commands/SQL, later battles, native host controls and full offline qualification
from deployment or permanent stock. Plot-only items are excluded.
