# Runner false-flag repairs — 2026-10-19

Completed 2026-10-19T14:42:52.186597+00:00. The runner's **nine previously diagnosed false flags now pass as declared outcomes** through fresh ordinary-player logins on the local server. No game mechanics were changed and no server reload was needed. The 20-scenario pilot passed **20/20**. All **6088 pre-existing gameplay/object records** and unrelated source work remain unchanged. No downloads occurred.

## Corrected expectations

| Previous catalog flag | Runner repair | Fresh result |
| --- | --- | --- |
| Castform-Rainy, Castform-Snowy, Castform-Sunny | Expect native entry to base Castform in clear weather, with Normal typing and canonical stats/max HP. | 3 passed |
| Cherrim-Sunshine | Expect base Cherrim when the required sun is absent. | Passed |
| Minior | Expect full-health native entry to Meteor with its calculated stats/max HP. | Passed |
| Terapagos | Expect native entry to Terapagos-Terastal and Tera Shell. | Passed |
| Tera Shift | Explicitly require Terapagos-Terastal, Normal typing, Tera Shell and calculated native stats/max HP. | Passed |
| Imposter | Observe copied Tackle's temporary PP 5 → 4; require copied form/ability and damage while the owned identity and moveset stay unchanged. | Passed |
| Plasma Fists | Require damage, same-turn Electric Tackle and Ground immunity, expiry by the prompt, next-turn Normal Tackle and damage, and exact PP debits. | Passed |

The runner uses explicit expected forms, types, abilities and PP sources. It does not exempt these subjects from validation. The read-only observer now retains the executed move's name/type. Native stat checks use `get_stats` and `get_max_hp` with the fixture's level, zero IVs/EVs and Hardy nature. Ordinary move checks continue to observe owned PP; Imposter explicitly selects temporary runtime PP.

## Validation

- **Nine affected catalog cases:** 9 declared outcomes verified, zero diagnostic flags or blocked cases.
- **Nearby catalog checks:** Wishiwashi, Mimic, Sketch and Transform all passed.
- **Five native positive controls:** rain/snow/sun Castform, sun Cherrim and low-HP Minior core all passed, including canonical stats/max HP.
- **20-scenario pilot:** 20 passed; retained evidence audited.
- **Focused runner tests:** 86 passed. The 51 new regression cases include wrong-form/type/stat/HP controls, incorrect Tera Shell transitions, missing or wrong temporary PP, owned-PP corruption, missing damage, and incorrect Plasma Fists conversion/expiry.
- **Mandatory combined, repeated and battle-first suite orders:** each passed **3,942 tests**, with **4,010 skipped** per run.
- **Independent evidence audit:** 38 records and 125 observations verified, with exact hashes, saved assertions, ordinary-account identities, callbacks and normal cleanup; no errors.

The fresh gameplay used one loaded version group: `233299f33c6544ba93f475e7e0e3297647c2571caa5bf434cead0d2e546fee55`. Read-only structural checks before and after verified 2,238 functions across 45 game modules. Loaded game functions remain identical to the previously accepted build; only the QA observation/expectation code changed.

## Safety and scope

A custom-format PostgreSQL backup was verified before the fresh QA identities were created. All 6088 pre-existing Pokémon/gameplay/object records remain unchanged, including character-linked attributes. All pre-existing dirty files remain byte-identical except the three authorized QA files listed below. Older QA accounts were not reused.

Fresh accounts **49, 50, 51** are disabled, their temporary staff/superuser rights removed and passwords unusable, and their temporary credential file is deleted. Exact secret-byte scans before and after deletion both passed in one process. Private room, manifest and ownership guards restricted all fixture changes to the new QA trainers. No downloads, dependency installs, migrations, reloads, commits or remote operations occurred.

Changed QA files: `tools/live_dex_cases.py`, `tools/live_dex_runner.py`, `tools/live_dex_server.py`. Added regression tests: `tests/test_live_dex_false_flags.py`.

This was a targeted rerun of 13 catalog cases plus five native controls and the 20-scenario pilot. It was not another full catalog sweep. The previous full sweep and its nine raw flags remain immutable historical evidence; this run retains the corrected fixtures and fresh results separately. Declared contexts do not prove every possible interaction or player progression route.

Evidence, source pins, backup and logs are under the already ignored `.codex-artifacts/runner-flags-20261019/` and `.codex-artifacts/runner-flags-20261019-work/`. The main indices are `results.json`, `native-controls.json`, `pilot-final/evidence-audit.json`, `final-independent-audit.json`, `current-evidence-sha256.json` and `final-account-safety.json`.
