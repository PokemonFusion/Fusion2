# Canonical Pokemon ownership and placement (#713)

`OwnedPokemon.trainer` is the owner. `PokemonPlacement` is the sole source of
party/box membership. An owned Pokemon has exactly one of:

| State | Required fields | Prohibited fields |
| --- | --- | --- |
| Party | Owner's storage, unique slot 1–6 | Box, box position |
| Box | Owner's storage and box, unique positive box position | Party slot |
| Fusion reservation | Owner's storage | Party slot, box, box position |

Fusion reservations preserve the existing temporary and permanent fusion paths,
including inactive unlocked permanent forms. This adds no October systems.
Legacy M2M/slot relations are compatibility mirrors, never ownership fallbacks.

## Write contract

Use `PlacementService` for moves, swaps, fusion reservations and release.
`move_to_party`, `move_to_box` and `UserStorage` methods delegate to it. The
service locks storage, then freshly reads/locks Pokemon, and validates ownership
before updating the canonical row and mirrors in one transaction. A storage
lock protects even empty parties and boxes. A swap reads its outgoing member
under that same lock. Direct ORM/bulk placement writes are not supported APIs.

`create_owned_pokemon` now requires a trainer, initializes and places a Pokemon
atomically, and uses a box if the party is full. Outer transactions around grant,
starter and explicit destination callers roll back creation if later work fails.
Use `EncounterPokemon` for wild/NPC instances.

Both in-battle capture and the post-battle commit adapter use the same service.
Capture requires a persisted wild encounter UUID. A locked encounter can produce
only one durable `CaptureReceipt`; the receipt and Pokemon commit together with
placement and encounter deletion. A retry returns the original capture result
without prompting for a nickname again. It does not move or modify the Pokemon
if the player has since moved it. The receipt retains the original UUID after
release, preventing resurrection. A missing encounter without a receipt is an
error. Battle tracking cleanup runs only after the outermost commit.

The old `+trade` command is intentionally blocked before any mutation: it moved
Pokemon across owners before changing the trainer, with non-atomic compensation.
A correct transfer protocol belongs to the deferred trading work. No trading,
Daycare, breeding or marketplace implementation is included here.

## Staff audit and rollout

Deployment migrations require operator approval under `AGENTS.md`. Do not run
these commands against a game database without that approval.

1. Back up the database and stop game writers for the deployment window.
2. Run the read-only audit with the game environment:
   `evennia shell` is not required; use
   `DJANGO_SETTINGS_MODULE=server.conf.settings python -m django audit_pokemon_placements`.
   Add `--database ALIAS` if needed. Each problem includes a Pokemon UUID, code,
   and relevant storage/slot/box identifiers. Exit status is nonzero for problems.
3. Staff must resolve every problem deliberately. In particular, do not infer
   ownership from conflicting mirrors or automatically box unplaced fusion forms.
4. Run approved migrations, then rerun the audit before resuming writers.

Migration 0040 locks the affected PostgreSQL tables, audits existing rows and
mirrors, and fails before adding constraints if any invalid state exists. It
performs no repairs. Its transaction leaves the prior schema/data intact on
failure. Migration 0041 repeats the guarded audit before adding deferred
PostgreSQL checks for exactly one placement and matching owner/storage/box.
The two deployments must finish before writers resume. Row constraints enforce
known states, NULL shape, positive/ranged slots, unique party slots and box
positions. Deferred checks permit creation and placement within one transaction,
and reject deletion of a placement/box/storage that would strand an owned row.
Deleting a Pokemon (release) remains valid. SQLite has no equivalent deferred
cross-table checks and is only a limited test backend.

## Tests

- `pytest -q` runs the existing suite and an isolated real-ORM lifecycle test
  process. The latter avoids the older tests' global Django/Evennia stubs.
- `python tests/integration/placement_cases.py` runs the isolated tests directly.
  Without a PostgreSQL DSN it uses disposable SQLite with test-only ArrayField
  serialization; row locking and PostgreSQL deferred-trigger cases are skipped.
- Set `PF2_TEST_POSTGRES_DSN` to an **isolated test PostgreSQL database** to exercise
  independent connections, competing captures, last-slot contention, conflicting
  moves, concurrent box allocation/swaps and deferred database checks. The runner
  creates and removes a randomly named `pf2_test_*` schema; it does not run
  deployment migrations or use game data. Do not point it at a live database.
- `.github/workflows/lifecycle-integrity.yml` provisions PostgreSQL 16 for these
  tests. `PF2_TEST_PGLITE=1` is reserved for optional local SQL/trigger verification
  and explicitly skips concurrency tests, since PGlite multiplexing is not proof
  of PostgreSQL row-lock behavior.
