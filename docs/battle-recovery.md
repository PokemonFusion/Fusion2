# Battle reward and lifecycle recovery

Use `+battle/retry` if a battle reports that reward delivery, turn saving or
cleanup is pending. The command retries saved work for your character; it does
not submit a second attack or spend another battle item for a completed turn.
An unfinished battle resumes its legal pending choices. A completed, conceded
or fled battle finishes result delivery and cleanup. With no active session,
the command can still claim your saved pending reward receipts.

## Delivery guarantees

Each new battle has a UUID in its persistent state. Each faint and trainer
prize has a stable effect key within that battle. Numeric room battle IDs are
not used as reward identities. Effect plans are retained on the owning
character using existing persistent Evennia Attributes, independently of room
cleanup; no schema migration is needed.

Receipt creation and claims take the character row lock. A claim commits its
Pokemon EXP/EVs, trainer XP or prize money and the delivered marker together.
A failed claim leaves its original plan pending. Duplicate or concurrent
claims cannot pay twice, and claims for separate effects cannot overwrite a
stale wallet. Success messages are published after commit. Completed receipts
are retained to reject future replays; normal cleanup and player retries read
a separate pending index instead of scanning completed history.

Ordinary trainer battles pay for defeated NPC teams before and after rebuild.
Player opponents do not become NPC prize sources. Existing gym badge and
Adventure result recovery remain in their own services; this layer retains
their battle state until protected cleanup can complete.

## Turn and session checkpoints

Persistent sessions commit one engine turn, its resource writes and its next
checkpoint in a transaction. Failed saves roll back SQL and restore runtime
Pokemon, pending choices and the random generator to the retained input.
Completed checkpoints discard consumed declarations. Reward receipts protect
against replay even if an older room checkpoint is restored.
Temporary damage and field effects store Pokemon references by roster identity,
then reconnect them during rebuild, so checkpoints do not pickle live ORM
relationships. A fully declared retained turn can resume with `+battle/retry`
after reload; partial PvP input still waits for the other player.

Rebuild retains faint markers, terminal teams, legal reserves and player
control on both PvP sides. Move, switch, item and flee choices are reconstructed
as executable actions. Changed actors, foreign trainer identities, exhausted
moves, missing targets and illegal reserves are discarded with a message
asking for a new choice.

Ending intent is saved before concession or terminal cleanup. Encounter-row
deletes, saved room state, matching player locks and NPC reservations are
cleaned atomically before runtime references are released. Failed cleanup can
be retried after rebuild. A repeated completed-session callback cannot clear
the player's next battle.

## Automated verification

`tests/integration/battle_recovery_cases.py` uses production sessions, models,
reward delivery and player recovery commands in disposable PostgreSQL schemas.
It exercises write and marker failures, duplicate/concurrent claims, stale
checkpoints, restored choices, fainting and exhausted reserves across NPC,
wild and PvP sessions, turn rollback and cleanup recovery. The lifecycle CI
workflow runs it with the existing capture, status, progression, evolution,
placement, gym and Adventure regressions.

Fault injection belongs in disposable schemas. A live acceptance run should
use tagged QA characters and fixtures, compare authoritative before/after
resources, verify one final result and clear locks, and inspect fresh log
deltas. Server-reload acceptance is separate from the database reconstruction
tests and must be reported as such.
