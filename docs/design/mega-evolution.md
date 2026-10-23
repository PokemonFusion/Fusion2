# Mega Evolution activation contract (#774)

Status: **first Venusaurite slice implemented in #784–#787**. See the
[player guide](../mega-evolution.md) and [local acceptance report](../testing/mega-core-2026-10-23.md).
Other pairs retain their individual gates; deployment and public stock remain
separate. The original design contract below uses source baseline
`1c36da6f449ce837455a65a1fa616013eee95c62`,
October 22, 2026. The [per-stone rollout](mega-stones.md) assigns every existing
stone to an implementation issue and keeps actual support separate from plans.

## First playable slice

The first allowlisted pair is native **Venusaur holding Venusaurite**, becoming
**Venusaur-Mega**. Ordinary-player activation supports existing single/double
Wild, Trainer and PvP sessions, with one or two active Pokemon per controller.
Only a human-controlled eligible battler may declare it in this slice. Existing
NPC AI never chooses Mega automatically. Scripted/unsupported battle types,
new encounter formats and four-human multi-battles remain outside this release.
The budget is keyed by battle team/side, so adding controllers later cannot
grant additional uses by accident.

Proposed player flow, **available only after the implementation gates close**:

1. Obtain Venusaurite from the deliberately configured source below; inspect it
   with `+inventory`/`+itemdex` and equip it with `+hold 3=Venusaurite` outside battle.
2. Enter an eligible normal battle with that native owned Venusaur active.
3. Use `+mega` in singles, or `+mega A2` / `+mega B1` for your own doubles slot.
4. Choose a legal move with ordinary `+attack`, including its actor/target when
   required. `+mega` reserves a transformation; it is not a separate battle action.
5. Before an action is queued, `+mega [slot] cancel` releases that actor's request.
   A second identical reservation is idempotent and reports the existing request;
   it cannot advance the turn or claim another use. Use the explicit cancel before
   reserving a different ally. Queued actions keep existing no-overwrite rules.

There is no Mega Ring, Key Stone, quest, tower, friendship threshold, recharge,
daily allowance, separate activation currency or plot unlock. A bag copy alone
does not qualify. `+use`, `+item` and ordinary permanent `+evolve` do not activate
a Mega Stone. The equipped stone remains owned, reusable and unconsumed.

## Rules and identity

Use **Generation 7 Mega activation and turn-order semantics**, with the existing
checked-in form stats/types and PF2's current combat engine. This is a mixed PF2
battle ruleset, not a claim that every move/ability uses its Generation 7 version.
Later batches retain current PF2 effects unless explicitly identified below:
the -ate boosts are 1.2; Parental Bond's second damaging hit is 0.25; Snow Warning
sets the existing **snow**, not a new Hail override. Do not rewrite those shared
abilities or other combat generations merely to introduce their Mega holder.

| Venusaur profile | HP | Atk | Def | SpA | SpD | Spe | Types | Ability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Native | 80 | 82 | 83 | 100 | 100 | 80 | Grass / Poison | Saved legal ordinary slot |
| Mega | 80 | 100 | 123 | 122 | 120 | 80 | Grass / Poison | Thick Fat |

These are species base stats, **not final level-scaled battle values**. Compute
final stats with `get_stats`/`get_max_hp`, battle-effective level, IVs/EVs/nature
and the existing Hyper Training overlay. All 47 checked-in canonical pairs have
unchanged HP base stats. Mega never heals or revives, refills PP, grants moves,
changes genetic data, level/EXP, friendship or placement. Preserve current HP,
major status, move slots/PP and battle stages; retain other volatile effects
according to their existing form/ability rules. Apply the new form's native
typing and ability through the normal battle consumers; rebind handlers and
run the legitimate ability-change/start sequence exactly once.

At reservation **and at commit**, validate all of:

- The session/turn is current, waiting for this ordinary controller, and not
  ending; actor is the same conscious active Pokemon in the owned slot.
- A fresh locked owned row has the same trainer and exact native species; a
  canonical party placement or this character's current Fusion reservation
  agrees with the battle roster. Eggs, boxes, foreign owners and inactive Fusion
  reservations reject. Legal current Fusion uses its Pokemon's native identity.
