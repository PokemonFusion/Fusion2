# Native non-plot Ultra Burst contract (#865)

Accepted design scope after the six repair gates and #859. The accepted two-form Necrozma
lifecycle and its sixteen-signature Z inventory remain historical completed
work. This design does not release Ultra or reinterpret #831's acceptance.

## Pinned reference versus PF2 policy

Showdown `7e6cea3605c20b44142b2aab22acf08df75ea52b` defines
[Ultra eligibility and its separate side limit](https://github.com/smogon/pokemon-showdown/blob/7e6cea3605c20b44142b2aab22acf08df75ea52b/sim/battle-actions.ts#L1876),
[the crystal/source/native identity](https://github.com/smogon/pokemon-showdown/blob/7e6cea3605c20b44142b2aab22acf08df75ea52b/data/items.ts#L6966)
and [Light That Burns the Sky](https://github.com/smogon/pokemon-showdown/blob/7e6cea3605c20b44142b2aab22acf08df75ea52b/data/moves.ts#L10751).
The real item is Ultranecrozium Z. Native Dusk Mane/Dawn Wings may enter Ultra;
the signature uses Photon Geyser, Psychic type,200 power, normal single target,
inherent accuracy and ability-ignoring behavior. Physical category applies when
the reference's `getStat('atk', false, true)` comparison exceeds the corresponding
Special Attack value; ties remain Special. This includes ordinary stored stat
stages, while skipping ModifyBoost and ModifyAtk/ModifySpA event modifiers
([getter definition](https://github.com/smogon/pokemon-showdown/blob/7e6cea3605c20b44142b2aab22acf08df75ea52b/sim/pokemon.ts#L581)).
Implement that comparison with stage, tie and modifier controls rather than
guessing from the move's ordinary category. Existing Neuroforce governs
super-effective damage. Reference facts do not prescribe PF2 custody, commands,
PP access or transactions; those selected rules follow.

## Genuine sources and preparation

Use only an existing live native combination proven by its exact host,
companion, owner, storage, lifecycle, reservation and active/displaced source
binding. The host remains the same persistent Dusk Mane/Dawn Wings owned row;
the companion remains frozen in its existing combined placement. Never store
an independently granted Ultra row or invent a missing partner. Human trainer
Fusion is a separate system and cannot act as native pair proof.

Photon Geyser is already a real native base-Necrozma move. The Gen9 reference
lists level 72, but PF2's ordinary capture/learning route includes legitimate
cross-generation level-up sources and already accepts Gen7 level 50. Released
#860 QA captured native level-50 Necrozma with actual Photon knowledge and an
active slot. Preserve that existing access; introduce no extra level-72 gate.
See the [preparation correction and source evidence](../testing/ultra-photon-preparation-erratum-2026-10-25.md).
Require legitimate base-Necrozma knowledge and an ordinary active slot before
combining. Preserve Photon in a different slot from the selected temporary
Sunsteel Strike/Moongeist Beam binding. A Photon source displaced by combining,
stored-only knowledge or a free slot cannot be activated while linked. Separate,
choose the legitimate active set normally, then recombine if necessary.
No automatic teaching, PP transfer from the companion, refill on combine,
shadow source slot or arbitrary source/level grant. Ordinary Photon and the signature
spend that exact current learned/active slot with existing PP boosts/caps.
Selected PP policy: activation itself neither pays nor refills Photon and may
proceed with Photon at0 PP if the actor's chosen ordinary attack is otherwise
legal. Signature execution separately requires current positive Photon PP.
Legitimate intervening PP changes must not be mistaken for a custody violation
or undone; recheck current source identity/eligibility and apply normal move
prevention without refunding another actor's lawful actions.

## Player declaration, form and budgets

Add discoverable `+ultra [acting slot]` preview/declaration before a normal
attack, alongside the existing native pair inspection. Confirmation binds this
controller, battle, current turn/slot/host/lifecycle, held crystal, ability,
source states and reviewed profile. It grants no standalone action or effect.
Selected UI policy: the command opens an explicit terms preview with **yes/no**.
Yes revalidates and saves the pending declaration; no makes no reservation or
resource change. The actor must still submit its ordinary attack. Do not open
the preview after that actor already has an action queued. An unconfirmed menu
may be reopened after reconnect with fresh terms; confirmed pending state uses
the durable checkpoint. Changed terms/turn require a fresh preview, never a
silent stale yes. Normal cancellation clears only that actor's uncommitted
Ultra declaration before execution and cannot refund an already spent side use.
Revalidate exact proof at the committing turn; cancellation, changed terms,
missing/foreign/fainted/egg/boxed actors, invalid pair, Transform/Imposter,
nickname/directly authored fused/Ultra identities and contradictory locks fail
without spending PP, inventory, side use or an action.

Require the legitimate current paired form and active native Prism Armor before
activation; reject copied/replaced/suppressed native ability. The real crystal
is physically held and reusable, following current Z physical-crystal policy
under Magic Room/Embargo/Klutz. Those effects must not grant an ability or relax
native proof. At execution switch only runtime species/type/calculated stats
to existing Necrozma-Ultra and install real Neuroforce with explicit owner
context. Use native project stats/HP helpers, retain damage/status/sleep and
all earned progression. No persistent genetic/owned species mutation.

Before activation, the current ability must be native unsuppressed Prism Armor.
After valid activation, ordinary ability replacement/suppression remains normal
battle state: the native Ultra proof persists, while Neuroforce boosts only when
actually active. The signature does not regrant Neuroforce or require that a
legitimate later ability change be undone. Reconnect preserves current ability
state without replaying Start. Switch/reset, faint/revival and ending follow
the explicit native form cleanup below; no borrowed runtime ability may leak
into the owned host or companion.

One Ultra activation per existing battle side, with pending/used state separate
from the Z budget. Ultra itself neither requires nor spends an unused Z budget.
The same actor cannot stack Mega/Tera or another pending incompatible mechanic.
An Ultra actor may use the signature only on a **later completed turn**, with
an unused existing side Z budget, real held crystal and its current ordinary
Photon slot/PP. This later-turn restriction is explicit PF2 policy. Signature
execution spends source PP and the Z budget exactly once; activation never
creates Photon PP. Other actors retain only their existing independently
reviewed mechanics and budgets. No mass signature/native allowlist relaxation.

## Persistence, lifecycle and recovery

Record versioned Ultra pending/active/used proof in the existing checkpoint,
including prior paired form/ability, host/lifecycle, activation turn and profile
fingerprint. Rebuild validates current SQL custody and learned source before
reconstructing runtime state. A queue restart cannot transform twice, refill,
regrant Neuroforce or pay twice. Bind exactly the relevant current request;
corrupt or stale proof requires existing recovery, never a guessed form.

Selected PF2 lifecycle: ordinary switch-out retains Ultra for that battle;
fainting reverts runtime to the current legitimate paired form with HP0, while
the side's Ultra use stays spent. Revival cannot reactivate Ultra. Battle end,
abort and recovery restore the current paired form/ability, retaining actual
HP/status/PP/progression. Separation outside battle uses the unchanged two-row
service and preserves the host's current progress; no old Ultra snapshot may
overwrite newer data or the companion. Pending activation cannot block safe
custody recovery. All form/ability/budget/PP/item writes and notifications share
the existing whole-turn transaction and outer-commit boundary.

## Implementation gates

Create four manageable issues: native eligibility/Photon preparation contract;
versioned pending/active checkpoint and switch/faint/end/rollback lifecycle;
ordinary command/actual Ultra and signature effects; and deliberately released
two-player acquire→learn→combine→equip→activate→signature→reconnect→recover QA.
First prove each base source was genuinely obtained and Photon learned through
ordinary current routes. Cover both forms, all spoof/copy/foreign sources,
zero/stale PP, displaced slots, wrong/missing crystal, ability replacement,
dual-controller side contention, cancellation, partial/outer rollback, native
Neuroforce and category/damage controls, Protect/immunity/ability-ignoring rules,
post-faint revival and safe separation with the companion baseline unchanged.

The current source audit confirms that `pokemon/services/necrozma.py` and
`necrozma_moves.py` own real source custody, temporary move resources and safe
separation; `pokemon/battle/necrozma.py::NativeNecrozmaBattle` validates live
pair provenance. `ZMoves.native`, `binding`, `begin` and `rebuild` in
`pokemon/battle/z_moves.py` currently reject an Ultra shortcut or missing
explicit profile. `OwnedBattleActor.item_key` intentionally reads physical
crystal ownership independently of suppression. `Pokemon.from_dict` and native
form rebuilds must gain only the new explicit proof path, never trust a saved
Ultra species string. These current guards are implementation constraints;
the source audit does not claim they already support Ultra.

No Ring/Key/quest/story flag, direct fused/Ultra grant, broad crystal activation
or public source is included. Operator releases/migrations remain explicit
environment/build plans. Implementation follows the linked issues below;
closing this design will not certify runtime or deployed support.


## Implementation follow-ups

This closes the design/scoping deliverable only. Runtime effects, source installation,
migration/release operations and ordinary acceptance remain with these open issues.

| Issue | Exact delivery | Dependencies |
| --- | --- | --- |
| [#885](https://github.com/PokemonFusion/Fusion2/issues/885) | Bind Ultra eligibility and legitimate active Photon preparation | #865 |
| [#886](https://github.com/PokemonFusion/Fusion2/issues/886) | Persist Ultra declaration and reversible battle lifecycle | #865, #885 |
| [#887](https://github.com/PokemonFusion/Fusion2/issues/887) | Add guarded Ultra command and Light That Burns the Sky | #865, #886 |
| [#888](https://github.com/PokemonFusion/Fusion2/issues/888) | Qualify both Ultra lifecycles on a released build | #865, #887 |

Scope/source checks: [2026-10-25 decision receipt](../testing/item-scope-decisions-2026-10-25.md).
