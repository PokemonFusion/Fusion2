# Agent Guidelines

This repository hosts a text-based Pokémon game built on the Evennia MUD framework.  Code is primarily Python and should follow object oriented design practices.

## Style and Conventions

- Use **OOP principles** when implementing new features.  Favor classes and methods over large procedural blocks.
- Keep code consistent with PEP 8 where practical and mimic the existing style of the project.
- Include module, class and function docstrings.
- Avoid modifying generated data files in `helpers/scripts` or `pokemon/data` unless explicitly required.

## Development Workflow

1. Install dependencies with `pip install -r requirements.txt` and, if needed, `pip install -r requirements-dev.txt`.
2. After modifying Python code, run the test suite with `pytest -q` from the repository root.  Ensure tests pass before committing.
3. Summarize your changes in the PR description and mention any test results.

More specific instructions may exist in subdirectories.  If so, those will override these rules within their scope.
