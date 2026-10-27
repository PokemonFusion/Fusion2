# Native legendary held-item boosters — October 25, 2026

Issue: [#854](https://github.com/PokemonFusion/Fusion2/issues/854), under
[#852](https://github.com/PokemonFusion/Fusion2/issues/852). Baseline:
`3cc9295ef13585beedcda75d344b611e6f07ed9a` (#853 completed).

Exactly seven existing `onBasePower` callbacks now use #853's unchanged
`HeldItemIdentity` helper. Nicknames and copied appearances no longer grant
foreign holders a legendary type boost or remove renamed natives' bonuses.
All seven retain their existing integer `int(base_power * 1.2)` modifier.

## Exact policy and pinned reference

The [reference item implementation](https://github.com/smogon/pokemon-showdown/blob/7e6cea3605c20b44142b2aab22acf08df75ea52b/data/items.ts)
was read from the local checkout at that commit. `data/items.ts` matches Git blob
`95103d8d5c0da5a646adc074d73610546f933757`, normalized SHA-256
`5163ddf04fc8928ac07c1bd40841ccc285ac1eb4544e84b24274cfe28cc41d1f`.
Its power rules use native `baseSpecies.num`; the shared helper resolves the
corresponding canonical species/form families without trusting display names.
The reference uses a fixed-point `[4915, 4096]` factor; PF2 retains its existing
integer ×1.2 power conversion. Full simulator damage parity is not claimed.

| Existing item | Native identities permitted by the power rule | Matching types |
| --- | --- | --- |
| Adamant Orb | Dialga, Dialga-Origin | Steel, Dragon |
| Adamant Crystal | Dialga, Dialga-Origin | Steel, Dragon |
| Lustrous Orb | Palkia, Palkia-Origin | Water, Dragon |
| Lustrous Globe | Palkia, Palkia-Origin | Water, Dragon |
| Griseous Orb | Giratina, Giratina-Origin | Ghost, Dragon |
| Griseous Core | Giratina, Giratina-Origin | Ghost, Dragon |
| Soul Dew | Latias, Latios, Latias-Mega, Latios-Mega | Psychic, Dragon |

All seven native-base bonuses survive actual Transform. A foreign Mew copying
any of these appearances gets no bonus, including when its new display name
matches the species. Unknown prefix-like species are not known dex identities.
This is power eligibility only: listing a Mega identity does not enable a new
Mega profile, simultaneous Soul Dew/Mega Stone holding or a new form source.

The existing native/current/untransformed form-entry guards remain unchanged.
Adamant Crystal, Lustrous Globe and Griseous Core still enter their legitimate
Origin forms; foreign exact/prefix nicknames cannot trigger that entry. The
Origin item entry can reset a native's runtime display name, so this report does
not claim every renamed Origin holder originally lost its power bonus. Owned
nicknames remain independently checked. Existing form abilities and calculated
stats remain governed by the existing form code, not by a new item policy.

All item-removal callbacks, including the three Origin `onTakeItem` methods,
remain unchanged for [#857](https://github.com/PokemonFusion/Fusion2/issues/857).
The code-scope check confirms exactly seven changed methods, all `onBasePower`.

## Reproduction and offline qualification

The new **125 offline cases** produced **60 failures / 65 passes** on the
baseline, then all 125 passed after the seven-callback repair. They execute real
dex moves and damage with project-calculated stats/HP, alongside exact power
checks. Default/renamed native holders, exact/prefix foreign names, both boosted
types, nonmatching Swift, Magic Room/Embargo/Klutz, genuine Transform in both
directions and native/Origin/Latios/Mega identity controls are included.

Paired native damage tests construct identical current forms, so Origin stat
changes cannot masquerade as a power modifier. The copied-state fixtures assign
Transform to native holders to exercise the engine; they do not claim that those
species normally learn Transform. Foreign player copy cases use Mew's legal
Transform below. Soul Dew's Mega identities are offline eligibility controls,
not ordinary activation acceptance.

## Ordinary owned-player acceptance

**86 PostgreSQL cases passed** using actual nickname-menu input, `+hold` and both
players' `+attack` commands through persistent production PvP sessions. Tagged
ordinary characters use canonical party slot 3 and genuine owned rows, native
abilities, legal moves, level 50, Hardy nature and zero IVs/EVs. Targets use
explicit defensive EVs/nature. HP and stats come from project helpers.

Each item has twelve cases: primary Dragon move, second boosted type, default
name, foreign exact name, foreign prefix name, nonmatching move, Magic Room,
Embargo, queued restore, genuine foreign Transform, save-fault rollback and
missing stock. Soul Dew has two additional ordinary Latios cases, covering
Dragon and Psychic independently of the Latias cases.

Source prerequisites are explicit tagged encounter creation plus production
capture finalization and a two-copy stock grant. Actual capture nickname-menu
inputs either decline a nickname or choose Buddy/the spoof name. This is not
proof of wild encounter/ball commands or current public obtainability.

Native entry, owned species/nickname and held state are retained separately.
The queued comparisons rebuild the saved session twice while an action waits
for the opponent. Magic Room/Embargo are applied by actual moves and also rebuilt
twice before the attack. Foreign Mew genuinely transforms into the relevant
native opponent, keeps native base Mew, then attacks without the item boost.
Battle end releases locks and preserves original owned species and held stock.
SQL HP/PP, placements, bags, inventory cache and runtime states are retained.
Normal uncopied attacks assert a one-PP debit against the saved move row; copied
move state is retained separately, with broader copied-move regressions included.

Seven injected post-debit held-save failures verify the handled command error,
full inventory/held/cache rollback and a successful subsequent equip/remove.
Seven missing-stock attempts leave the full state unchanged and retain their
command/error receipts. No human character or Pokémon is a fixture.

These cases retain **72 paired outcomes**, **186 full battle turns**, **158 hold
receipts**, **144 native-entry and 144 battle-end receipts**, **86 nickname-menu
receipts**, and seven rollback plus seven missing-stock receipts. The borrowed
#853 command/turn transport uses seed **853** with normal RNG; no hit, damage,
critical roll or callback success is substituted. Offline damage uses seed 854.

Matched native Buddy results, unheld → held:

| Item | Dragon Pulse power / damage | Second matching move power / damage |
| --- | --- | --- |
| Adamant Orb | 85 → 102 / 57 → 69 | Flash Cannon 80 → 96 / 54 → 64 |
| Adamant Crystal | 85 → 102 / 57 → 69 | Flash Cannon 80 → 96 / 54 → 64 |
| Lustrous Orb | 85 → 102 / 57 → 69 | Surf 90 → 108 / 61 → 72 |
| Lustrous Globe | 85 → 102 / 57 → 69 | Surf 90 → 108 / 61 → 72 |
| Griseous Orb | 85 → 102 / 39 → 46 | Shadow Ball 80 → 96 / 72 → 86 |
| Griseous Core | 85 → 102 / 39 → 55 | Shadow Ball 80 → 96 / 72 → 104 |
| Soul Dew / Latias | 85 → 102 / 42 → 51 | Psychic 90 → 108 / 22 → 27 |
| Soul Dew / Latios | 85 → 102 / 49 → 60 | Psychic 90 → 108 / 26 → 32 |

Origin entry can change stats and action order, so these ordinary equip damage
comparisons are not a claim that all HP differences come solely from ×1.2 power.
The exact emitted power is checked separately. Foreign, copied and nonmatching
controls with matched stats retain unheld damage. Suppressed copies emit unheld
power and preserve ownership; native Origin stat differences remain legitimate.

## Diagnostics, gates and cleanup

The first PostgreSQL pilot was **85 passed / one failed fixture assertion**.
Held Palkia-Origin used Water Pulse before its target could act: the real attack
dealt 48 damage and caused confusion, after which Mew lost another 23 HP while
failing its queued Safeguard action. The naive whole-turn HP comparison saw 71,
not the move's emitted 48. The saved volatile state identifies Water Pulse as
the confusion source. This was a valid secondary effect, not a broken booster.
The final player comparison uses legal Surf to isolate Water damage. Offline
Water Pulse coverage remains. Both the failed commands/state and corrected run
are retained; no unrelated confusion or action-order code was changed.

- **594 focused tests passed**, including the 125 new cases, #853's 82 cases,
  forced-form guards, incense, copied moves and historical reconciliation.
- **86 new ordinary-command/PostgreSQL cases passed.**
- **100 existing-item PostgreSQL cases passed:** #853 native items 52; incense
  40; remaining recovery items 8.
- The supplemental explicit database sweep had **15 passing wrappers / one
  unchanged Necrozma lifecycle concurrency assertion failure**. Its full 22-case
  suite passed a fresh isolated replay. The failure is retained separately below;
  the initial sweep is not described as wholly passing.
- **Required three-order full gate passed:** combined, repeat and battle-first
  each passed **5,126 tests / 4,028 skipped** in fresh processes with generated
  callback tests enabled and ambient pytest arguments cleared. The offline
  orders skip 14 explicit-DSN wrapper checks; their supplemental outcomes and
  baseline race diagnosis are recorded separately rather than hidden in skips.
- **1,121 Python sources** are frozen; source and log digests are in the JSON.
- The shared identity helper, form engine, removal methods and historical
  reports remain unchanged. The unrelated shared checkout's 25 dirty paths are
  preserved against the task-start snapshot.
- The task-only PostgreSQL fixture is stopped. Its controller verified zero
  disposable schemas and zero public tables after all checks and diagnostics.

The supplemental failure is the unchanged
`test_races_against_field_use_placement_release_and_old_cycle_keep_one_custody`
at `tests/integration/necrozma_lifecycle_cases.py:417`: it expected one
`PlacementError` but observed zero. The fresh full 22-case replay passed. Private
diagnostics then restored only the seven power methods from baseline `3cc9295`
in memory and repeated the original threaded race ten times: **eight passed,
two reproduced the same assertion**. All seven power-hook call counters stayed
zero. Separate serialized-order controls passed for baseline/current callbacks.
The service and test files are byte-identical to the baseline. This establishes
a pre-existing, scheduling-sensitive lifecycle assertion outside this repair;
it does not establish its root cause or resolve it. No unrelated service/test
fix was included. Failed logs, outcome/state observations and successful replay
are retained; the diagnostic controls are not claimed as a clean broad gate.

The [JSON report](legendary-item-identity-2026-10-25.json) retains exact per-item
cases/forms/types, both damage comparisons, projected native command/SQL state,
all outcome/diagnostic indexes, raw receipt ranges, run/source hashes and cleanup.
Full raw logs and snapshots remain in ignored
`.codex-artifacts/item-legendary-854-20261025/`. Passing logs include existing
dependency/model/cache warnings; warning-free execution is not claimed.

Rerun offline with `PF2_NO_EVENNIA=1` and
`python -B -m pytest -q pokemon/battle/tests/test_legendary_item_identity.py -o addopts=`.
For an explicitly disposable `PF2_TEST_POSTGRES_DSN`, run
`python -B tests/integration/legendary_item_cases.py`; guarded schemas are removed
on exit. `PF2_LEGENDARY_ITEM_EVIDENCE` retains raw receipts. Lifecycle CI now
includes this entry point; hosted completion is not asserted. The full fresh
gate is `python -B tools/run_mandatory_tests.py`.

This is fresh local automated ordinary production-command/model/full-turn
acceptance with real isolated PostgreSQL and captured session transport. It is
separate from a new socket login, intentionally released-server acceptance,
hosted CI, acquisition and deployment. [#860](https://github.com/PokemonFusion/Fusion2/issues/860)
retains released-candidate QA. Fixtures create model tables and install existing
integrity-trigger definitions only within disposable schemas. No migration
executor, existing-database migration, existing game service, PF2-Dev, new
definition, plot-only item, CAP expansion or unrelated product change is
included. Other repair families retain their separate acceptance criteria.
