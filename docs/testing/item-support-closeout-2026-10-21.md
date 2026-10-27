# Existing held-item support reconciliation — 2026-10-21

Issue [#757](https://github.com/PokemonFusion/Fusion2/issues/757) is a bounded
verification deliverable for existing in-policy items. The
[current matrix](battle-item-support-2026-10-21.json) accounts for **576 loaded
definitions: 283 retained battle/reward items and 293 explicit exclusions**.
Every retained item names its tested-context status, exact effect/evidence
pointers and finite rerun batches. Plot-only content and new item definitions
remain outside this work.

## Reusable fixture repair

- Recycle now starts at **49% HP** in both the catalog generator and supplemental
  effect plan. Entry consumes its real Oran Berry and heals above half HP; after
  Recycle restores it, the berry remains held. The catalog asserts both the empty
  initial item and restored final item. A **20% HP negative control** proves that
  consuming the restored berry again is a legal outcome.
- The paired ability runner now has durable Mycelium Might cases: **Good as Gold
  bypass positive**, **Limber cure negative**, and **Electric-type immunity
  negative**. Each pair changes only the user's ability. The negative pairs are
  marked `positive_trigger: false`; successful negative controls are not counted
  as positive-effect proof.
- Six native battle regressions execute these generated definitions through
  real dex moves/items, entry, action order and residual processing. They are
  offline battle proof, not new Telnet command acceptance. Existing battle
  mechanics and the native held-item form fixes are unchanged.
- The separate accuracy-only commit `df4e01f` seeds the real 90% Thunder Wave roll
  in the existing single-move immunity test. Its **27 tests passed** before the
  #757 work. It preserves the distinction between temporary move-time bypass
  and Limber's later completed-turn cure.

## Reconciled historical evidence

The final [post-form-repair report](full-battle-postformfix-2026-10-20.md) and
[JSON observations](full-battle-postformfix-2026-10-20.json) are the authority for
the retained local-player scope: **426/426 PvP effect checks**, **570 final battle
templates**, **8/8 reward effects plus one control**, **92 native/foreign holder
eligibility cases**, and **17 Plate power comparisons with identity/stat guards**.
The new matrix points into that report and retains exact compressed-case hashes.

Today's read-only archive audit rehashed all **570 PvP and nine reward/control
archives**, with **zero mismatches**. All **126 pinned runtime source files** in
the selected battle/dex/helper/service scope still match the historical local
bytes. This comparison is bounded to the pinned files; it does not certify every
file in the checkout or qualify new field routes. Git newline conversion is
handled separately for the portable matrix's published-text identity.

The chronology is explicit; prior reports and raw observations are unchanged:

| Snapshot | Meaning |
| --- | --- |
| [Original matrix](battle-item-matrix-2026-10-20.json) | Initial failures: 49 checks failed and two chance branches were unobserved; superseded for current battle-effect status |
| [Post-repair sweep](full-battle-items-postrepair-2026-10-20.md) | Declared effects passed after the original item repairs |
| [Forced-form repair](forced-form-item-repair-2026-10-20.md) | Additional native/foreign-holder and calculated-stat eligibility proof |
| [Final post-form-repair sweep](full-battle-postformfix-2026-10-20.md) | Fresh local-player sweep of the repaired snapshot, including task-local fixture corrections |
| [Current reconciliation](battle-item-support-2026-10-21.json) | Durable reusable fixtures, per-item final evidence pointers, bounded lists and fresh automated checks |

The historical sweep's build was based on `fd402f9` plus the then-uncommitted form
repair; that repair and its reports were subsequently published in `87bb3c0`.
The earlier report's statement that the reusable fixtures still needed correction
describes its historical state; the first section above resolves that remaining
work. Earlier missing field medicine/berry routes are addressed separately by
[field medicine](field-medicine-2026-10-20.md) and
[field berries](field-berries-2026-10-20.md).

## Bounded verification plan

The matrix fixes **18 batches**, each with exact item names, check labels and
case keys. Each has a maximum of **25 items / 50 battle templates** and a **zero
new-check budget**. Counts can overlap between families where an item has several
effects; the unique PvP total remains 570 templates. Preserve negative controls
and the declared seed/context on rerun. File newly discovered unrelated defects
as separate bounded issues before expanding these lists.

| Family | Batches | Exact lists |
| --- | --- | --- |
| Stat/type modifiers | `stat-type-1` through `stat-type-4` | Matrix `batches`, including species, critical, weight and type outcomes |
| Hit/stat-drop/consumable triggers | `hit-consumable-1` through `hit-consumable-6` | Berry, Gem, recovery, threshold, hit and natural-gift contexts |
| Accuracy/priority | `accuracy-priority-1` and `accuracy-priority-2` | Accuracy hit/miss, order, choice, flinch and multihit contexts |
| Field duration/trapping | `field-trapping-1` and `field-trapping-2` | Duration, trapping, suppression, prevention, switching and lifetime contexts |
| Item identity/forms | `identity-form-1` | Native form/ability and evolution-negative contexts; per-item supplemental eligibility pointers |
| Existing medicine/shared protocols | `medicine-protocol-1` and `medicine-protocol-2` | Battle medicine, targeting, invalid/no-effect and shared consumption protocols |
| Reward items | `rewards-1` | Eight named reward items and the ninth control encounter |

Current core coverage remains in
[core runtime](../../pokemon/battle/tests/test_item_core_runtime.py),
[diagnosed effects](../../pokemon/battle/tests/test_diagnosed_item_effects.py),
[additional effects](../../pokemon/battle/tests/test_additional_item_effects.py),
[remaining effects](../../pokemon/battle/tests/test_remaining_item_effects.py),
[native forms/persistence](../../pokemon/battle/tests/test_native_form_and_postbattle_items.py) and
[form eligibility](../../pokemon/battle/tests/test_forced_item_form_eligibility.py).
These include actual dex item assignment,
normal actions/residuals/switches, suppression, removal/replacement, one-shot
consumption, owned-state synchronization and serialized rebuild/checkpoint tests.
The retained effect rows also link to concrete normal-player battle observations.
Callback contracts and assignment smoke remain a separate, weaker evidence type.

## Fresh verification

Results and reproducible commands are in the
[machine-readable closeout report](item-support-closeout-2026-10-21.json).
The final affected selection passed **522 tests**, including **six reusable
fixture regressions and nine reconciliation/false-claim checks**. All three
mandatory runs passed **4,348 tests each**, with **4,014 skipped each**:

| Fresh process | Passed | Skipped | Duration |
| --- | --- | --- | --- |
| Combined | 4,348 | 4,014 | 204.36 seconds |
| Repeat | 4,348 | 4,014 | 204.85 seconds |
| Battle-first | 4,348 | 4,014 | 183.58 seconds |

Skipped cases remain outside the enabled gate scope. Existing Django model-reload
and shared pytest-cache permission warnings are retained in the logs; these runs
do not establish PostgreSQL integration or live-player acceptance.

One preliminary combined run used the earlier matrix format while its portable
text identity was being corrected, so its stale-matrix equality check failed
(4,346 passed / one failed). It is retained as nonqualifying evidence, superseded
by the finalized three-process gate above. No battle mechanics defect was found.

The affected selection includes the reusable generators/evaluators, reconciliation
false-claim controls, core held items, the preserved native form tests and the
separate accuracy fixture. The mandatory gate runs the full ordinary and battle
suites in three fresh processes, including callback tests.

## Publication and acceptance boundaries

Fresh automated proof, historical ordinary-player localhost proof, staging
publication, main-branch integration and remote deployment are separate. This
closeout performs no service reload, migration, remote deployment or new live
player session. The current matrix's retained statuses qualify only their
declared tested contexts; they do not claim all 428 audit entries or all 576 dex
definitions are supported.

The 293 exclusions retain per-item reasons. Evolution gaps remain with
[#755](https://github.com/PokemonFusion/Fusion2/issues/755) and
[#756](https://github.com/PokemonFusion/Fusion2/issues/756); new items #758–#762
remain behind the existing-item gate. Acquisition, full Mega/Z support,
probability distributions, every combined interaction and public-server
acceptance are separate work. Player command/help guidance remains with
[#731](https://github.com/PokemonFusion/Fusion2/issues/731); this change adds no
commands and makes no new availability promises.