- Both captured native provenance and current species are Venusaur. Derive
  identity from the model and dex, never nickname, display text, substring
  `mega`, a client-supplied `base_species`, copied ability or Transform target.
  Already-Mega, Primal, transient battle forms, transformed/Imposter copies,
  Dynamax and Tera-active/pending actors reject. Legally changed combat abilities
  do not grant species identity and do not alone block a native holder.
- The same equipped stone is present in fresh owned state **and** the current
  battle held slot; its exact metadata maps Venusaur to Venusaur-Mega, whose
  native origin and HP/type/ability profile exist. Bag stock cannot replace a
  removed held item. A wrong stone, unknown form or unsupported pair rejects.
- The team's Mega budget is unused and no different ally owns its reservation.
  Read battle team identity, not a participant-local dynamic boolean alone.

Recheck against fresh SQL values rather than cached Evennia model fields. A
disagreement between SQL and the runtime held slot fails closed before granting
Mega; never repair it by granting or debiting a stone. This retains battle-held
ownership protection and prevents stale or externally changed inputs.

## Timing, side use and unsuccessful choices

There is **one Mega activation per side per battle**, shared by all its active
and reserve Pokemon. Opposing sides have independent uses. A reservation spends
neither a turn nor the use. Persist it immediately, bound to battle identity,
turn, controller, side, owned Pokemon reference, active slot, stone and target.

| Event | Pending request | Mega use | Action / item |
| --- | --- | --- | --- |
| Unsupported pair/context, foreign actor, stale callback, no held stone | No new request | Unchanged | No queue, turn or debit |
| Legal repeated identical request | Keep original request | Unchanged | No extra action or debit |
| Invalid move or move-target input | Keep current request for correction | Unchanged | No move queued |
| Explicit cancel, or legal switch/item/flee choice for this actor | Clear that request | Unchanged | Normal chosen action only |
| Invalid switch/item/flee input | Preserve request and other actors' inputs | Unchanged | Existing rejection policy |
| Actor replaced, fainted or no longer eligible before lock | Clear stale request; explain rejection | Unchanged | Keep separately legal normal move if still executable; otherwise existing legality rejects it |
| Valid request plus legal MOVE action reaches commit | Clear request | Spent once | Transform, then execute normal action; no stone debit |
| Sleep, paralysis, flinch, miss, Protect or immunity later prevents the move | Already cleared | Remains spent | Normal prevention/PP rules; no refund of successful Mega |
| Checkpoint/effect write or unexpected transform failure | Restore prior request and full turn input | Rolled back | Restore runtime/SQL/RNG/messages; never publish false success |

Use the existing pre-move transformation boundary. Revalidate against the actual
locked MOVE action before changing form; a raw `pending_mega` flag is insufficient.
Recompute speed **and move priority** from the resulting form/ability before
ordering ordinary attacks that turn (including Trick Room and a future Prankster
holder). Cross-side transformations resolve deterministically from pre-Mega
modified speed, with normal seeded tie resolution; document/replay that order.
Entry abilities must apply in that order without accidental duplicate starts.
The first slice uses the current PF2 pre-switch lock phase; implementing it
does not reorder the global switch/Tera pipeline or promise complete cartridge
switch-versus-entry-weather timing. Later batches retain that phase: an incoming
Pokemon's switch-in event follows locked transformations. Paired declarations,
weather replacement and switch-in effects must be tested in that order before
enabling the relevant later weather/entry batch.

## Other transformations and suppression

