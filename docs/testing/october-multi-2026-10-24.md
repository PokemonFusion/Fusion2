# October four-player Multi implementation verification (#746)

October 24, 2026 candidate based on `9f09deb`; all final Python code is committed
in `e6373121f8fb8c2429498d97bd46be8978afaf82`. [JSON evidence](october-multi-2026-10-24.json)
contains the normal command transcript, fixture boundaries and source/log fingerprints.
**Automated checks and the separate final local four-account acceptance pass.**
This automated report uses actual typed Player models and PostgreSQL with captured
outbound transport. The [live record](october-player-live-2026-10-24.md) covers real
browser/WebSocket gameplay and cleanup. Shared-server deployment remains separate.

## Behavior

Four distinct accounts independently consent through `+pvp/multi`, select A1/A2
versus B1/B2, ready and launch in the same room. Each owns one active cell and
their full current eligible roster/Fusion and inventory. Current ownership,
reservations, connectivity, presence and readiness are revalidated at launch.
Concurrent or failed starts cannot create duplicate matches or partial locks.

Saved controller identity is separate from team and physical cell. Rebuild and
rollback restore exact bindings; foreign actors, teammate actions, stale turns,
inventory borrowing and account/object ID collisions are refused. Ally Switch
changes physical targets while control follows each trainer's own Pokemon.
Helping Hand, Surf, Follow Me, screens/guards and side-duration effects use actual
team relations. Tera, Mega and Z retain one shared use of each mechanic per team.

An exhausted controller leaves an empty cell while the partner continues.
Concession forfeits the team; a five-minute turn deadline prevents abandoned
matches from locking forever. Both overdue teams draw. Reconnect preserves the
deadline and queued legal inputs. Durable outcome receipts precede all-controller
cleanup; pending saves retain locks and allow `+battle/retry`. PvP remains without
EXP, trainer XP or prize money. See the [player rules](../multi-battles.md).

## Final checks

- **399 cases across 20 PostgreSQL suites**, including
  **32 dedicated four-controller cases**, **19 communication cases** and
  **15 sheet/rendered-guide cases**.
- **331 focused checks**.
- Three fresh callback-enabled full-suite orders: **4927 passed / 4014 skipped
  each**, including normal, repeat and battle-first orders.
- **1100 Python sources** fixed across the final gates; staged and committed
  Git-filtered blobs are verified before publication.

The first mandatory order found 13 compatibility failures in gym/Adventure
adapters without a battle state. Three Multi guards were corrected, the 25
affected compatibility checks passed, and all final gates were rerun. Four initial
focused catalog failures came from that selection's missing tools import path;
the ignored control environment was corrected without changing unrelated source.
Earlier failing evidence is retained rather than counted as a pass.

Live diagnosis also found four-controller status privacy and Follow Me allegiance,
target-kind and expiry gaps. Status now shows all four controllers with exact
private details only for the owner. Redirection classifies the holder relative
to the attacking source and applies only to eligible single-target moves; Surf
and team screens retain their real targets. Follow Me/Rage Powder/Spotlight clear
at turn end. The rule check used the [primary Pokémon Showdown move source](https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/moves.ts)
(accessed October 24): Follow Me lasts one turn and redirects opposing eligible
targets. Positive and negative controls pass on the final fresh server and in SQL.

Final review separated physical position changes from Trick Room changes, so
Ally Switch reports success without a false room-ending message. Its existing
SQL case now checks both outputs, and a fresh final-source four-account replay
confirms the correction. Both live source phases are retained in the live report.

The first app interruption occurred after live cleanup and two successful full
orders; their historical log is retained. A recovery attempt was interrupted for
the final narration correction. A second app interruption followed stale browser
cleanup after the final-source replay. Neither partial attempt is counted as a
completed gate. The complete final three-order gate restarted without browser
calls; completed final-source PostgreSQL suites were retained and only remaining
suites resumed. Final commands, source and log fingerprints are recorded here.

This feature changes no migration. The existing local Windows battle-log rotation
and model-reload diagnostics are retained. No existing server, human character,
game database, plot item, NPC partner or reward economy was changed. The separate
live report establishes ordinary sockets/browser behavior separately from these
automated checks. Neither establishes deployment to the shared game service.
The exact task-cluster audit removes only five inspected schemas orphaned by app
interruptions and verifies both live schemas absent, zero remaining disposable
schemas and zero public tables. The task-owned PostgreSQL process is stopped.
