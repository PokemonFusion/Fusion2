# Agent Guidelines

This repository hosts a text-based Pokémon game built on the Evennia MUD framework.  Code is primarily Python and should follow object oriented design practices.

## Style and Conventions

- Use **OOP principles** when implementing new features.  Favor classes and methods over large procedural blocks.
- Prefer class objects over dictionaries where appropriate.
- Keep code consistent with PEP 8 where practical and mimic the existing style of the project.
- Include module, class and function docstrings.
 - Avoid modifying generated data files in `pokemon/scripts` or `pokemon/data` unless explicitly required.
 - When recreating Pokémon stats such as max HP during tests or data restoration,
   use the `get_max_hp` function from `pokemon.helpers.pokemon_helpers` with the
  Pokémon's IVs, EVs, nature and level rather than hardcoded values.
- The same module also exposes `get_stats` and `_get_stats_from_data` which
  should be used when you need a full stat dictionary or to calculate stats
  from stored data.
- Follow the existing battle architecture when changing combat or battle-related behavior.

## Development Workflow

1. Install dependencies with `pip install -r requirements.txt` and, if needed, `pip install -r requirements-dev.txt`.
2. After modifying Python code, run the test suite with `pytest -q` from the repository root.  Ensure tests pass before committing.
3. Summarize your changes in the PR description and mention any test results.

## Operational Guardrails

- Never run migrations without asking first.
- Never restart services without asking first.
- Never use `sudo` without asking first.

## PF2-Dev Server Administration

- You are connected to PF2-Dev for server administration only.
- Do not edit project source code on this server.
- Do not commit code changes.
- Do not run migrations.
- Do not use `sudo` unless the exact command is explicitly approved.
- Do not restart Evennia, PostgreSQL, nginx, or the server unless explicitly approved.
- Do not delete files or directories unless explicitly approved.
- Prefer inspection, reporting, and setup verification.
- For installs or config changes, propose the exact commands first and wait.

More specific instructions may exist in subdirectories.  If so, those will override these rules within their scope.
