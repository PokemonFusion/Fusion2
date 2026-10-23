# Using Venusaurite in battle

Native **Venusaur holding Venusaurite** is the first accepted player Mega pair.
Use `+mega` before a normal move in existing Wild, Trainer or PvP singles/doubles.
There is one reusable activation per team per battle. Opposing teams have
independent uses; two active Pokemon on your team share yours.

1. At an explicitly configured Mega Stone Counter, use `+store` → **Buy items**
   → `Venusaurite 1`. The optional recipe charges **10,000** and starts with
   **one** copy, with no automatic refill or resale. Its `megastones`/`back`
   exits connect to the operator's selected public hub.
2. Check `+inventory`, then equip the native holder outside battle, for example
   `+hold 3=Venusaurite`. A bag copy does not qualify.
3. Enter a normal battle with that Venusaur active. Use `+mega` in singles or
   specify your doubles actor, for example `+mega A2` or `+mega B1`.
4. Choose its ordinary move with `+attack`, specifying actor/target when needed.
   For example, `+attack A2 Tackle B1`. Mega changes form before attacks are
   ordered; it adds no separate action or item debit.
5. Before queuing an action, `+mega [actor] cancel` releases that reservation.
   An identical reservation is idempotent. Invalid input keeps it; a legal
   switch, item or flee choice for that actor cancels it. Queued actions retain
   the ordinary no-overwrite rule. Doubles flee uses `+flee <acting slot>`.
6. After battle, `+hold 3=` returns the same uneaten stone to the bag.

The battle display retains the normal name/nickname and shows the Mega form,
your pending reservation and spent side uses. Mega stats use the battle's
effective level, genetics, EVs, nature, Hyper Training and configured Fusion
stat overlay. It grants no HP, PP, moves, permanent evolution or progression.
Thick Fat reduces actual Fire/Ice offense; ordinary ability suppression and
Mold Breaker still apply. Magic Room, Embargo, Klutz or generic held-effect
suppression do not remove an actually owned matching stone's eligibility.

The form and spent use survive switching, fainting, revival and checkpoint
rebuilds. Ending restores ordinary runtime identity and keeps genuine battle
HP/status/PP; saved species, native ability, nickname, genetics, placement and
the reusable stone remain ordinary. A new battle starts with a fresh budget.

Current owned party and current Fusion holders qualify. Eggs, boxes, inactive
Fusion reservations, foreign owners, copied/Transform species, wrong stones,
bag-only stock and unsupported formats do not. Fresh persistent ownership or
held-state conflicts stop the whole turn for recovery, without granting a copy.
Mega and Tera have separate team budgets on different eligible allies; the same
actor cannot stack them, and the existing held-Mega-Stone Tera exclusion remains.

Other stones, Rayquaza's required-move route, CAP, NPC Mega AI and four-human
multi-battles remain deferred in this first slice. No Ring, Key Stone, quest,
tower or story unlock is required. `+use`, `+item` and `+evolve` do not activate
a Mega Stone.

The [acceptance report](testing/mega-core-2026-10-23.md) distinguishes automated
production-command/SQL/effect checks from live login, deployment and public
availability. The optional `world/mega_stone_counter.json` is installed only
through `ItemCounter(...).install(reviewed_hub)`; it does not populate the world
or change the six-item Supply Corner. The earlier #782 live release did not
include this later feature.
