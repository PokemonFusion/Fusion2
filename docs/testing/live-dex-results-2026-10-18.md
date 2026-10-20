# Local logged-in QA result - 2026-10-18

<!-- full-dex-effects:start -->
## Full rerun with the actual-effect checks

The 2026-10-19 fresh local rerun covered **1,421 Pokémon/forms, 952 moves and 314 abilities**, plus six regressions and the new effect suite. Every raw flag is diagnosed; **0 new mechanics defects are confirmed**. The 374 former smoke entries have qualified effect/expected-no-effect proof, 313/314 abilities have a positive declared effect, all 1,421 stat/HP records match canonical calculations, and the pilot passed **20/20**. All 5973 protected rows and unrelated work remain unchanged; the fresh QA accounts are disabled and credentials deleted. No downloads occurred. See the [full catalog and effect report](full-dex-effects-2026-10-19.md). Earlier results below remain historical evidence for their own runs.
<!-- full-dex-effects:end -->

<!-- smoke-effects:start -->
## Remaining smoke checks converted to actual effects

The 2026-10-19 follow-up now maps all **374 former smoke entries** to qualified local proof: **108 moves and 265 abilities show an actual effect**, and **No Ability passes its expected-no-effect control**. Diagnosed repairs across 42 moves passed fresh effect checks; the 20-scenario pilot passed, and the mandatory suite passed 3,891 tests in each of three orders. All 5,850 protected rows and unrelated work remain unchanged, the fresh QA accounts are disabled, and no downloads occurred. See the [actual-effect acceptance report](smoke-effects-2026-10-19.md). Earlier sweep records below retain their original build and narrower scope.
<!-- smoke-effects:end -->

<!-- post-repair-sweep:start -->
## Full sweep after the five repairs

The fresh full local rerun exercised all **1,421 Pokémon/forms, 952 moves and 314 abilities**, plus six regressions, on the unchanged repaired build. All ten catalog flags are diagnosed; **no new mechanics defect was confirmed**. Fresh qualified repair replays passed **35/35**, Terapagos/Teraform Zero **14/14**, and the pilot **20/20**. At least one declared positive branch was observed for **313/314 abilities**; No Ability is a no-effect placeholder. The 374 raw smoke checks are retained with their narrower scope.

All **5,722 pre-existing rows** and unrelated source WIP are unchanged. Fresh QA accounts are disabled and credentials removed; exact secret scans and final evidence audits passed. No downloads occurred. See the [complete post-repair sweep report](full-dex-postfix-2026-10-18.md). The earlier results below are historical evidence.
<!-- post-repair-sweep:end -->

## Five diagnosed defects repaired and accepted

All five findings from the full rerun are now repaired and loaded locally. The final build passed 395 focused checks, 3,845 tests in each mandatory suite order, 35 affected real-login cases, 11 selected ability/control comparisons, 14 Terapagos regressions and the 20-scenario pilot. All 5,618 protected rows and unrelated work remain unchanged; fresh QA accounts are disabled and credentials removed. No downloads occurred. See the [repair acceptance report](five-defect-repairs-2026-10-18.md). The full rerun and earlier findings below are historical evidence, preserved with their original scope.

## Full rerun after the Teraform Zero repair

The fresh full local catalog rerun exercised all **1,421 Pokémon/forms, 952 moves and 314 abilities**, plus six regressions. The new Terapagos/Teraform Zero replay passed **14/14**, and the standard pilot passed **20/20**. Qualified evidence observes at least one declared positive branch for 313 abilities; No Ability is a no-effect placeholder.

**Five mechanics defects remain diagnosed:** generic form stat/HP recalculation, Shields Down's native Minior names, Schooling below level 20, Instruct's repeated-move PP/feedback, and Present's healing branch. These were reproduced and recorded without changing the frozen build. See the [full rerun report](full-dex-rerun-2026-10-18.md) for raw counts, expected outcomes, evidence audits and final account cleanup. Earlier claims below that no diagnosed failure remained describe their earlier scope and are superseded by this wider rerun.

## Teraform Zero follow-up

Teraform Zero's native Terapagos activation path is now implemented and has passed 14 targeted real-login scenarios plus the 20-scenario pilot on the local server. See the [Teraform Zero acceptance report](teraform-zero-local-2026-10-18.md) for the final regression and isolation results. The candidate06 ability-gap statement below describes the earlier sweep, before this repair.

## Diagnosed-failure and ability follow-up

Completed 2026-10-18T19:42:36.191324+00:00; local candidate06. Changes are local and uncommitted.

The mandatory combined/repeat/battle-first gate passed **3782 tests in each clean process**, with 4010 optional tests skipped. All retained final gameplay observations use the same loaded structural code fingerprint and were checked for ordinary battler permissions and normal cleanup.

**312/314 abilities have a fresh verified positive trigger** in the final follow-up build. This proves the declared native-carrier scenarios, not every interaction, chance distribution, species/move combination, or player journey. Remaining positive gaps: No Ability, Teraform Zero.

No Ability is a no-effect placeholder. Teraform Zero activates after Terastallization; the current game's explicit Terapagos/Ogerpon feature gate prevents that normal positive route. Merely switching a prepared Stellar form correctly does not clear the field.

