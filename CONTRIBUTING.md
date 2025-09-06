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

Run the test suite from the repository root using the Makefile target that mirrors the CI configuration:

Continuous integration sets `PF2_NO_EVENNIA=1` to stub out the Evennia framework and avoid dependency issues.  Export this variable locally before running the tests to mimic the CI environment:

```bash
export PF2_NO_EVENNIA=1
make test
```

With this flag, all tests run without a running Evennia server as the framework is stubbed where needed.
