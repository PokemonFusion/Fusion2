# Native stat and critical items — October 25, 2026

Issue: [#853](https://github.com/PokemonFusion/Fusion2/issues/853), under tracker
[#852](https://github.com/PokemonFusion/Fusion2/issues/852). Source baseline:
`08c1f3a7d9299ecc842e9b6685168334d5c7eb9b`.

The nine existing items below now use canonical native species identity instead
of nicknames or unrestricted critical bonuses. The product change consists of
one shared identity helper and ten callbacks across these nine items. No item
definitions, acquisition sources, removal protections or plot routes change.

## Exact eligibility and reference

The pinned [Showdown item implementation](https://github.com/smogon/pokemon-showdown/blob/7e6cea3605c20b44142b2aab22acf08df75ea52b/data/items.ts)
was read from the local checkout at that commit. Its working `data/items.ts`
matches Git blob `95103d8d5c0da5a646adc074d73610546f933757`; normalized SHA-256:
`5163ddf04fc8928ac07c1bd40841ccc285ac1eb4544e84b24274cfe28cc41d1f`.
This is a pinned identity/eligibility reference, not a claim of full simulator
damage parity or support for every form's acquisition/activation.

| Item | Native species/forms | Bonus | After genuine Transform |
| --- | --- | --- | --- |
| Light Ball | Pikachu and dex forms whose canonical base species is Pikachu | ×2 Attack and Special Attack | Retained for native Pikachu; copied Pikachu cannot grant it |
| Thick Club | Cubone, Marowak, Marowak-Alola, Marowak-Alola-Totem | ×2 Attack | Retained for those natives |
| Deep Sea Scale | Clamperl | ×2 Special Defense | Retained for native Clamperl |
| Deep Sea Tooth | Clamperl | ×2 Special Attack | Retained for native Clamperl |
| Metal Powder | Native/current Ditto, untransformed | ×2 Defense | Disabled |
| Quick Powder | Native/current Ditto, untransformed | ×2 Speed | Disabled |
| Lucky Punch | Chansey | +2 critical stages | Retained for native Chansey |
| Stick | Farfetch'd, Farfetch'd-Galar | +2 critical stages | Retained for those natives; Sirfetch'd excluded |
| Leek | Farfetch'd, Farfetch'd-Galar, Sirfetch'd | +2 critical stages | Retained for those natives |

The current Pikachu base-species set is Pikachu, Cosplay, Rock-Star, Belle,
Pop-Star, PhD, Libre, Original, Hoenn, Sinnoh, Unova, Kalos, Alola, Partner,
Starter, Gmax and World. These are exact known dex identities, not accepted
name prefixes. The JSON report enumerates complete canonical display names.
Gmax eligibility here does not add a Gigantamax activation route.

`HeldItemIdentity` reuses `resolve_dex_entry`, `normalize_name` and dex
`baseSpecies`. It reads the preserved battle `base_species`; it never consults
the holder's display `name`. An untransformed standalone adapter can provide a
real `species` if it has no base identity. Missing/unknown identities and copied
adapters without an authoritative base fail closed. Powder checks also require
the current native Ditto species and reject transformed state.

## Reproduced defects and repair

Running the new 82 regressions against the baseline produced **40 failures and
42 passes** (including the new helper's absence). Native nicknames lost stat
and Lucky Punch bonuses; foreign species could gain effects with the right
nickname; Stick and Leek had unrestricted critical bonuses. The repair replaces
those eligibility decisions while retaining each item's multiplier and the
existing effective-item suppression dispatch.

The final offline cases cover real dex items, renamed natives, exact/prefix-like
foreign nicknames, legitimate regional/special forms, Stick versus Leek,
Magic Room/Embargo/Klutz, actual damage and real Transform in both directions.
Transform tests execute the move and check native/current identity; they do not
merely set a flag. Powders deliberately differ from the other seven items.

## Ordinary owned-player flow

The **52 fresh PostgreSQL cases** use new tagged ordinary characters and
canonical party slot 3, production encounter capture finalization, the actual
capture nickname menu (`yes`, then `Buddy` or a foreign species-spoof nickname),
ordinary `+hold`, a persistent PvP BattleSession and both players' `+attack`
commands. Setup creates native level-50 Pokémon with legal active moves,
project-calculated stats/HP, and separately grants two held-item copies.
Foreign Mew controls use its own Pound/Swift/Transform/Iron Defense moves.
Capture finalization is an explicit setup boundary; this is not a full wild
encounter/ball-command walkthrough or proof that players can obtain the stock.

Each item has native, foreign nickname, queued checkpoint, missing-stock and
injected-save rollback cases. Seven also have Magic Room cases applied by an
actual opponent move. Native Ditto cannot idle to isolate a normal suppression
turn; its three suppression modes are isolated in the offline regressions.
There are 34 paired outcomes, 86 hold receipts, 82 complete battle turns,
52 nickname-menu receipts, 68 battle-end receipts and nine rollback receipts.

The queued cases rebuild the saved session twice while the native action is
waiting for the opponent, then execute the actual turn. SQL rows, bags, inventory
cache, held state, placements, HP and move PP are retained before/after.
Battle end releases the battle lock and preserves the held item. Save-fault
checks prove the command catches its error and rolls back both inventory and
held state; a subsequent ordinary equip/removal returns both copies to the bag.
The transport adapter captures output and resolves only these new players;
ordinary command parsing, ownership, inventory and battle effects remain real.

Matched native results with nickname **Buddy**, unheld → held:

| Item / normal action | Exact modifier | Observed result |
| --- | --- | --- |
| Light Ball / Quick Attack | Attack 60 → 120 | 11 → 21 outgoing damage |
| Thick Club / Bone Club | Attack 55 → 110 | 22 → 43 outgoing damage |
| Deep Sea Scale / incoming Swift | Special Defense 60 → 120 | 46 → 24 incoming damage |
| Deep Sea Tooth / Water Gun | Special Attack 79 → 158 | 15 → 28 outgoing damage |
| Metal Powder / incoming Pound before Transform | Defense 53 → 106 | 31 → 16 incoming damage |
| Quick Powder / Transform | Speed 53 → 106 | Ditto changes from second to first, then genuinely transforms |
| Lucky Punch / Pound | Critical stages 0 → 2 | Noncritical 3 → critical 4 damage |
| Stick / Peck | Critical stages 0 → 2 | Noncritical 21 → critical 31 damage |
| Leek / Peck | Critical stages 0 → 2 | Noncritical 21 → critical 31 damage |

All paired actions use seed 853 with the normal RNG. No hit, critical roll,
damage or callback success is replaced. The `use_move` wrapper only observes
execution order. Suppressed and foreign-nickname controls match the unheld
damage; renamed native positives retain the exact expected modifier. Quick
Powder's changed action order also changes which defenses Swift encounters;
its different damage is a consequence, not a separate damage multiplier claim.

## Validation and retained diagnostics

- **82 new offline regressions passed** within **447 focused tests** covering
  ordinary item runtime, native forms, copied moves and historical reconciliation.
- **52 new ordinary-command/PostgreSQL cases passed** on the final fixtures.
- **48 compatibility PostgreSQL cases passed:** incense 40; remaining items 8.
- **Required fresh full gate passed in all three orders:** combined, repeat and
  battle-first each passed **5,001 tests / 4,028 skipped**. Each ran in a fresh
  process with generated callback coverage enabled and no ambient pytest args.
- **16 explicit PostgreSQL suite wrappers passed.** The offline gate has no
  explicit PostgreSQL DSN. Its 14 database-only wrapper skips are qualified
  separately, together with the two existing placement/graph wrappers; these are
  suite wrappers, not an additional count of 16 individual gameplay scenarios.
  They cover ownership, Fusion, trading, market, daycare, breeding, gyms,
  onboarding, Multi Battle, communication, sheets and all three Necrozma suites.
  The remaining 4,014 skips are opt-in dex/Showdown coverage.
- **1,119 Python source files** are frozen for final qualification. The report
  pins relevant code/test/workflow hashes and the full manifest digest.
- The PostgreSQL controller confirmed zero disposable schemas, zero public
  tables and stopped only the task-owned loopback fixture after these checks.
- The unrelated shared checkout's 25 dirty paths remain byte-identical to the
  recorded preservation snapshot; no shared product files were written.

The first PostgreSQL pilot was **34 passed / 18 failed**. Diagnosis found nine
wrong test expectations that a handled `+hold` save error would escape, seven
Magic Room preludes blocked by the chosen Protect action, and two foreign-Ditto
fixture assumptions. The fixture now asserts the handled rollback message and
actual injected save boundary, uses legal nonprotecting idle moves, and checks
the holder's real base identity. No unrelated Protect/field-target repair was
made here. Its exact failed commands, state and log remain retained.

Subsequent fixture improvements use legal foreign Mew attacks and ordinary Peck
for the Stick/Leek critical comparison. The earlier Slash/Leaf Blade sample was
already critical without the item, so it was insufficient to demonstrate the
critical outcome difference. The final Peck controls explicitly assert a
noncritical unheld result and critical held result without forcing rolls.
Two early full-gate attempts were deliberately stopped before results while
these fixtures were refined; they are retained as interrupted, not passing gates.

The [JSON report](native-stat-items-2026-10-25.json) retains per-item cases,
effect-relevant before/after state, commands/output, exact run counts, durations,
source and log hashes, diagnostics and cleanup. Complete raw snapshots/logs
remain in ignored `.codex-artifacts/item-native-853-20261025/`. Passing logs can
contain existing dependency/cache warnings; warning-free execution is not claimed.

Rerun offline regressions with `PF2_NO_EVENNIA=1` and
`python -B -m pytest -q pokemon/battle/tests/test_native_stat_items.py -o addopts=`.
Run `python -B tests/integration/native_stat_item_cases.py` only with an explicit
`PF2_TEST_POSTGRES_DSN` for disposable PostgreSQL; its guarded schema is always
removed. Set `PF2_NATIVE_ITEM_EVIDENCE` to retain raw receipts. The lifecycle CI
workflow now includes that entry point; hosted completion is not asserted.
The full gate is `python -B tools/run_mandatory_tests.py`.

## Evidence boundary

This is local automated ordinary-command/model/full-turn acceptance using real
private PostgreSQL and captured session transport. It is separate from a fresh
socket login, released-server acceptance, hosted CI, item obtainability and
deployment. [#860](https://github.com/PokemonFusion/Fusion2/issues/860) retains
the released-candidate walkthrough. No migrations, PF2-Dev operations, existing
game database changes or human Pokémon/character edits occurred.

Legendary bonuses, Plates/Memories/Drives and special removal protections,
status berries, wider reporting/acquisition work and new definitions remain in
their separate tracker children. Historical reports remain unchanged. Plot-only
items, CAP expansion and unrelated battle UI work stay outside this change.
