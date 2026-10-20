# Full local catalog and effect acceptance — 2026-10-19

Completed 2026-10-19T13:18:06.760375+00:00. The fresh run exercised **all 1,421 Pokémon/forms, 952 moves and 314 abilities**, plus six catalog regressions. Every catalog flag is diagnosed; **0 new mechanics defects are confirmed**, with no pending diagnoses. The new effect suite again verified **108 moves and 265 formerly smoke-only abilities**, plus No Ability's explicit expected-no-effect control. Across the whole ability catalog, **313/314 have a declared positive effect**; No Ability is the intended no-effect placeholder. The pilot passed **20/20**.

All **5973 pre-existing gameplay/object rows** and unrelated work remain unchanged. Only fresh QA accounts were used; they are disabled and their credentials deleted. Nothing was downloaded. The earlier completed runs and their raw results remain unchanged.

## Full catalog raw results

| Catalog | Attempted | Declared outcomes | Raw smoke | Explained negatives | Raw flags reviewed | Blocked |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| pokemon | 1421 | 1415 | 0 | 0 | 6 | 0 |
| move | 952 | 837 | 109 | 5 | 1 | 0 |
| ability | 314 | 46 | 266 | 0 | 2 | 0 |
| regression | 6 | 6 | 0 | 0 | 0 | 0 |

Raw statuses are preserved. `outcome_verified` establishes the saved assertions; raw smoke establishes entry/action/PP only. Expected negatives, reviewed catalog flags and additional effect evidence are separate. The new effect map covers every one of the 374 former smoke entries: **373 positive effects and one expected-no-effect placeholder**, with no pending entries. All **375 raw smoke results in this fresh catalog** also have separate qualified effect or expected-no-effect proof, including Present's injured-target healing replay. The full coverage index joins those checks and all ability proofs to the unchanged raw catalog.

## Fresh functional checks

| Phase | Count | Current retained result |
| --- | ---: | --- |
| Actual move effects (subjects) | 108 | 108 outcome_verified |
| Main ability matched pairs | 297 | 297 outcome_verified |
| Additional ability pairs | 18 | 18 outcome_verified |
| Ability gap pairs, including bounded opportunities | 103 | 85 outcome_verified, 18 chance_not_observed |
| Wild cases | 11 | 11 outcome_verified |
| Post-battle item cases | 10 | 9 outcome_verified, 1 chance_not_observed |
| Terapagos/Teraform Zero | 14 | 14 passed |
| No Ability | 1 subject / 2 fixtures | Expected no effect verified |
| Native/form and repaired-path replays | 35 | All declared qualifications passed; raw scope retained |
| Standard real-login pilot | 20 | 20 passed |

The 108 move probes contain 137 independent fixtures. They require actual HP, healing, consumed items, owned PP, stats, status, field/side effects, legal blocked/allowed choices, critical damage or action-order outcomes. Spent PP or a success message cannot replace the effect assertion. Main ability comparisons cover the full catalog, with extra native, ally, field, wild, post-battle and Terastallization contexts. Inconclusive natural chance windows remain retained; a successful qualified window elsewhere supplies that ability's positive proof, not a relabeling of a failed proc.

All **1,421 species/form records** were checked against canonical calculated stats and max HP using their level, IVs, EVs and nature. There were **zero stat/HP discrepancies**. Native form changes are checked using the actual resulting form; owned species identities remain protected.

## Diagnoses

The exact commands, preconditions, states and checksums were retained. These observations were reviewed as rules or fixture/observer expectations before any potential mechanics change. Fresh native or functional replays confirm the relevant positive contexts. No game or test source was changed in this sweep.

| Raw catalog flag | Classification | Diagnosis and verification |
| --- | --- | --- |
| pokemon-castformrainy | expected_weather_precondition_and_generic_fixture_identity | Required weather is absent. Native entry correctly reverts to Castform; calculated stats and max HP match canonical helpers throughout. |
| pokemon-castformsnowy | expected_weather_precondition_and_generic_fixture_identity | Required weather is absent. Native entry correctly reverts to Castform; calculated stats and max HP match canonical helpers throughout. |
| pokemon-castformsunny | expected_weather_precondition_and_generic_fixture_identity | Required weather is absent. Native entry correctly reverts to Castform; calculated stats and max HP match canonical helpers throughout. |
| pokemon-cherrimsunshine | expected_weather_precondition_and_generic_fixture_identity | Required weather is absent. Native entry correctly reverts to Cherrim; calculated stats and max HP match canonical helpers throughout. |
| pokemon-minior | expected_shields_down_native_entry | Full-health native Minior correctly enters Meteor through repaired Shields Down. The generic catalog expects the supplied core to remain unchanged; calculated stats/max HP are correct. |
| pokemon-terapagos | expected_native_form_and_ability_transition | Native Tera Shift correctly installs Terapagos-Terastal and Tera Shell; the generic entry assertion expects the original form/ability. Calculated stats and max HP remain correct. |
| move-plasmafists | expected_one_turn_expiry_fixture_timing | Plasma Fists damages its target and converts same-turn Tackle into Electric (Ground immunity). Next-turn Tackle is Normal and damages Ground. The generic catalog incorrectly expects the one-turn field to remain at the next prompt. |
| ability-imposter | expected_temporary_move_pp_observer_mismatch | Imposter uses temporary copied Tackle PP 5 to 4 while the owned slot correctly stays 35; attack damage is observed. Generic PP observer checks the wrong slot. |
| ability-terashift | expected_native_form_and_ability_transition | Native Tera Shift correctly installs Terapagos-Terastal and Tera Shell; the generic entry assertion expects the original form/ability. Calculated stats and max HP remain correct. |

