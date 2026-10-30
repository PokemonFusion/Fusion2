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

### Initial implementation contract selected during plan execution

The user authorized executing the complete resolution plan and pushing tested
batches on October 29. The following values now define the first Training
Grounds delivery; existing-world operations remain separately authorized.

- One ordinary Training Grounds activity, available solo and free, gives up to
  **64 EVs in one chosen stat**, clipped to 252/stat and 510 total. It awards no
  EXP, level, healing, move PP or genetic change. Only a useful committed gain
  counts toward training milestones.
- A session has **three active exercise steps**, at least **30 real seconds
  apart**; the first step opens 30 seconds after confirmation. Minimum elapsed
  time is 90 seconds. Each step requires a deliberate command; elapsed time
  alone grants nothing. Technique/pace/recovery choices supply roleplay flavour
  with the same numerical effect. Chat and coaching can accompany the activity;
  another player or staff member is never required.
- `+train <party slot/UUID/current Fusion>=<stat>` previews a session, then
  `+train confirm` starts it. `+train continue <technique|pace|recovery>` advances
  one currently expected step. `+train`, `+train status` and `+train cancel`
  inspect/resume/cancel. Keep one active session per character, persisted across
  reconnect. Cancellation/interruption has no cost or partial numeric award.
- Use a living, non-egg, owned party member or current Fusion at the configured
  Training Grounds, outside battle and conflicting reservations. Revalidate
  current owner, exact target/placement, room, EVs and level at each action.
  Training that becomes stale refuses without undoing intervening gameplay.
- `+train reset <target>=<stat>[/<amount>]` previews partial/stat retraining;
  `+train reset <target>=all` previews a full reset. `+train confirm` revalidates
  the exact preview before committing. Resets are **free**, give no items or
  milestone progress, and require cancelling an active session first. Preview
  the EV and HP consequences. Preserve absolute HP deficit, keep fainted HP zero,
  and never refresh unrelated HP/PP, Nature or genetic IVs.
- Ordinary battle EV/EXP awards remain unchanged. Focused training is additive;
  an explicit confirmed reset is the only removal in this route. No trainer
  credits, new currency, automatic refill or three training shops are introduced.
- Every **six useful completed sessions** awards one Rare Candy; every **12**
  awards one Bottle Cap. The **60th** awards a one-time Gold Bottle Cap. These
  rewards share the committed session receipt and character identity, never
  timer callbacks or replayed commands. Minimum active elapsed times are nine,
  18 and 90 minutes respectively. Existing item use/Hyper Training eligibility
  still applies; merely owning a Cap bypasses no level or target guard.
- The separate opt-in `training-v1` Item Finder profile has a **5% success
  chance**, using the existing three-second character cooldown. Conditional
  weights total100: each of the six feathers8 (48 total), each of the six
  EV-reducing berries6 (36), Rare Candy12, Bottle Cap3, Gold Bottle Cap1. Every
  successful search credits exactly one selected item. The named existing
  Potion profile retains its current rules; conflicting/unknown configurations
  fail closed. No room receives this profile merely from a catalog entry.
- All 15 names have an explicit role: feathers and EV berries are optional
  Finder supplements to reliable direct training/free retraining; Candy and
  Caps also have dependable earned milestones. Gold is optional. No random
  drop is required to produce or change a viable build.

Measured example from `get_stats`: native Hardy Mew at level50, zero IVs/EVs,
has Attack105/Speed105. Four sessions in each stat yield252 Attack/252 Speed
EVs and Attack136/Speed136 in **12 minimum active minutes**. A ninth session in
HP clips to the remaining6 EVs, for510 total, in13.5 minimum active minutes.
An intentionally chosen252/252/4 spread takes a partial confirmed two-EV reset
afterward; spare EVs that do not change a displayed stat are not invented power.
These are calculated-stat and configured-activity measurements, not a logged-in
player timing or claim that the activity is already implemented.

Implementation batches: (1) session command/persistent EV delivery and status,
(2) stale-safe free partial/full retraining, (3) the15-name Finder profile and
atomic training milestones. Each batch needs useful ordinary command/SQL proof,
no-effect/eligibility/refusal controls, duplicate/concurrent completion, post-write
rollback and reconnect. Compare actual attacks and action order of trained versus
untrained native models in NPC and disposable player battle fixtures. Qualify
socket timing and acquisition separately; author a discoverable Training Grounds
and Training Trail without installing them in an existing world.

### Agreed direction and earlier source boundary

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

## Current issue audit and resolution order

