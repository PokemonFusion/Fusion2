# Remaining item scope decisions — October 29, 2026

Follow-ups [#947](https://github.com/PokemonFusion/Fusion2/issues/947),
[#948](https://github.com/PokemonFusion/Fusion2/issues/948),
[#949](https://github.com/PokemonFusion/Fusion2/issues/949),
[#950](https://github.com/PokemonFusion/Fusion2/issues/950) and
[#951](https://github.com/PokemonFusion/Fusion2/issues/951) were created for
#931/#933/#934/#936/#937. After explicit user approval, the redacted #930 source
follow-up was published as [#952](https://github.com/PokemonFusion/Fusion2/issues/952).
The 16 approved original-issue updates were appended and read back, preserving
their existing bodies and metadata. All issues remain open. The
[publication receipt](../testing/item-issue-publication-2026-10-29.json) records
the exact scope; implementation commits remain local.

Later on October 29, the user selected deliberate training and affordable
retraining, with Item Finder rewards as a supplement. #952 was rewritten around
that design and #930 links the revised direction. The original publication
receipt remains historical; the current issue snapshot is in
[the follow-up record](item-backlog-followups-2026-10-29.json).

These bounded decisions address #930, #931, #933, #934 and #936–#938 after
the existing-item repair gate. They define follow-up implementation and player
acceptance work. They do not install content, change live stock, alter rewards,
or claim that the missing runtime features already work. #932's six Z sources
and #935's four recovery equivalents have separate implementation receipts.

## Training access and existing stock (#930 / #952)

The fresh read-only inspection report is retained outside the repository for
user review. Publishing its operational details requires explicit approval.
The selected direction is now **Training Grounds, affordable EV retraining and
supplementary Item Finder/training rewards**. The previous three-counter plan,
including its prices, quantities, entrance names and recipe identities, is
superseded. This is a design task; no training activity or new drop is implemented
or installed by the decision.

For the 29 previously depleted offers, retain finite supply: the 21 mints, PP Up,
PP Max, Ability Capsule,
Ability Patch, Choice Band, Choice Specs, Choice Scarf and Exp. Candy XL.
Keep these offers finite. Do not reset them, automatically refill them, or opt
them into an operator policy as part of this backlog. Any later replenishment
request must name the source/version, existing sales, cap, window and rollback
as a separate approved operation. Existing opt-in protections remain in force.

Proposed player flow: choose a Pokémon → choose a stat → complete a short
training session or NPC sparring challenge → inspect the exact saved EV gain
and remaining capacity. Progress should be predictable, repeatable and available
solo, with room for roleplay or coaching. Avoid hundreds of repetitive fights,
single-point command spam or training access dependent on arranged PvP wins.
Preserve the existing 252-per-stat / 510-total EV limits and genetic data.

Affordable retraining must let players change a spread without rare loot, scarce
shared stock or a staff reset. Specify a service, reliably available EV-reducing
berries, or both. Preview and confirm destructive changes, costs and affected
stats. Define how training interacts with ordinary battle EV/EXP rewards without
silent erasure or duplicate credit.

Keep the original 15-name access inventory explicit:

| Family | Intended role |
| --- | --- |
| Health, Muscle, Resist, Genius, Clever and Swift Feather | Small boosts/shortcuts; suitable ordinary Finder rewards alongside reliable focused training |
| Pomeg, Kelpsy, Qualot, Hondew, Grepa and Tamato Berry | Accessible retraining aids; reliable access supplemented by gathering/growing |
| Rare Candy | Occasional exploration/challenge reward that speeds up leveling |
| Bottle Cap | Advanced training reward with a reliable progression route alongside rare finds |
| Gold Bottle Cap | Major milestone reward and optional shortcut |

Existing vitamins can remain training shortcuts; this decision selects no new
vitamin source batch. Preserve existing Hyper Training eligibility and its
stat-only overlay. Choose named Finder rules and eligible locations; the guarded
Potion source does not establish arbitrary training-item support. Preserve its
behavior when extending it. No blanket catalog drops, new currency or automatic
refill is selected.

Follow-up [#952](https://github.com/PokemonFusion/Fusion2/issues/952) must select
the first ordinary location/command/activity, useful EV gain, expected sessions
for a representative build, any fee, affordable reset policy, Finder weights
and advanced milestones. Values remain to be designed and measured against
actual PF2 stats and text-battle duration. Then create bounded implementation
and normal-player acceptance follow-ups, covering train/retrain/find/earn →
inspect/use → reconnect; fresh eligibility, caps, interruption, stale selection,
duplicate completion, concurrency and rollback. Distinguish deterministic Finder
tests from actual player acquisition. Existing-world installation requires its
own reviewed operation with exact targets.

## Three contextual held evolutions (#931)

Choose explicitly configured, discoverable day/night locations, retaining
server-owned context. Do not create a global clock or accept player eligibility
flags in this batch. Proposed annex entrances from the same hub are `daygrove`
and `nightgrove`, with signs naming their fixed evolution context and public
return exits. These are proposed content identities, not installed rooms.

| Exact native source | Held item | Context | Exact target |
| --- | --- | --- | --- |
| Happiny | Oval Stone | `time_of_day=day` | Chansey |
| Sneasel | Razor Claw | `time_of_day=night` | Weavile |
| Gligar | Razor Fang | `time_of_day=night` | Gliscor |

Preserve the existing explicit `+evolve <id>` contract: these dex entries have
no species-specific minimum level, so valid stored levels 1–100 remain eligible
when all other requirements hold; the command grants no level. Require the exact
native branch and real held copy, consume one only on a committed evolution,
and preserve current owner, egg, placement, Fusion and reservation checks.
Hisuian Sneasel→Sneasler retains its distinct existing day branch; its companion/source
acceptance is outside this first matrix. Other existing day evolutions keep their
normal rules. Regional rules retain precedence and may never be satisfied by renaming a source.

Propose finite Oval Stone 2,000×5, Razor Claw 5,000×5 and Razor Fang 5,000×5 as a
separate optional recipe. Native companion sources and all other region/magnetic
evolution contexts remain **world-unverified**, rather than assumed absent.

Follow-up: **Qualify three non-plot contextual held evolutions and their access**.
Author the exact room contexts and optional recipe without installing them.
Test actual travel, useful evolution, wrong time/region/native/owner, egg/current
Fusion/reservation controls, level bounds, no debit on refusal, one debit on
commit, stale target/held changes, rollback and reconnect. Preserve Sweet,
trade-held, Link Cord, Peat Block, Kingambit, Kubfu and coin routes.

## Chesto, Sitrus and Lum growing (#933)

Extend only the existing five-seed allowlist by these three names. Keep one
private bed per trainer, one actual bag berry spent at planting, four one-hour
stages / four real hours, one water operation per stage and yield **1 + watered
stages (1–5 berries)**. Unwatered crops still yield one; no extra berry-specific
yield or hidden fee. An abandoned bed stays tied to its current cycle until
explicitly tended/harvested. Do not add automatic withering, refunds, timer
credits, another bed or clock controls in this batch.

Sitrus and Lum already have finite public offers in the existing held-items
counter; their use as planting input does not create new stock. Propose only
a separately versioned Chesto offer, 200×5, for source authoring and later
installation review. Other berries and all fourteen snack contracts stay intact.

Follow-up: **Grow and accept Chesto, Sitrus and Lum through the private nursery**.
Reuse current owner/location/battle guards, cycle identity and atomic harvest.
Qualify exact seed debits, water stages, useful harvested effects, gapped/late
watering, abandoned/replayed/stale cycles, concurrent harvest, reconnect and
rollback. Automated controlled clocks must be labelled separately from a real
four-hour ordinary-player acceptance run. No source installation is implied.

## Mirror Herb egg-move teaching (#934)

Choose a non-plot existing Daycare location and a review/confirm command:
`+daycare herb <recipient>=<donor>/<exact move>`. Both Pokémon must belong to the
current trainer and be ordinary non-egg party members, outside battle/Fusion/
reservations and Necrozma restrictions. The recipient must physically hold a
Mirror Herb and have an empty active move slot. The donor must actually know
the selected move in an active slot; zero donor PP does not erase that knowledge.
The recipient's exact native/form egg-move metadata must authorize it. Use a
reviewed generation-nine egg-species resolver; missing/ambiguous metadata refuses.

Adopt generation-nine nonconsumption and no breeding-compatibility requirement:
do not require matching gender, species or Egg Groups, generate an egg, charge
money, add a timer or require staff. The recipient receives exactly one new
knowledge/active-slot entry with ordinary new-move PP. Existing knowledge uses
the normal moveset route instead; do not overwrite a slot or refresh existing PP.
Item, donor, recipient and unrelated move PP remain unchanged.

Follow-up: **Implement reviewed Mirror Herb teaching with stale-safe confirmation**.
Reuse move-learning/edit and placement locks. Confirm owner, room, item, donor
move, recipient native metadata and exact empty slot again under locks. Include
wrong/full/already-known/foreign/egg/Fusion/reserved controls, concurrent held or
move edits, donor transfer, duplicate confirmation, rollback and reconnect. Prove
the ordinary command with prepared legal donors separately from public donor/item
acquisition. Preserve hatch inheritance and existing battle boost-copy consumption.
Primary [generation-nine transfer reference](https://github.com/rh-hideout/pokeemerald-expansion/blob/8654616bd38d9b28cc7dd8f3d0b4cb030aa2d40c/src/daycare.c).

## Soothe Bell friendship (#936)

First runtime batch: a genuinely held, reusable Soothe Bell multiplies only the
existing six EV-berry positive friendship deltas by **1.5, rounded down before
the 255 cap**. Current base deltas 10/5/2 become 15/7/3 using the pre-use tier.
Never multiply a loss, a zero change, a mint, a hatch baseline or a retry. Use
fresh owner/held/placement state in the same field transaction as the berry debit.
Party and current Fusion remain eligible; inactive reservations do not. Field
feeding already excludes battle, so battle-only Klutz/Magic Room/Embargo do not
silently remove this out-of-battle effect.

Useful first player route: hold Bell→feed a useful EV berry→inspect friendship→
reach the existing threshold→evolve native Golbat to Crobat. Preserve current
herbal penalties, genetic/nature state, EV reduction, breeding and evolution
guards. No general walking, level-up or battle friendship service is claimed.
Propose a separate finite Bell source, 4,000×2, after runtime qualification.

Follow-up: **Add Soothe Bell through one authoritative field friendship modifier**.
Test exact positive deltas, both friendship tiers, cap/no effect, a real held
copy, stale owner/held edits, current Fusion, one debit/bonus, concurrent final
copy, rollback, inspect/evolution and reconnect. Keep source installation separate.
Primary [positive-only friendship modifier](https://github.com/rh-hideout/pokeemerald-expansion/blob/8654616bd38d9b28cc7dd8f3d0b4cb030aa2d40c/src/pokemon.c).

## Amulet Coin and Luck Incense rewards (#937)

First runtime batch: double the existing **standard NPC `TRAINER` prize-money
payload once** when an owned party/current-Fusion Pokémon qualifies by active
entry or a completed ordinary action while physically holding either item.
Persist qualification with the battle's outcome/owner identity before payout;
do not recalculate from final gear. A later transferred item qualifies only
through later participation, never a post-outcome edit. A qualifying fainted
holder retains its earned qualification. Benched-only holders do not qualify.
Use the same multiplier for both names and any number of holders: maximum ×2.

Exclude wild/PvP/Multi payouts, Pay Day, scripted/gym/Adventure rewards, fees,
transfers, resale, first-clear items and other currencies from this first batch.
Keep the base NPC formula and zero/loss behavior unchanged. These explicit
limits avoid inventing a new beta reward economy. Treat qualifying held ownership
as a field prize condition, without borrowing held battle-effect suppression.

Follow-up: **Add two nonstacking prize items to once-only NPC reward receipts**.
Extend `BattleRewards`/existing outcome transactions, with durable participation
qualification and exact base/bonus payloads. Test entry/action participation,
bench/loss/zero controls, held transfer timing, owner/placement changes, duplicate
outcomes, interrupted writes, concurrency, wallet rollback and reconnect. Propose
finite 10,000×1 offers separately; no inventory definition alone claims support.

## Cleanse Tag and Pure Incense (#938)

**Defer both definitions and runtime behavior.** PF2's explicit `+hunt` is an
intentional request for an encounter; reducing its success would make these
items counterproductive. No ambient walking-encounter system currently supplies
their ordinary role. Do not invent automatic fleeing, free rewards, hidden
cooldown advantages, capture changes or a new walking system to justify a name.

Record these as intentional missing-definition deferrals in the current support
index, preserving existing hunts, finder/wild-held sources and scripted gates.
Revisit only with a separately requested useful encounter-system policy. This
decision needs no implementation/source issue until that prerequisite exists.
