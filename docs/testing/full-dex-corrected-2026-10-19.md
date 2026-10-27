# Full local sweep with the corrected runner — 2026-10-19

Completed 2026-10-19T16:32:36.256584+00:00. The fresh run exercised **all 1,421 Pokémon/forms, 952 moves and 314 abilities**, plus six catalog regressions, through ordinary local-player commands. The **nine previous runner false flags all passed their corrected declared expectations**. There are **0 newly confirmed mechanics defects** and no pending diagnoses. The standard pilot passed **20/20**.

All **6192 pre-existing gameplay/object records** and unrelated work remain unchanged. Fresh QA accounts are disabled and credentials deleted. Nothing was downloaded. All earlier reports and raw observations remain immutable historical evidence.

## Fresh catalog raw results

| Catalog | Attempted | Declared outcomes | Raw smoke | Explained negatives | Flags reviewed | Blocked |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| pokemon | 1421 | 1421 | 0 | 0 | 0 | 0 |
| move | 952 | 838 | 108 | 5 | 1 | 0 |
| ability | 314 | 48 | 266 | 0 | 0 | 0 |
| regression | 6 | 6 | 0 | 0 | 0 | 0 |

`outcome_verified` proves the exact saved assertions. Raw smoke proves entry/action/PP and is joined to separate actual-effect evidence; raw statuses remain unchanged. All **374 current raw smoke results** have qualified effect or expected-no-effect proof. The original 374 former-smoke entries also have **373 positive effects plus No Ability's expected-no-effect control**, with no gaps.

## Fresh effect and context checks

| Phase | Count | Retained result |
| --- | ---: | --- |
| Actual move effects (subjects) | 108 | 108 outcome_verified |
| Main ability matched pairs | 297 | 297 outcome_verified |
| Additional ability pairs | 18 | 18 outcome_verified |
| Ability gap pairs, including retained chance windows | 95 | 82 outcome_verified, 13 chance_not_observed |
| Wild cases | 11 | 11 outcome_verified |
| Post-battle item cases | 10 | 9 outcome_verified, 1 chance_not_observed |
| Terapagos/Teraform Zero | 14 | 14 passed |
| No Ability | 1 subject / 2 fixtures | Expected no effect verified |
| Native/form and repaired-path replays | 35 | All declared qualifications passed |
| Standard logged-in pilot | 20 | 20 passed |

The 108 move-effect subjects use 137 base fixtures, plus bounded natural chance opportunities where needed. They require actual damage, healing, stat/status/field changes, owned PP, item consumption, legal choices, critical damage or action order. Across the entire ability catalog, **313/314 have declared positive-effect proof**. No Ability is the intended no-effect placeholder. Negative controls and unsuccessful proc windows remain separately retained; a positive qualified window elsewhere is required for an ability's positive proof.

All **1,421 species/form records** were checked against `get_stats` and `get_max_hp` with their fixture level, IVs, EVs and nature. There were **zero stat/max-HP discrepancies**. Native entry transitions use the resulting form's canonical stats while the owned species identity remains protected.

## Diagnoses and runner verification

| Flag | Classification | Diagnosis |
| --- | --- | --- |
| move-present | full_health_healing_cap_and_generic_branch_observation_limit | The generic target was at full HP and no accuracy miss was reported. Its selected random healing branch was not recorded, so the precise original roll is not claimed. Fresh natural injured-target rolls restore one-quarter maximum HP; fresh observed healing rolls at full HP restore zero. The no-effect flag is consistent with the legitimate cap, and does not reproduce as a mechanics defect in these qualified contexts. |

The nine previous false flags concern four clear-weather Castform/Cherrim entries, full-health Minior, native Terapagos, Tera Shift, Imposter temporary PP and Plasma Fists' turn lifetime. This full run uses explicit expected entry forms/types/stats/abilities, copied runtime PP with unchanged owned slots, and observed same-turn versus next-turn Plasma Fists conversion. These entries were freshly executed and their declared effects passed.

| Expected negative | Diagnosis |
| --- | --- |
| move-celebrate | expected_no_direct_combat_effect_in_pvp |
| move-happyhour | expected_no_direct_combat_effect_in_pvp |
| move-holdhands | expected_no_direct_combat_effect_in_pvp |
| move-sheercold | expected_natural_accuracy_miss |
| move-splash | expected_no_direct_combat_effect_in_pvp |

The four no-direct-combat-effect moves are scoped to their prepared PvP context, including actual owned PP use; no reward-context claim is made. Sheer Cold also has fresh native Ice-carrier hit proof in a bounded unforced accuracy window. Present is separately checked on injured targets and on observed natural healing rolls at full HP. Sketch's unrelated slots and Instruct's repeated owned PP remain checked.

## Build, evidence and safety

The source is byte-identical to the accepted corrected-runner build: **113 Python source files and 46 runtime source files**. That exact build already passed **3,942 tests in each of three clean suite orders**, with **4,010 skipped per order**. Start provenance binds that earlier offline gate to the current pins; this turn claims fresh local gameplay rather than a new offline gate. No source change or reload was needed.

Read-only structural audits before and after checked **2,238 functions across 45 game modules**, with zero mismatches. All retained observations use one loaded version group: `233299f33c6544ba93f475e7e0e3297647c2571caa5bf434cead0d2e546fee55`. The independent audit verified **3752 records and 11770 observations**, original compressed-byte hashes, every exact pinned catalog fixture and assessment, ordinary QA identities, callback errors, normal cleanup, saved effect rules, matched controls, native replays and the pilot. It found no evidence-integrity errors.

A custom-format PostgreSQL backup was created and its contents verified before creating QA accounts. Every phase rechecked all 6192 pre-existing Pokémon/gameplay/object rows, including character-linked attributes. All initial dirty files and source pins remain unchanged. Only the newly tagged QA trainers and private room were used for fixture replacement, wild encounters and battle commands.

Fresh QA accounts **52, 53, 54** were the only accounts used. Older QA accounts stayed disabled. The fresh accounts are now inactive, staff/superuser rights removed, passwords unusable and the temporary credential file deleted. Exact secret-byte scans before and after deletion both passed in one process. No downloads, dependency installs, migrations, service reloads, commits or remote operations occurred.

## Scope and artifacts

This proves the declared contexts through real ordinary-player Telnet commands on localhost, with separate guarded staff setup and read-only observation. It does not prove every species/move/ability combination, natural learnset, probability distribution, progression route, generation variant, browser UI, production deployment or concurrent multiplayer behavior.

Logs, compressed transcripts, backup, source pins and raw evidence are under the already ignored `.codex-artifacts/full-dex-corrected-20261019/`. Transcripts rotate and compress. Key indices include `results.json`, `full-coverage-index.json`, `smoke-effect-coverage.json`, `reviewed-diagnoses.json`, `expected-negative-reviews.json`, `species-stat-review.json`, `final-independent-audit.json`, `current-evidence-sha256.json`, `final-account-safety.json` and `completion.json`. All changes remain local and uncommitted.