The fresh GitHub audit covers **176 `[Items]` issues: 151 closed and 25 open**.
There are no literal `item` or `items` labels; the title prefix identifies this
backlog. Open and closed searches were partitioned below the connector's
100-result limit. Each issue was fetched, its discussion read where present,
and repository report references checked. The
[complete per-issue inventory](../testing/item-issue-audit-2026-10-29.json)
records status, evidence and next action for all 176.

All 151 closed issues have retained resolution reports, with no missing report
references. Keep them out of the new implementation queue unless a fresh scoped
regression is reproduced. This documentary audit does not repeat every historic
mechanics test or certify present live behavior.

The current local candidate is `19f8eab5f4c7d2236542f3157e1791754b6921cf`.
GitHub staging was independently read at
`9c36beec68b2e3b6a413b2c4c93785f620831e48`; six later commits remain local.
All 35 fingerprints in the recent repair/addition/next-action evidence still
match. The prior candidate passed 8,135 tests / 4,032 skips in each of three
mandatory processes and 374 SQL cases across three separate batches. Those
are retained test results, not new executions in this audit. Running-game
deployment and current public stock were not inspected here.

### The 25 open issues

| Issue | Current finding | Remaining action |
| --- | --- | --- |
| #919 | Aggregate tracker, still incomplete | Reconcile children after every delivery; keep genuine follow-ups explicit |
| #922 | Pinch berries implemented and tested locally | Publish/accept existing work; do not recode |
| #923 | Reactive stat consumables implemented and tested locally | Publish/accept existing work; do not recode |
| #924 | Terrain seeds implemented and tested locally | Publish/accept existing work; do not recode |
| #925 | Indirect item damage implemented and tested locally | Publish/accept existing work; do not recode |
| #926 | Residual healing guards implemented and tested locally | Publish/accept existing work; do not recode |
| #927 | Manual medicine Embargo implemented and tested locally | Publish/accept existing work; do not recode |
| #928 | Berserk Gene implemented and tested locally | Publish/accept existing work; do not recode |
| #929 | Repair reconciliation/gate closeout remains | Accept all nine repair dependencies on the final published candidate |
| #930 | Access direction recorded; former training-shop proposal superseded | Review scope checklist and hand off to #952 |
| #931 | Contextual evolution scope recorded | Review scope checklist and hand off to #947 |
| #932 | Six Z mappings implemented and tested locally | Publish/accept existing work; no new crystal batch |
| #933 | Three-berry growing scope recorded | Review scope checklist and hand off to #948 |
| #934 | Mirror Herb teaching scope recorded | Review scope checklist and hand off to #949 |
| #935 | Four recovery medicines implemented and tested locally | Publish/accept existing work; no live stock claim |
| #936 | Soothe Bell scope recorded | Review scope checklist and hand off to #950 |
| #937 | Prize-item scope recorded | Review scope checklist and hand off to #951 |
| #938 | Cleanse Tag/Pure Incense intentionally deferred | Retain the documented reason; no implementation selected |
| #939 | All 14 Link Cord mappings already published to staging | Acquisition plan/source and authorized logged-in live acceptance remain |
| #947 | Evolution rules exist; proposed public day/night content is unfinished | Author/qualify three contextual evolution access routes |
| #948 | Nursery still accepts only its original five seeds | Implement and accept Chesto, Sitrus and Lum growing |
| #949 | Daycare has no Mirror Herb teaching route | Implement reviewed native egg-move teaching and confirmation |
| #950 | EV-berry friendship still has no Soothe Bell modifier | Implement the bounded positive-gain modifier and useful evolution |
| #951 | Reward receipts exist; held prize-item qualification is unfinished | Implement once-only nonstacking NPC prize support |
| #952 | Training direction agreed; activity/balance/access design unfinished | Finish the design, then deliver bounded implementation batches |

The six scope parents and #938 are scope/deferral closeout candidates, not proof
that their generated runtime work is complete. Review their remaining criteria
and links before closing them. No issue was changed or closed by this audit.

### Recommended sequence

1. **Clear completed work and the repair gate.** Reconcile #922–#928 against
   their existing commits/reports. Publish the tested local candidate only when
   authorized and verify its CI and evidence. Accept the exact nine repairs
   #920–#928, then reconcile #929's source/facet matrix and intentional limits.
   After clearing that gate, sign off the already implemented #932/#935 additions
   and begin further feature implementation. Review
   the six recorded scope handoffs and #938's explicit deferral so they do not
   masquerade as duplicate coding tasks. Keep published, deployed and player
   acceptance evidence distinct.