| Expected negative | Classification |
| --- | --- |
| move-celebrate | expected_no_direct_combat_effect_in_pvp |
| move-happyhour | expected_no_direct_combat_effect_in_pvp |
| move-holdhands | expected_no_direct_combat_effect_in_pvp |
| move-sheercold | expected_natural_accuracy_miss |
| move-splash | expected_no_direct_combat_effect_in_pvp |

The weather-form replays supply the required weather, Minior is checked above and below its HP threshold, and native Terapagos/Tera Shift/Teraform Zero is exercised through ordinary Terastallization. Plasma Fists is checked during the affected turn and after expiry. Present is checked on injured targets and on observed natural healing rolls at full HP. Sheer Cold also receives a bounded native Ice-carrier positive-hit window. The four no-direct-combat-effect moves are described only for this PvP context; reward and other contexts are not implied.

The stronger Instruct PP assertions and Sketch's unrelated-slot integrity checks also pass against the retained ordinary commands. The prior 22 mechanics repair groups remain loaded; their affected moves are included in the fresh actual-effect suite.

## Build, evidence and safety

The initial audit proved the current source identical to the accepted repair candidate: **112 Python files and 46 runtime source files**, including the unchanged four user work-in-progress files. That build had already passed **3,891 tests in each of three clean suite orders**, with 4,010 optional skips per order. This rerun made no implementation change and did not claim a new offline test gate. No reload was needed.

Before and after gameplay, read-only structural audits checked **2,238 source-defined functions across 45 loaded modules**, with zero mismatches. All final retained observations have the same loaded version group:

`58a050cf4cca3ff84e3679b8de89c86fab833301281aef032689131166ff9867`

The independent audit checked **3768 current records** and **11873 observations**, exact compressed-byte hashes, original catalog assessments, ordinary QA identities, callback errors, cleanup, saved move rules, matched gap fixtures, native checks and the pilot. It found no evidence-integrity errors. Initial dirty files are preserved except for the requested result documentation update, and all Python/runtime pins remain unchanged.

A custom-format PostgreSQL backup was created and its contents verified before QA preparation. The saved baseline protects all 5973 pre-existing Pokémon/gameplay/object rows, including character-linked attributes. Each phase rechecked it. Fresh accounts **46, 47 and 48** were the only identities used; older QA accounts were not reused. The new accounts are now disabled, their staff/superuser rights removed and passwords unusable, and their temporary credential file is deleted. Exact secret-byte scans before and after deletion passed in one process. The private QA room and fixture ownership guards prevented public encounter or existing-roster changes.

All logs, compressed transcripts, backups and raw evidence are under `.codex-artifacts/full-dex-effects-20261019/`, already ignored. Transcripts rotate and compress. No downloads, dependency installs, migrations, service reloads, commits or remote operations occurred in this sweep.

## Scope and retained artifacts

This is fresh localhost gameplay through real ordinary-player Telnet commands, with separate guarded staff setup/observation and private reproducible battle seeds. It proves the declared contexts and outcomes. It does not prove every species/move/ability combination, generation variant, natural learnset, chance distribution, progression route, browser UI, production deployment or multiplayer concurrency.

The ignored run folder retains `catalog.json`, `results.json`, the immutable per-case bytes under `evidence/`, `smoke-effect-coverage.json`, `full-coverage-index.json`, `reviewed-diagnoses.json`, `expected-negative-reviews.json`, `diagnosis-summary.json`, `species-stat-review.json`, `final-independent-audit.json`, `current-evidence-sha256.json` and `final-account-safety.json`. Start provenance links the reused accepted offline gate to this exact unchanged build. All changes are local and uncommitted.
