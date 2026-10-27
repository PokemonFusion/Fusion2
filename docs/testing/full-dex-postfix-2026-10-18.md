# Full local dex sweep after the five repairs — 2026-10-18

Completed 2026-10-19T02:38:25.445711+00:00. Every loaded Pokémon/form, move and ability was exercised again through real localhost player logins on the unchanged repair build. **No new mechanics defect was confirmed; all ten catalog flags were diagnosed.** The 20-scenario pilot, 14 Terapagos/Teraform Zero scenarios and 35 qualified repair/diagnostic replays passed.

## Complete catalog

All 2,693 entries completed: 1,421 Pokémon/forms, 952 moves, 314 abilities and six regressions. Raw observations retain their original expectations and classifications.

| Catalog | Entries | Declared outcome verified | Smoke only | Expected failure | Flags reviewed separately |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pokémon/forms | 1421 | 1415 | 0 | 0 | 6 |
| Moves | 952 | 837 | 108 | 5 | 2 |
| Abilities | 314 | 46 | 266 | 0 | 2 |
| Regressions | 6 | 6 | 0 | 0 | 0 |

Totals: **2,304 declared outcomes verified, 374 smoke checks, five expected failures and ten diagnosis flags**. An independent review of all 1,421 species records found **zero calculated-stat or maximum-HP discrepancies**. Stats use each prepared Pokémon's species/form, level, IVs, EVs and nature through the canonical helpers. Imposter's legitimate copied battle stats are assessed separately.

The five expected negatives are Celebrate, Happy Hour, Hold Hands and Splash having no direct effect in these PvP fixtures, and a legal Sheer Cold accuracy miss. A fresh native-carrier follow-up observed Sheer Cold's positive knockout without forcing accuracy. Smoke completion proves execution and the stated basic checks; it does not prove every move effect.

## Qualified gameplay follow-ups

| Phase | Cases/comparisons | Recorded result |
| --- | ---: | --- |
| Main matched ability/control comparisons | 297 | 297 outcome_verified |
| Extra ability/control comparisons | 18 | 18 outcome_verified |
| Gap and bounded chance comparisons | 95 | 82 outcome_verified, 13 chance_not_observed |
| Wild escape and trapping | 11 | 11 outcome_verified |
| Post-battle item cases | 10 | 9 outcome_verified, 1 chance_not_observed |
| Sketch ownership/integrity | 1 | 1 outcome_verified |
| Affected repairs and temporal/healing diagnoses | 35 | 35 passed |
| Native Sheer Cold bounded follow-ups | 8 | 7 expected_failure, 1 outcome_verified |
| Present full-health cap probe | 1 | 1 outcome_verified |
| Terapagos/Teraform Zero | 14 | 14 passed |
| Standard pilot | 20 | 20 passed |

**313/314 abilities have at least one declared positive branch observed** in this new sweep. Remaining entry without a positive effect: No Ability, a no-effect placeholder. Negative controls are excluded from that positive count. Chance windows without activation remain recorded as inconclusive; later successful windows do not erase them. This establishes the declared native-carrier scenarios, not every interaction or probability distribution.

## Diagnosis of all ten catalog flags

| Flag(s) | Diagnosis and fresh qualification |
| --- | --- |
| Rainy/Snowy/Sunny Castform; Sunshine Cherrim (4) | The clear-weather generic fixture correctly reverts these forms. Fresh required-weather positive cases pass, including calculated stats and max HP. |
| Minior (1) | Full health correctly enters Meteor form; the generic fixture expected the core to remain. Fresh full/low-HP cases verify Meteor/core transitions and calculated stats. |
| Terapagos; Tera Shift (2) | Native entry correctly becomes Terastal with Tera Shell. The generic identity/ability expectation is obsolete. The 14-case native Terastallization/Teraform Zero replay passes. |
| Imposter (1) | Copied battle Tackle spends temporary PP (5 → 4), while owned Tackle remains 35. The generic observer checked the owned move instead of the temporary copied move. |
| Plasma Fists (1) | The one-turn field correctly expires before the next prompt. A fresh same-turn Tackle becomes Electric and cannot damage Ground; next-turn Tackle is Normal and damages it. |
| Present (1) | The original no-effect occurred against a full-health target, with no miss recorded. Fresh natural healing rolls restore one-quarter maximum HP on an injured target and correctly add zero HP at full health. The original generic observer did not retain the selected random branch, so its precise roll is not claimed. |

All ten original raw flags remain preserved and linked by checksums to the separate diagnosis ledger. There are **zero pending diagnoses and zero newly confirmed mechanics defects**. Fresh Present observations: **1** qualifying injured-target healing outcome and **1** selected healing outcome capped at full HP.

The five repaired mechanics also passed fresh qualified replays: generic form stat/HP recalculation, Minior's Shields Down names/thresholds, Schooling's level-20 requirement, Instruct's repeated-move PP and feedback, and Present's healing. Power Construct changed 42/168 HP to 150/276 while preserving damage. Instruct's target Tackle PP was 35 → 34 → 32, including the repeated use. Original catalog Instruct proof was additionally assessed for the exact PP costs without rewriting its raw smoke label.

## Build and evidence integrity

No game source changed during this sweep. All 100 tested Python source pins and 44 runtime source pins match the accepted repair build. Before/after loaded-code audits agree: 43 modules, 2,210 checked functions, zero mismatches. The prior mandatory gate of 3,845 passed and 4,010 optional skipped in each of three fresh suite orders belongs to this same pinned build; it is earlier automated evidence, separate from this new logged-in sweep. No server reload was needed or performed.

The retained proof audit checked **3,613 gameplay records and 7,649 snapshots**, found one loaded structural code version group, zero integrity errors and zero callback-failure observations. Participants were the fresh ordinary QA battlers; staff was restricted to guarded fixture preparation/observation. All retained battles cleaned up through the normal player path without staff fallback.

A missing ignored observer helper stopped the first gap-run setup before it executed a case. Its failure logs are preserved; copying the existing local read-only helper allowed the phase to resume. This was a runner setup issue and required no game repair. Natural rolls and original failures remain retained.

## Existing data and closeout

The baseline covers **5,722 pre-existing rows**, including existing characters, Pokémon and previous QA fixtures. Final comparison found them unchanged. All four unrelated WIP files and the pre-existing game/test source remained unchanged. Only new isolated QA identities/fixtures were used. A verified local PostgreSQL backup preceded preparation; backups contain private data and remain local and ignored.

Fresh QA accounts **40, 41 and 42 are disabled**, staff/superuser flags removed, passwords invalidated and the private credential file deleted. Exact scans for all three current passwords passed before and after deletion with zero matches or read errors. Large logs, backups, proof and helper artifacts are covered by the existing Git ignore rules.

**Nothing was downloaded.** No install, migration, reload, remote change, commit or PR occurred. These results establish the stated local fixtures, not deployment, complete interaction coverage, natural learnsets/progression, live fault injection or concurrency acceptance.

Private local evidence: `.codex-artifacts/full-dex-postfix-20261018/`. Primary indices are `results.json`, `reviewed-diagnoses.json`, `diagnosis-summary.json`, `coverage-summary.json`, `qualified-assertion-audit.json`, `full-evidence-audit.json`, `final-account-safety.json` and `closeout-summary.json`. Raw compressed command/state proof and checksums remain available locally.
