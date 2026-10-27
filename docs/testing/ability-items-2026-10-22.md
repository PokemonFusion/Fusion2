# Ability Capsule and Ability Patch acceptance - October 22, 2026

Issue: #769. Source baseline: `c9fdcaac7532cbfc8397d02ca1174f714e311608` on `staging`.

Both existing ability items now work through ordinary `+use`, with the same fresh party/current-Fusion eligibility, placement/trainer locks, inventory and target transaction used by field medicine. Only one legal ability name and one bag copy change. Success shows the committed old and new ability; no arbitrary ability argument or mutation route is added.

## Selected ability transition policy

The bounded policy follows Scarlet/Violet-style Patch reversibility. The [primary reference ability-change implementation](https://github.com/kwsch/PKHeX/blob/master/PKHeX.Core/Legality/Verifiers/Ability/AbilityChangeRules.cs) distinguishes ordinary-slot Capsule, ordinary-to-hidden Patch and generation-9 Patch reversal. PF2 explicitly chooses hidden-to-slot-0 reversal; Capsule can then select ordinary slot 1.

| Item | Current slot | Result |
| --- | --- | --- |
| Ability Capsule | ordinary 0 | ordinary 1 if present/distinct |
| Ability Capsule | ordinary 1 | ordinary 0 if present/distinct |
| Ability Capsule | hidden H or special S | no effect |
| Ability Patch | ordinary 0 or 1 | hidden H if present/distinct |
| Ability Patch | hidden H | ordinary 0 if present/distinct |
| Ability Patch | special S | no effect |

A single-ordinary-slot species can Patch if it has a distinct hidden slot, but cannot Capsule. Missing/distinctness failures spend no stock. Neither item creates/removes special S abilities such as Rockruff Own Tempo, Greninja Battle Bond or Zygarde Power Construct.

Canonical slots come only from the freshly saved exact native species/form. Nicknames, transformed copies and base-species fallback cannot grant eligibility. Regional and gender forms keep their own slots; unknown, battle-only, required-item/ability forms and fixed-gender mismatches reject unchanged. No form, held item or unlock is changed to make an item legal.

The model stores an ability name, not a separate ability index. Current and destination names must therefore identify unique normalized canonical slots; blank/foreign/ambiguous values reject unchanged. The checked-in dex audit found 1421 profiles with no duplicate normalized ability names within a profile. That metadata audit is separate from the actual command/SQL tests below; it is not proof every profile has a useful transition or a fresh player battle.

## Verified results

- **30 new PostgreSQL cases** cover both ordinary Capsule directions; Patch from either ordinary slot to H and H back to 0; actual inventory/party/use/reload and battle-Pokemon reconstruction; single-ability/no-hidden/special no-effect cases; native regional/gender and unsupported locked forms; nickname/foreign/ambiguous/malformed profiles; stale species/ability/owner; normal targeting/current Fusion/deposit/egg/reservation/battle guards; failed/partial debit and post-SQL save rollback/cache recovery; final-copy/different-target and mixed/two-copy contention; and evolution after both item types.
- **505 PostgreSQL cases total** passed: ability_item 30; field_training 30; legacy_berry 26; battle_item_validation 22; smoke_ball 17; player_doubles 10; battle_recovery 36; pp_capacity 37; name_resolution 8; capture_ether 21; status_item 9; rare_candy 25; field_item 23; field_berry 26; field_food 70; remaining_item 8; capture_pp_item 16; leader_crest 29; evolution 28; progression 11; cloud_gameplay 9; ui 14.
- **677 focused pytest tests** passed, including ability/native-form/transform, inventory, EV/stat, food/medicine, PP, battle validation, capture and evolution regressions.
- **Mandatory fresh-process orders:** combined: 4624 passed / 4014 skipped; repeat: 4624 passed / 4014 skipped; battle-first: 4624 passed / 4014 skipped.
- **973 frozen Python files** stayed unchanged throughout verification; **52 relevant source hashes** pin code, tests, help/workflow and the canonical dex generation files for staged/committed comparison.
- **65 command/SQL observations** preserve inputs/output, complete Pokemon/placement/move/boost rows, bag quantities and inventory cache.
- Passing logs contain dependency/cache warnings; a warning-free environment is not claimed.

## Ordinary player flow and failure evidence

Disposable setup creates normal User owners, canonical party slot 3, real bag stock and saved legal abilities. The production `+inventory`/`+party 3` commands discover the item and target; `+use Ability Capsule=3` changes Eevee Run Away to Adaptability (or the reverse), while Patch changes either ordinary ability to Anticipation or Anticipation back to Run Away. Output identifies the change and `+party 3` shows the new ability. Closing SQL connections, flushing the identity cache and reconstructing a production battle Pokemon retain the same result. Every other saved field, placement, move, HP/status, held item and progression value stays unchanged.

Rattata-Alola switches Gluttony/Hustle/Thick Fat and Meowstic-F uses Keen Eye/Infiltrator/Competitive, preserving native form and gender restrictions. Foreign base abilities and nickname spoofing reject. Capsule cannot spend on a hidden or one-ordinary-slot target; Patch cannot spend without a distinct H destination. Special S abilities remain independent. Invalid duplicate/malformed dex profiles are injected only as negative setup and never create successful effects.

After Patch, ordinary `+evolve <id> Fire Stone` maps Eevee H Anticipation to Flareon H Guts, and a later Patch returns to Flash Fire. After Capsule selects Eevee slot 1, Water Stone evolution retains existing fallback to Vaporeon ordinary slot 0 Water Absorb; Capsule then has no effect and keeps its copy. No evolution implementation changes are included.

Both items support exact normalized full names, legacy bag aliases, unambiguous name/full-ID/target-first syntax and the actual current fusion/self/me. Missing stock, eggs, normal box deposit followed by stale-ID use, inactive reservations, party gaps, duplicate names, foreign ownership, battle locks, move selectors and arbitrary ability arguments cannot alter rows or spend stock. Fainted legal targets can change ability and remain at zero HP with saved status unchanged.

A failed debit before or after real inventory SQL leaves full state unchanged. Exceptions injected after the actual ability UPDATE roll back ability, bag and inventory cache; shared model ability is restored. Two independent connections competing for the last copy cause one paid change, even across two different targets. Two stocked intentional uses serialize two legal paid toggles and may return to slot 0. When Capsule and Patch compete, Patch-first leaves Capsule unused on H; Capsule-first followed by Patch spends both. These outcomes preserve current-slot and inventory rules rather than claiming duplicate commands are free.

## Scope and cleanup

The [JSON report](ability-items-2026-10-22.json) embeds rules, command/SQL walkthroughs, exact test commands, counts/durations, source/log hashes, metadata audit and cleanup. Raw logs remain under ignored `.codex-artifacts/ability-items-20261022/`. The first 29-case run also passed; the final expanded frozen-build runs are acceptance. Lifecycle CI includes the new suite; a future hosted result is not asserted here.

This is local automated production-command/model evidence with captured session transport and real private PostgreSQL. It is separate from a fresh live login, current item availability, hosted CI completion, main merge, deployment or all-species live battles. Isolated schemas were removed, public schema is empty and the private task cluster stopped. No existing game database, human character, game service or migration runner was used.

Plot-only content, unrelated work, new definitions, arbitrary ability selection, slot schema changes and new form/unlock routes remain excluded. Existing medicine/berry/EV/PP, held/native forms, evolution and battle validation behavior retains regression coverage.
