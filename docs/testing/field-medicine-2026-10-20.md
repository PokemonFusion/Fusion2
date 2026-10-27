# Field medicine: issues #748 and #749

## Implementation and scope

`+use` now routes the existing HP/status/revival, PP and herbal medicines through
`FieldMedicineUse`, which reuses `BattleMedicineUse`. Battle dispatch, queued
target identity, snapshot timing and checkpoints retain their existing code.
This change adds no item definitions or plot-only content.

Supported field medicines:

| Family | Items |
| --- | --- |
| HP/status | Potion, Super Potion, Hyper Potion, Max Potion, Full Restore, Antidote, Paralyze Heal, Burn Heal, Ice Heal, Awakening, Full Heal |
| Revival | Revive, Max Revive |
| PP | Ether, Max Ether, Elixir, Max Elixir |
| Herbal | Heal Powder, Energy Powder, Energy Root, Revival Herb |

Targets are canonical party slots with gaps preserved, exact unambiguous names,
full Pokemon UUIDs, or the current Fusion (`fusion`, `self`, `me`). Eggs, boxed
Pokemon, foreign owners and inactive Fusion reservations are rejected. The
service reloads authoritative model fields instead of trusting cached HP/status,
locks storage before trainer/inventory and Pokemon writes, and rechecks the
battle guard inside the transaction.

Use `+use Ether=3/Water Gun` or `+use Max Ether=3/4` for a chosen active move.
Move numbers are canonical active-move slots, including gaps. Omitting the
selector restores the first depleted active move. Elixirs affect all active
moves and reject single-move selectors. Current active slots and dex PP plus
stored boosts determine caps; existing PP Up/PP Max progression is unchanged.

Each effective use consumes one item. Failed or ineffective uses consume none.
Energy Powder and Heal Powder lower friendship by 5 below 200 or 10 at 200+;
Energy Root uses 10/15 and Revival Herb 15/20. Friendship cannot fall below zero.
No-effect herbs apply no penalty. Player help includes these rules and syntax.

## Verification

Tests run locally using Python 3.12 and a dedicated, loopback-only PostgreSQL 16
instance. Every integration suite creates production model tables directly in a
random disposable schema; all ORM connections are guarded to that schema.
No migrations, live game rows or running game services are used. This is
automated normal-command proof, not a live Telnet/browser walkthrough, public
deployment or hosted CI result.

| Command | Result |
| --- | --- |
| `python -B tests/integration/field_item_cases.py` | 23 passed |
| `python -B tests/integration/cloud_gameplay_cases.py` | 9 passed |
| `python -B tests/integration/remaining_item_cases.py` | 8 passed |
| `python -B tests/integration/status_item_cases.py` | 9 passed |
| `python -B tests/integration/capture_pp_item_cases.py` | 16 passed |
| `python -B -m pytest -q tests/test_useitem_pp.py tests/test_exp_items.py tests/test_inventory_command.py -o addopts=` | 17 passed |
| `python -B tools/run_mandatory_tests.py` | Combined, repeat and battle-first each passed: 4,333 passed, 4,014 skipped; runner exit 0 |
| `python -B -m ruff check --no-cache pokemon/services/field_items.py tests/integration/field_item_cases.py commands/player/cmd_inventory.py` | Passed |
| `git diff --check` | Passed |

Mandatory-run summaries: combined completed in 201.00s with 1,356 warnings;
repeat in 182.11s with 1,356 warnings; battle-first in 196.13s with 1,366
warnings. Warnings include the existing isolated-test model reload notices and
the local pytest-cache permission notice; all three runs had zero failures.
After integration checks, the disposable schema count was verified as zero and
the dedicated test PostgreSQL instance was stopped.

