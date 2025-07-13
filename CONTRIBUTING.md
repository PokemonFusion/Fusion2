# Contributing

Thank you for your interest in contributing to **Pokemon Fusion 2**. This project uses [Evennia](https://www.evennia.com/), and its dependencies are listed in `requirements.txt`.

## Setting up the development environment

1. Create and activate a virtual environment for Python 3.
2. Install the server requirements (this will install Evennia and other packages):

   ```bash
   pip install -r requirements.txt
   ```

3. Install the test requirements (optional) from `requirements-dev.txt`:

   ```bash
   pip install -r requirements-dev.txt
   ```

## Running the tests

Run the test suite from the repository root with `pytest`:

```bash
pytest
```

All tests should run without a running Evennia server as they stub the framework where needed.
