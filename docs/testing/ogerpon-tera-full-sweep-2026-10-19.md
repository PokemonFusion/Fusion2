# Ogerpon Terastallization and full local sweep — 2026-10-19

Completed 2026-10-19T20:48:51.207203+00:00. All four native Ogerpon forms now Terastallize through ordinary player commands. The focused live acceptance passed **29/29**, the fresh catalog covered **1,421 Pokémon/forms, 952 moves and 314 abilities**, and the standard pilot passed **20/20**. No diagnoses remain pending; **0 additional mechanics defects** were confirmed by the post-repair sweep.

All **6411 pre-existing gameplay/object rows** and unrelated local work were preserved. Fresh QA accounts are disabled and their temporary credentials removed. Nothing was downloaded.

## Diagnosed repairs

The old native-form gate rejected all four ordinary Ogerpon forms; fresh ordinary-account before evidence reproduces all four rejections. Eligibility now uses the native species family, the actual held mask and the required fixed Tera type. Prebuilt Tera forms, missing masks, transformed/copy cases and fainted holders remain rejected.

| Native form | Required item | Fixed Tera type | Native Tera ability | Entry boost |
| --- | --- | --- | --- | --- |
| Teal | None | Grass | Embody Aspect (Teal) | Speed +1 |
| Wellspring | Wellspring Mask | Water | Embody Aspect (Wellspring) | Special Defense +1 |
| Hearthflame | Hearthflame Mask | Fire | Embody Aspect (Hearthflame) | Attack +1 |
| Cornerstone | Cornerstone Mask | Rock | Embody Aspect (Cornerstone) | Defense +1 |

The transition preserves damage, canonical stats and owned identity, installs the correct temporary form/ability/type, and activates the native aspect once. Mask entry and changes among ordinary native forms use reversible battle state. Mask power checks now recognize native identity even when nicknamed and apply the mask's 20% boost to damaging moves. Unrelated mask holders cannot acquire an Ogerpon form.

Two shared integration defects surfaced in these checks and were repaired: ordinary switching retained stat stages, and the default stat getter ignored boosts stored under long stat names. Switching now clears stages while preserving Baton Pass transfer, and stat aliases resolve consistently. The numeric 1.5× stage effect is tested for all four aspects. Ivy Cudgel already selected its type correctly and required no move callback change.

## Four-form live acceptance

All 29 cases used fresh ordinary QA players on localhost. Each form was exercised through a real `+tera` reservation/commit, Ivy Cudgel's actual damage/type/PP, cancellation, switching out and back, one-use side budget, doubles A2 selection, ability suppression and prebuilt-form rejection. Each of the three masks also has base-form entry, missing-mask rejection and changed-mask entry proof. Owned identity, saved Tera type, held item and canonical HP were checked, including cleanup. No existing Pokémon were used.

The independent Ogerpon audit checked **106 observations**, original compressed-byte hashes, ordinary identities, observer provenance, correct forms/types/abilities, stages, commands and normal cleanup. Before-fix evidence remains separate from the final build's evidence.

## Fresh catalog results

| Catalog | Attempted | Declared outcomes | Raw smoke | Explained negatives | Flags reviewed | Blocked |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| pokemon | 1421 | 1421 | 0 | 0 | 0 | 0 |
| move | 952 | 838 | 109 | 5 | 0 | 0 |
| ability | 314 | 52 | 262 | 0 | 0 | 0 |
| regression | 6 | 6 | 0 | 0 | 0 | 0 |

Raw outcomes prove the saved assertions; raw smoke is supplemented by separately qualified actual effects. All **371 current raw smoke entries** have qualified proof. The original 374 former-smoke entries remain covered by 373 positive effects and No Ability's expected-no-effect control. The four Embody Aspect catalog cases now activate through native ordinary forms and real Tera commands.

All 1,421 species/form observations were independently compared with `get_stats` and `get_max_hp` for the fixture level, IVs, EVs and nature: **zero discrepancies**.

