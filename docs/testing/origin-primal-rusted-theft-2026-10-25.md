# Origin, Primal and Rusted removal identity — October 25, 2026

Issue [#857](https://github.com/PokemonFusion/Fusion2/issues/857), tracker #852.
Baseline `54275b1d67669a839b3cf6575a6d55d1d588bdf1`. This repair changes exactly
seven existing `onTakeItem` methods and reuses the unchanged `HeldItemIdentity`
helper and physical removal dispatch from #855. It adds no item or source.

## Exact rules

| Item | Native family | Roles that protect removal | Existing item form |
| --- | --- | --- | --- |
| Adamant Crystal | Dialga | Holder or source | Dialga-Origin |
| Griseous Core | Giratina | Holder or source | Giratina-Origin |
| Lustrous Globe | Palkia | Holder or source | Palkia-Origin |
| Blue Orb | Kyogre | Holder only | Kyogre-Primal |
| Red Orb | Groudon | Holder only | Groudon-Primal |
| Rusted Sword | Zacian | Holder or source | Zacian-Crowned |
| Rusted Shield | Zamazenta | Holder or source | Zamazenta-Crowned |

Each rule accepts the known canonical base and special form. None requires an
ability for removal protection. Nicknames, unknown invented forms and foreign
copied appearances cannot qualify. Native base identity survives Transform.
Item suppression does not disable physical removal protection. Native/current/
untransformed form-entry checks remain separate and unchanged.

These policies come from the [pinned Showdown item source](https://github.com/smogon/pokemon-showdown/blob/7e6cea3605c20b44142b2aab22acf08df75ea52b/data/items.ts).
The local reference matches Git blob `95103d8d5c0da5a646adc074d73610546f933757`.
Origin/Rusted items compare the native species number in either role. Primal
Orbs' callback names its second argument `source`, but it is the physical
holder: the argument occupies the normal `pokemon` position. Its
`baseSpecies.baseSpecies` compares the canonical family; [Species defaults
that field to its name](https://github.com/smogon/pokemon-showdown/blob/7e6cea3605c20b44142b2aab22acf08df75ea52b/sim/dex-species.ts#L280).
It therefore includes dormant/base Kyogre/Groudon as well as Primal forms.
Requiring the active form, an ability, or a native thief would be incorrect.

## Reproduction and ordinary commands

The 364 new offline cases produced **317 failures / 47 passes** before the
repair, then all passed. They use real dex items, native project stats/HP and
actual damaging Thief, Knock Off, Trick and Switcheroo. Controls include exact/
prefix foreign names in both roles; base/special native holders and sources;
absent abilities; Magic Room, Embargo and Klutz; wrong families and malformed
adapters; legitimate form entry/reversion guards; and actual Transform.

The **237 owned-player PostgreSQL cases** cover every exact item through:

- Default/exact/prefix foreign holder names, default/Buddy native holders and
  a foreign source using the protected species' nickname.
- Capture nickname-menu inputs, normal `+hold 3=<item>` and `+attack` commands,
  actual damage/removal and the correct saved PP cost.
- Thief, Knock Off, Trick and legal Hypno Switcheroo; two-item Shed Shell swaps;
  actual Magic Room and Embargo; an occupied thief and native Sticky Hold.
- Two queued checkpoint restores, two post-turn restores, real battle end and
  normal unhold into the correct owner's bag.
- Missing stock and an injected post-debit held-save failure, with complete
  SQL/bag/cache/placement/move snapshots unchanged.

Dialga and Palkia additionally use legal native-source Trick, including default
names and occupied swaps. Other native source-role theft/copy tests are
explicitly offline adapters; they do not claim unlearned ordinary moves.
Native idle moves are legal Safeguard or Zacian's Iron Defense. Native abilities
are checked before the first attack: genuine Pressure costs two PP, Primal
weather is present, Crowned entry grants one boost, and restores cannot replay
entry boosts or repair missing callbacks. Real seeded prevention and accuracy
remain enabled. No callback outcome or move effect is forced.

The shared Plate fixture adds an optional PP cost, defaulting to one, and
records it in the receipt. Other Plate assertions remain unchanged. The new
suite overrides only the seven-item preparation, native form assertions and
restore invariants. It borrows the existing real command/lifecycle checks.

SQL and runtime held slots are checked independently, including explicit empty
slots. Attacks/restores cannot change bags or caches. Raw inventory rows plus
physical held copies are independently summed; theft/swaps preserve the two
setup copies, protected items return to the original owner, and a successfully
Knocked Off foreign item cannot reappear. All source/genetic fields and
canonical placements remain unchanged, and both players' battle locks clear.
Owned source species/nicknames remain intact even when runtime form entry
changes display names. The [machine report](origin-primal-rusted-theft-2026-10-25.json)
retains per-case commands/state, per-item matched damage and source hashes.

## Diagnosed ability defect and separate repair

The first pilot stopped at case 3: the old fixture assumed one PP, but real
native Pressure charged two after restore. Correcting that expectation exposed
case 18: fresh form entry installed a display-only `Ability(raw={})`, so Thief
spent one PP before restore and two afterwards. This was a separate runtime
defect, not permission to weaken the PP check.

[#872](https://github.com/PokemonFusion/Fusion2/issues/872) fixes canonical form
ability installation in a separate commit. It also prevents redundant startup
for an unchanged ability and gives changed-ability startup and Primal weather
cleanup the proper owner/battle context. Focused failures exposed and retained
the stale weather-End argument and duplicate Crowned boost cases. Its
[separate report](item-form-abilities-2026-10-25.md) describes that repair.
Earlier diagnostic logs/receipts are retained; the final replay freezes both
repairs together and never counts earlier loaded code as current acceptance.

## Qualification and boundaries

The frozen replacement candidate passed:

- **364 new removal regressions** and **11 form-ability regressions**.
- **1,513 focused tests**, plus **46 existing runtime-hook tests** after the
  ability display correction.
- **237 ordinary-command/PostgreSQL cases**: 223 completed removal battles and 14
  rejected equip attempts, replayed against the final 1,128-file Python manifest.
- **556 compatibility PostgreSQL cases**: 212 Plates, 258 Memories/Drives and 86
  legendary boosters.
- **Three fresh full orders**: combined, repeat and battle-first each finished
  with **6,045 passed / 4,028 skipped**; the wrapper completed cleanup and exited
  zero. Default optional/explicit-DSN skips are not represented as acceptance;
  the scoped PostgreSQL suites above ran explicitly. No new hosted CI claim.

The approved task-only PostgreSQL fixture is stopped with zero disposable
schemas and zero public tables. All 25 unrelated dirty shared-checkout paths
remain byte-for-byte unchanged. Publication keeps the six-file #872 repair
separate from the eight-file #857 repair; qualification covers their combined
frozen candidate, not an untested intermediate commit alone.

Matched foreign default/exact/prefix/source-name Thief cases each lost34 HP
and transferred the genuine item. Native default/Buddy holders agreed:

| Item | Native HP loss | Native form retained | Thief PP charged |
| --- | --- | --- | --- |
| Adamant Crystal | 15 | Dialga-Origin | 2 |
| Griseous Core | 34 | Giratina-Origin | 1 |
| Lustrous Globe | 17 | Palkia-Origin | 2 |
| Blue Orb | 18 | Kyogre-Primal | 1 |
| Red Orb | 12 | Groudon-Primal | 1 |
| Rusted Sword | 4 | Zacian-Crowned | 1 |
| Rusted Shield | 4 | Zamazenta-Crowned | 1 |

Native damage is not compared against foreign Mew damage: real typing,
calculated stats, legitimate abilities and normal move order differ. Native
items remain held, owned source forms do not leak into persistent species,
and returned stock stays with the correct owner.

The PostgreSQL harness creates/drops only a new random disposable schema on the
previously approved task-owned loopback fixture. Tagged encounter/capture
finalization and bag grants are labelled prerequisites; nickname/equip/attack/
unhold are actual ordinary command handlers. Captured transport and manager
lookup are adapters. This is automated local command/model acceptance, not
released socket QA, public acquisition or hosted CI acceptance.

Reproduce with `python -B -m pytest -q -o addopts=
pokemon/battle/tests/test_origin_primal_rusted_theft_identity.py`, then
`python -B tests/integration/origin_primal_rusted_theft_cases.py` with an explicit
disposable `PF2_TEST_POSTGRES_DSN`. `PF2_ORIGIN_PRIMAL_RUSTED_EVIDENCE` names a
task-owned JSON receipt path. Full qualification uses
`python -B tools/run_mandatory_tests.py`.

The separate [existing Knock Off power discrepancy](plate-theft-identity-2026-10-25.md#separate-pre-existing-move-power-discrepancy)
is unchanged; these checks qualify removal and persistence. Mega Stone removal,
CAP Vile Vial, new forms, plot-only items and new acquisition are excluded.
Historical reports and all 25 unrelated dirty paths in the shared checkout
remain unchanged. #859/#860 retain reporting/released-acceptance scope.
