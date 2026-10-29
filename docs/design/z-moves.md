# Non-plot Z-Crystal activation contract (#775)

Status: **63 explicit mappings on 35 crystals accepted locally**, including one
separately guarded [Ultra profile](../ultra-burst.md). The original 42-mapping
inventory below is historical; the [current matrix](z-crystals.md) names the
bounded additions and their dated evidence.
See the [player guide](../z-moves.md), [foundation](../testing/z-core-2026-10-23.md)
and [status/signature qualification](../testing/z-special-2026-10-23.md).
The first-slice rules below remain the contract; later combinations are gated
by the current matrix. This does not assert deployment or live stock.
Inspected October 22, 2026 at `4f0995b1b53e3b5a040d27092e48da05c67aa2d8`.
The [catalog and implementation gates](z-crystals.md) separate all 18 existing
generic and 17 signature crystals. Metadata and equip support prove no activation.
This design deliberately shares battle transaction conventions with
[Mega](mega-evolution.md), but Z use is a move action, not a transformation.

## First slice and player flow

Select **Normalium Z + the holder's actual active Tackle slot -> Breakneck
Blitz**, Normal/Physical, base power **100**, priority **0**, single ordinary
opponent target. An owned native Eevee with Tackle is the acceptance example;
the generic rule is not Eevee-only. Exact species/ability/genetics never change.

Proposed `+zmove [actor] <active move slot or full move name>=<target slot>`
both selects and queues the single MOVE action. Singles may omit the actor;
doubles require the player's own A1/A2/B1/B2 actor and a legal target.
`+zmove` with no arguments shows only the current actor's accepted combinations,
source move PP, crystal and remaining team use; it queues nothing. Use the normal
move UI/help for discovery; no numeric renumbering of gapped move slots.
There is no second `+attack`, menu-generated substitute move learned by the
Pokemon, Z-Ring, Key Stone, quest, tower, recharge, activation fee or staff
unlock. `+item`, `+use` and `+evolve` cannot activate crystals.

Require an actual held reusable Normalium Z, current owned conscious active
party/current-Fusion holder, fresh canonical placement/owner and non-egg state.
Validate exact active move identity, positive PP and current legal target on
request and resolution. Bag copies, another controller, stale slots, moved or
traded Pokemon, nickname/copied-species claims and free-form invented moves do
not qualify. Generic crystals accept any native species with the reviewed
source move; signature crystals additionally require their exact native form
and source move, never just appearance or copied ability. Transform/Imposter,
Mega, Primal, Ultra and Dynamax holders are excluded from the first slice.

Support existing human-controlled Wild/Trainer/PvP singles/doubles, one or two
actives per controller. No new formats or automatic NPC use. A new allowlist
contains only the first crystal/source-move pair; it must not iterate every
move or every `zMove` item entry. Other Normalium moves remain explicitly
deferred until their named effect/restriction gate passes.

## Action, resource and failure rules

The budget is **one successful Z activation per team/side per battle**, with
an independent opposing side. Reserve it by battle/turn/team/controller/owned
ID/actor/source move/target/crystal when the validated MOVE queues. Identical
retries report the queued action; different allies cannot reserve another.
Existing no-overwrite/cancel rules apply. Invalid input never queues an action,
spends PP, advances a turn or consumes the budget. Switching/item/flee choices
cannot secretly inherit a Z modifier; cancelled/invalidated declarations release
the reservation without replenishing a spent use.

Revalidate before resolution. Stale ownership, actor, crystal or source move
clears the unsafe action and requires legal input; never silently execute an
ordinary Tackle or a different Z move. An actor fainted before its action,
sleep/freeze/full paralysis/flinch/confusion self-hit and other ordinary
prevention consume the normal turn but **no PP or Z use**. Once the actor passes
those checks and begins its Z move, atomically deduct **one source-move PP**
(also against Pressure), mark the team used, and resolve its effect. Miss,
immunity, protection, absent target or an effect failure after that point still
spends the use and PP. No separate Z PP meter, doubled deduction or crystal debit.
All unexpected transaction/checkpoint failures roll back actions, resource use,
HP/status/PP, RNG, messages and runtime together; the legal input can be retried.

The first damaging Z move bypasses ordinary accuracy/evasion rolls, retaining
type/ability immunities, semi-invulnerable targeting restrictions and normal
redirection/Substitute. It is **non-contact**, has no Tackle contact flag,
secondary effect or ordinary-move recoil, and uses normal STAB, attack/defense,
screens, critical and seeded damage rules. Protect-family personal protection
reduces otherwise effective damage to **one quarter**, rounded by the existing
damage pipeline, minimum one; immunity remains zero. Quick/Wide Guard,
priority shields, Endure, Substitute and ability protection require explicit
positive/negative tests rather than treating every shield as Protect.

