# Compact battle UI verification — 2026-10-27

The approved compact default is complete in source, with selectable legacy,
classic-modern and PF1 layouts. The player sees every physical field slot,
ownership-aware HP, Fusion identity, conditions, PP, action state and committed
turn results. Screen-reader and ASCII modes, narrow terminals and move-detail
queries remain available. Source publication and shared-game deployment are
separate.

## Branch update and preservation

Local staging advanced from `f6826a9a1cf61be9899936232e57240ff8a7e0a7` to `7f57b0aab21f1a89a6e5f8aa8bef5bc26d0a1a50` by
fast-forward. All 25 original WIP paths were copied and hashed before a named
safety stash. Reapplication was conflict-free; only battleinstance.py needed
incoming source integration, preserving its newer item, form and roster guards.
Original line endings were restored where Git normalized them. The full original
backup and stash remain available locally. The first main promotion, PR #940,
excluded the unfinished UI. Its merge `b931ecf6be3ef074c80757e26b4244416f1e2536` has the identical
tree to the tested staging candidate; local staging then fast-forwarded to that
merge without changing UI source. GitHub automatically deleted the PR head
branch after merging; staging was restored at its exact tested tip. The later
UI promotion uses a separate temporary PR branch so automatic cleanup preserves
staging. The UI evidence below qualifies source bytes, including across that
merge-only parent change.

## Repairs and normal command coverage

- Explicit redraw sessions retain reserved/spent mechanics and observer identity.
- Fainted battlers receive replacement guidance; failed saves guide retry and
  completed battles stop offering another attack.
- Partial PP snapshots do not invent boosted capacity or missing remaining PP.
- Move details use ASCII-safe placeholders while older move cards retain their
  existing presentation. Blank slots keep stable letters and are rejected safely.
- Current engine weather, terrain and Trick Room replace stale initial room text.
- **89 focused tests passed.** The isolated command walkthrough passed
  **30 production command inputs and 7 selector replies** through
  `+battleui`, `+battleui/style`, `+uimode` and `+attack`. It covers all styles,
  accessible/ASCII output, unavailable and zero-PP rejection, Struggle, details,
  cancellation, duplicate/stale input, doubles actors, four-controller HP
  ownership and observers. Redraws preserve engine state and RNG.
- A separate two-controller native Double Team turn passed through `+attack`,
  the real engine and `BattleSession.run_turn`: both battlers spent PP 7→6 and
  gained Evasion +1, compact results were grouped and PF1 retained its stream.
  Its exact controller source and receipt are retained in the machine report;
  this supplement uses synthetic message transport and no SQL or socket.
- Real Evennia ANSI and HTML parsing agreed in **15 width/mode combinations**.
  A fresh headless Edge preview was visually inspected. Initial sandboxed Edge
  attempts could not initialize their GPU process; the separate approved
  headless run succeeded without opening or controlling an existing browser.

## Mandatory verification

Both gates ran the canonical `tools/run_mandatory_tests.py` with callbacks enabled,
three fresh processes and no ambient pytest omissions. Every order and outer
runner returned zero. The UI's 1,207-file Python source map remained unchanged.

| Build / fresh process | Passed | Skipped | Duration |
|---|---:|---:|---:|
| Clean staging / combined | 7,350 | 4,032 | 666.36s |
| Clean staging / repeat | 7,350 | 4,032 | 810.72s |
| Clean staging / battle-first | 7,350 | 4,032 | 737.95s |
| Compact UI / combined | 7,383 | 4,032 | 449.40s |
| Compact UI / repeat | 7,383 | 4,032 | 373.31s |
| Compact UI / battle-first | 7,383 | 4,032 | 406.33s |

Existing model-registration warnings and optional-suite skips are retained,
not treated as acceptance evidence. UI orders also retain a pytest cache-write
warning from the shared checkout; it does not skip or fail tests. The machine
receipt records commands, durations, source hashes and log/transcript hashes.

## Diagnoses retained

Six presentation reproductions failed before repair, and a further field-condition
reproduction exposed stale room weather. One intermediate focused run failed
because the first placeholder repair changed the legacy card's em dash; the fix
was narrowed to the new details renderer and the legacy regression passed.
Early standalone-command attempts lacked Evennia flat API exports, active input
control and session ndb fixtures; these were fixture initialization failures.
A declaration assertion was corrected to accept the engine's canonical case.
No battle validation or mechanics was bypassed to make those attempts pass.
Failed/superseded logs are retained in the local task artifact directory.

## Evidence limits

This is local automated command/engine and rendering evidence. Controllers and
runtime battlers are synthetic; interactive transport and the session registry
are supplied, and database connections are refused. It does not certify socket
login, owned SQL persistence, public sources, PostgreSQL concurrency or a live
game release. No migration, existing game service, human character or Pokemon
was changed. The existing mandatory gate still includes the prior item and
battle regressions; skipped integration suites are not counted as new coverage.
