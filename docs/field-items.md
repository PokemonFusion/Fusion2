# Field items

Use `+use <item>=<target>` outside battle. Medicine and berry feeding share the
same transaction, fresh ownership/placement checks and canonical target rules.
Targets are party slots 1-6 (with gaps preserved), unambiguous names, full
Pokemon UUIDs, or `fusion`/`self`/`me` for the current reserved Fusion. Eggs,
boxed Pokemon, foreign owners and inactive Fusion reservations are ineligible.
An effective use consumes one item; invalid or ineffective uses consume none.

## Battle item boundary

`+item` / `+battle/item` accepts the existing 21 battle medicines (including
reserve revival, Ether/Max Ether and Elixir/Max Elixir), the later
[32 reviewed recovery foods/berries](battle-recovery-items.md), and capture balls
in wild battles. It rejects unsupported items before reserving an actor,
persisting a declaration, changing a turn or consuming stock. Fresh Water and
Oran Berry retain their `+use` field routes and their reviewed manual battle use.
Held items use `+hold` before battle; Smoke Ball holders escape with `+flee`.

Command choices, public queue entry, restored/deferred declarations and final
dispatch share the same capability policy. Invalid old item choices are removed
before turn readiness, while valid sibling choices remain queued. In doubles,
supported items still require an owned actor such as `+item A2 Potion=3`.
Wild-only capture restrictions and selected reserve/move targets remain intact.

Capability is distinct from effect. A supported Potion used on a full-health
target still spends the queued battle action, but consumes no item; unsupported
manual use never queues an action. This repair preserves that existing no-effect
turn policy. The later #773 extension supplies only its named battle foods and
berries; it adds no new item definitions or plot items.
See the [battle-item validation report](testing/battle-item-validation-2026-10-22.md)
for ordinary-command/SQL, restore, actor-selection and regression evidence.

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

The separate [nursery feature](berry-nursery.md) grows Oran Berry through
`+berry` and deliberately feeds Razz through `+berry snack Razz Berry=<target>`
for up to 10 HP outside battle. It does not implicitly register a Razz `+use`
alias, held effect, EV effect or another flavor berry.

| Items | Field effect |
| --- | --- |
| Oran Berry | Restore up to 10 HP |
| Berry | Restore up to 10 HP |
| Gold Berry | Restore up to 30 HP |
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
| Mystery Berry | Restore up to 5 PP to one current active move |
| Burnt Berry | Cure freeze |
| Ice Berry | Cure burn |
| Mint Berry | Cure sleep and clear its saved remaining turns |
| Miracle Berry | Cure major persistent status, including toxic poison |
| PRZ Cure Berry | Cure paralysis |
| PSN Cure Berry | Cure poison or toxic poison |
| Pomeg, Kelpsy, Qualot, Hondew, Grepa, Tamato Berry | Reduce the corresponding EV and increase friendship as below |

HP recovery requires a living, injured target and is capped at its calculated
maximum HP. Manual feeding can be used above the automatic held activation
threshold. Status cures require the matching saved condition on a living target.
Leppa and Mystery require a living target with a depleted active move. Use
`+use Leppa Berry=3/Water Gun` or `+use Mystery Berry=3/4`: move numbers retain
canonical active-slot gaps. Without `/move`, restore the first depleted active
move. Stored PP boosts and current dex data determine its cap; other moves are
untouched. Examples: `+use Oran Berry=3`, `+use Lum Berry=fusion`.

The five flavor recovery berries have a concrete HP effect in this allowlist.
Their nature-based confusion is a combat-only volatile and is not introduced or
persisted by field feeding. Lum's field use cures persistent status, not a
nonexistent out-of-battle confusion state. The existing held effects retain
their normal thresholds, nature/confusion rules, triggers and consumption.

