# Pokemon Fusion 2 Test Server

This project is an experimental MUD built with [Evennia](https://www.evennia.com/). It aims to reimagine the world of Pokémon in a text-based multiplayer setting. The repository hosts the game code as well as data files for Pokémon, regions and mechanics.

Please note that the server is under heavy development. You can follow progress on the project repository and report issues on the corresponding tracker.

For setup instructions and other notes migrated from the original Evennia README, see [README.instructions.md](README.instructions.md).

## Documentation

Project documentation lives in the [docs](docs/) folder:

- [Documentation home](docs/index.md) - choose a guide, design, or verification report.
- [Feature guides](docs/guides.md) - find player and builder workflows by system.
- [Code map](docs/code-map.md) - trace commands, logic, storage, and tests.
- [Verification reports](docs/testing/README.md) - dated evidence and its limits.
- [Local workspace hygiene](docs/workspace-hygiene.md) - keep test output organized.

The codebase targets **Python 3.12**. To run the server you must install the Python requirements, including `psycopg2` for PostgreSQL support:

```bash
pip install -r requirements.txt
```

## Contributing and Testing

Development requirements, including the Evennia framework, are installed from `requirements.txt`.  Test-specific packages are kept in `requirements-dev.txt`.

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # optional
```

Continuous integration stubs out the Evennia dependency by setting `PF2_NO_EVENNIA=1` before running tests.  Export this variable locally to mimic the CI environment and avoid requiring Evennia:

```bash
export PF2_NO_EVENNIA=1
make test
```

For the canonical mandatory gate, use `python -B tools/run_mandatory_tests.py`
with the project's Python environment. See [CONTRIBUTING.md](CONTRIBUTING.md)
and [offline battle testing](docs/offline-battle-testing.md) for the different
test targets and their scope.

A project-wide [.editorconfig](.editorconfig) specifies space indentation and LF line endings. Ruff is configured in [pyproject.toml](pyproject.toml), and tests are discovered via [pytest.ini](pytest.ini). Use [.env.example](.env.example) as the local environment template. Common development tasks are provided by the [Makefile](Makefile):

```bash
make setup  # install dependencies
make lint   # run Ruff
make test   # run tests
```

## License

This project is distributed under the terms of the [MIT License](LICENSE).
