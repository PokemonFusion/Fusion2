# Isolated Nature mint migration rehearsal plan (#897)

Status: the user approved these isolated rehearsals. Execution and fixture
diagnostics are recorded below. Approval was required by `AGENTS.md`:
“Never run migrations without asking first.” Prior 0057–0058 and PF2-Dev
release approvals do not authorize the new 0059 rehearsal.

This plan applies only to the existing task-owned loopback PostgreSQL fixture.
It does not change any existing game schema, PF2-Dev, service or installed source.
The private DSN is read from this task's existing fixture state and never printed.
Every scenario runs in a fresh Python process and new random schema; the
`IsolatedPostgres` guard overrides all database aliases, checks the selected
schema on every connection and removes only that generated schema on completion
or failure. The wrapper and harness both reject a non-loopback DSN.

From `H:\PokemonFusionProject\fusion2-necrozma-items`, the proposed command is:

```powershell
H:\PokemonFusionProject\evenv\Scripts\python.exe -B .codex-artifacts/nature-mints-897-904-20261025/run_migrations.py approved-migrations
```

The reviewed wrapper launches:

```powershell
H:\PokemonFusionProject\evenv\Scripts\python.exe -B tests/integration/nature_mint_migrations.py
```

The second command requires the wrapper's private `PF2_TEST_POSTGRES_DSN`;
there is no fallback to server settings. Logs and exit/hash receipts remain in
the task artifact directory. If the existing task fixture is stopped, its
already authorized controller may resume it first; this plan starts no game
server, performs no service restart and requests no sudo.

Six scenarios cover an empty full-graph install, 0058→0059 upgrade, an already
active historical native pair, unused reversal/reapplication, refusal to remove
paid training, and an injected failure after real DDL with atomic rollback.
They check the 21 allowed values, invalid-value SQL refusal, model drift,
unchanged genetics/IVs/EVs/Hyper Training/inventory/progression, native source PP,
frozen companion fields, placement integrity and immutable historical receipts.
Historical pair setup is a labelled migration prerequisite, separate from the
ordinary captured/combined player tests.

Initially approved SHA-256 review inputs (retained historical receipt):

| File | SHA-256 |
| --- | --- |
| `tests/integration/nature_mint_migrations.py` | `da4c22675d8adb1fe824b508ee5e4ed3e9485ceb305a0e57797ba868ee525dc5` |
| `pokemon/migrations/0059_owned_trained_stat_nature.py` | `dc9f6287fc0800f9e91a1bb988923feac6f38ccc073bb99fa5da5f60e36d2a73` |
| `.codex-artifacts/nature-mints-897-904-20261025/run_migrations.py` | `dc3b6d659a52558adabd60e37761e19f4d739907d64a6074ba6a0fdb7e8b8880` |

0059 adds only a nullable trained preference and its constraint, with no genetic
rewrite, inferred training, stock or item grant. Its reverse operation refuses
nonblank training before removing the field. A failure is diagnostic evidence,
never permission to repair an existing game database or discard paid training.
Any revised migration/rehearsal source must be reviewed before execution.

## Approved-scope fixture corrections

The first rehearsal installed0059, then its inherited generic fresh fixture
correctly failed a stat read because it had blank genetic Nature. The fresh-only
fixture now explicitly authors Jolly after migration; upgrade rows still prove
unchanged genetics. This is labelled QA setup, not a migration backfill.

The next run passed fresh/upgrade but the inherited v1 audit rejected a combined
companion shape introduced in0058. The active-pair scenario now keeps the same
pending/replayed progression assertions and uses the existing current v3 audit.
The migration-stable v1 audit is unchanged. Both failed logs/hashes are retained.

The current audit then identified that the manually seeded historical receipt
lacked the actual host/source introduction fields. The fixture now records the
real source/host/companion identities and must pass v3 before0059 is applied.
This preserves the existing audit and all database guards.

Reviewed corrected harness SHA-256:
`62acf723ce5968f7cf85dcf43e2efeda82b9e6d9df30c033ee00502068091744`.
The migration and private wrapper remain byte-identical to the initially
approved inputs. All six scenarios, random-schema guards, loopback-only target,
cleanup and operational limits are unchanged. The rerun uses the same wrapper
with a new `approved-migrations-final` log label so prior evidence is
not overwritten. These routine fixture corrections stay inside the user's
approved isolated rehearsal scope; they authorize no new game operation.

The injected-failure runner also needed a fresh MigrationExecutor after its
baseline application; its stale loader initially attempted to recreate already
applied framework tables. The corrected atomic-failure diagnostic now passes,
including actual post-DDL rollback and reapplication. This is a harness loader
correction, with unchanged0059 and connection/cleanup guards. A complete final
six-scenario rerun and a full source/test gate include the corrected harness.
