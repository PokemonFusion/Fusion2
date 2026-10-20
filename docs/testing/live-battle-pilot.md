# Logged-in local battle pilot

`tools/live_battle_pilot.py` prepares and drives twenty small battle scenarios
through two ordinary player Telnet sessions and one dedicated QA staff session.
This is local running-game acceptance, not browser UI acceptance, production
acceptance, an exhaustive dex sweep, or a load test.

The catalog in `tools/live_battle_pilot_cases.py` declares each team's species,
abilities, moves, initial HP and items, the exact player commands, and the
expected behavior. It covers damage/PP, type immunity, stat changes, healing,
burn, paralysis, Protect, Water Absorb, Levitate, Flash Fire, Intimidate,
Leftovers, Stealth Rock, switching, Fly, doubles Surf, wild fleeing/capture,
and the trainer flee restriction. Teams are staff-prepared; these cases do
not prove move learning, breeding, or starter selection.

## Safety boundary

- The tool only connects to `127.0.0.1`; preparation rejects remote databases.
- Preparation creates and checks a PostgreSQL custom-format backup before
  creating any fixture. The backup remains private in the ignored run folder.
- Every run creates a new room and new accounts/characters. It never reuses
  existing player accounts, characters, Pokemon, rooms or Adventure instances.
- The manifest pins the new object, account and trainer IDs and ownership tag.
  Staff operations reject pre-baseline character IDs, changed ownership,
  changed rooms, privileged battling accounts and non-QA room occupants.
- Fixture replacement only touches Pokemon/inventory owned by the new QA
  trainers. The canonical Pokemon creation and placement services are used.
- No migrations, server restarts, global RNG reseeding, battle-engine patches,
  or new persistent game commands are performed.
- The two battlers retain ordinary Player permissions. Only the separate
  setup account gets temporary staff access. Its helper offers setup,
  observation, per-battle RNG seeding and QA-only cleanup, never player choices.
- Final verification checks hashes of every pre-existing `pokemon_*` row,
  object record and object-linked attribute, plus the original dirty files.
  Added QA rows are allowed; modified or deleted baseline rows are reported.
- `disable` invalidates only this run's account passwords, deactivates those
  accounts, removes temporary staff privileges and removes their credential
  file. Disabled characters and the final fixture teams remain inspectable.

Backups contain game data and should not be committed or shared. Credentials
are stored only in a per-run local temporary file and redacted from transcripts.

## Running

From the `fusion2` root, using the project's installed interpreter:

```powershell
..\evenv\Scripts\python.exe -B tools/live_battle_pilot.py catalog
..\evenv\Scripts\python.exe -B tools/live_battle_pilot.py prepare --output .codex-artifacts/battle-pilot-NEW
..\evenv\Scripts\python.exe -B tools/live_battle_pilot.py run --output .codex-artifacts/battle-pilot-NEW
..\evenv\Scripts\python.exe -B tools/live_battle_pilot.py verify --output .codex-artifacts/battle-pilot-NEW
..\evenv\Scripts\python.exe -B tools/live_battle_pilot.py disable --output .codex-artifacts/battle-pilot-NEW
..\evenv\Scripts\python.exe -B tools/live_battle_pilot.py verify --output .codex-artifacts/battle-pilot-NEW
```

The game must already be running. Preparation refuses to overwrite an output
directory. Each new full run uses a fresh directory and fresh identities.
The port can be selected with `--port`, but the host is fixed to loopback.
`run` resumes by skipping cases already marked passed; `--case 09-water-absorb`
explicitly replays one case. Failed and blocked attempts remain in `attempts/`;
`results.json` holds the latest result for each scenario. After disabling
accounts, prepare a fresh run to test again.

Every case has a known seed attached only to that battle's RNG after entry.
Entry effects execute naturally before that assignment. This does not force
hits or secondary effects, prove probability distributions, or isolate any
mechanic that still uses module-level randomness.

## Reading evidence

`transcript.jsonl` contains the exact normal-player commands and output,
separately labeled staff observations/setup, and redacted authentication.
Each scenario JSON includes the initial live and stored state, the state after
each turn, the expected outcome, an explicit assertion result and cleanup state.
Turn advancement is checked so an unexecuted attack cannot pass as immunity.
Damage messages alone cannot pass a damage check.

The runner first tries ordinary player concession for cleanup. A scoped staff
fallback is recorded as a failure, never accepted as normal player cleanup.
Unresolved cleanup stops the batch. No broad battle cleanup command is used.

`safety-verification.json` records baseline preservation and new log error
lines. Service status should also be checked before and after. `accounts-disabled.json`
records the final removal of temporary access.

A pass means the declared scenario's observations matched its expectations.
It does not establish every interaction of a move/ability, every species/form,
browser presentation, AI strategy, network deployment, or player readiness.
Expand the catalog with positive, negative and mode-specific cases before
claiming wider coverage.

## Diagnose failures before changing mechanics

A failed scenario assertion is not automatically a game defect. The runner
records a `failure_review` with the seed, actual status/ability/volatile/PP
state, field effects, relevant blocker messages and scenario-specific valid
failure conditions. It labels observations as requiring diagnosis or possibly
expected; it never promotes an assertion failure to a confirmed defect.

Before repairing a failed move or ability:

1. Check Fusion2's intended rules and a primary rules/implementation reference.
   Account for intentional custom behavior.
2. Verify the fixture, legal target/move, available PP, turn phase, accuracy and
   evasion, immunities, status prevention, protection, suppression, weather and
   terrain. No damage during a charging turn can be correct; a 95-percent move
   can miss. A protected target is a valid reason for a strike to fail.
3. Inspect exact player output and before/after state, distinguish a runner or
   fixture error from gameplay, and reproduce unexplained outcomes using fresh
   fixtures. Never force success to conceal an expected failure.
4. Record the diagnosis, ruled-out alternatives, reproduction and affected
   source path. Add positive and relevant negative regressions before claiming
   the game is repaired.

The Flash Fire scenario now checks retained state over two turns and a
subsequent Fire attack. The Fly scenario checks charging, impact, charge
cleanup and exactly one PP spent. Engine regressions additionally check the
actual Fire damage boost, valid switch-out expiry and a Protect-blocked Fly.
