# Local full battle sweep with knockout-boost fix

Completed 2026-10-20T04:53:03.955761+00:00. Fresh localhost player logins exercised the loaded knockout-boost build. No downloads, production source changes, migrations or additional reloads were needed.

| Catalog | Total | Declared outcomes | Raw smoke | Expected failures | Unresolved flags |
|---|---:|---:|---:|---:|---:|
| pokemon | 1421 | 1421 | 0 | 0 | 0 |
| move | 952 | 838 | 109 | 5 | 0 |
| ability | 314 | 52 | 262 | 0 | 0 |
| regression | 6 | 6 | 0 | 0 | 0 |

The raw labels are retained. Separate current effect checks qualify all 371 raw smoke records: 313 effect-bearing abilities have observed positive evidence; No Ability has an expected no-effect control. All 108 added move-effect subjects passed. Canonical stats and HP were checked for all 1,421 species records.

Native acceptance passed all 29 Ogerpon scenarios across four forms and 14 Terapagos/Teraform Zero scenarios. The 35 retained repair qualifications and 20-scenario pilot passed independent reassessment. All 36 fresh knockout-boundary checks passed and were independently audited: ongoing and final knockouts, matched no-ability controls, Aftermath, recoil, and indirect poison. Positive fixtures retain an opposing reserve, so an ongoing battle is required to award the boost.

## Diagnosis

No unexpected catalog flags were raised. The five expected negatives were Celebrate, Happy Hour, Hold Hands and Splash (no direct combat effect in these PvP fixtures), plus a normal Sheer Cold miss at 30% accuracy. A separate native Sheer Cold hit was observed on attempt eight; its seven misses remain in the evidence. Present's full-HP healing cap and its injured-target positive effect both passed. No unresolved diagnoses or confirmed new mechanics defects remain; no battle-code changes were needed.

The gap comparisons retain 14 no-proc attempts and the post-battle tests retain one. Every effect-bearing ability still has current positive evidence; these retained no-procs are not counted as positive effects or defects. This run does not measure chance-rate distributions.

## Protection and provenance

A verified PostgreSQL backup precedes QA creation. All 6630 existing protected rows and 1100 existing source files are unchanged. Only this run's three new QA accounts were used; both battle players remained ordinary players. All three accounts are now inactive, have unusable passwords and have no staff rights. Temporary credentials were deleted; exact-secret scans found no disclosures. 3 QA-owned Pokémon remain under the disabled fixtures.

Loaded-code audits before and after checked 2708 functions in 46 modules, with zero mismatches and one consistent loaded build across the observed states. Logs and backups are in the existing ignored artifacts folder.

## Scope

This proves the declared local scenarios and observed effects on the current local build. It does not establish exhaustive move/ability interactions, chance-rate distributions, ordinary progression access, multiplayer load, external deployment or final human player acceptance.

Machine-readable evidence: `.codex-artifacts/full-dex-knockout-20261019/`, including the full coverage index, independent audit, diagnoses, native forms, pilot, protected-row fingerprints, source pins and account closeout.
