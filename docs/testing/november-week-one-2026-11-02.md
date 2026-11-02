# November week one — local implementation and acceptance

Date: November 2, 2026. Issues: #832 and #833.

Baseline: staging `695cd7947269b76d7b97a413e56dde42c35b1103`, which already
contains battle-interlock PR #917. Work is isolated on
`codex/833-adventure-privacy`; the primary checkout and its design WIP are preserved.

## Result

The #832 interlock implementation is retained. Real ordinary-player socket
acceptance now exercises wild/NPC battle gates and reconnect on the combined
local candidate. #833 adds transactional reservations, database uniqueness,
character-bound room access, and battle observation/output privacy.

Occupancy is independent of completion and reward delivery. A completed run
keeps its room until departure; battles, pending original outcomes and failed
returns cannot release it. Starts, returns and encounter-result persistence
follow the battle lock order: room, character, session. Delayed cleanup cannot
release a newer run. Allocation recognizes legacy boolean/string/numeric room
flags consistently with admission. If ownership storage cannot be read, privacy
denies access without interrupting battle result recovery/cleanup.

## Evidence

This table records local qualification before publication. Hosted CI and
integration status are tracked on the pull request separately.

| Category | Current result |
| --- | --- |
| Broader Adventure, battle, UI and world regressions | 1,291 passed, 8 skipped; includes 114 Adventure and 23 rebuild cases |
| Disposable PostgreSQL reservation/privacy | 17 passed, including independent-connection races, database uniqueness, failed-creation rollback, rejected movement, stale ownership, same-account isolation and frozen Pokemon migration-state inspection |
| Retained PostgreSQL player/lifecycle/recovery/doubles | 84 passed: 17 player-command, 12 lifecycle, 9 reward recovery, 36 battle recovery, 10 doubles |
| Ordinary-player Telnet/AMP | 24 checks passed; core source fingerprints match the candidate and fixture runtime logs are clean |
| Canonical mandatory combined/repeat/battle-first | All three passed: 8,246 passed and 4,032 skipped per order |
| Diff lint / whitespace | No introduced Ruff findings; whitespace clean. Seven baseline import-order findings remain in three touched files |
| Existing local-game occupancy preflight | Read-only inspection passed: no held session IDs and no ownership conflicts |
| Approved disposable migration rehearsals | All three passed: fresh installation, legacy upgrade, and conflicting-ownership rejection/rollback |
| Hosted CI at local qualification | Not run at this snapshot; see the pull request for subsequent hosted results |
| Shared game activation/deployment | Not performed |

The first broad pass exposed two recovery failures from propagating ownership
lookup exceptions through private battle restoration/output. Those paths now
deny access without raising. Focused rebuild and ownership-outage regressions
pass; that earlier failed pass is retained separately and is not passing evidence.

After the full gate, only the order of names imported from the same module was
formatted in three files. Reconstructing those import lists reproduces their
gate-time source hashes exactly. The broader focused checks were repeated after
that formatting cleanup. `lint-baseline-comparison.json` records the seven
existing Ruff I001 findings and confirms that this change introduces none.

Local artifacts are under
`H:\PokemonFusionProject\.codex-artifacts\nov-w1-20261102`:

- `mandatory-first-attempt.log`: earlier failed broad pass.
- `mandatory-final.log`: final canonical gate.
- `candidate.json`: changed-path source fingerprints.
- `postgres-237dd0967240400d855a461b992806bc/result.json`: final 101 PostgreSQL
  checks and source-matched socket run; all suites passed and the cluster stopped.
- `socket-ce494bfa7852/evidence.json`: final 24 socket checks, clean logs,
  matching source fingerprints, stopped fixture processes and schema cleanup.
- `postgres-38ccd6d9b0924f5bad25797a2b8a25a4/result.json` and
  `adventure_migration_cases.py.log` in that directory: the approved migration
  rehearsals; all three scenarios passed and the task-owned cluster stopped.
- Each `socket-*/evidence.json` contains redacted command responses, fixture
  permissions, assertions, source fingerprints and cleanup status. Use the
  final successful run whose source fingerprints match the candidate.

## Ordinary-player checks and limits

The socket fixture creates two non-admin Player accounts, with two characters
on one account. It uses real production account login, character puppeting,
Telnet/AMP transport, Adventure/cardinal/attack/concession commands, persistence
and reconnect. Room/party prerequisites are labeled disposable fixtures.

Both wild and trainer encounters block Adventure movement/search/leave while
preserving the run. Wild combat also rejects another start or route selection;
look/objective inspection remains usable. Reconnect retains the original wild
battle and encounter; normal attacks finish it, cardinal movement resumes,
the survey completes and leaves. A trainer concession records the original loss
and allows the survey to continue.

An unrelated player and a second character on the owner's account cannot enter
the reserved room, watch the battle or select its status by name. Distinct
characters can own different rooms concurrently. Staff permission checks are
separate PostgreSQL fixtures; neither socket account is elevated.

The fixture builds production model tables without migrations in a private
schema and starts task-owned Portal/Server processes on unused loopback ports.
It omits shared-world startup hooks and deployment secrets. All fixture services
are stopped and their private schemas removed after a run. Existing game
databases, characters and Pokemon are not used by these fixtures. A separate
inspection of the existing local game used its original configuration with
`default_transaction_read_only=on` enforced before Django setup. Its saved
`game-occupancy-preflight.json` reports empty held-session and error lists;
that inspection applied no schema or gameplay changes.

There is no socket fault injection, artificial expiry clock, service reload,
shared-world playthrough or production deployment proof. Pending-outcome,
expiry, rejected-return and injected-write recovery remain independently
covered by the command/PostgreSQL suites.

## Approved migration rehearsal results

The user explicitly approved disposable migration rehearsals. The prepared
runner created a new task-owned loopback PostgreSQL cluster and ran each
scenario in a separate, guarded schema:

- **Fresh installation:** migration 0060 applied and the Pokemon model state
  matched the frozen migration graph.
- **Legacy upgrade from 0059:** active runs, completed-but-occupied runs and
  pending original-result/battle identities retained their occupancy. A completed
  run that had already left did not reserve a room. Exact historical run and
  participation snapshots were unchanged, including the unclaimed Potion and
  original capture outcome. No Pokemon model drift remained.
- **Conflicting ownership:** competing sessions for one room rejected the
  migration. The added occupancy column rolled back completely, with run and
  participation histories unchanged; the rehearsal did not choose or repair a
  winning claim.

All three scenarios passed. Their schemas were removed and the task-owned
PostgreSQL cluster stopped. These rehearsals changed no existing game database
and performed no shared-service restart or activation. No implementation code
changed as a result, so the existing behavioral validation remains applicable.

Approved command executed:

```powershell
H:\PokemonFusionProject\evenv\Scripts\python.exe -B H:\PokemonFusionProject\.codex-artifacts\nov-w1-20261102\run_approved_migration_rehearsals.py adventure_migration_cases.py
```

## Remaining gates

1. Run hosted CI on the pull request's exact head, review, then integrate the qualified change into staging.
2. Separately approve any game migration/activation. Follow the preflight in
   [Adventure operations](../adventure-operations.md#schema-preflight-and-activation).

Keep issue status distinct from local evidence. The acceptance above is for
the combined local candidate, not an assertion that staging, main or a running
shared game has loaded #833. General terminal-return recovery remains #837;
mission boards, repeat/cooldown policy and content installation retain their
later-week scope.