| Interaction | Selected PF2 behavior |
| --- | --- |
| Tera on the same Pokemon | Reject stacking in either order, including pending requests; no silent replacement |
| Tera on a different ally | Separate per-side budget; may reserve/activate in the same turn as Mega on its ally |
| Any currently held Mega Stone and `+tera` | Retain #715's conservative rejection, including deferred stones; no Tera eligibility expansion here |
| Mega after another ally used Tera, or Tera after another ally used Mega | Allowed if that mechanic's own budget and actor are eligible |
| Primal or an item-forced form | Keep existing automatic entry, identity, suppression and cleanup rules; never route through `+mega` or spend its budget |
| Transform, Imposter, copied Mega appearance or nickname | Cannot grant native eligibility or another activation; use existing copying rules after the first slice's guarded entry |
| Magic Room, Embargo, Klutz, generic held-effect suppression | Do not prevent a genuinely held matching stone from enabling Mega; inspect ownership, not `EffectContext.item` alone |
| Ability suppression / Neutralizing Gas / Mold Breaker | Mega form persists; the new ability obeys existing effective-ability rules. Thick Fat is not an unconditional damage reduction |
| Knock Off, Trick/Switcheroo and item-removal consumers | Preserve matching-stone protection before and after Mega, including native-origin matching; no Knock Off removable-item bonus for a protected matching stone. Wrong-holder controls still follow ordinary item rules |
| Rayquaza / Dragon Ascent, Ultra Burst, Z-Moves, new ZA/other definitions, CAP | Ordinary activation remains deferred/excluded; internal hooks or metadata do not widen the allowlist |

No change to Tera is enabled by this design. Its implementation issue must test
both reservation orders and separate actors against current #715 code. Existing
Primal/forced native form and held-item tests remain required regressions.

## Lifetime, persistence and cleanup

A successfully Mega-Evolved Pokemon stays Mega on voluntary/forced switch-out,
on the bench and while fainted. Revival during that battle restores HP under
the ordinary medicine rules and retains the form; it grants no new Mega use.
Re-entry dispatches normal switch-in ability events, not a second activation.

Add a versioned checkpoint contract containing `mega_used` by team and
`mega_pending` declarations, plus each activated Pokemon's native origin,
Mega form, stone, activated marker and restoration profile. Serialize primitive
data for the whole roster, including benched/fainted members. Preserve current
Mega ability/state, types/stats, effective level, HP/status/PP, IV/EV/nature and
Hyper Training context across reconstruction. Rebuild must not rerun activation
or recharge a used side; owned-model type/ability fallbacks must not overwrite
an explicit valid battle snapshot.

For older snapshots, absence of fields defaults to unused only when there is
no evidence of a prior Mega. A dex-confirmed Mega species is evidence even if
dynamic flags were omitted: recover native provenance from validated owned data
and infer that side's used state, without enabling a deferred pair. Ambiguous,
corrupt, foreign or conflicting origin/ledger data reports a recovery error and
fails closed; never silently refill the use or invent an owned species. Old
raw pending flags without a valid bound action are discarded without spending.

Mega form, ability, handlers, declaration, side-use ledger, HP/PP and RNG belong
to the existing complete-turn transaction/checkpoint. Failures restore the same
legal input in runtime and SQL; public success messages follow committed state.
Test a failed write after activation, after another actor's move, and during
checkpoint persistence. Do not add a second independent inventory transaction
or migration to pay for activation.

At end, flee, concession and abort cleanup, perform idempotent Mega-specific
restoration alongside runtime transform restoration: after the current
`PostBattleItems.resolve` step and before strict owned-state sync. Preserve
current real HP/status/PP and established reward/post-battle rules; restore
ordinary runtime species, types, stats and native ability before discarding
the battle. Durable `OwnedPokemon.species`, ordinary ability, genetic data,
held stone and placement never become Mega data. Clear ledgers only with the
ending session's committed cleanup; a failed end/retry cannot reopen a use.
A new battle starts with the native form and a fresh budget. Permanent
`+evolve`/ownership writers remain independent.

## Deliberate acquisition and release

Author one **optional Mega Stone Counter** using the existing configured shop
and normal `+store` Buy menu: initial catalog **Venusaurite only**, price
**10,000**, finite initial stock **1**. These are selected PF2 authoring values,
not canonical prices. The checked-in reference CSV has cost **0**, which must
not become an automatic free offer. No automatic restock, grant, quest reward,
live population or economy rebalancing belongs to the runtime feature.

The content follow-up delivers an opt-in recipe/configuration and directions
from the ordinary shop/help surface. Test normal purchase -> bag -> `+hold` ->
battle -> `+mega` + `+attack` -> switch/rebuild -> end -> unequip, with exact
currency/stock/bag/held counts. Include insufficient funds, empty/disabled shop,
duplicate requests and stone-return negatives. The player uses ordinary
permissions; disposable setup is separate. A correctly configured shop is not
proof that the current world contains or exposes it.