Later damaging moves use a reviewed immutable mapping of source move to Z power,
category, priority, type and target. Never derive power from the sentinel
`basePower=1` of a generic Z definition. The first 40-power Tackle maps to 100;
variable/fixed/multi-hit/charging/recharge/spread/called moves need explicit
maps/tests before acceptance. Preserve original-source PP and priority consumers
without mutating MOVEDEX or learned/active move rows. First-slice status Z moves
are rejected; there is no blanket stat boost, healing or copied base effect.

## Interactions, persistence and ending

Tera, Mega and Z have **separate per-team budgets**. Same-actor active/pending
Tera/Mega/Z combinations reject in both orders; different eligible allies may
use their separate mechanics in the same turn/battle. Preserve #715's existing
held-crystal Tera restriction. The first Z slice need not wait for Mega to ship,
but must expose the shared eligibility seam and test available Tera integration;
the later Mega implementation must test Z once both are enabled.

For the actual matching owned crystal, Magic Room/Embargo/Klutz do not disable
activation, and normal crystal removal protection remains. These are explicit
Z rules, not a generic item suppression change. Wrong-source controls and
ability suppression/bypass remain normal. No forced form change or new native
form is granted by a crystal, including Ultranecrozium Z.

Version checkpoint fields for `z_used` keyed by team and bound queued/reserved
Z action metadata. Include source move ID/slot, PP, target, actor and crystal;
restore a declaration without replaying deduction/effects, or refilling a use.
Keep benched/fainted members and both teams' budgets across switches, revival,
reconnect and repeated rebuilds. Missing legacy fields mean unused only when
there is no prior activation evidence; inconsistent or unbound metadata fails
closed through recovery. A normal old move remains normal, never inferred as Z
from its holder. Whole-turn fault injection includes post-damage/post-PP,
another actor's move, checkpoint writes and end/retry.

End/flee/concede/abort cleanup clears session-only data after committed ending
work, preserves real battle HP/status/PP and reusable ownership, and grants a
fresh budget only in a genuinely new battle. No permanent Mega/form cleanup or
new evolution writer is added. Existing items, Tera, Primal, capture, battle
recovery and progression/rewards are required regressions.

## Acquisition and later gates

Plan an **optional Z-Crystal Counter**, existing `+store` Buy flow, Normalium Z
only initially: selected PF2 price **10,000**, finite stock **1**, no automatic
refill. No plot item, live stock population, free metadata-price grant or
automatic species-wide availability. Test purchase -> inventory/itemdex ->
`+hold` -> `+zmove` -> actual damage/PP/used state -> checkpoint/reload -> end ->
return crystal. Funds, disabled/empty shop and purchase rollback/contention are
mandatory. #781 configured supply and #782 released live acceptance stay distinct.
Later batches extend only their named accepted offers under the same policy.

Implementation gates separate action/engine work, durable state/interactions,
normal command acceptance/source, three small generic batches, bounded status
effects and four signature groups. Every enabled crystal **and source move**
needs effect and player-route proof. Generic crystal support is partial until
its move allowlist/status-effect matrix is explicitly complete. Signature
forms whose acquisition/native lifecycle is unsupported stay deferred behind
named prerequisites; Ultranecrozium needs a separate reviewed Ultra route.
No follow-up may silently enable it from `itemUser` metadata.

Acceptance uses real complete turns/commands, independent SQL PP/inventory,
side contention/opponents, gapped move slots, current Fusion, meaningful
immunity/Protect/prevention/negative controls, repeated rebuild and rollback.
Executable changes require disposable PostgreSQL plus the mandatory three-order
gate. Source/static/catalog checks are not player acceptance; live/CI/deployment
remain separately reported.

## Sources and local limits

The primary simulator's [Z action resolution](https://raw.githubusercontent.com/smogon/pokemon-showdown/master/sim/battle-actions.ts),
[move metadata](https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/moves.ts)
and [crystal metadata](https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/items.ts)
were reviewed October 22. They inform the first mapping and reservation/effect
boundary. The explicit allowlist, conservative native/transformation checks,
command syntax and cross-mechanic policy are PF2 design choices; this is not a
claim of complete cartridge or simulator compatibility.

At the October 22 design baseline, local `itemsdex.py` had 35 crystal
definitions; Tackle had 40 power and no explicit Z-power field. No ordinary Z
command or durable Z action/side ledger was found. That design closure added
documentation and implementation issues. The current guide and qualification
above supersede that baseline for the 18 named generic pairs. Generated dex
data and Ultra Burst remain outside this implementation.
