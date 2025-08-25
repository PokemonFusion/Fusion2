# Fusion2 Documentation

## Quickstart

1. Create and activate a Python 3.12 virtual environment:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) Install development extras:
   ```bash
   pip install -r requirements-dev.txt
   ```
4. Run the test suite:
   ```bash
   pytest
   ```
5. Start the Evennia server:
   ```bash
   evennia start
   ```

## Project Structure

- `commands/` - player command handlers
- `pokemon/` - core Pokémon game logic and data
- `server/` - server configuration and startup scripts
- `typeclasses/` - Evennia typeclasses for game objects
- `utils/` - shared utility helpers
- `world/` - world data and scripts
- `docs/` - project documentation and reference materials

See [code-map.md](code-map.md) for more details on the codebase layout.
