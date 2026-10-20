# Knockout-boost reload and live acceptance — 2026-10-19

## Result

The authorized local Evennia reload completed successfully. **All 36 affected live checks and all 20 pilot scenarios passed.** Independent evidence audits passed with no errors, and no new server-log errors were found. No additional gameplay repairs were needed.

These checks used normal player commands through real localhost Telnet connections. Two fresh ordinary Player accounts battled; a separate temporary staff account prepared only tagged, newly owned fixtures in a private room and observed state. Staff did not invoke battle-effect callbacks or patch mechanics to obtain outcomes.

## Loaded build

The source matched the exact build that passed the optional dex/Showdown and standard regression gates in `optional-dex-showdown-2026-10-19.md`. No production source changed during this live task.

A verified local PostgreSQL backup preceded account creation and the reload. The backup is `.codex-artifacts/knockout-boost-live-20261019/before-qa.dump`, SHA-256 `575fb34d291360ccd8cdbc151d899d4c498ad2e5f8995c19e2c113b790ca9651`; its restore listing was checked.

The command `H:\PokemonFusionProject\evenv\Scripts\evennia.exe reload` returned success. Before and after gameplay, structural audits compared **2,708 loaded functions across 46 modules** against pinned source compiled without execution. Both audits had zero mismatches and identical loaded-version maps. The audit separately lists 62 generated/external functions. All 114 retained gameplay observations used one matching version group.

## Affected live checks

| Context | Checks | Required outcome |
| --- | ---: | --- |
| Direct knockout with an opposing reserve | 12 | Six native abilities receive their correct boost; six matched No Ability controls do not |
| Final opposing knockout | 12 | Six abilities and their six matched controls retain zero boosts after battle ends |
| Aftermath | 8 | Surviving carriers boost only while opponents remain; carriers fainted in the contact trade never boost, with and without reserves |
| Recoil trade | 2 | A carrier fainted by Double-Edge recoil receives no bonus despite living reserves |
| Indirect poison faint | 2 | False Swipe leaves the foe at 1 HP; subsequent poison fainting gives no direct-knockout bonus |
| **Total** | **36** | **All declared outcomes verified** |

The native positive carriers were Gyarados/Moxie, Nihilego/Beast Boost, Glastrier/Chilling Neigh, Spectrier/Grim Neigh, Calyrex-Ice/As One (Glastrier), and Calyrex-Shadow/As One (Spectrier). Moxie, Chilling Neigh and the Glastrier variant raised Attack; Grim Neigh and the Spectrier variant raised Special Attack; Nihilego's Beast Boost raised Special Defense.

The Aftermath, recoil and poison cases used Moxie and Beast Boost as representatives of the shared source-faint event path. Each targeted check observed actual owned moveslot PP use, the original source and target identities, and the raw battle roster. All seven stages were checked on the original carrier, including fainted carriers after replacement. The independent audit required a real living reserve where declared, the expected battle-ending state, the recorded damaging move/source, canonical starting HP, and exact Aftermath HP loss where applicable. It did not accept synthesized zero-stage defaults from replacement Pokémon.

## Twenty-scenario pilot

All twenty scenarios passed and their retained evidence was re-evaluated independently. Coverage includes damage/PP, type immunity, stat changes, healing, status and protection; Water Absorb, Levitate, Flash Fire and Intimidate; Leftovers, Stealth Rock, canonical party switching, both Fly turns, doubles Surf/Water Absorb, wild escape, Master Ball capture/storage placement, and trainer flee restrictions. The pilot contributed 42 observed states; the targeted checks contributed 72.

Normal concession or normal battle completion cleared each QA battle. No check required staff fallback cleanup. Callback-failure observations were empty, and the post-run log review found zero new exception/severity errors.

## Preservation and cleanup

All **6,526 pre-existing protected gameplay, object and character-attribute rows** remained unchanged, including existing characters and owned Pokémon. The preservation checks ran after preparation, during targeted execution, after the pilot, and after account retirement. All **1,099 pre-existing pinned files**, including earlier reports and unrelated WIP, remained byte-identical.

Only new QA accounts 61/62/63, characters 176/177/178, and private room 175 were used. All three accounts are now inactive, passwords unusable, and staff/superuser privileges removed. Temporary credentials were deleted. One final tagged QA-owned Pokémon remains with the retained test identities for inspection. No pre-existing character, Pokémon or QA fixture was reused or retired.

Exact password-byte scans of this run's artifacts, its work directory and all game logs found zero matches and zero scan errors before and after credential deletion: 173 and 175 files respectively. Gzip contents were inspected after decompression. An initial file-only scan over older archives was stopped before account retirement and replaced with this scoped scan.

All generated logs, compressed evidence, backups and local helper scripts are under the already ignored `.codex-artifacts/` directory; existing ignore rules also cover game logs and rotated logs. No downloads, installs, migrations, commits or remote operations occurred.

## Diagnostics and scope

One local driver preflight initially supplied a single case to an API expecting a case collection. The retained TypeError occurred before game connections or scenario setup. The driver was corrected, its 36 distinct fixtures validated before connecting, and the complete live execution passed. No live mechanics failures remained to diagnose or repair.

This proves the declared knockout boundaries and the twenty local pilot scenarios on the reloaded build. It does not constitute a new full-dex sweep, every interaction or probability distribution, browser-client acceptance, concurrency/soak testing, or production deployment. Staff-supplied moves do not prove natural learnsets.

Evidence is under `.codex-artifacts/knockout-boost-live-20261019/`; the original source/database preflight is under the sibling `knockout-boost-live-20261019-work/` directory. Key indices are `reload.json`, `catalog.json`, `knockout-contexts.json`, `results.json`, `knockout-independent-audit.json`, `pilot-independent-audit.json`, `pilot-after-reload/evidence-audit.json`, both `candidate01-loaded-code-audit*.json` files, `new-log-review.json`, `final-protection.json`, `final-account-safety.json`, both `secret-scan-*-disable.json` files, and `completion.json`.
