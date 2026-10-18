# Terastallization

September Week 4 (#715) supports the 18 standard Tera types and Stellar in
ordinary singles and doubles Wild, Trainer and PvP battles. Each side may
Terastallize once per battle, including across switches, disconnects and battle
rebuilds. There is no item, Orb or recharge requirement.

## Player commands

Use `+tera` before choosing a move with `+attack`. Singles can omit the actor;
doubles must specify their own slot, such as `+tera A2` or `+tera B1`.
`+tera A2 cancel` releases that actor's reservation before its action is queued.
The command does not spend an action. The transformation locks before moves;
a switch, item or flee choice discards the reservation without spending Tera.
An inactive, fainted or replaced actor cannot consume it. Queued or stale
commands cannot overwrite another choice. The log announces the transformation
and the battle HUD identifies the active slot and Tera type, including A2/B2.

The Pokemon's stored `tera_type` is configuration, separate from the current
battle transformation. Existing blank values use the Pokemon's first ordinary
type; invalid nonblank values are rejected. This release does not add a player
type-changing economy or editor.

## Supported Generation 9 rules

- Standard Tera replaces defensive typing with its one type. The Pokemon keeps
  1.5x STAB for its previous types, gains 1.5x STAB for the new Tera type, or
  receives 2x STAB when its Tera type already matched a previous type.
- Adaptability follows the current defensive type: 2x for that type, or 2.25x
  when the matching original Tera type already supplied 2x STAB.
- Matching damaging moves below 60 base power become 60, except priority,
  multi-hit and qualifying variable-power moves. Struggle receives no Tera STAB
  or power floor.
- Stellar keeps the pre-Tera defensive types. The first damaging use of each
  move type receives 2x STAB for an original type or 4915/4096 (approximately
  1.2x) otherwise. Later uses return to ordinary STAB. A single use shares its
  boost across every hit and spread target. Damage previews consume nothing;
  the spent-type ledger survives switching and rebuilds. Stellar bypasses
  Adaptability's STAB modification. Its 60-power floor applies to any move type
  while that type's boost is unused, with the same priority, multi-hit and
  variable-power exceptions. Later uses lose this floor along with the boost;
  every target of one spread use shares the first-use floor.
- Tera Blast is Normal, Special, 80 power before Tera. After Tera it uses the
  Tera type and whichever of the staged Attack and Special Attack is higher
  (ties stay Special), before ability/item stat modifiers. Stellar Tera Blast
  has 100 power, is neutral against ordinary targets and 2x against any
  Terastallized target, and lowers the user's Attack and Special Attack one
  stage after a successful damaging use.
- Type-changing callbacks cannot overwrite Tera defensive typing. Battle end
  restores ordinary runtime types and clears temporary Stellar state without
  writing battle types into owned Pokemon records.

Scripted battles and species-specific Ogerpon/Terapagos transformations are
rejected in this release. Mega/Primal forms, transformed Pokemon and active
Dynamax are incompatible. Dynamax, Z-Moves and special-species Tera behavior
remain separate work.

The rule references are [the official Tera Blast introduction](https://www.pokemon.co.jp/ex/sv/ja/battle/220822_02/),
[the primary simulator's damage and Tera implementation](https://github.com/smogon/pokemon-showdown/blob/master/sim/battle-actions.ts),
and [its move definitions](https://github.com/smogon/pokemon-showdown/blob/master/data/moves.ts).

## NPC policy and persistence

Existing AI profiles do not Terastallize. The explicit `trainer_tera` profile
reserves its side's use on its first eligible, selected damaging move that
matches its Tera type, or Tera Blast; Stellar permits any selected damaging
type. It refuses a currently immune target and reads no hidden opponent moves
or choices. Active slots are evaluated in stable order, so only one ally can
reserve the side's use. The policy is deterministic; the profile disables
random score variation.

Existing room NPC encounter specifications accept `tera_type`, including
Stellar. Static NPC templates use the ordinary primary-type fallback. Encounter
battle snapshots carry the resolved configuration without new database fields.

Pokemon checkpoints contain configured type, active Tera type, original types
and consumed Stellar types. Battle checkpoints contain used sides and pending
reservations. A failed transactional turn restores the declaration, side use,
typing and Stellar ledger alongside HP/PP; rollback also refreshes Evennia's
cached owned models so party views reflect the restored database state.

## Validation and activation

Run `pytest -q tests/test_terastallization.py --run-callback-tests -o addopts=`
and the mandatory normal/repeat/battle-first gate with
`python -B tools/run_mandatory_tests.py`. With an explicit disposable PostgreSQL
DSN, `python tests/integration/terastallization_cases.py` exercises normal
singles/doubles commands, checkpoints, rollback, cleanup and NPC authoring.
The lifecycle CI workflow includes these checks and migration rehearsals.

No migration is required. Activating the code on the running game requires an
approved service restart. Automated command tests do not substitute for live
player acceptance. Nothing in this PR installs a new gym or changes an existing
trainer's AI profile.
