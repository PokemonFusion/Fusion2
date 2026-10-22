# Field items

Use `+use <item>=<target>` outside battle. Medicine and berry feeding share the
same transaction, fresh ownership/placement checks and canonical target rules.
Targets are party slots 1-6 (with gaps preserved), unambiguous names, full
Pokemon UUIDs, or `fusion`/`self`/`me` for the current reserved Fusion. Eggs,
boxed Pokemon, foreign owners and inactive Fusion reservations are ineligible.
An effective use consumes one item; invalid or ineffective uses consume none.

## Rare Candy

`+use Rare Candy=3` raises the eligible target by one level, up to level 100.
The same canonical slots, unambiguous names, full UUIDs and current-Fusion
aliases apply. For example, use `+use Rare Candy=<full Pokemon ID>` or
`+use Rare Candy=fusion`; the older `+use 3=Rare Candy` order also works.
Eggs, boxes, foreign owners and inactive Fusion reservations cannot use it.

One bag debit, the next-level EXP threshold, saved level and level-up learning
commit together. Failed debit/write/learning attempts consume nothing and grant
no level or moves. Inconsistent saved level/EXP is rejected for staff review;
level 100 is a free no-op. A fresh intentional second use can buy another level,
while competing commands cannot both spend the same final copy. HP, status,
friendship, held items and unrelated progression are preserved. Learning retains
the normal free-slot/stored-move behavior; replacement prompts open only after
commit.

## PP Up and PP Max

Start with `+use PP Up=3` or `+use PP Max=fusion`, then choose a move using
`+use <exact displayed move slot or full move name>`. Active slots retain gaps:
if the prompt lists 1 and 3, `+use 3` selects 3 and `+use 2` is invalid. Move
names ignore punctuation, spaces and case, but ambiguous names are rejected.
Use `+use cancel` to cancel; another `+use <item>=<target>` starts a fresh use.

Each PP Up advances one of three stages, adding a cumulative fifth of base PP
per stage, rounded down with integer arithmetic. PP Max fills the remaining
boost to three stages. Tackle's base 35 becomes 42, 49, then 56; PP Max reaches
56 from any legal stage. Current PP increases by the capacity difference and
retains already-spent PP. NULL current PP retains the existing full-capacity
initialization convention. Base PP below 5 and dex `noPPBoosts` moves (Sketch,
Revival Blessing, Struggle and Trump Card) cannot use either item.

Prompts contain stable Pokemon, placement, move-row and boost identities.
Confirmation rechecks ownership, party/current Fusion, egg state, battle guard,
active move identities, boost state and actual inventory under the shared field
locks. Target/move/boost changes require a fresh prompt. Inventory, raw bonus PP
and affected active current PP commit together. A failed debit/save consumes
nothing; successful prompts cannot be replayed even with more stock. Inventory
cache updates and success messages follow commit.

### Saved bonus compatibility

`MovePPBoost.bonus_pp` continues to mean raw extra PP throughout battle, field
restoration and move management. Existing values are never bulk multiplied or
silently rewritten. A 25-PP move with raw bonus 15 still has 40 PP. Legal stages
can use PP Up normally. An in-range but nonstandard saved bonus (for example
Tackle +1 or +3) cannot reveal how many old items were spent: PP Up rejects it
without cost, while one explicit PP Max fills the remaining capacity to +21.
Already-maxed, out-of-range and unboostable rows are left unchanged; invalid
rows need staff investigation. There is no automatic refund or migration.

The [PP-capacity acceptance report](testing/pp-capacity-2026-10-22.md) records
the source/disposable-fixture audit and SQL reload evidence. No existing human
or game database was queried or modified for legacy recovery.

## Healing food, drinks and revival equivalents

The [14-item effect/price and acquisition table](field-food-medicine.md) adds
Fresh Water (30 HP), Soda Pop (50), Lemonade (70), Moomoo Milk (100), Sweet Heart
(20), seven major-status foods, and two revival equivalents to the same field
medicine service. For example, use `+use Fresh Water=3` or `+use Max Honey=6`.
Max Honey revives one eligible fainted target to full HP. `+use Sacred Ash=party`
revives eligible fainted canonical party members with one item; living members,
eggs, boxes and all Fusion reservations are untouched. These equivalents are
field-only, accept no move selector, and add no story/Max Soup/Gigantamax unlock.
They are opt-in existing shop/reward stock; no live shop or automatic grant is
created. Inventory and itemdex show full names, descriptions and metadata.

