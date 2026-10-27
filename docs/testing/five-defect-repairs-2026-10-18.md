# Five diagnosed battle repairs — local acceptance, 2026-10-18

Status: complete. All five repairs are loaded and verified on the local server. Changes are local and uncommitted.

This repairs the five confirmed defects from the [full dex rerun](full-dex-rerun-2026-10-18.md). No files or dependencies are downloaded. Fresh private QA identities are used; older characters, Pokémon and QA fixtures remain protected.

## Repairs

- Generic form changes now use calculated stats with level, IVs, EVs and nature. HP-changing forms recalculate max HP while preserving damage; fainted Pokémon stay fainted. Same-HP forms retain their HP pool, boosts and training. Unknown forms are rejected before identity changes.
- Shields Down uses the loaded Minior and Minior-Meteor names, preserves the original core identity, and respects both HP thresholds. Transformed or fainted holders do not trigger native transitions.
- Schooling requires level 20 and more than one-quarter HP for School form. Level 19, low HP, transformed and fainted cases have explicit regressions.
- Instruct repeats use the target's learned PP and ordinary cost/prevention path. Other callers keep their PP exemption. Empty PP and forbidden charging/recharging/repeat moves are rejected. Successful repeats receive called-move feedback instead of a false no-effect message. Reduced custom executable-move adapters remain supported.
- Present supplies per-use healing metadata to the normal healing pipeline and avoids the damage branch when healing is selected. It resets branch data between uses, respects accuracy, HP caps and Heal Block, and preserves shared dex data. The natural power distribution is 20% healing, 40% power 40, 30% power 80 and 10% power 120. A related Heal Block callback relay argument mismatch was corrected during the negative regression.

## Validation

The focused run passed **395 tests**, including all semantic contracts, new five-defect regressions, item/form hooks, field-stat paths and other called-move PP behavior. Fourteen older form contracts asserted raw dex values; they now assert calculated level-50 stats. Power Construct's HP assertion now preserves damage across its max-HP increase. Their original failures are retained privately.

The mandatory gate passed **3,845 tests with 4,010 optional skips in each of three fresh processes**: normal, repeat and battle-first. Callbacks were enabled. The initial failed gate and the superseded candidate02 run remain private diagnostic history; acceptance uses only the final frozen candidate03.

Fresh ordinary QA players completed **35/35 affected gameplay cases**, including all 12 targeted diagnosis fixtures, 16 affected/related species and seven related moves. Separate qualifications check every retained native calculated-stat/max-HP observation, Power Construct damage preservation, Instruct PP and feedback, and each observed natural Present healing roll. **11/11 selected ability/control comparisons** passed. The **14/14 Terapagos regressions** and **20/20 standard pilot** also passed. No game source changed after the final freeze.

Present's negative checks include full HP, Heal Block, Substitute and a real miss. Instruct's negative checks include depleted PP and disallowed repeats. These are declared scenario outcomes; they do not establish every possible interaction or chance distribution.

The evidence audit verified **91 retained current records and 244 snapshots**, with zero integrity errors or callback-failure observations and one loaded code group. The structural audit matched **2210 functions in 43 modules** before and after gameplay, with zero mismatches. All 100 Python source pins and 44 runtime source pins remained unchanged. The full 2,693-entry catalog remains historical evidence from before these repairs; it was not rerun here.

## Isolation

A verified local PostgreSQL backup preceded creation of three fresh accounts and a private fixture room. Ordinary battlers execute player commands; a separate staff identity prepares only guarded QA fixtures and reads battle observations. Protection hashes cover all pre-existing rows, including earlier disabled QA accounts and Pokémon. Unrelated dirty work remains preserved.

Private logs, backups, commands, before/after state, source pins, diagnoses and final cleanup audits are retained in .codex-artifacts/five-defect-repair-20261018/, already ignored by Git. No migration, remote deployment or commit is part of this repair.


Final closeout: **all 5,618 pre-existing protected rows and unrelated WIP are unchanged**. Only the three new QA accounts were disabled; staff rights/passwords were invalidated and private credentials removed. Exact credential-byte scans passed before and after deletion, with zero matches or read errors. A final database query independently verified inactive accounts with no staff/superuser rights and unusable passwords. A second verified backup and isolation check preceded the authorized local reload.

The 35 affected cases retain **32 outcome-verified records and three supplemental smoke records**. A separate audit independently re-evaluated all 35 sets of qualifications against the exact saved observations with zero errors. Concrete repair observations include Power Construct changing 42/168 HP into 150/276 while preserving damage, target Tackle PP going 35 → 34 → 32 through Instruct, and a natural Present healing roll increasing 113/250 HP to 175/250.

Three initial Castform catalog flags were classified as expected clear-weather reversion combined with an obsolete type expectation. Their original records are preserved. Corrected explicit entry-form/type assertions, PP, owned identity and calculated-stat qualifications passed in fresh replays. No game source changed for these fixture corrections.
