# Contributing

Thank you for your interest in contributing to **Pokemon Fusion 2**. This project uses [Evennia](https://www.evennia.com/), and its dependencies are listed in `requirements.txt`.

## Setting up the development environment

1. Create and activate a virtual environment for **Python 3.12**:

   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```
2. Install the server requirements (this will install Evennia and other packages):

   ```bash
   pip install -r requirements.txt
   ```

3. Install the test requirements (optional) from `requirements-dev.txt`:

   ```bash
   pip install -r requirements-dev.txt
   ```

## Running the tests

Run commands from the `fusion2` repository root with the Python environment
that has the project dependencies installed. The canonical mandatory gate is:

```bash
python -B tools/run_mandatory_tests.py
```

For this Windows workspace, the existing environment can be invoked directly:

```powershell
..\evenv\Scripts\python.exe -B tools/run_mandatory_tests.py
```

`make test-mandatory` calls the same runner. It enables generated callback
checks and runs both test directories together in three fresh processes:
combined, repeat, and battle-first. It sets its own offline environment.

The parallel developer target remains available:

Continuous integration sets `PF2_NO_EVENNIA=1` to stub out the Evennia framework and avoid dependency issues.  Export this variable locally before running the tests to mimic the CI environment:

```bash
export PF2_NO_EVENNIA=1
make test
```

This target is separate from the mandatory fresh-process gate. See
[offline battle testing](docs/offline-battle-testing.md) for focused, exhaustive
dex, and Showdown commands and the distinction between offline checks and live
acceptance.

## Finding and documenting a feature

Start with the [code map](docs/code-map.md) for commands, services, models, and
representative tests. The [test source index](tests/README.md) describes feature
folders and shared support; the [tools index](tools/README.md) separates QA,
audits, and data generation. The [documentation home](docs/index.md) links feature
guides, design contracts, operational notes, and dated verification reports.

When adding a document, link it from the appropriate index. Keep a guide about
the workflow and put dated test results under `docs/testing`. Report the tested
build, environment, and limits without treating a local pass as deployment.
Preserve existing document paths when adding navigation so older links keep
working.

Keep disposable output under the locations described in
[local workspace hygiene](docs/workspace-hygiene.md). Preserve unrelated local
work and retained acceptance evidence during cleanup.
