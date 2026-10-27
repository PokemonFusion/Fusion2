# Logged-in local dex sweep

`tools/live_dex_runner.py` extends the isolated twenty-scenario pilot to every
loaded Pokemon form, unique move and ability. It drives two ordinary accounts
over localhost Telnet. A separate temporary QA staff account prepares owned
teams and observes live state. Battle choices always use player commands.

The current catalog has 1,421 Pokemon forms, 952 distinct moves and 314 abilities.
Move compatibility aliases are deduplicated by raw display name. Additional
named regressions are reported separately from these catalog totals.

## Run and resume

Use the installed project interpreter from the repository root. No downloads,
dependency installation or remote service is involved.

```powershell
..\evenv\Scripts\python.exe -B tools/live_dex_runner.py prepare --output .codex-artifacts/live-dex-NEW
..\evenv\Scripts\python.exe -B tools/live_dex_runner.py run --output .codex-artifacts/live-dex-NEW --order ability move pokemon regression
..\evenv\Scripts\python.exe -B tools/live_dex_runner.py verify --output .codex-artifacts/live-dex-NEW
..\evenv\Scripts\python.exe -B tools/live_dex_runner.py disable --output .codex-artifacts/live-dex-NEW
```

`run` skips entries with retained results. `--kind move` selects one catalog;
`--limit 50` bounds a batch. `--case move-fly` explicitly reruns a subject using
fresh owned fixtures. `--retry` selects unresolved entries, and `--seed-offset 1`
changes only the private battle RNG. Creating `stop-requested` in the run folder
stops between cases after normal cleanup; remove that file before resuming.
The exclusive run lock prevents two workers controlling the same run at once.

The initial catalog is pinned in `catalog.json`. New attempts also save their
exact case definition, so later observer or fixture changes cannot silently
rewrite what was originally tested. The evidence audit uses that saved fixture.

`--rerun-all` makes a fresh pass after repairs; prior compressed observations are
retained in `attempts/`. `reassess` applies a corrected observer to the exact
saved fixtures without playing again and writes an assessment history with
evidence and evaluator hashes. It does not substitute newer fixtures or repair
unscoped log errors. Those require a fresh execution or a separate diagnosis.

`tools/live_dex_ability_probes.py run --output RUN --rerun-all` executes matched
ability/control pairs. The carrier, inputs and private per-turn seed match;
only the subject ability changes. Positive and relevant negative comparisons
are retained separately in `ability-probes.md`, with evidence checksums. Its
`audit` action verifies those bindings and the independently observed outcomes.
These comparisons prove the declared direction or prevented status, not every
branch or exact multiplier.

Additional matched situations include actual switches, ally attacks and
protection in doubles, knockout triggers, held-item transfer and form changes.
Assertions follow the original Pokemon through a switch when needed; a healthy
reserve cannot prove that the original Pokemon recovered.

`tools/live_dex_wild_probes.py run --output RUN` creates disposable wild foes in
the same private QA room and uses the ordinary player's `+flee` command. It
checks escape/trapping state, normal cleanup and deletion of the new encounter.
Its `audit` action rechecks the saved observations and checksums. It shares the
exclusive run lock with the PvP workers, so these modes must run sequentially.
Wild results remain separate in `wild-probes.md`.

## Interpreting coverage

- `outcome_verified`: the exact declared state assertions matched. For a species
  probe this is identity/types, positive HP, real entry, turn completion and PP;
  it does not establish all species-specific mechanics.
- `smoke_completed`: a real battle and selected move completed with PP spent,
  but the subject's full trigger/effect remains unverified.
- `expected_failure`: directly observed accuracy, typing or another evidenced
  rule explains the negative result. This is not positive effect proof.
- `needs_diagnosis`: an unexplained mismatch, exception or cleanup fallback.
  This is not automatically a game defect.
- `blocked`: setup, communication or cleanup could not complete safely.

Moves have direct outcome checks where metadata gives an independently
observable expectation: damage, status, boosts, healing, weather and terrain.
Fixtures supply sleep, Stockpile, items, earlier moves, reserves or allies for
conditional moves where practical. Abilities use native carriers where one
exists, incoming/outgoing actions, and explicit trigger checks for entry
weather/terrain, absorption, stat changes and status prevention. Probability
branches, complete callback behavior and every interaction require further
targeted cases. A no-status observation alone does not establish a prevention
ability if accuracy, chance or native typing also explains it.

Prepared moves and abilities isolate mechanics; they do not establish natural
learnsets, legal transformation/Z/Max activation, evolution, breeding, browser
UI or production readiness. Catalog entries include forms and nonstandard data
that may not be obtainable in ordinary gameplay. The report preserves those
limitations rather than hiding entries.

## Protecting existing data

Preparation verifies a local PostgreSQL custom-format backup before creating a
new tagged room, accounts, characters and trainers. The staff helper delegates
all mutations to the pilot's exact manifest ownership guards. It rejects old
IDs, changed ownership/location, non-QA occupants, non-local databases and
privileged battling accounts. Fixture replacement only deletes/recreates rows
owned by the two newly created QA trainers through canonical placement helpers.

Every 25 cases, the runner hashes all pre-existing `pokemon_*` rows, object rows
and object-linked attributes. It stops on any mismatch or unresolved cleanup.
The user's unrelated source WIP is also checked. Authorized source repairs are
listed separately as changed source, with diagnoses and regression evidence.
No global RNG is reseeded and no callbacks are replaced by the runner.

Normal player concession ends each remaining battle. Any guarded staff fallback
is an unsuccessful cleanup result, never a passing player action. Final
`disable` deactivates only the run's new accounts, invalidates their passwords,
removes staff access and deletes the private temporary credential file.

## Evidence and disk use

`progress.json`, `results.json`, `diagnosis-queue.json` and `report.md` provide the
current index. `evidence/*.json.gz` retains full observations and normal commands;
`attempts/` retains replaced attempts. `transcript.jsonl` redacts every QA
password and rotates/compresses at 16 MiB. New server callback failures are read
from live battle state and log offsets rather than inferred from player text.
The expanded observer fingerprints loaded callback code, so observations can
be distinguished from source edits that have not yet been loaded by a reload.
Earlier observations without that field retain their runtime feature flags.

All backups, reports, compressed observations and logs are under
`.codex-artifacts`, which `.gitignore` excludes. Existing `*.log` and `*.log.*`
rules also exclude server logs. Do not share backups or credential files.

Diagnose unexpected results against actual preconditions and the local primary
rules source before repairing mechanics. Preserve valid failures, reproduce with
fresh fixtures, add positive/negative regressions, and verify repairs again
through real player sessions. Use the mandatory combined/repeat/battle-first
test gate for stable mechanics changes.

The [2026-10-18 local results](live-dex-results-2026-10-18.md) record the complete
catalog run, qualified coverage, remaining diagnoses and account cleanup. The
private closeout retains source/version and redaction audit limitations.
Future snapshots use structural code fingerprints; legacy marshal fingerprints
can change with constant reference counts despite unchanged code. Existing
observations keep their original bytes and audit qualifications.