| Fresh effect/context phase | Count | Retained results |
| --- | ---: | --- |
| Actual move effects (subjects) | 108 | 108 outcome_verified |
| Main ability pairs | 297 | 297 outcome_verified |
| Additional ability pairs | 18 | 18 outcome_verified |
| Ability gap pairs, including retained chance windows | 103 | 83 outcome_verified, 20 chance_not_observed |
| Wild cases | 11 | 11 outcome_verified |
| Post-battle item cases | 10 | 9 outcome_verified, 1 chance_not_observed |
| Terapagos/Teraform Zero | 14 | 14 passed |
| No Ability | 1 subject / 2 fixtures | Expected no effect verified |
| Earlier repaired-path/native replays | 35 | All qualified |
| Native Ogerpon acceptance | 29 | All passed |
| Standard logged-in pilot | 20 | All passed |

All **313 effect-bearing abilities** have declared positive-effect evidence; No Ability is the intended no-effect placeholder. The 108 move-effect subjects have actual-effect assertions, including bounded natural chance opportunities when required. Failed proc windows remain retained separately and do not qualify an ability as positively verified.

## Failure review

No catalog entry produced a diagnostic flag or blocked result.

| Expected negative | Diagnosis |
| --- | --- |
| move-celebrate | expected_no_direct_combat_effect_in_pvp |
| move-happyhour | expected_no_direct_combat_effect_in_pvp |
| move-holdhands | expected_no_direct_combat_effect_in_pvp |
| move-sheercold | expected_natural_accuracy_miss |
| move-splash | expected_no_direct_combat_effect_in_pvp |

Expected no-direct-combat effects are scoped to the prepared PvP context. Accuracy-dependent actions have separate positive windows where required. Present's injured-target healing and expected full-HP healing cap, native Sheer Cold hits, Sketch slot integrity and Instruct's repeated owned PP remain part of the fresh follow-up program. The nine earlier runner false flags passed their corrected assertions.

## Tests, loaded build and safety

The frozen final candidate passed **271 focused checks** and **4,023 tests in each of three fresh suite orders** (combined, repeat and battle-first). Each order also had 4,010 skips; skips are not effect-coverage claims. Earlier intermediate candidates and their stopped/failed runs remain historical artifacts and are not counted as acceptance.

The final source pin includes **116 Python files and 47 runtime sources**. A fresh verified PostgreSQL backup and isolation preflight preceded the authorized local Evennia reload. Structural audits before and after gameplay matched **2708 functions across 46 modules**, with zero mismatches and one loaded version group. The independent full audit checked **3797 evidence records and 11977 observations**, exact fixtures/assessments, original hashes, source pins, ordinary actors, callbacks, controls and cleanup.

All 6411 pre-existing gameplay/object rows were rechecked after every phase, including earlier QA fixtures and character-linked attributes. Of the 132 initial dirty files, 123 unrelated files remain byte-identical; only the nine explicitly scoped existing paths changed. The newly changed mask callback, Ogerpon test and this report are also scoped and recorded. Earlier reports remain untouched.

Only fresh QA accounts 58/59/60, characters 172/173/174 and private room 171 were used. Those accounts are now inactive, passwords unusable and staff/superuser rights removed. Exact secret-byte scans of retained raw/compressed artifacts and server logs passed before and after temporary credential deletion in one process. No downloads, installs, migrations, commits or remote operations occurred. All logs, backups and compressed transcripts are under the already ignored `.codex-artifacts/` directory.

## Scope and evidence

This proves the declared local battle contexts through ordinary Telnet commands with separate guarded staff fixture setup and read-only observation. It does not exhaust every interaction, natural learnset, progression route, chance distribution, browser client, production deployment or concurrent multiplayer case.

Evidence is under `.codex-artifacts/ogerpon-full-dex-20261019/`; offline diagnostics and gates are under `.codex-artifacts/ogerpon-tera-20261019-work/`. Key indices: `ogerpon-results.json`, `ogerpon-independent-audit.json`, `results.json`, `full-coverage-index.json`, `smoke-effect-coverage.json`, `species-stat-review.json`, `diagnosis-summary.json`, `final-independent-audit.json`, `current-evidence-sha256.json`, `final-account-safety.json`, `source-scope-audit.json` and `completion.json`. Changes remain local and uncommitted.
