# Optional dex and Showdown testing — 2026-10-19

## Scope

Ran the optional suites against local Fusion2 source and the existing local Pokémon Showdown checkout. No network fetches, downloads, installs, migrations, game logins or service reloads were used. Showdown revision: `7e6cea3605c20b44142b2aab22acf08df75ea52b`; the executing compiled simulator and data files are hashed in `showdown-local-source.json`.

## Results

| Run | Result |
| --- | --- |
| Initial optional dex | 3,914 passed; 29 failed |
| Initial Showdown comparisons | 65 passed; 2 failed |
| Final affected dex, knockout lifecycle and live-runner checks | 114 passed |
| Complete suite, all three optional flags enabled | 8,043 passed; zero failures, errors or skips |
| Standard fresh-process regression gate: combined, repeat, battle-first | 4,029 passed and 4,014 opt-in skips in each of three runs |

The dex portion contains 952 move execution cases, 314 ability cases (including No Ability), 104 heal/Snatch flag cases, 576 item callback checks, 576 held-item assignment checks and 1,421 species construction cases: 3,943 checks total. The expanded Showdown comparator runs 71 scenarios.

The standard gate intentionally leaves dex and Showdown flags off; its 4,014 skips are precisely the 3,943 dex checks and 71 Showdown comparisons that passed in the all-options run. Existing legacy model-reload and cache-permission warnings remain recorded in the logs.

## Diagnosis before repair

All original failures and intermediate candidates are retained. Fresh isolated reproductions saved move state immediately after resolution and after cleanup, selected targets, callback counts and messages. Separate Showdown experiments retained complete snapshots for terminal knockouts, actual Aftermath trades and knockouts with a healthy opponent in reserve.

The 29 dex failures were fixture or observation errors:

| Cause | Moves |
| --- | --- |
| Expected accuracy miss; positive check used a miss-producing RNG window | Dark Void, Grass Whistle, Hypnosis, Lovely Kiss, Poison Powder, Sing, Sleep Powder, Stun Spore, Supersonic, Sweet Kiss |
| Asserted temporary effect after end-of-turn expiry | Baneful Bunker, Burning Bulwark, Detect, Electrify, Endure, King's Shield, Magic Coat, Obstruct, Powder, Protect, Silk Trap, Spiky Shield |
| Checked the wrong recipient or omitted a real ally | Aromatic Mist, Coaching, Helping Hand, Howl, Life Dew |
| Expected boosts before the required charge turn | Geomancy |
| Used move history instead of a currently queued priority attack | Upper Hand |

The optional runner now uses a private hit-producing seed, retains real move accuracy, selects an actual ally where required, observes effects before cleanup, executes both Geomancy turns, and gives Upper Hand an actual pending Quick Attack. It also verifies that the flinching opponent's queued attack does no damage. Helping Hand additionally has the same temporary-effect timing concern. An intermediate seed still missed because action ordering consumes an RNG draw; that candidate was rejected. The initial Geomancy no-boost assertion also needed to compare stage values rather than short/long key spelling.

The two Showdown mismatches exposed one engine defect: `AfterFaint` source bonuses ran after the final opponent was knocked out. Local Showdown's `sim/battle.ts` checks for a winner before dispatching `AfterFaint`. Fusion now retains the ordinary `Faint` effects and only dispatches the source bonus while an opposing team has a living Pokémon. This covers Moxie, Beast Boost, Chilling Neigh, Grim Neigh and both As One variants through their shared event path.

The original comparator fixtures were mislabeled as Aftermath trades: the attackers survived at 249/331 HP (Gyarados) and 195/259 HP (Kartana). Those original snapshots are preserved and the cases now describe terminal knockouts accurately. Four added differential cases separately prove the actual trades and positive boosts when a reserve opponent remains. Six native negative cases cover terminal knockouts; existing positive and cause-of-faint negatives now have opposing reserves so the terminal-battle guard cannot mask their intended conditions. The six corresponding live-runner positive fixtures also retain a reserve opponent for future runs.

## Invocation correction

The first all-options combined run had all 4,014 optional checks pass, but failed `test_manifest_refuses_outside_artifacts`. Its pytest temporary directory had been placed inside `.codex-artifacts`, which made the test's supposedly outside path an allowed inside path. The security check was correct and was not changed. Final full-suite temporary files use a separate checkout-local `.pytest-basetemp-*` directory. The original failed invocation and traceback remain retained.

## Remaining limits

One existing scenario, `choice-band-locks-user-into-first-move`, remains excluded from differential collection. It submits an illegal locked-out move; Showdown rejects the choice before turn resolution, while the Fusion adapter resolves actions through a different interface. This is a comparator-interface gap, not a newly diagnosed Choice Band mechanics defect. Other Choice-item comparisons still execute. No comparison fields or existing HP-ignore rules were loosened to obtain these passes.

These optional checks combine metadata/callback smoke coverage and bounded scripted effect comparisons. They do not prove every interaction, probability distribution, ordinary-client journey, concurrency case or deployed/live behavior. No new actual-effect coverage claim is inferred merely from an ability callback being invoked in the generic smoke fixture.

The engine repair remains local source validated by offline tests; the running Evennia server was not reloaded, and these new fixtures have not been exercised through fresh logged-in acceptance.

## Safety and evidence

Read-only database fingerprints after the complete all-options suite match all 6,526 initial gameplay/object/character-attribute rows exactly, with no additions, modifications or deletions. The final read-only verification after all gate processes also matches exactly. No QA accounts or owned Pokémon were created for this task.

The only pre-existing source files changed by this task are `pokemon/battle/engine.py`, `pokemon/battle/tests/test_live_trigger_lifecycle.py`, `pokemon/battle/tests/test_showdown_differential.py`, `tests/test_all_moves_and_abilities.py` and `tools/live_dex_ability_probes.py`. Of the 135 initially dirty paths, 132 are byte-identical; the other three are within this repair's scope. The two remaining changed test files were initially clean. Other pinned pre-existing source files match their initial SHA-256 hashes. No commits were made.

All raw runs, diagnostics, JUnit results, source backups and database hashes are under the already ignored `.codex-artifacts/optional-dex-showdown-20261019/`. Checkout-local pytest temporary directories and the legacy `move_ability_report.txt` are also already ignored. No ignore-rule changes were necessary.

Key evidence: `dex-before.xml`, `showdown-before.xml`, `dex-move-diagnosis.json`, `faint-order-diagnosis.json`, `diagnosis-index.json`, `affected-final.xml`, `all-options-final.xml`, `mandatory-final.log`, `source-tested.json`, `source-scope-audit.json`, `database-protection.json` and `completion.json`. Exact executable argument lists and exit codes are retained in the per-run JSON files.