The 23 field cases exercise every supported family, specific cures and all major
statuses, full/zero HP, Full Restore's independent and combined effects, fainted
slot-6 revival, no-effect repeats, selected/all-move PP, zero PP, boosted caps,
canonical move-slot gaps, actual PP Up/Max prompts, Rare Candy, friendship
thresholds/floor, invalid syntax, duplicate names, foreign IDs, ownership
changes, eggs, boxes, Fusion reservations, stale model caches and battle guards.
Injected failures verify rejected debits, HP/herbal save rollback, and rollback
of both PP slots when the second save fails. Independent database connections
verify one last Potion cannot be spent twice and a waiting Max Potion command
sees freshly healed HP and consumes nothing.

The existing battle suites retain reserve revival, exact queued-target behavior,
replay protection, persistent conditions, all-move rollback, captured PP, and the
outer-turn snapshot timing fixes. Their deliberately injected failure traces
are expected rollback evidence; the test outcomes pass.

## Recorded command walkthrough

`test_ordinary_player_command_walkthrough_and_battle_rebuild` invokes the shipped
`CmdUseItem.parse/func` with an ordinary caller context, real trainer inventory
and production owned/placement/move models. No administrator item/effect bypass
is used during the command sequence. Fixtures start with a poisoned Mew in
canonical party slot 3, a fainted Eevee in slot 6, and depleted Tackle/Water Gun
in move slots 1/4. Water Gun has a stored +15 PP boost. Each command starts with
one corresponding item and leaves zero of that item.

| Command | Persisted result | Command output |
| --- | --- | --- |
| `+use Potion=3` | HP 1 -> 21; poison remains | `Used Potion on 3.` |
| `+use Antidote=3` | Poison cleared; HP remains 21 | `Used Antidote on 3.` |
| `+use Revive=6` | Eevee HP 0 -> 57; slot 3 untouched | `Used Revive on 6.` |
| `+use Max Ether=3/Water Gun` | PP `[0, 0]` -> `[0, 40]` | `Used Max Ether on 3.` |
| `+use Elixir=3` | PP `[0, 40]` -> `[10, 40]` | `Used Elixir on 3.` |
| `+use Energy Root=3` | HP 21 -> 141; friendship 70 -> 60 | `Used Energy Root on 3.` |

A new battle snapshot is then built and serialized/rebuilt from these saved
models; HP, cleared status and current PP match SQL. The test prints the
machine-readable `FIELD_COMMAND_WALKTHROUGH` record with before/after state.

## Preservation and availability

Baseline checkout: `staging` at `fd402f935e9e6c8980d41cd3beb9f86d2c9849a8`.
At verification and initial issue closure, the field implementation, help,
integration tests and this report were local working-tree changes. This report
preserves that test snapshot. Subsequent publication is identified by the
containing commit and the issue follow-ups; deployment remains separate from
these test results.

SHA-256 comparisons against the pre-edit baseline confirmed that all nine
existing dirty/untracked battle files and reports were preserved, including
`pokemon/battle/engine.py`, the Showdown runtime-hook tests, forced-form item
regressions and the forced-form/post-form/post-recovery reports.

The lifecycle-integrity workflow now runs the field and existing medicine suites
and watches inventory-command changes. Hosted execution has not been claimed.
Issues #754-#757 and later missing-item additions retain their own scope and
acceptance; this report does not complete those issues.

## GitHub disposition

After all checks passed, [#748](https://github.com/PokemonFusion/Fusion2/issues/748)
and [#749](https://github.com/PokemonFusion/Fusion2/issues/749) were closed as
completed, with their acceptance checklists updated. Detailed completion evidence
is retained in [the #748 comment](https://github.com/PokemonFusion/Fusion2/issues/748#issuecomment-6305599791)
and [the #749 comment](https://github.com/PokemonFusion/Fusion2/issues/749#issuecomment-6305600684).
[Tracker #747](https://github.com/PokemonFusion/Fusion2/issues/747) remains open
with 6/15 children completed: all P1 repairs #748-#753 closed, P2/P3 still open.
The initial issue updates identified the field changes as local and uncommitted.
Subsequent publication is recorded in Git history and issue follow-ups. The
existing-item gate for later additions remains in place.
