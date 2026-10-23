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
See [offline-battle-testing.md](offline-battle-testing.md) for the non-live
battle validation workflow.
See [held-incense.md](held-incense.md) for the five existing incense boosters,
ordinary equip/battle routes and current bounded acceptance evidence.
See [battle-recovery-items.md](battle-recovery-items.md) for the named manual
battle food/berry allowlist, exclusions and action/rollback policy.
See [item-availability.md](item-availability.md) for acquisition, ordinary item
commands and the dated limits of authored stock and current-world evidence.
See the [released nine-item walkthrough](testing/item-live-2026-10-22.md) for
PF2-Dev purchase/effect/reconnect proof, fixture cleanup and remaining feedback.
See the [Mega Stone player guide](mega-evolution.md),
[activation contract](design/mega-evolution.md) and
[per-stone rollout](design/mega-stones.md) for the bounded non-plot Mega route,
its optional source and the 47 locally accepted canonical pairs.
See [design/z-moves.md](design/z-moves.md) and its
[crystal inventory](design/z-crystals.md) plus [Z-Move guide](z-moves.md) for the
42 accepted generic/status/signature mappings and remaining gates. The
[Necrozma combine/separate plan](design/necrozma-combination.md) scopes a safe
non-plot lifecycle and its open implementation issues; it enables no new holder
or command. See
[design/berry-player-routes.md](design/berry-player-routes.md) for the separate
Oran growing/Razz snack contracts. The [berry nursery guide](berry-nursery.md)
describes their implemented commands, optional source and release requirements.
See [gimmighoul-evolution.md](gimmighoul-evolution.md) for the 999-coin Chest
equivalent, [recovery-equivalents.md](recovery-equivalents.md) for two field-only
medicines, [hunt-item-sources.md](hunt-item-sources.md) for reviewed hunt sources,
and [item-supply-route.md](item-supply-route.md) for optional six-item supply.
See [alpha-reliability-validation.md](alpha-reliability-validation.md) for the
Adventure, trainer-team, gym recovery, and onboarding branch validation record.
See the [September closeout](testing/september-closeout-2026-10-23.md) for the
current issue reconciliation, Adventure survey/room-pool repairs and the
separate fresh regression and dated player-protocol evidence.
See [battle-coverage-report.md](battle-coverage-report.md) for the current
offline battle proof coverage inventory.
See [move-inventory-audit-2026-06-22.md](move-inventory-audit-2026-06-22.md)
for the latest full move inventory audit and generated CSV reference.
See [design/npc_trainer_battles.md](design/npc_trainer_battles.md) for the
NPC trainer battle system design reference.
See [design/adventure-system.md](design/adventure-system.md) for Adventure Mode
design and current status, and [adventure-operations.md](adventure-operations.md)
for the player and builder workflow.
See [static-npc-trainer-battles.md](static-npc-trainer-battles.md) for the
current Builder workflow for static NPC trainer battle setup and validation.
See [design/battle_ai.md](design/battle_ai.md) for the battle AI design
reference and phased implementation roadmap.

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
