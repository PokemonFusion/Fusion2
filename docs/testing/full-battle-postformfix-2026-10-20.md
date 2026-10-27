# Full local battle sweeps with forced-form repair — 2026-10-20

**Passed the declared live scope:** 1,421 Pokémon species/forms, 952 moves, 314 abilities, and all 283 retained battle/reward items. No confirmed mechanics defects or unreviewed failures remain in this run.

The frozen working tree is based on `fd402f935e9e6c8980d41cd3beb9f86d2c9849a8` and includes the prior uncommitted forced-form repair. All 1,120 original nonignored files were pinned by SHA-256 before play and remained unchanged. Loaded source matched across 50 modules and 2,739 functions before and after testing. The prior three-process mandatory suite is separate evidence for this same repair; no new source patch or reload was needed here.

| Coverage | Current result |
| --- | --- |
| Pokémon species/forms | 1,421 catalog cases; canonical calculated stats and maximum HP checked for every entry |
| Moves | 952 catalog entries plus all 108 supplemental declared effect subjects |
| Abilities | Positive effect proof for all 313 effect-bearing abilities; No Ability negative control |
| Items | All 283 retained items; 426 direct PvP effect probes in 570 final case templates, plus eight reward effects and a control |
| Forced forms | All 92 eligibility cases: 45 foreign holders, 45 native holders, and two missing-ability controls |
| Plates | All 17 damage comparisons passed with initial/final species, type, ability and calculated-stat guards |
| Native Tera forms | All 29 Ogerpon cases across four forms and 14 Terapagos/Teraform Zero cases |
| Knockout boundary | All 36 ongoing/terminal, Aftermath, recoil and indirect-faint cases |
| Complete ordinary battles | Three six-on-six PvP and two three-on-three NPC battles completed by knockout; wild item consumption persisted through victory |
| Pilot | 20/20 scenarios passed with independent retained-evidence audit |

## Diagnosis and qualification

Raw catalog statuses: `{"expected_failure": 5, "outcome_verified": 2317, "smoke_completed": 371}`. Raw smoke status remains visible and is joined to fresh actual-effect proof rather than relabeled as a raw pass. Expected negative outcomes were individually reviewed; injured Present healing and a successful native OHKO window were separately exercised.

Specialized ability opportunities, including retained retries: `{"chance_not_observed": 12, "outcome_verified": 84}`. A chance-only nonactivation stays inconclusive for that opportunity; every one of the 313 effect-bearing abilities must still have a separately observed positive effect before this report can pass. Activation rates are not certified by these windows.

The previous forced-form defect did not recur. Foreign holders retained their own species, ability, typing and calculated stats, while eligible native holders changed correctly. Multitype and RKS System now have valid ability-only controls.

Two known fixture expectations were corrected only in this task’s saved plans before execution: Recycle starts at 49% HP so its restored berry can remain held after the entry heal; Mycelium Might uses Good as Gold for a persistent bypass positive and Limber as an expected cure negative. Natural chance windows retain unsuccessful attempts. No mechanics patch was applied during the sweeps.

The initial catalog audit stopped because the orchestration omitted its separate catalog index. The index was recovered after execution from the unchanged pre-run-pinned case-builder source, requiring exact equality with all 2,693 saved stimuli, result identities and execution order. The original compressed records were unchanged, the failed audit was archived, and the affected audit passed on rerun. This setup error is retained separately from mechanics results.

Catalog and effect battles used two different fresh teams. The final audit admits exactly their pinned whole actor pairs, checks the source SHA-256 of each copied catalog record, and requires the expected ordinary actors, loaded build, clean callbacks and cleanup in retained states. No prior run outcome is substituted for current execution.

## Data protection and cleanup

All **7,649 preexisting protected rows across 32 tables remained unchanged**, including characters, Pokémon, ownership, storage, placements and related attributes. Both preparations independently verified their immediate baseline; all later checks used the shared original baseline from before either team existed.

All six fresh QA accounts were retired: inactive, unusable passwords, temporary staff access removed, and credential files deleted. Only tagged private fixtures were used. The exact original battle-room registry and live cache were restored, the advanced QA battle-ID counter was retained, and unrelated original lock values were preserved.

The final exact-credential scan covered 11,224 files with zero matches and zero scan errors. Raw evidence, failed attempts, backups and rotating/compressed logs remain under already ignored `.codex-artifacts/`; server logs are ignored. No dependency install, download, migration, reload, remote deployment, commit or push occurred.

## Remaining boundaries

- Declared effects and observed branches do not establish every combined interaction, natural learnset, progression route or activation rate.
- 293 excluded item definitions and missing field-use, evolution, training and acquisition routes remain outside this battle-item scope.
- Full Mega/Z support, sustained load, abrupt crash/cold boot, browser UI and remote deployment remain separate acceptance work.
- Recycle and Mycelium Might use explicit task-local corrected fixtures here; the reusable runner definitions still need those fixture corrections incorporated durably.

This is current local acceptance of the declared battle scenarios, not a release or deployment signoff.

[Machine-readable matrix and audit](H:/PokemonFusionProject/fusion2/docs/testing/full-battle-postformfix-2026-10-20.json).

Raw evidence roots:

- `H:\PokemonFusionProject\fusion2\.codex-artifacts\full-dex-postformfix-20261020`
- `H:\PokemonFusionProject\fusion2\.codex-artifacts\full-items-postformfix-20261020`
- `H:\PokemonFusionProject\fusion2\.codex-artifacts\full-effects-postformfix-20261020`
- `H:\PokemonFusionProject\fusion2\.codex-artifacts\full-battle-postformfix-20261020`
