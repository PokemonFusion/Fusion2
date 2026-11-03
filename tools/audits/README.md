# Audit and maintenance tools

[Tools index](../README.md) | [Code map](../../docs/code-map.md) |
[Item guides](../../docs/guides.md#items-acquisition-and-progression)

| Tool | Purpose |
| --- | --- |
| [audit_item_availability.py](audit_item_availability.py) | Audit item support, acquisition sources, and bounded evidence |
| [reconcile_item_support.py](reconcile_item_support.py) | Reconcile the checked-in item matrix with declared support/evidence |
| [ci_assessor.py](ci_assessor.py) | Inspect CI configuration; its explicit write option changes files |
| [org_score.py](org_score.py) | Report repository organization heuristics; its score is not a gameplay or readiness check |

From the repository root:

```powershell
..\evenv\Scripts\python.exe -B tools/audits/audit_item_availability.py --help
..\evenv\Scripts\python.exe -B tools/audits/reconcile_item_support.py --check
..\evenv\Scripts\python.exe -B tools/audits/ci_assessor.py --help
..\evenv\Scripts\python.exe -B tools/audits/org_score.py
```

These four scripts formerly lived directly under `tools/`. Use the new
`tools/audits/` paths in current commands. Dated reports and immutable receipts
can retain their earlier paths and source pins. Read each tool's options before
selecting actions that write output or compare a running environment.
