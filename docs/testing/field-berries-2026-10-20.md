# Existing field berries: issue #754

## Delivered behavior

`+use` now supports an explicit 21-item allowlist: Oran, Sitrus, Figy, Wiki,
Mago, Aguav, Iapapa, Cheri, Chesto, Pecha, Rawst, Aspear, Lum, Leppa, Pomeg,
Kelpsy, Qualot, Hondew, Grepa and Tamato Berry, plus Berry Juice. See
[field-items.md](../field-items.md) for the complete effect table, eligible
targets, friendship policy and field/battle limits.

`FieldBerryUse` inherits the field medicine ownership, canonical placement,
storage/trainer/Pokemon lock order, fresh scalar reads, battle guard, inventory
check and rollback/cache recovery. A protected `_apply` extension point avoids
copying those checks. HP/status/PP berry effects reuse `BattleMedicineUse` and
its durable selected-move PP service through a berry-only configuration. Held
callbacks are not invoked or modified by inventory feeding.

The EV mapping is Pomeg/HP, Kelpsy/Attack, Qualot/Defense, Hondew/Special Attack,
Grepa/Special Defense, Tamato/Speed. Each removes up to 10 selected EVs (floor
zero) and independently raises friendship by +10 below 100, +5 below 200, or +2
at 200+, capped at 255. A useful EV or friendship effect permits one debit;
zero selected EVs plus capped friendship is a free no-op. Standard EV limits
and saved friendship are validated before consumption. Existing stat helpers
recompute stats/max HP. Pomeg preserves missing HP, keeps living Pokemon at
least at 1 HP, and never revives fainted Pokemon. Non-HP EV changes leave valid
current HP unchanged.

Recovery berries require a living target and their matching missing HP/status/
PP effect. Manual feeding is allowed above the automatic held activation
threshold. Fractional recovery matches the repaired held amounts; Leppa uses
current active slots and boosted caps. Flavor recovery has only its selected
HP effect outside battle; combat-only nature confusion remains in the held
route. Confusion-only, combat-trigger and contest-only berries are explicitly
unsupported by field feeding. BerryPlant, item definitions and battle behavior
remain outside this change.

## Test environment and results

Baseline: clean `staging` checkout at
`87bb3c041502977ad537774a26fe9bb2bc0c5bc9`, which includes the published field
medicine and native held-item form repair. This berry implementation and its
reports were local working-tree changes at verification. This report preserves
that test snapshot; subsequent publication is identified by the containing
commit and issue follow-ups. Hosted CI, deployment and live Telnet/browser
acceptance remain separate.

Production-model suites ran on a dedicated loopback-only PostgreSQL 16 instance
with an explicit test DSN. Every suite creates and deletes its own guarded,
random disposable schema using production table definitions. No migrations,
game rows or existing game services are used. The normal-command walkthrough
is automated `CmdUseItem.parse/func` execution with ordinary caller context and
actual saved inventory, Pokemon, placements and moves.

| Command | Result |
| --- | --- |
| `python -B tests/integration/field_berry_cases.py` | 26 passed |
| `python -B tests/integration/field_item_cases.py` | 23 passed |
| `python -B tests/integration/cloud_gameplay_cases.py` | 9 passed |
| `python -B tests/integration/remaining_item_cases.py` | 8 passed |
| `python -B tests/integration/status_item_cases.py` | 9 passed |
| `python -B tests/integration/capture_pp_item_cases.py` | 16 passed |
| Focused `tests/test_useitem_pp.py`, `tests/test_exp_items.py`, `tests/test_inventory_command.py` | 17 passed |
| `python -B tools/run_mandatory_tests.py` | Combined, repeat and battle-first each passed: 4,333 passed, 4,014 skipped; runner exit 0 |
| Seeded `pokemon/battle/tests/test_live_ability_reactions.py` | 27 passed |
| Ruff on changed service/command/berry integration files | Passed |
| `git diff --check` | Passed |

### Unrelated fixture diagnosis during the gate

The initial combined and repeat runs each passed 4,333 tests. The reversed-order
run found an existing nondeterministic Mycelium Might/Limber test: it asserted
that an unseeded, 90%-accurate Thunder Wave always inflicted paralysis. A
standalone battle-only reproduction, without importing any field services,
confirmed seed 1 hits and bypasses Limber while Electric typing still blocks
paralysis; seed 2 legitimately misses. This is an accuracy precondition in the
fixture, not a field-berry or battle-mechanics defect.

