# Hyper Training contention fixture closeout (#783)

October 22, 2026. This correction changes only the PostgreSQL fixture in
`tests/integration/hyper_training_cases.py`; production training/inventory
behavior is unchanged. Prior baseline diagnostics in the #773 report remain
unaltered: retained objects could report partial flags while committed SQL held
all six. The corrected assertions read independent SQL and reload the model.

The final-copy test also reloads its retained target before checking training.
Other contention assertions were audited: distinct-target and duplicate/distinct
stat tests already read SQL/fresh models. The Gold/single test retains every
flag, genetic IV, HP-deficit policy, unrelated field and exact Gold debit check;
the concurrent single-cap debit remains legally zero or one. New explicit tests
prove Gold-first leaves the single cap, while single-first spends both.

| Final checks | Result |
| --- | --- |
| Complete Hyper Training PostgreSQL suite | 31 passed |
| Additional genuine concurrent attempts | 30 passed |
| Both explicit serialized orders, five times each | 10 passed |
| Focused Hyper Training unit regressions | 11 passed |
| Mandatory combined/repeat/battle-first fresh processes | 4,729 passed / 4,014 skipped each |

All 43 captured final-state observations have seven exact SQL flags (the six
training markers plus the unchanged fixture flag), matching the fresh model;
all genetic IVs remain `[0,1,2,3,4,5]`. Retained objects differed from final SQL
in **0** observations. Their values are diagnostic, never accepted in place
of committed state. Inventory checks retain Gold remaining zero and the exact
serialized/allowed concurrent single-cap outcome.

The [JSON receipt](hyper-training-fixtures-2026-10-22.json) retains command
arguments, summaries/log hashes, SQL-versus-retained-versus-reloaded evidence
and all 986 Python source identities frozen through validation. Only the
named fixture differs from its baseline; #774–#776 design publication is
separate. Standalone suites used the schema-guarded private PostgreSQL harness,
real commands and worker connections, not the game database or migrations.
An initial sandbox cluster launch failed before connection; the disposable
cluster then started successfully and all qualifying suites passed.

This is local automated ordinary-command/model QA, not a fresh live login,
availability, hosted CI, merge or deployment claim. No production source,
plot item, running game data, migration or service restart is changed.
