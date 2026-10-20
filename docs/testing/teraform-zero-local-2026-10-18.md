# Teraform Zero local acceptance — 2026-10-18

Status: complete. The repair is loaded and verified on the local server; changes remain local and uncommitted.

## Diagnosis

Fresh ordinary QA players reproduced the rejection through `+tera` after native Terapagos entered as Terapagos-Terastal. Rain Dance and Electric Terrain were both active and remained unchanged. This was an explicit unsupported-form gate, rather than an accuracy roll, failed move, missing PP, or an ability failing to activate on entry.

Three integration gaps existed behind the gate:

- The activation path did not change Terastal Terapagos into Stellar or dispatch `AfterTerastallization`.
- Teraform Zero's old callback attempted another form change instead of clearing weather and terrain. Its isolated contract consequently asserted that incorrect transformation behavior.
- Native Stellar Terapagos needed its calculated form stats/HP, persistent Stellar boosts, and signature move behavior connected to the existing battle pipeline.

Rules were checked against the already-present local Showdown sources: `sim/battle-actions.ts` (Terastallization and Stellar boosts), `sim/pokemon.ts` (HP damage preservation), and `data/abilities.ts`, `data/moves.ts`, and `data/pokedex.ts`. No files or dependencies were downloaded.

## Resulting behavior

After Tera Shift, `+tera` reserves Stellar for native Terapagos-Terastal regardless of its saved ordinary Tera type. Its next committed move changes it into Terapagos-Stellar and installs Teraform Zero. Calculated max HP and other stats increase while the amount of existing damage is retained. The ability event then clears existing weather and terrain through the normal field lifecycle. Ordinary defensive typing stays Normal.

Use the ordinary player commands `+tera`, then `+attack <move>`. In doubles, specify the acting slot, for example `+tera A1`, then `+attack A1 Tera Starstorm B1`. No staff permission or owned-Pokémon edit is required.

Teraform Zero does not clear fields merely on entry or after a cancelled/failed declaration. Weather and terrain established later remain active. Suppression can prevent the ability's clearing effect. A copied ability on another species does not clear fields. The usual one-use allowance per side remains enforced; unsupported Ogerpon forms remain blocked.

Terapagos-Stellar retains its Stellar damage boosts for repeated uses. Its Tera Starstorm becomes Stellar, hits adjacent foes in doubles while sparing allies, and uses Physical damage when its staged Attack exceeds staged Special Attack. Other forms retain Normal Tera Starstorm. The move's shared dex definition is unchanged.

Native form changes and final restoration affect battle objects. The owned species, ability, moves, identity, placements and saved Tera configuration are not rewritten. Normal battle HP/status/PP persistence still applies to the disposable QA Pokémon.

## Isolation and evidence

This task created a new private room, two ordinary battlers and a separate fixture staff account. A verified local PostgreSQL backup preceded fixture creation, and a second verified backup preceded the authorized reload. The new protection baseline includes the old disabled QA fixtures and all other pre-existing rows.

Private, Git-ignored evidence is retained under `.codex-artifacts/teraform-zero-20261018/`, including the original rejection, exact redacted commands, complete before/after observations, candidate source pins, loaded-code audit, focused tests, mandatory gate output, protection checks and account cleanup.

The frozen local build passed **14/14 targeted real-login scenarios** and the **20/20 standard pilot**. The evidence audit checked 101 retained snapshots against one loaded code version group, ordinary battler permissions, no callback failures, and normal battle cleanup. The structural audit matched 2,210 loaded functions across 43 modules to frozen sources with zero mismatches. Focused tests, including semantic contracts, passed 384 checks.

Automated engine regressions additionally cover checkpoint rehydration, the wider weather/terrain matrix, calculated stats, defensive typing, dex isolation, and rejected-commit edge cases.

The first live attempts were correctly classified as runner/fixture issues: the observer represents an empty field as the string `"None"`; per-turn hit diagnostics expire before the next prompt; the physical damage fixture legitimately fainted; and asynchronous receive frames were mistaken for the previously captured rejection response. The runner now normalizes empty fields, observes retained executed moves read-only, uses a sufficiently durable target, and checks the captured response. No game source changed after the final candidate freeze.

All **5,388 protected pre-existing rows** and the four protected unrelated work files remain unchanged. Earlier unrelated work is preserved; the source comparison confines edits to the declared mechanics, tests, QA observer and result report. The previously clean Terastallization module and new focused test file are also included in the source freeze. The three fresh QA accounts are disabled, their passwords invalidated, staff rights removed, and private credentials deleted. Exact secret-byte scans passed both before and after deletion.

The mandatory fresh-process gate passed **3,805 tests with 4,010 optional skips in each order**:

| Order | Result | Duration |
| --- | --- | --- |
| Combined | Passed | 258.27 s |
| Repeat | Passed | 257.59 s |
| Battle first | Passed | 227.31 s |

The final candidate's game source stayed frozen through the gate and live replays. `git diff --check` passed. Logs, backups and compressed evidence remain Git-ignored. No downloads, migrations, remote changes or commits occurred. This is local-server evidence.