| Final phase | Raw recorded result |
| --- | --- |
| affected | 83: {'outcome_verified': 51, 'smoke_completed': 21, 'expected_failure': 5, 'needs_diagnosis': 6} |
| main | 297: {'outcome_verified': 297} |
| extras | 18: {'outcome_verified': 18} |
| gaps | 103: {'outcome_verified': 86, 'chance_not_observed': 17} |
| retired_fixtures | 1: {'needs_diagnosis': 1} |
| postbattle | 10: {'outcome_verified': 9, 'chance_not_observed': 1} |
| qualified | 1: {'outcome_verified': 1} |
| wild | 11: {'outcome_verified': 11} |
| pilot | 20: 20 audited passes |

All six original `needs_diagnosis` observations in the affected replay have been classified as expected rules or fixture expectations. The retired Wonder Skin observation is a classified runner issue. **No diagnosed mechanics failure remains unresolved.**

The affected replay retains original expectations, including four legitimate weather-form reversions, the incorrect old Mimic five-PP assertion, and Light Metal's obsolete absolute damage threshold. Qualified Mimic and fresh matched Light Metal comparisons establish the correct behavior. Legitimate accuracy misses, chance windows without activation, and negative controls are kept separate from mechanics defects.

Repairs cover the reproduced command/checkpoint integration failures: called and copied moves, first-turn and delayed actions, native forms and weight, owned ability/state dispatch, priority/redirection/protection, status and accuracy consumers, ally/item lifecycles, and ordinary wild post-battle item awards. Ball Fetch/Honey Gather persist only to the canonical owned party, with duplicate/retry protection. Forced receipt-write failure is isolated automated regression evidence; live PostgreSQL fault injection and concurrency were not claimed.

Fixture diagnoses preserved in private evidence include immune Water Absorb allies that never fainted, berries consumed before the attempted Stuff Cheeks, healing that capped a damage comparison, correctly expiring weather, and a next-turn reset clearing the observer's temporary critical flag. Super Luck's qualified matched damage comparison supports additional critical-sized damage; it does not claim a directly retained critical flag.

**All 5236 protected pre-existing rows and four unrelated WIP files are unchanged.** The three fresh QA accounts are disabled, staff privileges/passwords invalidated, and private credentials removed. Exact byte scans with the current three secrets passed before and after credential deletion. No downloads, migrations, remote changes, or commits occurred. Large logs, backups, compressed proof, and temporary tests are ignored by Git.

The prior 1,421 species/form and 952 move catalog sweep below is historical evidence. This follow-up reran the affected cases and ability coverage; it does not label that entire catalog as rerun on the final build.

Private bound evidence, checksums, source pins, classifications, and protection audits: `.codex-artifacts/live-dex-followup-20261018/followup-closeout-summary.json` and the final candidate evidence audit. Backups contain private data and must remain local.

## Original catalog sweep (historical build 13)

Completed 2026-10-18T14:43:56.289814+00:00; local build 13.

The runner attempted every loaded species/form (1,421), distinct move (952) and ability (314), plus six regressions. Ordinary QA players used real commands; a separate new QA staff identity prepared only isolated fixtures.

Catalog outcomes: `{'outcome_verified': 2292, 'smoke_completed': 369, 'needs_diagnosis': 28, 'expected_failure': 4}`. Matched ability comparisons: `{'outcome_verified': 279, 'needs_diagnosis': 18}`. Additional comparisons: `{'outcome_verified': 13, 'needs_diagnosis': 5}`. All 20 pilot and 11 wild cases passed. 214/314 abilities have at least one matched positive trigger; this is not complete mechanics coverage.

The mandatory combined/repeat/battle-first gate passed 3607 tests per process, with 4010 skipped. Full final catalog proof uses one loaded build after its reload; passing evidence and matched controls were audited.

Supplemental code-version equality has a documented metadata qualification: legacy marshal hashes depend on constant reference counts. Final live structural checks matched the pinned affected source; historic per-case stable hashes were not available. The original failed hash audit is retained, and future runner fingerprints have been repaired. A further 54 tooling checks passed.

Remaining reviewed observations: `{'mechanics_defect_reproduced': 38, 'expected_rule': 8, 'needs_further_isolation': 10}` plus the separate Shedinja HP discrepancy. Prepared Struggle/Ghost, Magic Bounce, Truant, Gluttony, Ripen and Innards Out remain among the diagnosed gaps. These are observation counts, not a count of distinct root causes. Weather-form reversion and the four flavor/context moves supply the eight expected observations.

Existing data: 4,411 protected rows and four unrelated WIP files unchanged. All three new QA accounts were disabled, staff rights/passwords invalidated and the private credential file removed. No download, migration or remote deployment occurred.

A report-schema error occurred after successful account cleanup and has been repaired. Retained login/echo fields passed redaction checks; the planned exact-password byte scan could not run after the credentials had been removed. This limitation is retained in the private audit.

Private full evidence and diagnoses are retained locally at `.codex-artifacts/live-dex-20261018/closeout.md`, with per-case compressed observations, prior attempts, failure classifications and backups. That folder and large logs are ignored by Git; backups must not be published.

See [runner usage](live-dex-sweep.md) for fresh isolated runs and the interpretation of smoke versus outcome proof.