The nine legacy names are existing definitions. Their field mapping follows
the reviewed [reference item implementation](https://github.com/smogon/pokemon-showdown/blob/master/data/items.ts)
and the existing medicine/berry policy. Burnt thaws, while Ice cures burn;
the names do not imply the opposite. Miracle cures saved major status but does
not invent persistent field confusion. Bitter Berry and Persim Berry only cure
combat confusion and remain unavailable through `+use`.

Bag feeding consumes one bag copy, never the stored held item, and does not
require a held activation threshold. Existing held callbacks are unchanged:
PF2 currently also lets held Burnt cure burn and restricts held PSN Cure to
ordinary poison. Those held differences are preserved separately from the
reviewed field mapping. See the [legacy berry acceptance report](testing/legacy-berries-2026-10-22.md)
for per-item ordinary commands, SQL reload and regression evidence.

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

## Vitamins and feathers

The twelve existing training items use `+use <item>=<party slot, exact name,
full ID or current Fusion>`, for example `+use Protein=3` or
`+use Health Feather=fusion`. They share the medicine/berry owned-target,
egg, battle, current-Fusion, reservation and ambiguity checks and the same
placement/trainer transaction. They accept no move selector or party-wide target.

| Stat (stored EV index) | Vitamin (up to +10 EVs) | Feather (+1 EV) |
| --- | --- | --- |
| HP (0) | HP Up | Health Feather |
| Attack (1) | Protein | Muscle Feather |
| Defense (2) | Iron | Resist Feather |
| Special Attack (3) | Calcium | Genius Feather |
| Special Defense (4) | Zinc | Clever Feather |
| Speed (5) | Carbos | Swift Feather |

The current-generation supplement policy permits vitamins above 100 EVs,
up to **252 per stat and 510 total**, using the existing EV validators and
the existing item callbacks' +10/+1 amounts. This follows the
[official Sword/Shield supplement policy](https://swordshield.pokemon.com/en-gb/gameplay/features-raise-pokemon/)
which allows supplements to reach maximum base points. A use adds the minimum
of its amount, remaining stat capacity and remaining total capacity. For example,
Protein at 250 Attack adds 2 EVs; at 252 Attack it has no effect. A useful EV
increase consumes exactly one bag item even if rounding leaves a displayed stat
unchanged. Capped or invalid saved EVs consume nothing and are never silently
repaired. Friendship, held items, IVs, nature, level and moves are unchanged;
this is the bounded EV-training route, with no separate friendship-only use.

Stats refresh immediately. As with EV berries, preserve the absolute HP deficit
when max HP changes: living HP becomes old HP plus the max-HP difference,
clamped to 1..new maximum; fainted HP stays zero. A non-HP increase does not heal
an ordinary injured target. Inventory, EVs and adjusted HP commit together;
failed debits (including partial writes), failed saves and competing uses cannot
leave a free effect or spend a useless item. See the
[training acceptance report](testing/field-training-2026-10-22.md) for actual
commands, SQL reload, caps, rollback and concurrent-use evidence.

Vitamins and feathers use this EV-specific service; ability-changing items and
Bottle Caps use the separate routes below. Pretty Feather, nature mints and
battle training remain unsupported. Existing EV-lowering berry amounts,
friendship and HP behavior remain separate and covered by regressions.

## Ability Capsule and Ability Patch

Use `+use Ability Capsule=3` or `+use Ability Patch=fusion` with the shared
fresh owned-party/current-Fusion, egg, placement/reservation, ambiguity and
battle checks. Both are single-target field consumables with no move selector
or arbitrary ability argument. The selected policy follows Scarlet/Violet's
reversible Patch model, as represented by the
[reference ability-change rules](https://github.com/kwsch/PKHeX/blob/master/PKHeX.Core/Legality/Verifiers/Ability/AbilityChangeRules.cs).

| Item | Current canonical slot | Result |
| --- | --- | --- |
| Ability Capsule | Ordinary 0 | Ordinary 1, if distinct and present |
| Ability Capsule | Ordinary 1 | Ordinary 0, if distinct and present |
| Ability Capsule | Hidden H or special S | No effect |
| Ability Patch | Ordinary 0 or 1 | Hidden H, if distinct and present |
| Ability Patch | Hidden H | Ordinary 0, if distinct and present |
| Ability Patch | Special S | No effect |

Patch reversal always chooses slot 0; use Capsule afterward to select slot 1.
A Pokémon with one ordinary ability can use Patch if it has a distinct hidden
ability, but cannot use Capsule. A species/form without a distinct hidden slot
cannot use Patch. Missing/identical destinations have no effect and spend none.
Special event/evolution abilities such as Rockruff's Own Tempo, Greninja's
Battle Bond and Zygarde's Power Construct are not ordinary/hidden slots and
these items cannot create or remove them.

Eligibility comes only from the freshly saved exact canonical species/form's
dex ability slots. Nicknames, temporary transformations and base-species fallback
cannot supply another species' abilities. Native regional and gender forms
retain their own slots. Unknown species, battle-only forms, item/ability-locked
forms and active transformed instances are rejected. Cached native-family
metadata, if present, must agree with the saved canonical family. No form or
required item is changed to make a use legal.

The model stores an ability name rather than an independent slot index. A name
must therefore match exactly one normalized canonical slot, and its destination
must also be unambiguous. Empty, foreign or ambiguous saved abilities are
rejected unchanged rather than silently repaired. All checked-in dex ability
names currently map uniquely within each species/form. Evolution's existing
slot mapping can consequently preserve the changed ordinary/hidden slot.

One useful ability change and one bag debit commit together; failed/partial
debits and failed saves roll both back and restore model/inventory caches.
Waiting commands re-read the current slot and inventory under the shared locks.
HP, status, identity, placement, held item, EVs/IVs, friendship, level, moves and
cosmetic flags are unchanged. Fainted eligible targets remain fainted. See the
[ability-item acceptance report](testing/ability-items-2026-10-22.md) for commands,
reloads, evolution/native-form cases, rollback and competing-use evidence.

## Bottle Caps and Hyper Training

`+use Bottle Cap=3/Atk` trains one selected stat. Full stat names and the exact
aliases `HP`, `Atk`, `Def`, `SpA`, `SpD`, `Spe`, `SpAtk` and `SpDef` are accepted;
numbers, partial names and move names are not stat selectors. A Bottle Cap
always requires a selector. `+use Gold Bottle Cap=3` trains every remaining
eligible stat with one copy and accepts no selector. Targets also accept exact
unambiguous names, full IDs and the current Fusion under shared field rules.

The selected Generation-9 rule requires **level 50 or higher**, with consistent
saved level/EXP. See the primary reference's
[Hyper Training level policy](https://github.com/kwsch/PKHeX/blob/master/PKHeX.Core/PKM/Interfaces/IHyperTrain.cs)
and [perfect-IV eligibility checks](https://github.com/kwsch/PKHeX/blob/master/PKHeX.Core/Legality/Verifiers/HyperTrainingVerifier.cs).
An eligible stat has genetic IV below 31 and is not already Hyper Trained.
Gold Bottle Cap skips genetically perfect and previously trained stats and
consumes nothing if no eligible stats remain. Training applies effective IV 31
for stat calculation; it can be useful before rounding changes a displayed stat.
Fainted targets can train but remain at zero HP. Living targets preserve their
absolute HP deficit when maximum HP changes, matching the field EV convention.

**Persistent contract:** the existing `OwnedPokemon.flags` array stores one
`hypertrained:<canonical stat>` marker per trained stat. The six keys are `hp`,
`attack`, `defense`, `special_attack`, `special_defense` and `speed`. Existing
flags are preserved. No schema change, migration or retroactive training is
required; old rows with no markers retain genetic stat behavior. Invalid saved
IV/EV arrays, invalid training markers, unknown/battle-only species, item/ability-locked
forms, transformed targets, inconsistent level/EXP, eggs, foreign/boxed/inactive reservations and battle locks cannot
spend a cap. Training flags, adjusted HP and one inventory debit commit together,
with post-write rollback, commit-aware caches and fresh concurrent-use checks.

Genetic `ivs` remain untouched in SQL and battle snapshots. The overlay is
applied by common stat helpers, battle construction and native-form recalculation,
and is carried independently in battle checkpoints. Legacy owned checkpoints
without the new optional `hyper_training` key recover it from the owned flags;
standalone old snapshots default to no overlay. Battle-level scaling retains
training even if the temporary battle level is below 50. Evolution preserves
the markers. Genetic/Hidden Power and future inheritance inputs are not replaced
with trained values; no breeding or Hidden Power implementation is added.

`+party <slot>` continues to show genetic IVs and adds an Effective IV row and
the Hyper Trained stat labels. Inventory/itemdex describe both existing caps
and the route. The existing competitive dex retains their Generation-7 IDs
795/796 and Fling power 30. No new price, shop stock, world grant, plot unlock,
NPC or live availability claim is added; current obtainability stays in #772.
Mints, breeding and broader training systems remain separate. See the
[Hyper Training acceptance report](testing/hyper-training-2026-10-22.md) for
ordinary commands, SQL/session rebuilds, genetic preservation and failure proof.

## Limits

The berry service uses an explicit 30-item field allowlist (29 berries and Berry Juice), not
generic support for every `isBerry` entry. Persim/Bitter (confusion-only), Enigma
(damage-triggered), resist, stat-boost, accuracy, retaliation and other combat
berries remain held-only. Contest/flavor-only berries such as Razz and Bluk have
no manual field effect. No plants, harvest persistence, contests, cooking, new
berry names, plot items or additional training items are introduced.

`+use` is blocked during battle. This work adds no battle inventory-feeding
action, and EV reduction is field-only. Existing held berries still work through
their repaired battle paths. Field medicine, Rare Candy and PP Up/PP Max retain
their existing command routes; see `help use` and the in-game maintenance help.
