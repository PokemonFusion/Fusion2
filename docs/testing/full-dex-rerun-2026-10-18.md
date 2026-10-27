# Full local dex rerun — 2026-10-18

Follow-up: **the five defects below are now repaired and locally accepted**. See the [repair report](five-defect-repairs-2026-10-18.md). This report retains the full rerun's original results and diagnoses from before those repairs.

Status: complete, including evidence audits and QA account cleanup. **Five confirmed mechanics defects remain.** No game source changed during this rerun.

The frozen local build containing the [Teraform Zero repair](teraform-zero-local-2026-10-18.md) was exercised through real localhost logins and ordinary player commands. The catalog covered all **1,421 loaded Pokémon/forms, 952 moves and 314 abilities**, plus six named regressions. Qualified follow-ups covered ability/control comparisons, wild battles, post-battle awards, storage integrity, native Terapagos and the standard pilot.

## Results and coverage limits

The catalog ran from 21:08:33 to 22:04:14 UTC. Original classifications are preserved; diagnoses and stronger follow-up assertions are separate records.

| Catalog subject | Entries | Outcomes verified | Smoke completed | Expected failure | Raw diagnosis flags |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pokémon/forms | 1,421 | 1,416 | 0 | 0 | 5 |
| Moves | 952 | 837 | 107 | 5 | 3 |
| Abilities | 314 | 46 | 266 | 0 | 2 |
| Named regressions | 6 | 6 | 0 | 0 | 0 |
| **Total** | **2,693** | **2,305** | **373** | **5** | **10** |

| Qualified phase | Final recorded result |
| --- | --- |
| Main matched ability/control comparisons | 297/297 verified after bounded chance retries |
| Extra ability/control comparisons | 18/18 verified, including negative controls |
| Ability-gap comparisons and retries | 99 pairs: 81 verified, 18 natural no-proc windows |
| Wild escape/trapping cases | 11/11 verified |
| Post-battle item cases | 9 verified, 1 Honey Gather no-proc; later item awards observed |
| Sketch unrelated-slot integrity | 1/1 verified |
| Terapagos/Teraform Zero | **14/14 passed** |
| Standard pilot | **20/20 passed** |
| Targeted diagnostic replays | 12 cases: 7 declared outcomes verified, 5 reproduced diagnosis flags |

Qualified evidence observes **at least one declared positive branch for 313/314 abilities**. No Ability is a no-effect placeholder. Negative controls do not count as positive triggers. This does not establish complete correctness: passing form assertions coexist with the additional stat, HP and threshold failures below.

Smoke checks establish entry/action execution without a complete mechanic assertion. The run does not exhaust every interaction, natural learnset, species/move combination, chance distribution, progression path or concurrency condition. Chance windows without activation remain recorded. Static and Poison Touch activated in fresh matched retries; their initial no-proc observations remain intact.

## Confirmed mechanics defects

All five findings were diagnosed using retained commands, before/after state, fresh isolated fixtures, local implementation and already-present primary Showdown sources. They were **not patched during this frozen rerun**.

| Finding | Reproduction and cause |
| --- | --- |
| Generic form changes use incorrect calculated stats/HP | Pokemon.formeChange assigns raw dex baseStats and leaves max HP unchanged. Level-50 Castform changes calculated 75-point stats to raw 70-point stats. Legal Forecast/Flower Gift transitions and independent level-50/100 cases reproduce this. A review of all 1,421 species records flags ten affected observations: Aegislash, three Castform weather forms, Sunshine Cherrim, both Darmanitan Zen forms, both Morpeko forms and Wishiwashi. Power Construct changes Zygarde from 42/168 HP to Complete at 42/168; the canonical helper requires 150/276 when preserving existing damage. |
| Shields Down uses incorrect native Minior names | Full-health native Minior stays in core form. Low-health Meteor becomes Minior-Core, which is absent from the loaded dex. The callback checks for Core, while the native core is named Minior. Both thresholds were reproduced. |
| Schooling lacks its minimum level | Fresh level-19 Wishiwashi incorrectly becomes School form. The level-20 positive case passes. The callback omits the required level-20 gate. |
| Instruct skips repeated-move PP and reports no effect | The repeated Tackle executes and deals damage, but target PP goes 35 → 34 → 33 for three uses instead of ending at 32. The generic called-move exemption suppresses the repeated move's PP charge. The outer message incorrectly reports no effect. A fresh explicit-PP replay reproduces this. |
| Present's healing branch does nothing | Two natural healing rolls on an injured target select power 0 and heal 0.25 but leave HP at 125/250 and 119/250 respectively. The callback writes move.heal, while generic healing reads raw['heal']. The original full-health target alone would not prove a defect because healing can legitimately cap. |

Terapagos uses a separate calculated native-form path. Its new 14-case replay passes, including calculated HP/stat transitions, real Teraform Zero clearing, later field persistence, suppression, rejected/copied activation, Stellar attacks, cancellation and the side budget.

## Expected behavior and corrected expectations

All ten original catalog diagnosis flags have final classifications. Five species flags are correct entry transitions: Castform weather forms and Sunshine Cherrim revert without required weather; native Terapagos becomes Terastal. Fresh legal-weather replays confirm the weather-form identities. The separate generic stat defect still applies.

Tera Shift correctly installs Tera Shell, so expecting the initial ability to remain unchanged was a fixture error. Imposter correctly spends temporary copied Tackle PP from 5 to 4 while owned Tackle stays at 35; the generic observer checked the wrong PP source.

Plasma Fists works during the same turn and then expires. In a fresh Ground-type test, same-turn Tackle becomes Electric and is immune; next-turn Tackle is Normal and deals damage. The original assertion incorrectly expected the field at the next prompt.

Celebrate, Happy Hour, Hold Hands and Splash have no direct effect in these PvP contexts. The original Sheer Cold miss is an expected accuracy outcome. Eight additional native Glalie attempts retained seven misses and one knockout, from 310 HP to zero. The hit's raw smoke label is preserved; a separate assessment against those exact saved observations verifies damage and zero target HP.

## Evidence, isolation and closeout

A verified PostgreSQL backup preceded fixture creation. Only three newly created QA accounts, their private room and their owned fixtures were used. Both battlers had ordinary player permissions; a separate staff identity prepared guarded fixtures and made read-only observations. Existing characters, Pokémon and older QA records were protected by a **5,492-row baseline**, checked throughout the run. The four unrelated WIP files and all pinned Python sources remain unchanged.

The final evidence audit checked **3,597 retained current records and 7,626 snapshots**, with **zero integrity errors, zero callback-failure observations and one consistent loaded code group**. The loaded-source audit matched **2,210 functions across 43 modules** with zero mismatches before and after gameplay. All 99 changed/new Python source pins and 44 runtime source pins remain unchanged. No reload was needed. The earlier mandatory three-order 3,805-test gate belongs to this unchanged build; this task's new verification is the logged-in sweep and its evidence audits.

All **5,492 protected pre-existing rows remain unchanged**. Only the three fresh QA accounts are disabled; staff rights and passwords are invalidated, and private credentials are removed. Exact credential-byte scans of retained artifacts and server logs passed both before and after removal, with zero matches or read errors. The final database query independently confirmed inactive, non-staff, non-superuser accounts with unusable passwords.

Private backups, redacted command evidence, hashes, raw classifications, diagnoses and audits are retained under .codex-artifacts/full-dex-rerun-20261018/. This directory and large server logs are already ignored by Git. No files or dependencies were downloaded; no migration, remote deployment or commit occurred. Backups and private evidence must remain local.