2. **Finish #952's design.** Specify the Training Grounds activity, predictable
   EV gain, representative sessions-to-build, fees if any, affordable partial/full
   retraining, ordinary battle EV/EXP interaction, named Finder rules and advanced
   milestones. Use actual PF2 stats and text-battle pacing. Keep all 15 item names
   mapped; the removed shops and prices are not balance defaults.
3. **Deliver the Training Grounds design in three bounded follow-ups.** First
   focused EV training, then affordable retraining, then supplementary Finder
   drops and advanced/milestone rewards. These implementation/acceptance issues
   must be created from the completed design; they do not yet exist. Reuse field
   training, Hyper Training and the guarded Finder foundations. Test useful
   stats, caps, one committed gain/cost, stale targets, interruption, duplicate
   completion, concurrency, rollback and reconnect. Finish with representative
   NPC and agreed PvP build comparisons. Completing a design ticket alone does
   not deliver these mechanics.
4. **Finish #939's acquisition and live acceptance.** Select and author a
   discoverable Link Cord source without assuming the training-item Finder
   decision supplies it. Preserve all 14 published mappings and trade-held
   behavior. Qualify acquisition → bag evolution → exact one-copy debit →
   reconnect, including form/size and independent Karrablast/Shelmet controls.
   Logged-in/shared-world checks require their separately reviewed setup.
5. **Deliver #947 contextual evolution access.** Reuse current room context and
   `EvolutionService`; author day/night locations and optional item supply for
   Happiny, Sneasel and Gligar. Prove travel, native branches, wrong context,
   useful evolution, one held debit, refusal preservation and reconnect. Treat
   companion/item access and authored locations separately from installation.
6. **Deliver #948's three nursery seeds.** Extend the existing allowlist and
   source plan without replacing the growth system. Prove seed debit, stage
   watering, useful harvest, cycle retries, contention and rollback. Keep a real
   four-hour player run separate from controlled-clock tests; its elapsed wait
   can overlap independent later work.
7. **Deliver #950 Soothe Bell.** Add the positive-only EV-berry friendship
   modifier to the existing field transaction, retaining rounding, caps,
   ownership and HP/EV conservation. Prove the useful feed → inspect → friendship
   evolution route, plus stale held state, no effect, retry and rollback.
8. **Deliver #949 Mirror Herb teaching.** Reuse Daycare placement/move-edit locks
   with reviewed native egg-move metadata, an empty active slot and actual donor
   knowledge. Qualify review/confirm, donor/item/owner changes, full/already-known
   refusals, concurrent edits, unchanged donor/unrelated PP and nonconsumption,
   rollback and reconnect. Preserve existing breeding and battle Herb behavior.
9. **Deliver #951 prize items last.** Extend the existing reward receipts with
   durable genuine participation and a maximum ×2 standard NPC TRAINER prize.
   Prove exact base/bonus money, multiple-holder nonstacking, bench/loss/zero
   controls, item transfer timing, duplicate/interrupted outcomes, concurrent
   payout, rollback and reconnect. Retain all PvP/wild/script/gym/Adventure and
   non-prize exclusions. This has the broadest economy/persistence exposure.
10. **Complete release/player reconciliation and #919.** After each code batch,
    run the relevant focused and disposable SQL checks plus the mandatory gate
    for runtime changes. Qualify actual acquisition/use/reconnect separately
    from prepared fixtures and deployment. Update source/support evidence with
    explicit unknowns and the intentional #938 deferral. Close the tracker only
    after required implementation/acceptance children are reconciled, without
    claiming every item or source works merely because scopes were written.

#929 is the hard prerequisite. #952 design must precede its implementation
batches. After #929, #947/#948/#950/#949/#951 are independent: the sequence above
is a recommended delivery order based on reuse, complexity and economy exposure,
not a set of invented hard dependencies. No push, release, stock write, migration,
service restart or operation on human fixtures is authorized by this plan.


## Execution completed — October 29, 2026

The ordered plan is complete: all 25 original open issues and the three generated training implementation issues are closed. The final GitHub sweep has 179 closed / zero open [Items] issues. [Execution evidence](../testing/item-plan-execution-2026-10-29.md) records staging publication, all three mandatory orders at 8,187 passed / 4,032 skipped, 230 final SQL cases, 100 actual socket inputs, three actual four-hour crop flows, green hosted CI and fixture cleanup. Historical findings above remain the original dated audit; #938's intentional deferral and existing-world deployment/source limits remain explicit. No shared-world operations or human fixture changes occurred.
