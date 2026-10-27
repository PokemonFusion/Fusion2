# Full local battle sweeps after recovery fixes — 2026-10-20

Fresh real-login sweeps on `fd402f9` completed for **1,421 Pokémon species/forms, 952 moves, 314 abilities, and all 283 retained battle/reward items**. **One shared mechanics defect remains confirmed and unfixed.** Raw passes are not substituted for valid effect proof.

## Confirmed defect

**Held-item forced forms lack a native-species eligibility check.** A normal Mew holding Flame Plate becomes Arceus-Fire; one holding Fire Memory becomes Silvally-Fire. The incorrect battle form also installs its native ability and calculated stats. Fresh ordinary-command reproductions confirmed both; the underlying owned species stayed Mew.

The cause is `Battle._apply_item_forme_effects` applying `Item.forced_forme` without checking the native base species before `Pokemon.formeChange` installs the requested form and ability. Nine fresh cases and independent review retained matching-item native positives, native no-item controls, foreign-holder failures, and the invalid No Ability controls.

**All 17 plate power probes are confounded:** their Mew holders entered as Arceus forms. Their original directional damage assertions passed, but they do not isolate the plate power effect. The matrix marks those 17 plates plus the directly reproduced Fire Memory eligibility failure as affected. Other forced-form item families need wrong-holder checks after the shared gate is repaired.

## Current results

| Coverage | Result |
| --- | --- |
| Pokémon species/forms | 1,421 catalog entries; all canonical calculated stats and maximum HP checks passed |
| Moves | 952 catalog entries; all 108 supplemental declared effect subjects qualified |
| Abilities | 311 have qualified positive effect evidence; No Ability control passed. Multitype and RKS System native activation was observed, with ability-only controls still invalid/open |
| Items | All 283 retained items exercised; 426 original assertions passed in 570 final case templates, but 17 plate damage probes are confounded by the confirmed form defect |
| Reward items | Eight effects plus an unassisted control passed |
| Native forms | 29 Ogerpon cases across four forms; 14 Terapagos/Teraform Zero cases passed |
| Knockout boundary | All 36 ongoing/terminal, Aftermath, recoil and indirect-faint checks passed |
| Complete ordinary battles | Three six-on-six PvP and two three-on-three NPC matches completed by knockout; wild item consumption persisted through normal victory |
| Real-login pilot | 20/20 passed with retained-proof audit |

Raw catalog statuses: `{"expected_failure": 6, "outcome_verified": 2317, "smoke_completed": 370}`. Six expected outcomes were individually reviewed: Celebrate, Happy Hour, Hold Hands and Splash in the declared PvP context; Present's full-HP healing cap; and a natural Sheer Cold miss. Injured Present healing and a successful native OHKO window were separately observed.

## Other diagnoses

- **Recycle:** the 20%-HP fixture consumed its Oran Berry on entry (32 to 42 HP), then consumed the recycled berry again (42 to 52 HP). The held-item endpoint assertion was invalid. Fresh below-half-HP reconsumption, above-half-HP held restoration, and no-used-item control checks passed. The original flag remains retained; only a task-local fixture was adjusted.
- **Mycelium Might:** the Limber target cures paralysis before the endpoint snapshot. The existing local Showdown simulator produced the same state. A fresh matched Good as Gold target proved persistent status bypass. The original flagged Limber case and local comparison remain retained.
- **Multitype/RKS System controls:** native held-item form entry reinstates the native ability, invalidating a No Ability control. Fresh native matching-item/no-item cases passed; the generic foreign-holder form defect remains open. These two abilities are not represented as clean ability-only passes.
- **Item-runner startup:** a late greeting left the first staff socket unauthenticated before any item battle. The failed startup transcript was retained; fresh sockets completed the item sweep. No game change was required.

## Data protection and cleanup

- **All 7,265 pre-existing protected rows across 32 tables remain unchanged.** Existing characters, Pokémon, ownership, placements, storage and related protected attributes were not modified or deleted.
- Two independently tagged teams used private rooms and only newly created fixtures. Ordinary Player accounts issued all battle choices; separate setup accounts prepared and observed those fresh fixtures.
- All six fresh QA accounts are disabled, passwords are unusable, temporary staff access is removed, and both temporary credential files are deleted.
- The exact original battle-room registry and live cache were restored. The advanced QA battle-ID counter remains to prevent reuse; unrelated pre-existing lock values were preserved.
- All 1,115 original pinned files remained unchanged. Loaded game modules matched the committed recovery-fixed source before and after testing. No source patch, reload, migration, dependency install, download, remote deployment, commit or push occurred.
- Final exact-credential scan: 7253 files, zero matches, zero scan errors. Raw evidence, failed attempts, local backups and rotating/compressed logs are retained under already ignored `.codex-artifacts/`; game logs are ignored too.

## Required followup

- Fix the forced_forme native-species eligibility gate, then rerun all affected plate power checks, wrong-holder item negatives, and Multitype/RKS System controls.
- The reusable Recycle fixture and Mycelium Might endpoint expectation still need their task-local corrections incorporated into durable runner definitions.
- Declared scenarios and observed branches do not establish every combined interaction, natural learnset, progression route or activation rate.
- 293 excluded item definitions, missing field-use/evolution/training/acquisition routes, full Mega/Z support, sustained load, abrupt crash/cold boot, browser UI and remote deployment remain separate.

The machine-readable matrix retains all 576 definitions and all 293 exclusions. Excluded definitions are not marked working.

[Current catalog, item matrix and diagnosis evidence](full-battle-postrecovery-2026-10-20.json).

Raw evidence roots:

- `H:\PokemonFusionProject\fusion2\.codex-artifacts\full-dex-postrecovery-20261020`
- `H:\PokemonFusionProject\fusion2\.codex-artifacts\full-items-postrecovery-20261020`
- `H:\PokemonFusionProject\fusion2\.codex-artifacts\full-battle-postrecovery-20261020`