No authored Venusaurite supply route was found in the inspected source search.
The [#772 world snapshot](../testing/item-world-snapshot-2026-10-22.json), taken
at 20:04 UTC on October 22 from an older checkout, had no enabled shops. That
is dated evidence, not a current availability claim. Coordinate source content
with #781 and released ordinary-player acceptance with #782; this design does
not deploy or populate the running world.

After that source issue closes, each later stone batch may add only its named
offers to the optional Counter recipe: the same selected price 10,000 and finite
initial stock 1 per stone. Verify purchase-to-equip-to-effect for each pair in a
disposable shop. Neither an allowlist extension nor an opt-in source recipe is
a live stocking operation; later availability and release remain separately
verified. The remaining batches depend on the initial source recipe as well as
the accepted player route.

## Implementation gates and evidence

The [follow-up table](mega-stones.md#implementation-issues) separates guarded
engine work, persistence/Tera integration, normal command acceptance, optional
source content and nine bounded stone batches. First enable **Venusaurite
only** after engine + persistence + command acceptance pass. Each later batch
adds only its named pairs after fresh effect and normal-route acceptance; an
unreviewed ability interaction becomes a small prerequisite fix, not permission
to mark the entire metadata catalog supported. NPC Mega AI, Rayquaza's move
route, CAP stones and additional definitions need a separate reviewed scope.

Required first-slice evidence:

- Ordinary singles Wild/Trainer/PvP and both sides' doubles slots; owned party
  and current Fusion; exact stats/types/ability and Thick Fat effect with
  meaningful suppression/bypass controls; same-turn order and no extra action.
- Native/nickname/Transform/foreign/egg/box/inactive/wrong-stone/bag-only guards;
  live ownership/placement/held-state rechecks and stale callback/replacement.
- Both sides independently activate once; two allies contend for one team's
  request/use; Tera on the same and different actors in both request orders.
- Cancel and failed-input matrix; status prevention and miss after successful
  activation; switching, faint/revive and multiple rebuilds before/after use.
- Post-activation and whole-turn rollback, failed end/retry, legacy snapshots,
  canonical owned state and held counts after cleanup, and a new battle reset.
- Existing Primal/forced forms, Tera, battle items/field medicine, held removal,
  Hyper Training, progression and reward/checkpoint regressions. Use fresh
  disposable PostgreSQL, targeted effect tests and the mandatory three orders
  after executable changes. Keep local automated, ordinary live, CI, merged and
  deployed evidence separate. #783's unrelated fixture work remains separate.

## Sources and interpretation

The [official Mega Stone guide](https://assets.pokemon.com/assets/cms2-en-uk/pdf/video-game/pokemon-xy/MegaStoneGuide_LowRez.pdf)
identifies species-matched held stones, including Venusaurite. PF2 deliberately
omits its story/Key Stone acquisition prerequisites. The primary simulator's
[Mega action implementation](https://github.com/smogon/pokemon-showdown/blob/master/sim/battle-actions.ts),
[Generation 7 move-order refresh](https://github.com/smogon/pokemon-showdown/blob/master/sim/battle.ts),
[action queue](https://github.com/smogon/pokemon-showdown/blob/master/sim/battle-queue.ts)
and [stone protection](https://github.com/smogon/pokemon-showdown/blob/master/data/items.ts)
inform the mechanical choices above. Its Mega check reads `getItem`, while
[effective held-item suppression is separate](https://github.com/smogon/pokemon-showdown/blob/master/sim/pokemon.ts);
the suppression exception above is an explicit PF2 choice consistent with that
source, not a proposed global exception for other held items. Sources were
reviewed October 22, 2026; their newer definitions do not expand this local list.

Local authority is the pinned dex and the inspected `turns.py`, `battledata.py`,
`state.py`, `logic.py`, `player_choices.py`, `battleinstance.py`,
`terastallization.py`, `effect_context.py` and command registration. Existing
semantic form contracts are internal effect fixtures; they do not prove a player
activation route. The [design validation receipt](../testing/mega-design-2026-10-22.md)
records catalog, link, scope and source checks without claiming implementation.
