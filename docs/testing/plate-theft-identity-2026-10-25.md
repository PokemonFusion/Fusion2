# Native Plate removal protection — October 25, 2026

Issue: [#855](https://github.com/PokemonFusion/Fusion2/issues/855), under
[#852](https://github.com/PokemonFusion/Fusion2/issues/852). Source baseline:
`081af5a3e45412f167358f5fc8aad23cbd856c6f` (#853 and #854 completed).

Exactly 17 Plate `onTakeItem` callbacks now reuse the unchanged
`HeldItemIdentity` helper. A display name cannot grant or remove native Arceus
protection. Every Plate's generic matching-type power callback stays unchanged.
The engine also includes physical held items in `TakeItem` events during
suppression, preserving native protection under Magic Room, Embargo and Klutz.
All other scoped event consumers retain effective-item suppression.

## Rules and pinned reference

The [reference item rules](https://github.com/smogon/pokemon-showdown/blob/7e6cea3605c20b44142b2aab22acf08df75ea52b/data/items.ts)
were read from the local checkout at that commit. The working file matches Git
blob `95103d8d5c0da5a646adc074d73610546f933757`, normalized SHA-256
`5163ddf04fc8928ac07c1bd40841ccc285ac1eb4544e84b24274cfe28cc41d1f`.
Each Plate protects removal if **either holder or source has native Arceus base
species**. Canonical Arceus type forms belong to that family. The rule has no
ability condition. Genuine Transform retains native identity; a foreign copied
appearance and exact/prefix nicknames cannot grant it. Unknown dex identities
are not native Arceus.

The [reference event dispatcher](https://github.com/smogon/pokemon-showdown/blob/7e6cea3605c20b44142b2aab22acf08df75ea52b/sim/battle.ts#L874)
exempts `TakeItem` from item suppression. PF2 previously skipped the Plate hook
for Thief/Knock Off under suppression, although its swap path checked the
physical item. The repaired scoped event path includes physical held items only
for `TakeItem`; it dispatches each hook once with the correct holder/source.
This event correction applies to physical removal callbacks generally, while
only the 17 Plate identity callbacks change in this issue. Other families'
nickname checks retain their separate repair tickets.

The existing form-entry checks separately require native/current eligibility,
an untransformed holder and Multitype. No ability, typing, form activation or
acquisition rule changes here. Native form entry can reset the runtime display
name; owned nicknames are checked independently. All Plates retain PF2's
`int(base_power * 1.2)` matching-type modifier for **all species**. The reference
uses a fixed-point modifier; complete simulator damage parity is not claimed.

The [machine-readable receipts](plate-theft-identity-2026-10-25.json) include
the exact item list, all 212 player cases, actual commands, HP/PP and item
outcomes, relevant messages, restored runtime/SQL state, source hashes and
failure diagnoses. Supporting reference files (`sim/battle.ts`, `sim/pokemon.ts`
and `data/learnsets.ts`) were independently checked against their pinned blobs.

## Reproduction and offline checks

The initial **183 offline cases** reproduced **108 failures / 75 passes** before
the repair. Positive/negative controls use real dex objects, native calculated
stats and HP, normal move execution and actual theft/removal. After the repair,
all 183 passed. Another 34 foreign-source nickname cases and two observation-only
single-dispatch controls bring the final new suite to **219 passing tests**.

Every Plate has ordinary/exact/prefix foreign-holder Thief controls, native and
renamed holder/source controls, foreign-source nickname controls and generic
matching-type power plus real-damage checks. Representative Knock Off,
Trick/Switcheroo, occupied source slots, Sticky Hold, Magic Room/Embargo/Klutz,
genuine Transform, unknown identities and missing native ability are covered.
Physical protection does not bypass ordinary ability protection or occupied
thief checks. Suppressed items still provide no power effect.

Arceus's assigned Thief/Transform and native Klutz cases are explicit offline
policy adapters, not new learnset or ability support. The owned-player source
checks below use Arceus's legal Trick instead of assigning it Thief.

## Ordinary owned-player acceptance

**212 PostgreSQL cases passed**, using real capture nickname-menu input,
`+hold 3=<Plate>` and both players' `+attack` commands through production choices,
turn execution and durable PvP sessions. These are local automated command/model
checks with captured message transport, not a newly released socket walkthrough.

Each of the 17 Plates has eleven separate cases:

- Foreign Mew with its default name, exact Arceus nickname and Arceus-Imposter
  nickname: a normal Mew's Thief takes exactly one Plate.
- Native Arceus with its default name and Buddy nickname: Thief damages it but
  cannot take its Plate; legitimate type-form entry remains available.
- Foreign Mew named Arceus as the Thief source: its name cannot block transfer.
- Foreign-holder Thief with two restores while the other action is queued,
  then two additional completed-turn restores: the empty old holder slot and
  new owner's item both survive.
- Renamed/default native Arceus as Trick source: the Plate remains with its
  foreign holder. Arceus legally learns Trick; it does not learn Thief.
- Missing stock and an injected post-debit held-save fault: the entire SQL,
  bag/cache, placement and runtime snapshot stays unchanged. All 17 actual
  rollback injections are observed and produce the normal rejection receipt.

The remaining 25 Flame Plate cases cover actual Knock Off, Trick and Switcheroo
against foreign/native holders, a source holding Shed Shell, native Arceus as
Trick source while holding Shed Shell, all four removal moves in Magic Room,
Thief under Embargo, an occupied thief and a real Sticky Hold Gastrodon.
Switcheroo uses native Hypno with Insomnia; Mew does not learn Switcheroo.
Suppression is applied by actual moves and restored twice before removal.

Tagged ordinary Player characters occupy only their new private room and own
newly created rows in canonical party slot 3. Both sides use level 50, Bold
nature, zero IVs and 252 HP/252 Defense EVs; stats and HP come from project
helpers. The fixture labels encounter creation, production capture finalization
and two-copy bag grants separately. Only nickname selection and subsequent
player commands are ordinary flow acceptance; wild encounter/ball commands and
public item obtainability are not claimed. No human session or existing owned
Pokemon is used. All move/ability assignments follow the pinned learnsets in
the player cases.

There are **178 completed battle outcomes** and **34 rejected equip attempts**.
Each removal move spends exactly one saved PP, including legitimate protected
failures. Successful Thief or swapping moves preserve one Plate across the two
physical slots. Knock Off intentionally removes the foreign holder's Plate;
it does not reappear in either bag. Protected removal preserves both original
items, including an occupied source. Battle turns and restores do not debit or
credit either bag/cache. Two completed-turn restores preserve the exact
canonical item ownership, including empty slots, in every battle case.

Battle end clears both players' locks and preserves original owned species,
nickname, ability, IVs, EVs, nature, level, trainer and canonical placements.
The report independently rechecks these fields from SQL, mapping owned UUIDs
to controllers rather than relying on UUID sort order. Both players then use
ordinary `+hold 3=` to return their surviving held items to their own bags.
The final per-owner quantities and total Shed Shell quantity are asserted.

The harness reuses the accepted incense/native-stat command, observation,
snapshot and restore helpers. Transport capture and the optional game-manager
lookup are isolated adapters; item effects, targets, legal PP, turn ordering,
normal seeded RNG and item persistence are not replaced or forced. Production
debug damage traces, exact commands and before/after states remain in the
hashed raw evidence, with bounded receipts published in the JSON report.

## Fixture diagnoses retained

The first 212-case pilot completed with 176 failures / 36 passes. A fresh
single-case replay isolated an overly strict fixture comparison: checkpoint
restoration can save `Dracoplate` rather than `Draco Plate`. Both resolve to the
same real item. The corrected fixture compares canonical identity and still
retains exact raw strings and explicit empty SQL/runtime slots.

The next pilot stopped at case 47 (46 passes): the `embargo_native` label had
created Mew because setup recognized only a native prefix. The suffix now also
selects actual Arceus. Hypno's separately legal Magic Room move is explicitly
assigned for the Switcheroo suppression cases. These were fixture corrections;
no item effect or game decision was forced to satisfy a label. A completely
fresh final run passed all 212 cases. Exact failed logs and receipts were
retained without overwriting them.

## Exact per-Plate outcomes

The three foreign columns below use the same Mew stats and seed: default name,
Arceus and Arceus-Imposter. All transfer the Plate to the attacking Mew; damage
is identical. A foreign source named Arceus also produces that same damage and
transfer. Native Buddy Arceus takes damage but retains its Plate; its native
type form affects Dark effectiveness. A renamed native Arceus using Trick
cannot take the Plate from foreign Mew. Default native controls agree.

| Plate | Foreign Thief HP loss: default / exact / prefix | Native Buddy HP loss and item | Native Arceus Trick source |
| --- | --- | --- | --- |
| Draco Plate | 34 / 34 / 34 | 15; retained | retained with foreign holder |
| Dread Plate | 34 / 34 / 34 | 7; retained | retained with foreign holder |
| Earth Plate | 34 / 34 / 34 | 15; retained | retained with foreign holder |
| Fist Plate | 34 / 34 / 34 | 7; retained | retained with foreign holder |
| Flame Plate | 34 / 34 / 34 | 15; retained | retained with foreign holder |
| Icicle Plate | 34 / 34 / 34 | 15; retained | retained with foreign holder |
| Insect Plate | 34 / 34 / 34 | 15; retained | retained with foreign holder |
| Iron Plate | 34 / 34 / 34 | 15; retained | retained with foreign holder |
| Meadow Plate | 34 / 34 / 34 | 15; retained | retained with foreign holder |
| Mind Plate | 34 / 34 / 34 | 30; retained | retained with foreign holder |
| Pixie Plate | 34 / 34 / 34 | 7; retained | retained with foreign holder |
| Sky Plate | 34 / 34 / 34 | 15; retained | retained with foreign holder |
| Splash Plate | 34 / 34 / 34 | 15; retained | retained with foreign holder |
| Spooky Plate | 34 / 34 / 34 | 30; retained | retained with foreign holder |
| Stone Plate | 34 / 34 / 34 | 15; retained | retained with foreign holder |
| Toxic Plate | 34 / 34 / 34 | 15; retained | retained with foreign holder |
| Zap Plate | 34 / 34 / 34 | 15; retained | retained with foreign holder |

## Qualification and limits

- **219 new offline regressions passed.**
- **813 focused tests passed**, including the prior nine stat/critical items,
  seven legendary boosters, incense, item runtime, form eligibility, copied
  move persistence and support reconciliation.
- **212 new ordinary-command/PostgreSQL cases passed.**
- **186 existing-item PostgreSQL cases passed:** native stat items 52,
  legendary boosters 86, incense 40 and remaining medicine/item cases 8.
- **All three required fresh full orders passed:** combined, repeat and
  battle-first each finished with **5,345 passed / 4,028 skipped**. The wrapper
  completed its temporary cleanup and exited zero. Optional dex/Showdown and
  explicit-DSN suites retain their default skips; this task separately qualifies
  the scoped PostgreSQL suites above, without claiming a new broad database or
  hosted CI acceptance run.
- The task-owned loopback PostgreSQL fixture was stopped after these checks,
  with **zero disposable schemas and zero public tables** remaining.

The source manifest freezes **1,123 Python files**. The separate shared
checkout's **25 unrelated dirty paths** retain their original contents. AST
comparison proves exactly 17 item methods changed, all `onTakeItem`, and two
engine methods changed for the scoped `TakeItem` suppression exception. The
shared helper, effective-item resolver, moves, abilities, owned battle
persistence, Necrozma service/tests and historical reports/matrix are unchanged.

Run the new offline checks from the repository root:

```powershell
..\evenv\Scripts\python.exe -B -m pytest -q -o addopts= pokemon/battle/tests/test_plate_theft_identity.py
```

Run `python -B tests/integration/plate_theft_cases.py` only with an explicit
disposable `PF2_TEST_POSTGRES_DSN`. Its connection guard creates and drops only
its random private schema and never falls back to game settings. The CI
PostgreSQL workflow now includes this standalone suite; adding that step does
not claim a successful hosted run. The repository gate is
`python -B tools/run_mandatory_tests.py`, which enables callback tests and runs
combined, repeat and battle-first orders in fresh processes.

This acceptance does not establish a new deployment, released socket run,
public item source, existing-database migration or service restart. Released
item acceptance remains separate in #860. There is no plot-only content or new
item definition, ability policy, form activation or acquisition support.
Other removal families remain in #856/#857 and status berries in #858. The
historical support matrix is preserved; #859 owns current reporting reconciliation.

### Separate pre-existing move-power discrepancy

Knock Off's removal/persistence checks are accepted here; complete move parity
is not. Its unchanged `Knockoff.onBasePower` implementation boosts power whenever
the target holds any item. The owned-player Flame Plate receipts show power
97 (65 × 1.5, truncated) against both foreign Mew (item removed, 52 HP damage)
and protected native Arceus (item retained, 24 HP damage). The
[pinned reference](https://github.com/smogon/pokemon-showdown/blob/7e6cea3605c20b44142b2aab22acf08df75ea52b/data/moves.ts#L10347)
checks the item's removal veto before applying this bonus. The callback and
move dispatch are byte-for-byte unchanged from the source baseline. This is a
separate move-power gap, not an unreviewed Plate-transfer failure or a claim
that protected items should receive that bonus. It needs a bounded move repair
covering protected item families and source/holder context; it is not folded
into this 17-callback identity repair.