## Existing berry feeding allowlist

| Items | Field effect |
| --- | --- |
| Oran Berry | Restore up to 10 HP |
| Sitrus Berry | Restore up to 1/4 maximum HP, rounded down |
| Figy, Wiki, Mago, Aguav, Iapapa Berry | Restore up to 1/3 maximum HP, rounded down |
| Berry Juice | Restore up to 20 HP |
| Cheri Berry | Cure paralysis |
| Chesto Berry | Cure sleep, including its saved remaining turns |
| Pecha Berry | Cure poison or toxic poison |
| Rawst Berry | Cure burn |
| Aspear Berry | Cure freeze |
| Lum Berry | Cure any of those major persistent conditions |
| Leppa Berry | Restore up to 10 PP to one current active move |
| Pomeg, Kelpsy, Qualot, Hondew, Grepa, Tamato Berry | Reduce the corresponding EV and increase friendship as below |

HP recovery requires a living, injured target and is capped at its calculated
maximum HP. Manual feeding can be used above the automatic held activation
threshold. Status cures require the matching saved condition on a living target.
Leppa requires a living target with a depleted active move. Use
`+use Leppa Berry=3/Water Gun` or `+use Leppa Berry=3/4`: move numbers retain
canonical active-slot gaps. Without `/move`, restore the first depleted active
move. Stored PP boosts and current dex data determine its cap; other moves are
untouched. Examples: `+use Oran Berry=3`, `+use Lum Berry=fusion`.

The five flavor recovery berries have a concrete HP effect in this allowlist.
Their nature-based confusion is a combat-only volatile and is not introduced or
persisted by field feeding. Lum's field use cures persistent status, not a
nonexistent out-of-battle confusion state. The existing held effects retain
their normal thresholds, nature/confusion rules, triggers and consumption.

## EV berries

| Berry | Stored EV index | Stat |
| --- | --- | --- |
| Pomeg | 0 | HP |
| Kelpsy | 1 | Attack |
| Qualot | 2 | Defense |
| Hondew | 3 | Special Attack |
| Grepa | 4 | Special Defense |
| Tamato | 5 | Speed |

The PF2 field policy removes `min(10, current EV)` from the selected stat and
adds friendship based on its value before feeding: +10 below 100, +5 from
100-199, or +2 from 200-254. Friendship is capped at 255. Either useful effect
permits feeding: zero EVs can still gain friendship, and maximum friendship can
still permit an EV reduction. At zero selected EVs and 255 friendship, the use
has no effect or cost. No additional location, held-item or luxury-ball bonus is
applied by this policy.

EV arrays retain project limits (six values, 0-252 each, total at most 510).
Invalid saved EV or friendship rows are rejected for staff review without
spending an item. Project stat helpers recalculate the affected stats. When HP
EVs fall, current HP changes by the maximum-HP difference to preserve missing
HP; a living target stays at least at 1 HP, and a fainted target stays at 0.
EV berries can be fed to fainted eligible members and never revive or cure them.
HP/status/PP, EVs, friendship and inventory remain durable and atomic; a failed
write rolls back the debit, and waiting uses recheck fresh saved values.

## Limits

This is an explicit 21-item field allowlist (20 berries and Berry Juice), not
generic support for every `isBerry` entry. Persim/Bitter (confusion-only), Enigma
(damage-triggered), resist, stat-boost, accuracy, retaliation and other combat
berries remain held-only. Contest/flavor-only berries such as Razz and Bluk have
no manual field effect. No plants, harvest persistence, contests, cooking, new
berry names, plot items or additional training items are introduced.

`+use` is blocked during battle. This work adds no battle inventory-feeding
action, and EV reduction is field-only. Existing held berries still work through
their repaired battle paths. Field medicine, Rare Candy and PP Up/PP Max retain
their existing command routes; see `help use` and the in-game maintenance help.