Both test battles now use `random.Random(1)`, consistent with the surrounding
ability tests. Move accuracy, immunity rules and battle runtime are unchanged.
The 27-case ability file passes with the seeded fixture. The full three-process
mandatory gate was rerun with this correction: combined passed in 192.31s with
1,356 warnings, repeat in 189.17s with 1,356 warnings, and battle-first in
181.57s with 1,366 warnings. Each run passed all 4,333 tests (4,014 skipped).
Warnings include existing model reload notices and the local pytest-cache
permission notice. The initial failed gate remains retained in the JSON
evidence. Disposable schemas were verified removed and the task's isolated
PostgreSQL instance was stopped after the last field tests.

The battle accuracy-fixture edit is separate local work and is excluded from
the #754 berry commit. Full-suite results above describe the tested working-tree
snapshot with that local RNG seed, rather than a fresh checkout of the berry
commit alone. The berry/medicine integration and focused command results do
not depend on that battle-test fixture. Its unchanged local after-hash remains
in the JSON evidence so the distinction can be checked.

The six production suites total **91 passing integration tests**. The 26 new
cases include matrices covering every feedable name, specific status cures,
every Lum major status, all six EV indices and stat recalculation, 0/1/9/10/11/
252 EV boundaries, total 510 EVs, friendship 0/99/100/199/200/254/255, invalid
saved rows, Pomeg full/damaged/one/fainted HP, actual party and move-slot gaps,
PP caps, no-effect repeats, exact names/IDs and aliases, eggs/boxes/foreign
ownership, changed owners, inactive/current Fusion, persistent/runtime battle
locks, stale model state and connection reopen/battle snapshot reconstruction.

Injected failures prove that rejected debits, EV writes and Leppa PP writes
cannot escape the transaction. EV failure after an actual save restores SQL
EVs, friendship, HP, inventory and the shared Evennia model instance. Two
independent SQL connections prove that one last berry cannot be spent twice,
and that a waiting/repeated command sees the new zero-EV/capped-friendship
state and consumes nothing. Two effective concurrent feeds also accumulate both
EV reductions and friendship gains without a lost update. Tests verify that feeding leaves held items
unchanged and that unallowlisted berries remain unavailable.

## Recorded command walkthrough

The fixture starts with a poisoned Mew in canonical party slot 3, 252 HP EVs,
friendship 70, HP 1/191, and depleted Tackle/Water Gun in active move slots 1/4.
Water Gun has a stored +15 PP boost. Each command begins with one matching
inventory item, returns `Used <item> on 3.`, and leaves zero of that item.

| Command | Authoritative saved result |
| --- | --- |
| `+use Oran Berry=3` | HP 1 -> 11; poison and EVs unchanged |
| `+use Pecha Berry=3` | Poison cleared; HP remains 11 |
| `+use Leppa Berry=3/Water Gun` | PP `[0, 0]` -> `[0, 10]`; HP/status unchanged |
| `+use Pomeg Berry=3` | HP EVs 252 -> 242; friendship 70 -> 80; max HP 191 -> 190; current HP 11 -> 10 |

`test_recorded_ordinary_field_feeding_walkthrough` prints the full
`FIELD_BERRY_WALKTHROUGH` before/after JSON. A separate case closes database
connections and rebuilds a battle snapshot to check saved EV/friendship/HP/
status/PP visibility. The JSON companion to this report preserves the command
record, source hashes and final gate results.

## Preservation and remaining scope

Of 144 protected tracked battle files, item definitions/callbacks and the
planting helper, 143 match pre-edit SHA-256 hashes. The sole exception is the
documented test-only RNG seed in `test_live_ability_reactions.py`; its before
and after hashes are retained. Existing held berry consumption,
flavor confusion, low-HP activation, resist/conditional triggers and native form
eligibility are unchanged. The lifecycle-integrity workflow now also runs the
production-model berry field suite.

The issue closure records local implementation plus automated field/model
proof. It does not close #755-#757 or authorize the missing-item phase. Plot-only
content, contests, cultivation, acquisition expansions, new berry definitions
and additional training items are not part of this work.

## GitHub disposition

After field/integration checks and the corrected three-process gate passed,
[#754](https://github.com/PokemonFusion/Fusion2/issues/754) was closed as
completed with all five acceptance criteria checked. The [completion comment](https://github.com/PokemonFusion/Fusion2/issues/754#issuecomment-6306300833)
records the allowlist, policy, walkthrough, test counts, fixture diagnosis and
original local/uncommitted availability boundary. Subsequent berry publication
is recorded in Git history and the issue follow-ups; the separate battle
accuracy-fixture edit remains uncommitted. [Tracker #747](https://github.com/PokemonFusion/Fusion2/issues/747)
remains open with 7/15 children completed; #755-#762 remain open and the
missing-item phase gate remains closed.
