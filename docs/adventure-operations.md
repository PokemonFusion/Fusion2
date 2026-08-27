# Adventure Mode Operations

Adventure Mode provides short authored expeditions launched from Adventure
Hall. The current playable mission is `alpha_meadow` (Alpha Meadow Survey).

## Player Flow

The player must be in Adventure Hall and have a battle-ready party.

```text
+adventure/list
+adventure/info alpha_meadow
+adventure/start alpha_meadow
north
+adventure/choose wild
```

At the Tall Grass Path, choose `wild` for a catchable Rattata or `trainer` for
Surveyor Mina's Pidgey. Finish the battle normally. Winning, losing, catching,
or fleeing resolves the encounter; ordinary setbacks do not restart the run.

Continue north, search the Old Tree, and return south to the entrance:

```text
north
+adventure/search
south
south
+adventure/leave
```

Useful commands during a run are `+adventure/look`, `+adventure/objectives`,
and `+adventure/leave`. A route choice is locked once its encounter begins.
If battle startup fails before a battle is created, repeat the same choice.

The first completed clear records the chosen route and encounter result and
grants one Potion. Later clears remain available for alternate outcomes,
catching, and roleplay but do not duplicate the first-clear reward.

## Builder Setup

Run `batchcommands adventure_hall` once from the room that should link to
Adventure Hall. The batch file is intentionally non-idempotent and must not be
rerun against the same database.

Validate content and room setup with:

```text
+adventureadmin/validate all
+adventureadmin/preview alpha_meadow
+adventureadmin/cleanup
```

Use `+adventureadmin/list` and `+adventureadmin/info <session_id>` to inspect
sessions. Staff can abort a broken run or return a stranded player with the
documented Adventure admin commands.

The migration adding per-player result and reward tracking must be applied as
part of the normal deployment process before enabling this version.

## Current Boundaries

- Solo only; data is per-participant so party support can follow.
- One authored mission and one fixed difficulty.
- No weekly/monthly board goals or permanent milestone UI yet.
- No reputation, procedural generation, crafting loop, or player-authored maps.
