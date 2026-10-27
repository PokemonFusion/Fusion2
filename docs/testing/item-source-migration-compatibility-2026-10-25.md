# Supply Corner migration compatibility (2026-10-25)

#862 remains open. Its migration qualification exposed three dependencies on
`objects.0016_delete_exit`, a node absent from the deployed framework history.
The same Evennia 6.0.0 version label did not guarantee identical migration files:
the local environment also contained later, project-specific proxy migrations.

The three project migrations now depend on the common ObjectDB 0013 migration,
which supplies its current primary-key type. Their model/schema/data operations
are unchanged, verified by comparing their syntax trees with dependencies removed.
This adds no framework migration file, version upgrade, data repair or item effect.
Existing histories that already include later ObjectDB migrations retain those
records. The deployed-history atomic fixture deliberately adds an unknown legacy
0014 record in its disposable schema and verifies preservation without inventing
its missing file.

## Verification

- The graph regression first passed the installed history and reproduced the
  missing-node failure with the deployed ObjectDB files through 0013. Both cases
  pass after the repair. Graph construction uses no database.
- Twenty-eight isolated PostgreSQL rehearsals passed: fourteen each against the
  installed and deployed ObjectDB histories. Each group covers six ownership/
  marketplace/daycare/breeding fresh/upgrade/refusal cases, seven native-pair
  fresh/upgrade/refusal/reverse cases, and one seeded whole-chain 0045→0058 case.
  The latter proves deliberate outer rollback, identical legacy assets, successful
  commit including post_migrate, preserved migration records and usable progression.
  Its initial strict whole-row comparison detected the expected new nullable
  combination_id column. The corrected fixture preserves every original column
  and separately proves that no existing asset gained a combination link; the
  failed snapshot/diagnosis are retained, with no additional game-code change.
- Forty-three production-command/PostgreSQL acquisition cases passed: eleven
  Supply Corner cases and thirty-two general acquisition cases. They cover
  travel, menu, six useful effects,
  conservation, conflicts, rollback, finite stock, concurrent last-copy purchase,
  and installer retry. These use disposable schemas and separate authored fixtures.
  The task-owned cluster is stopped with zero remaining schemas/public tables.
- All three fresh full-suite orders passed **6,188 tests /4,028 skipped** each;
  wrapper exit zero. The final 1,139 Python identities match the qualified copy;
  all twenty-five unrelated dirty paths in the shared checkout are preserved.

[Machine receipt and exact per-scenario log hashes](item-source-migration-compatibility-2026-10-25.json).
The explicit PostgreSQL checks qualify their cases separately from the full
suite's skipped database wrappers.

## Remaining acceptance

These results qualify the source prerequisite. They do not install permanent
stock or complete a deliberately released ordinary-player walkthrough. The
original [published plan](item-source-release-plan-2026-10-25.md) names a different
candidate; any replacement must identify its exact build and obtain the required
operational approval. #862 stays open until its public route and six effects pass.
Plot-only items, unrelated work and new acquisition policy remain excluded.
