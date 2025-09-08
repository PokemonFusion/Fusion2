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

## Battle HP Display

During a battle, trainers see exact hit point numbers for their own Pokémon
(for example, `25/40 HP`) while viewing the opposing team as percentages.
Spectators watching the fight see percentage-based values for both teams so
they know the relative health of each combatant without exact numbers.

### Example

```
Team A's view
  Team A
    Pikachu 35/50 HP
    Bulbasaur 20/45 HP
  Team B
    Charmander 26%
    Squirtle 86%

Team B's view
  Team A
    Pikachu 70%
    Bulbasaur 44%
  Team B
    Charmander 10/39 HP
    Squirtle 30/35 HP

Watcher view
  Team A: Pikachu 70%, Bulbasaur 44%
  Team B: Charmander 26%, Squirtle 86%
```

This ensures battlers can track precise HP while observers only see
percentages.

## Deterministic Battle Replays

Each battle script stores an ``rng_seed`` when it is created.  Logging this
value during debugging allows the sequence of random events to be
reconstructed.  Create a ``random.Random(rng_seed)`` instance and pass it
through battle helpers to reproduce move accuracy checks, damage rolls and
capture attempts exactly.
