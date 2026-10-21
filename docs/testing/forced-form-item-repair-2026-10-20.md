# Forced-form item repair and local acceptance — 2026-10-20

**The forced-form item eligibility defect is fixed and the affected live checks pass.** Existing characters and Pokémon were not modified. No files were downloaded.

## Repair

The shared item-form path now uses canonical dex base species for both the original and current Pokémon identity. It rejects foreign and transformed holders, requires Multitype or RKS System for their forms, and compares species rather than nicknames. The guard also runs before Primal callbacks so a copied appearance or a matching nickname cannot activate another species’ item form.

The repair is in `pokemon/battle/engine.py`. New regression coverage exercises every one of the 62 loaded forced-form item definitions with a foreign holder and a matching native holder, plus missing abilities, copied appearances, original identity and nickname cases. Existing callback fixtures now construct native Genesect/Groudon/Kyogre with calculated stats, rather than renaming a generic Attacker.

## Validation

| Check | Result |
| --- | --- |
| Fresh pre-fix live reproductions | 4 reproduced: Mew/Flame Plate, Mew/Fire Memory, Arceus/No Ability, Silvally/No Ability |
| New regressions | 134 passed |
| Focused regressions and existing callback tests | 180 passed |
| Mandatory combined, repeat and battle-first suite orders | 4,333 passed and 4,014 optional checks skipped in each of three fresh processes |
| Live foreign/native eligibility | 45 foreign holders, 45 native holders and two missing-ability controls passed |
| Live plate power | 17 checks in 34 battles passed; both comparisons retain native Mew identity, Psychic typing, prepared ability and canonical stats at entry and after the attack |
| Live Multitype/RKS System | Both original ability-only matched pairs passed; No Ability controls stay Normal and do not gain the native ability |
| Real-login pilot | 20/20 passed with retained-proof audit |
| Lint and diff checks | Touched-file Ruff and `git diff --check` passed |

The plate plan retains its existing issue #757 attribution. No new issue was created or existing issue closed by this task.

All battle choices used ordinary Player Telnet commands in a new private QA room. Independent audits checked exact command order, evidence hashes, account/character IDs, original owned identities, actual effects, calculated stats, PP, held-item persistence and cleanup. The repaired server matched 50 loaded modules and 2,739 functions. Only the battle engine’s loaded version changed.

## Diagnosed test failures

The first full-suite attempt found three old callback fixtures that had changed only a generic Pokémon’s name/species label, leaving the original native identity as Attacker. The new guard correctly rejected those holders. The fixtures were repaired to use real native species and calculated stats; the affected tests and all three full-suite orders then passed. The original failures remain retained.

Two test-only lint cleanups followed live acceptance: an extra blank line and an unused import. All test function ASTs remained identical, focused tests passed again, and a final loaded-code audit confirmed the same production build. The final source snapshot retains these cleanups separately from the immutable live candidate.

## Protection and operations

- **All 7,545 pre-existing protected rows across 32 tables remain unchanged.** Existing characters, Pokémon, ownership, placements, storage and protected attributes were not updated or deleted.
- A verified local PostgreSQL backup preceded fixture creation. Only three new tagged accounts and one private room were used. All three accounts are now inactive, passwords unusable, temporary privileges removed, and the temporary credential file deleted.
- The original room registry and cache were restored exactly. The advanced QA battle counter was kept to avoid ID reuse, and unrelated existing lock values were preserved.
- 1,115 unrelated original files, including both existing uncommitted sweep reports, remain unchanged. The final candidate pins 1,118 files.
- The final exact-credential scan checked 3683 files with zero matches and zero errors. Logs, snapshots, backups and failed attempts are in already ignored `.codex-artifacts/`; game logs are ignored too.
- One authorized local reload loaded the repair. No dependency installation, migration, download, remote deployment, commit or push was performed.

This is affected-check acceptance. The previous full-sweep report remains an accurate record of the earlier run; a new complete catalog/item sweep was not performed here. It does not establish every combined interaction or release readiness.

[Machine-readable results and proof references](forced-form-item-repair-2026-10-20.json).

Raw evidence: `H:\PokemonFusionProject\fusion2\.codex-artifacts\forced-form-items-fix-20261020`.
