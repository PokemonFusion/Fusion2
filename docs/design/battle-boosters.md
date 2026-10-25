# Manual battle booster contract (#871)

Accepted design scope after repair/report gates. No item is enabled by this design. Unsupported
names must continue to reject before declaration, PP, inventory or turn changes.

## Selected generation and exact batch

Use a Generation7+ effect baseline: six X items add two relevant stat stages;
Dire Hit applies Focus Energy's +2 critical stage; Guard Spec. creates Mist
on the acting side for five turns. These are named effects, never an arbitrary
callback loaded from inventory metadata. The pinned RHH
[item table](https://github.com/rh-hideout/pokeemerald-expansion/blob/44bc3e0473b85d8e254c8dbc9004ac2d7b0a5fb3/src/data/items.h)
selects the post-Gen7 X amount and separate Focus Energy/Mist effects. The
pinned Showdown [Focus Energy condition](https://github.com/smogon/pokemon-showdown/blob/7e6cea3605c20b44142b2aab22acf08df75ea52b/data/moves.ts#L6190)
adds two critical stages; its [Mist condition](https://github.com/smogon/pokemon-showdown/blob/7e6cea3605c20b44142b2aab22acf08df75ea52b/data/moves.ts#L12526)
has five-turn duration and filters negative boosts with source/effect context.

| Exact item | Effect | Optional future finite offer |
| --- | --- | --- |
| X Attack | Attack +2 |1000, stock 5 |
| X Defense | Defense +2 |1000, stock 5 |
| X Sp. Atk | Special Attack +2 |1000, stock 5 |
| X Sp. Def | Special Defense +2 |1000, stock 5 |
| X Speed | Speed +2 |1000, stock 5 |
| X Accuracy | Accuracy +2 |1000, stock 5 |
| Dire Hit | Focus Energy, +2 critical stages |1000, stock 5 |
| Guard Spec. | Side Mist, five-turn protection |1500, stock 5 |

Prices are selected PF2 policy; no automatic refill, resale, machine, source
grant or world installation. Do not import unsupported plot/capture items.

## Ordinary declaration and spending

Use the existing `+item [acting slot] <full name>=<target slot>` route. Require
an ordinary controller, one conscious current owned active actor and that same
actor as target for X items/Dire Hit. Guard Spec. uses that actor to identify
its existing battle side; it is not a new cross-controller targeting command.
Initially accept only existing two-participant wild/trainer/PvP single/double
formats; reject unreviewed four-controller and other formats before declaration.
Do not change medicine/capture format policy to implement boosters.

Discovery lists exact names, actor selection, effects and restrictions. Fresh
bag stock and native ownership/reservation checks belong to declaration and
execution, not just the menu. Missing stock, unsupported input, wrong/foreign/
fainted/bench target, unreviewed format and already capped/no-effect state
reject before reserving an action. Preserve valid sibling declarations.

A useful execution costs one actor action and one bag copy, atomically with
the effect. Existing shared whole-turn rollback handles a stale ownership,
identity, inventory or checkpoint conflict; do not publish half a turn. If an
otherwise legal queued effect becomes redundant because of earlier normal
actions, the actor's action is spent but no copy is debited (selected PF2
no-effect policy). Do not refund opponents' legitimate actions, PP or residuals.
One last copy cannot satisfy competing requests; pending saves/reconnects
cannot replay a paid action or reuse another actor's declaration.

## Effects and lifecycle

X stages use the shared boost service with source/effect identity and ±6 caps.
Simple/Contrary participate through normal change/try-boost events; test both
actual changed stages and resulting damage/order/accuracy. No direct assignment
that skips abilities, negative-stage caps or side protections. The UI must
explain ability-modified outcomes. No effect means no changed relevant stage.
Stages reset through existing switch/faint/end policy; never persist to owned
base stats or overwrite EVs/IVs/Nature.

Dire Hit reuses the real Focus Energy volatile. An already active copy is
no-effect; other critical bonuses combine under the existing critical cap and
Battle Armor/Shell Armor prevention. Ordinary switching clears it; preserve
only a deliberately supported normal Baton Pass interaction. It must survive
checkpoint/reconnect once and clear at faint/end under the reviewed volatile
policy. Prove real critical hits and blocked criticals, not only a stage value.

Guard Spec. reuses a side condition. Count the activation turn under normal Mist
residual timing, retain the condition when the user switches/faints, clear it
at expiry/battle end, and reject repeat use while active rather than refreshing
its timer. Test blocked opposing Growl/Intimidate, legal self-debuff and Haze/
Clear Smog, ability-modified boosts and Infiltrator where supported. Preserve
source/controller/side identity across doubles and checkpoint reconstruction.

Magic Room and Klutz suppress held effects, not these bag activations. Select
an explicit Embargo rejection for the new target route; keep existing medicine
behavior unchanged. Heal Block does not suppress a stat/critical/Mist effect.
Keep these decisions separate from ordinary move prevention and held-item
consumption. No hidden callback fallback may bypass eligibility.

## Bounded implementation and proof

Create three issues: six X items plus shared declaration/execution/persistence
foundation; Dire Hit critical effects; Guard Spec. side protection/duration.
The latter two depend on the foundation. Each requires actual `+item`, useful
and no-effect controls, normal suppression/ability interactions, final-copy
contention, queued/partial/outer rollback, restored pending actions, reconnect,
switch/faint/end cleanup and inventory conservation. Preserve ordinary battle
medicine and unsupported-input safety. Separate local offline/SQL evidence,
source publication, optional acquisition and deliberately released socket QA.

The current source audit found Focus Energy in
`pokemon/dex/functions/moves/damage_moves.py:2052` and an explicit Focus Energy
critical consumer in `pokemon/battle/damage.py:1131`. Bind the new bag route
through the normal volatile/event system and prove it cannot double-count.
`Contrary.onChangeBoost` and `Simple.onChangeBoost` are in
`pokemon/dex/functions/abilities_funcs.py:618,2947`; X items must use this event
path rather than assigning stages. Whole-turn medicine declaration/execution
and owned synchronization remain in `pokemon/battle/turns.py` and
`pokemon/services/battle_items.py`.
The concrete boost entry is `pokemon/utils/boosts.py::apply_boost`; the existing
`pokemon/battle/utils.py` wrapper and `ZEffects.start` use that same service.

Mist currently has a boolean `side.screens` marker and a broad `onTryBoost`
return in `pokemon/dex/functions/moves/damage_moves.py:4322-4342`. This is a
**known implementation prerequisite**, not accepted Guard Spec. support:
its follow-up must prove five-turn structured duration and correctly filter
only relevant negative changes with source/effect context. Do not add Guard
Spec. by calling the existing broad handler and declaring success. Keep the
repair inside that bounded future implementation issue with ordinary Mist
regressions and no unrelated move parity claim.
An offline native probe starts the real battle with Lapras50/Water Absorb and
Eevee100/Run Away, uses legal Mist then opposing Growl, and observes Attack-1
both with and without Mist. The boolean screen also remains after five
residuals, with no callback failures. This is a confirmed reused-condition gap,
not a Guard Spec. player test; its implementation issue owns the repair/proof.

Implementation follows the linked issues below. This is a source/design
audit, not runtime booster acceptance.


## Implementation follow-ups

This closes the design/scoping deliverable only. Runtime effects, source installation,
migration/release operations and ordinary acceptance remain with these open issues.

| Issue | Exact delivery | Dependencies |
| --- | --- | --- |
| [#907](https://github.com/PokemonFusion/Fusion2/issues/907) | Add six X items with guarded manual battle action persistence | #871 |
| [#908](https://github.com/PokemonFusion/Fusion2/issues/908) | Implement Dire Hit with actual Focus Energy critical outcomes | #871, #907 |
| [#909](https://github.com/PokemonFusion/Fusion2/issues/909) | Implement Guard Spec. with timed source-aware Mist protection | #871, #907 |

Scope/source checks: [2026-10-25 decision receipt](../testing/item-scope-decisions-2026-10-25.md).
