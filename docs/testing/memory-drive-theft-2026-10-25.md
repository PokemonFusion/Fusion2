# Native Memory and Drive removal protection — October 25, 2026

Issue: [#856](https://github.com/PokemonFusion/Fusion2/issues/856), under
[#852](https://github.com/PokemonFusion/Fusion2/issues/852). Source baseline:
`fd04c31a9263bba489347328e91e56a932cb2efe` (#855 completed).

Exactly 21 existing `onTakeItem` callbacks now reuse the unchanged
`HeldItemIdentity` helper. A Memory is protected when either holder or source
is natively Silvally; a Drive is protected when either is natively Genesect.
Known type/Drive forms resolve to their canonical family. Renaming cannot
change eligibility, and foreign exact/prefix nicknames or copied appearances
cannot grant it. Native base identity survives genuine Transform.

## Exact reference and boundaries

The [pinned reference item rules](https://github.com/smogon/pokemon-showdown/blob/7e6cea3605c20b44142b2aab22acf08df75ea52b/data/items.ts)
were read from the local checkout. `data/items.ts` matches Git blob
`95103d8d5c0da5a646adc074d73610546f933757`, normalized SHA-256
`5163ddf04fc8928ac07c1bd40841ccc285ac1eb4544e84b24274cfe28cc41d1f`.
All 17 Memories check native base species 773, and all four Drives check 649,
for both participant roles. There is no ability condition on removal
protection. The shared canonical helper implements that family identity without
consulting display names. Unknown/fabricated species names do not qualify.

RKS System's native/current/untransformed form-entry checks remain separate.
Genesect's existing Drive form rules, both native signature-move type routes,
abilities, item suppression and owned battle persistence are unchanged. The
engine is byte-for-byte unchanged from #855, including its physical `TakeItem`
exception under Magic Room, Embargo and Klutz. No item definition, form source,
move mapping, ability rule or acquisition route is added.

The [machine-readable report](memory-drive-theft-2026-10-25.json) records the
21 rules, per-item command/state outcomes, exact source hashes, qualification
commands, retained failure diagnosis and independent owned-state checks.
Reference move, event and learnset files were also checked against their pinned
Git blobs. Historical reports and the support matrix remain immutable.

## Offline reproduction

The new **325 offline cases** produced **241 failures / 84 passes** on the
baseline, then all 325 passed after the 21-callback repair. Every item has
matched default/exact/prefix foreign-holder Thief controls, exact/prefix foreign
source names, default/renamed native holder and source controls, missing-ability
protection, wrong native-family controls, and canonical form/malformed adapter
checks. All 21 native item forms execute real Multi-Attack or Techno Blast with
their existing item-selected type and actual damage.

Representative Fire Memory/Burn Drive cases cover Thief, Knock Off, Trick and
Switcheroo under Magic Room, Embargo and Klutz, and genuine Transform in both
native and foreign directions. Real dex items/moves, project `get_stats` and
`get_max_hp`, actual prevention/damage/removal and the shared removal harness
are used. Callback/metadata presence alone is not accepted as support.

Native-source Thief, native Transform and native Klutz are explicitly assigned
offline policy adapters. Neither Silvally nor Genesect learns Thief, Covet,
Knock Off, Trick, Switcheroo, Metronome, Mimic or Transform in the pinned
learnsets. These tests do not create or claim an ordinary native theft route.
Foreign Mew uses legal Thief; ordinary native signature-move coverage is below.

## Ordinary owned-player flows

The reusable Plate harness now accepts a fixture tag, native family and native
ability mapping. Its default Plate configuration is preserved and separately
replayed. This issue borrows its real command, capture nickname-menu, equip,
turn, snapshot, restore, rollback, battle-end and stock-conservation checks;
it does not inherit the Plate test methods or weaken their assertions.

Each of the 21 items has ten separately counted cases:

- Foreign Mew with default name, exact Silvally/Genesect nickname and corresponding
  Imposter prefix: a normal Mew's Thief transfers exactly one item.
- Native Silvally/Genesect with default name and Buddy nickname: Thief damages
  it but cannot remove its item. Legitimate native form entry is retained.
- A foreign Mew thief named after the native species: its name cannot block
  transfer from a foreign holder.
- A queued-action case with two restores before the opponent acts, then two
  completed-turn restores: empty old-holder slots and new ownership persist.
- Missing stock and an observed post-debit held-save fault: complete SQL,
  placement, move, bag/cache and runtime snapshots remain unchanged.
- Native Multi-Attack/Techno Blast through `+attack`: observation of the real
  executed action confirms the item-selected type, positive damage and a
  one-PP saved debit. Two restores retain native form and physical holding;
  battle end retains the owned source and item, followed by ordinary unhold.

The remaining 48 representative Fire Memory/Burn Drive cases cover Knock Off,
Trick and Switcheroo against foreign/native holders, two-item Shed Shell swaps,
all four removal moves under actual Magic Room, Thief under actual Embargo, an
occupied thief and native Sticky Hold Gastrodon. Switcheroo uses Hypno with
Insomnia, not an invented Mew learnset. Native source-role protection is tested
offline; foreign source-name protection is exercised through legal player Thief.

Only new tagged Player characters, owned rows and private rooms are used.
Both sides use canonical party slot 3, level 50, Bold nature, zero IVs and
252 HP/252 Defense EVs, with HP/stats calculated by project helpers. Native
holders have RKS System or Download and their legal Iron Defense/signature
move. Opponents use ordinary Mew/Hypno moves. Normal seeded RNG and actual
targets, move legality, prevention, effects and PP remain intact.

Tagged encounter creation, production capture finalization and two-copy stock
grants are labelled prerequisites. The real capture nickname menu, `+hold`
and `+attack` are player command acceptance. This is not proof of wild/ball
commands or public item obtainability. Native form entry may reset runtime
display names; the original owned nickname and source species are checked
independently. Captured transport and the optional manager lookup are adapters;
this is local automated command/model acceptance, not released socket QA.

## Persistence and conservation

The 258-case inventory consists of **195 removal battles**, **21 native typed
move battles** and **42 rejected equip attempts**. Each removal/typed move
checks exactly one saved PP debit. Suppressed native items remain physically
held and protected; foreign holders lose the item normally. Swaps preserve
both items and the correct participant roles. An occupied thief and a real
Sticky Hold holder preserve the original items.

The shared removal checks compare both SQL held slots and runtime items,
including explicit empty slots, before and after two completed-turn restores.
Queued cases also restore twice while one action waits. Canonical item identity
is compared independently of restored display spelling; raw SQL strings are
retained. Bags and their caches do not change during attacks or restores.

Battle end clears both players' locks. The report independently compares owned
species, nickname, level, trainer, ability, IVs, EVs, nature, egg state and
canonical placements before/after every completed battle. Owned UUIDs are
mapped to controllers explicitly. All 21 saved signature-move PP/type results
and native item forms are retained alongside actual action observations.

Both players use ordinary unhold after removal battles. Successful theft or
swap returns the surviving item to its new owner's bag; protected removal
returns it to the original owner. Knock Off deliberately removes a foreign
held item, and it does not reappear in either bag. The expected per-owner
quantities and total Shed Shell stock are asserted. Typed-move cases also
assert normal unhold returns the original two-copy stock.
The report additionally sums normalized raw inventory rows plus physical held
slots for every battle, and sums both owners' post-unhold rows for every
removal case. This independently excludes hidden alias stock or duplicate
items rather than relying only on the quantity lookup used by commands.

## Retained fixture diagnosis

The initial player pilot stopped at case five, with four passes. The exact
commands were `+attack A1 Rest` and `+attack B1 Thief`. Normal turn ordering let
the faster foreign Mew deal **18 damage**, then native Silvally-Bug used Rest
and healed it. A whole-turn HP-difference assertion saw zero, correctly
exposing a poor fixture choice rather than broken theft/damage.

The native idle move was replaced with **Iron Defense**, which both Silvally
and Genesect legally learn. It does not undo the measured HP loss; its normal
Defense changes are retained in snapshots. The corrected 258-case pilot
passed, followed by a separate final replay against frozen source. No accuracy,
effect, immunity, ability or target decision was forced. Failed logs and full
receipts were kept without overwriting them.

## Reproduction and remaining boundaries

Run the new offline suite from the repository root:

```powershell
..\evenv\Scripts\python.exe -B -m pytest -q -o addopts= pokemon/battle/tests/test_memory_drive_theft_identity.py
```

Run `python -B tests/integration/memory_drive_theft_cases.py` only with an
explicit disposable `PF2_TEST_POSTGRES_DSN`. The integration connection guard
creates/drops its own random schema and never falls back to a game database.
Set `PF2_MEMORY_DRIVE_EVIDENCE` to a task-owned JSON path to retain full raw
command/state receipts from a replay.
The PostgreSQL workflow includes this standalone suite, without claiming a
successful hosted CI run. Required combined/repeat/battle-first qualification
uses `python -B tools/run_mandatory_tests.py` in fresh processes.

This issue does not expand typed-move suppression parity or generic Knock Off
power/source-context behavior. The [pre-existing Knock Off power gap](plate-theft-identity-2026-10-25.md#separate-pre-existing-move-power-discrepancy)
remains documented and unchanged; the checks here qualify physical removal
and persistence. Other special protected items remain in #857. Current support
reporting and released socket acceptance remain separate in #859/#860.

There is no deployment, migration executor, existing-game database operation,
public item source, plot-only content or new move/form profile in this repair.
The 25 unrelated dirty paths in the separate shared checkout are preserved.

## Exact per-item outcomes

Foreign columns pair identical Mew stats and seed for default, exact native
nickname and Imposter prefix; all lose their item to Thief. A foreign source
with the exact native nickname also produces that same damage and transfer.
Default/renamed native holders agree and retain their item. Native forms may
change Dark effectiveness; native damage is not compared against Mew damage.
Signature columns are actual native `+attack` results with the item-selected
type, a saved one-PP debit, restored form and retained physical item.

| Item | Native family | Foreign Thief HP loss: default / exact / prefix | Buddy native HP loss and item | Actual signature type and damage |
| --- | --- | --- | --- | --- |
| Bug Memory | Silvally | 34 / 34 / 34 | 18; retained | Bug; 92 HP |
| Burn Drive | Genesect | 34 / 34 / 34 | 18; retained | Fire; 61 HP |
| Chill Drive | Genesect | 34 / 34 / 34 | 18; retained | Ice; 61 HP |
| Dark Memory | Silvally | 34 / 34 / 34 | 9; retained | Dark; 92 HP |
| Douse Drive | Genesect | 34 / 34 / 34 | 18; retained | Water; 61 HP |
| Dragon Memory | Silvally | 34 / 34 / 34 | 18; retained | Dragon; 46 HP |
| Electric Memory | Silvally | 34 / 34 / 34 | 18; retained | Electric; 46 HP |
| Fairy Memory | Silvally | 34 / 34 / 34 | 9; retained | Fairy; 46 HP |
| Fighting Memory | Silvally | 34 / 34 / 34 | 9; retained | Fighting; 23 HP |
| Fire Memory | Silvally | 34 / 34 / 34 | 18; retained | Fire; 46 HP |
| Flying Memory | Silvally | 34 / 34 / 34 | 18; retained | Flying; 46 HP |
| Ghost Memory | Silvally | 34 / 34 / 34 | 36; retained | Ghost; 92 HP |
| Grass Memory | Silvally | 34 / 34 / 34 | 18; retained | Grass; 46 HP |
| Ground Memory | Silvally | 34 / 34 / 34 | 18; retained | Ground; 46 HP |
| Ice Memory | Silvally | 34 / 34 / 34 | 18; retained | Ice; 46 HP |
| Poison Memory | Silvally | 34 / 34 / 34 | 18; retained | Poison; 46 HP |
| Psychic Memory | Silvally | 34 / 34 / 34 | 36; retained | Psychic; 23 HP |
| Rock Memory | Silvally | 34 / 34 / 34 | 18; retained | Rock; 46 HP |
| Shock Drive | Genesect | 34 / 34 / 34 | 18; retained | Electric; 61 HP |
| Steel Memory | Silvally | 34 / 34 / 34 | 18; retained | Steel; 46 HP |
| Water Memory | Silvally | 34 / 34 / 34 | 18; retained | Water; 46 HP |

## Qualification

- **325 new offline regressions passed.**
- **1,138 focused tests passed**, including the existing Plate, stat/critical,
  legendary booster, incense, item runtime, form eligibility, copied-move
  persistence and support-reconciliation checks.
- **258 ordinary-command/PostgreSQL cases passed** in the corrected pilot and
  again in a fresh accepted replay against frozen source. These are 258 distinct
  cases replayed twice, not 516 different acceptance scenarios.
- **All 212 existing Plate PostgreSQL cases passed** with the shared fixture's
  default configuration, including its original native-source Trick controls.
- **All three mandatory fresh full orders passed:** combined, repeat and
  battle-first each finished with **5,670 passed / 4,028 skipped**. The wrapper
  completed temporary cleanup and exited zero. Optional dex/Showdown and
  explicit-DSN suites retain their default skips; this task separately
  qualifies the scoped PostgreSQL suites above, without claiming a new broad
  database or hosted CI acceptance run.
- The task-owned loopback PostgreSQL fixture is stopped, with **zero disposable
  schemas and zero public tables** remaining.

The manifest freezes **1,125 Python files** and independently preserves the
separate shared checkout's **25 unrelated dirty paths**. AST comparison confirms
exactly 21 changed item methods, all `onTakeItem`; the shared fixture changes
only configurable tags, native ability lookup, native-family form assertion
and fault label. The engine, identity/effective-item helpers, moves, abilities,
owned battle persistence and historical reports remain unchanged. Source
publication is separate from deployment and hosted CI acceptance.
