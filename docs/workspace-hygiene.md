# Local workspace hygiene

Run development commands from the `fusion2` repository root. Runtime packages,
tracked tests, authored world data, and documentation keep their existing paths.

## Disposable output and retained evidence

| Location | Purpose |
| --- | --- |
| `.codex-artifacts/test-work/<task>/` | Explicit scratch location for focused local test runs |
| `.codex-artifacts/<task>/` | Retained local observations, backups, logs, and QA receipts |
| `.codex-artifacts/local-clutter-20261030/` | Archived root-level test/cache folders from the first organization pass; `manifest.json` maps original paths to archive paths |
| `.pytest_cache*`, `.ruff_cache`, `__pycache__` | Regenerable tool caches; ignored by Git |
| `.pytest-basetemp-mandatory-*` | Temporary directories created by the existing mandatory runner; normally removed when it exits |

For a focused run that needs an explicit pytest temporary directory:

```powershell
..\evenv\Scripts\python.exe -B -m pytest tests/test_trade_safety.py --basetemp .codex-artifacts/test-work/trade-safety
```

Pytest clears the selected `--basetemp` directory. Choose a dedicated scratch
directory, never the retained evidence directory or the `.codex-artifacts` root.
Use a distinct task directory for concurrent runs. The canonical mandatory
command remains in [offline battle testing](offline-battle-testing.md); it
manages its own temporary directories.

## Reviewing old folders

Check that no test process is using a folder before moving or removing it.
Inspect its contents: a temporary-looking name can still contain the only copy
of a useful log or observation. Archive retained material with a manifest rather
than assuming every ignored directory is disposable.

The October 30 archive records successful moves and any folders retained because
of access errors. Check the manifest before restoring an original path; do not
overwrite a newly created folder with an older run's contents. Archiving clears
the project root but does not reclaim disk space.

Databases, `server/conf/secret_settings.py`, server logs, and QA backups need
their own retention decisions. Sibling checkouts and worktrees under
`H:\PokemonFusionProject` are separate from this repository's test clutter.

## Adding documentation

- Player and builder workflows: add a guide and link it from [feature guides](guides.md).
- Design contracts and proposals: link them from the [design index](design/README.md).
- Persistence, permissions, and operator workflows: use the [operations index](operations/README.md).
- Dated validation reports and companion receipts: use the [testing index](testing/README.md).
- Entry-point changes: update the [code map](code-map.md).

Keep established file paths stable when improving navigation. Record evidence
at its original scope and date, and link later reports for corrections or broader
acceptance.
