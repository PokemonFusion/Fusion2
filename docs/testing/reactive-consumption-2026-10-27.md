# Guarded reactive consumption and recovery — October 27, 2026

Issue [#921](https://github.com/PokemonFusion/Fusion2/issues/921) is accepted on
the frozen local candidate based on `d1cbe5175e1a30a9c25c055aec84e1b5a2afe4b0`, identified by the
eleven Python fingerprints in the [machine receipt](reactive-consumption-2026-10-27.json).
Publication and shared-server deployment are separate.

## Exact scope and behavior

The six items are **Jaboca Berry, Rowap Berry, Kee Berry, Maranga Berry,
Weakness Policy and Throat Spray**. Four berries use the engine's real eating
gates/history. The two non-berries pass UseItem before the existing used-removal
path. Active/effective holding, category, actual damage, sound, fixed damage,
faint and suppression preconditions protect the physical copy. Jaboca/Rowap
retain the reference's fainted-holder retaliation exception; a fainted or absent
attacker cannot activate retaliation. A permitted use produces one removal and
AfterUse notification. Unnerve refuses the berries; a genuinely suppressed
opposing Unnerve does not supply that veto for these reactive hits.

Checkpoint data now stores primitive named item histories and the side recovery
ledger. Rebuilds reconnect canonical item objects without replaying eating,
effects, PP or grants. Explicit malformed histories refuse before partial
replacement; absent legacy history grants nothing. Recycle/Harvest retire every
recovery alias and the corresponding available side entry on successful return.
Existing side-based Pickup retires the matched owner's aliases and refuses an
ambiguous owner. A later theft cannot clone the restored copy. The lifetime
eaten-berry marker survives recovery, independently of recoverable references.
A later non-berry use supersedes the
older berry recovery slot without forgetting that it was eaten.

An AST comparison restricts changes to the eight callbacks belonging to those
six items; all other item callbacks, including #920's 47 Mega Stones and CAP,
remain unchanged. Shared changes are limited to history/gating/checkpoints,
Recycle/Belch history consumers and Harvest/Pickup recovery retirement.

Reference: pinned [item rules](https://github.com/smogon/pokemon-showdown/blob/7e6cea3605c20b44142b2aab22acf08df75ea52b/data/items.ts)
and [eating/UseItem semantics](https://github.com/smogon/pokemon-showdown/blob/7e6cea3605c20b44142b2aab22acf08df75ea52b/sim/pokemon.ts#L1736).
Direct stat writes are deliberately retained for #923. Jaboca/Rowap indirect
damage guards, including their remaining Ripen/Magic Guard work, stay with #925.

## Accepted verification

- **150 new engine cases** qualify real trigger moves, all six consumption/
  Recycle routes, Unnerve, Magic Room/Embargo/Skill Swap, UseItem veto, wrong
  category, Protect, Substitute, multihit, fixed damage and actual KO rules.
  Cheek Pouch, existing Belch callback/post-eat damage, Harvest, Pickup, failed
  recovery, aliases, malformed/legacy data and notification counts are covered.
  Non-native ability/learnset combinations in this mechanics matrix are explicitly
  adapters; the SQL route evidence separately uses native ordinary owned fixtures.
- **325 focused tests passed**, including existing berry/core item,
  native consumption/form, Multi and checkpoint/restore coverage.
- **46 new PostgreSQL command cases passed**: 22 blocked controls, 16 ordinary
  useful outcomes and six post-write rollback/retry cases, plus two mixed-use
  routes. They record
  **734 ordinary command inputs** through real +inventory, +party,
  +hold, +pvp/create/join/start and +attack parsers. Ten routes recover, suppress,
  steal and attempt Recycle again without duplicating a copy. Two more routes
  use actual Trick to receive a
  second physical item, consume it and recover only that newer item. All 46 check
  postbattle item/bag conservation. Native Swoobat Skill Swap supplies Klutz;
  native Unnerve Houndoom and real Gastro Acid provide opposing controls. All
  selected Mew/Swoobat/Houndoom moves and native abilities were checked against
  the pinned primary learnset/Pokedex files; those fingerprints are retained.
- **31 existing held-status-berry and 65 battle-item SQL cases passed**, retaining
  earlier owned-state guards and persistent rollback. Total: **142 SQL cases**.
  Pending inputs and completed states rebuild through production checkpoints.
  Fault injection is separately labelled and never presented as ordinary setup.

| Mandatory fresh process | Passed | Skipped | Duration |
| --- | --- | --- | --- |
| combined | 7,350 | 4,032 | 864.88s |
| repeat | 7,350 | 4,032 | 885.98s |
| battle-first | 7,350 | 4,032 | 742.20s |

All three mandatory orders and the outer gate returned zero. Existing model
registration warnings remain in the receipt; skips are not acceptance proof.
Production and executed offline-test sources stayed frozen for the full gate.
The only Python difference between its source map and final publication is the
standalone SQL fixture's native-species/move correction. The mandatory wrapper
skips that script without its explicit DSN; final-v4 separately qualifies its
46 cases. Both 1,202-file map fingerprints and the exact one-file delta are
recorded. The **25 unrelated dirty paths** retain their baseline bytes/status.

## Diagnosis, cleanup and limits

Fresh pre-fix cases reproduced missing histories and UseItem/Unnerve bypasses.
Eight isolated baseline Recycle/Harvest recoveries demonstrably produced two
held copies after recovery/theft/Recycle; the pinned reproduction source is in
the receipt. Twelve additional cases exposed stale Pickup opportunities before
retirement. Four Gastro Acid/Unnerve cases justified the bounded eating-gate fix.
Eight
additional mixed-use failures justified superseding an old berry slot after a
non-berry use. The earlier incomplete mandatory run was stopped for that repair.
The first complete v2 order then exposed one new empty-history dependency on the
optional catalog. The None fast path now precedes that import; a fresh standalone
regression and existing gender round-trip cover it. Only the complete final-v3
three-order gate qualifies the final source.

Preliminary fixture mistakes (dynamic attributes, entity display names, zero-stage
key normalization and a mistyped path) are retained separately. Two SQL Bite
fixtures encountered flinch during Recycle; legal Aerial Ace/Earth Power moves
isolate recovery without changing flinch. An older Emergency Exit fixture took
a legitimate critical KO; production fainting/damage rules stayed unchanged.
The new test module seeds/restores its own legacy RNG state. Only final frozen
passes qualify this candidate.

A supplemental primary learnset check rejected Tyranitar's Thief/Embargo fixture
slots. Accepted command evidence uses native Unnerve Houndoom with verified
Payback/Swift/Rain Dance/Thief/Embargo. All 46 command cases passed again. Only
that standalone SQL fixture changed during the remaining gate orders; no
production or executed offline-test code changed. Earlier Tyranitar command
observations are not accepted normal-player proof.

Evidence is local automated engine and production-command/model PostgreSQL with
captured transport, **not a Telnet/WebSocket login, shared release, public stock
or natural move-learning certification**. Native rows, known legal moves,
nickname and stock are labelled separate prerequisites. Disposable schemas use
direct model tables without migrations/integrity triggers. No human fixtures,
game data, world stock or Evennia service changed; the private schemas were
removed and the task-owned cluster stopped empty.

Belch's existing DisableMove callback/history is verified, including after
recovery, and post-eating damage works. Direct engine actions do not invoke
that move callback as a generic pre-eating selection guard; this repair does
not certify that broader route. Pickup eligibility remains its existing side
model; the bounded one-copy ledger and ambiguity refusal are qualified here.
Canonical stat and indirect-damage facets remain open under #923/#925. Plot-only,
CAP and other backlog work remain excluded.
