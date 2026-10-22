# Mega activation design validation (#774)

October 22, 2026. Baseline: `1c36da6f449ce837455a65a1fa616013eee95c62`.
This is a documentation/planning closeout. It implements no battle command,
item effect, acquisition source or world stock. All 986 Python source files
remained unchanged during validation.

The [contract](../design/mega-evolution.md) selects native Venusaur/Venusaurite
and proposed `+mega` followed by a normal legal `+attack`. It defines fresh
identity/held-state checks, team reservations, selected timing/effect rules,
Tera/Primal boundaries, durable state, rollback and cleanup. The optional
Counter's 10,000 price and finite stock 1 are deliberate PF2 authoring values,
not existing supply or canonical prices.

The [per-stone plan](../design/mega-stones.md) and
[JSON catalog](../design/mega-stones.json) cover all 48 loaded Mega Stone
definitions: 47 canonical pairs deferred for implementation, plus excluded CAP
Crucibellite. Every canonical pair appears exactly once: Venusaurite first,
then 46 pairs in nine batches of at most six. All pairs retain native HP base
stats. Thirteen confirmed open implementation issues (#784–#796) separate
effects, persistence, player acceptance, optional supply and later effects.
Zero ordinary-player Mega pairs are declared supported.

## Existing baseline checks

Both fresh-process runs used `PF2_NO_EVENNIA=1`, callback tests enabled,
`PYTEST_ADDOPTS` cleared, cache provider disabled and private checkout-local
basetemp directories. Python was `..\evenv\Scripts\python.exe -B`.

| Existing checks | Result |
| --- | --- |
| `pytest tests/test_battle_semantic_contracts.py -k form_change_semantic_contracts -q --run-callback-tests -o addopts= -p no:cacheprovider` | 17 passed |
| `pytest tests/test_terastallization.py pokemon/battle/tests/test_forced_item_form_eligibility.py pokemon/battle/tests/test_native_form_and_postbattle_items.py -q --run-callback-tests -o addopts= -p no:cacheprovider` | 205 passed |

These 222 tests preserve a useful baseline for internal form hooks, Tera and
native forced forms. They are **not** normal `+mega` acceptance. The
[JSON receipt](mega-design-2026-10-22.json) retains exact arguments, log hashes
and normalized-LF identities for all 986 Python files. The mandatory three-order
gate was not repeated for documentation-only changes; it remains required
after future executable changes.

## Source inspection and limits

`turns.py` contains internal `perform_mega_evolution`/pending-flag hooks, but
`commands/cmdsets/battle.py` registers no `CmdBattleMega`. Dynamic participant
and side flags are insufficient for a durable team budget. Current Pokemon,
battle-state and session serializers need the explicit origin, use, pending
and whole-roster restoration contracts before a player route can ship.
Owned-model reconstruction must not overwrite a valid battle overlay.

Inspection also separated raw held ownership from effective-item suppression,
reviewed the pre-switch lock phase, stat/Hyper Training calculation and the
post-battle restoration/sync boundary. No authored Venusaurite source was found
in the inspected source. The earlier #772 server snapshot is dated evidence,
not current stock verification. Existing #757/#772 snapshots were not rewritten.

Catalog coverage, issue mapping, unchanged Python scope and local Markdown
link targets were checked before publication. The linked primary references
inform the selected policy; newer external catalogs do not widen the local list.
No PostgreSQL acceptance, live login, deployment, service restart, migration,
character mutation or stock population occurred in this design task.
