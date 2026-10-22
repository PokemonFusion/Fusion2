# Smoke Ball held escape (#759)

Smoke Ball is a reusable held item. Equip it outside battle with
`+hold <canonical party slot>=Smoke Ball`, then use the ordinary `+flee`
(`+battle/flee`) command during an eligible wild encounter. It guarantees escape
for the living acting holder, including against Arena Trap, Shadow Tag and
Magnet Pull. The bag, bench, partner and opponent cannot lend this effect to a
different acting Pokemon. The held copy is not consumed or awarded back to the
bag when escaping; ordinary `+hold <slot>=` removal returns it normally.

The existing-item gate in #747 and held-item repairs/evidence #752/#757 precede
this addition. The definition uses the normal supplemental gameplay metadata,
complete normalized name lookup, equip/inventory/itemdex interfaces, Held Items
category and the existing price source's 4000 reference cost. It does not stock
live shops or grant items. Existing optional shop/reward configuration can offer
it deliberately, as with the other supplemental items.

## Effective item and encounter policy

The run-action consumer uses `EffectContext.item`, so Klutz, Magic Room, Embargo
and explicit item suppression disable the guarantee without removing ownership.
Removing or replacing the item disables its effect. Suppressing Klutz restores
the item's eligibility through the ordinary effective-ability rules. Ordinary
Run Away and speed/formula escape continue to operate as before.
Explicit item/ability suppression flags now serialize with each Pokemon;
old snapshots default to unsuppressed. Embargo and Magic Room use their existing
volatile/field checkpoints. An explicit empty held item remains empty on reload.

Encounter restrictions are checked **before** item or ability guarantees:

- Trainer, NPC trainer and PvP battles cannot be escaped with Smoke Ball.
- A server-authored wild battle can set `battle.flee_allowed = False` to forbid
  all running, including Smoke Ball and Run Away. This Boolean is persisted in
  `BattleState.flee_allowed` at the existing checkpoint boundary and survives
  session rebuild. Old checkpoints default to allowing normal wild fleeing.
- No player command can change this flag. Scripts must set the runtime policy
  and save through the existing session checkpoint when configuring a battle.
- Invalid, fainted, benched or foreign acting Pokemon cannot supply an escape.
  A completed battle is not reopened or given a new flee result by a retry.

Smoke Ball bypasses the ordinary trapping abilities handled by the flee route;
this change does not redefine switching traps or introduce new trap mechanics.
It does not grant universal/script/trainer escape or a travel action.

## Capture separation

Capture items are classified by exact canonical item metadata (`isPokeball`),
never the text suffix `ball`. Smoke Ball has no capture capability. This rule is
shared by the battle item command, current and legacy queues, restored item
declarations and final engine dispatch. Unknown `... Ball` names fail closed.
Existing real Poke Balls retain their metadata and normal capture behavior.

`+item Smoke Ball` explains that it must be held and used through `+flee`;
it never queues a capture, debits an item or manufactures an escape item action.
Legacy/restored/direct item actions cannot turn it into a capture either.
This adds no new capture ball, Poke Doll/Toy, plot-only item or story unlock.

## Validation boundary

Automated tests exercise the ordinary equip/flee command path, real battle
sessions, durable snapshots, suppression/removal, failed/restricted attempts,
capture controls, shared-instance/rollback behavior and session rebuild in
isolated PostgreSQL schemas. Session transport and controlled fixture setup are
recorded separately. Local command/model proof does not establish a live login,
main merge, hosted CI completion or deployment.
