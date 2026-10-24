# Native Necrozma released-build plan (#831)

Status: **awaiting separate operator approval; not executed**.
The [local implementation receipt](necrozma-items-2026-10-24.md) closes #825–#830;
this plan does not close #831 or authorize itself. The [JSON](necrozma-release-plan-2026-10-24.json)
contains exact candidate/configuration, complete reviewable controller sources
and hashes. No runtime credentials or database DSN are published.

## Deliberately selected local release

- Published candidate: `02c81c0d62364d48d3cdae6d8b57023d8ed99249`.
- Named environment/tag: `necrozma-release-777571d2a1114aac812d180fff18a87f`.
- New archived source: `H:\PokemonFusionProject\fusion2\.codex-artifacts\necrozma-20261024\released\source`. Its 1116
  Python identities match the tested/committed implementation; the separate
  QA settings hash is `cdfbd4f6a3e5c6e0a67f0ea2d63b3234d892f368c0cd7578487fe4e598ea1edb`.
- New loopback ports: telnet 53231, HTTP 53232, internal web 53233, AMP 53234,
  WebSocket 53235. Startup refuses occupied ports or mismatched source/configuration.
- Database: a new randomly generated disposable schema on this task's verified
  loopback PostgreSQL cluster. No existing game database/service is connected.
  The controller migrates this empty schema through the complete framework and
  Pokemon 0058 graph before starting new hidden test processes.

PF2-Dev was inspected read-only on October 24: clean `af0eca6` checkout,
recorded Pokemon migrations through 0045. It remains unchanged. A shared-server
release would also need review of the intervening October upgrade chain; this
local plan avoids applying that unrelated release to the shared world.

## Exact operations requiring approval

`AGENTS.md` says “Never run migrations without asking first.” #831 additionally
requires separate exact release/setup approval. The existing human approval
covers only `tests/integration/necrozma_migrations.py` rehearsals; it does not
cover this released instance. Source archival/preparation alone did not start
a service or run migrations.

After approval of this candidate/tag, record that approval in
`H:\PokemonFusionProject\fusion2\.codex-artifacts\necrozma-20261024\released\operator-approval.json` with these exact fields:

```json
{"candidate":"02c81c0d62364d48d3cdae6d8b57023d8ed99249","tag":"necrozma-release-777571d2a1114aac812d180fff18a87f","approved_local_release_and_tagged_qa":true}
```

Run only these task-owned controllers:

```powershell
& 'H:\PokemonFusionProject\evenv\Scripts\python.exe' -B 'H:\PokemonFusionProject\fusion2\.codex-artifacts\necrozma-20261024\postgres_fixture.py' resume
& 'H:\PokemonFusionProject\evenv\Scripts\python.exe' -B 'H:\PokemonFusionProject\fusion2\.codex-artifacts\necrozma-20261024\release_supervise.py'
```

The supervisor verifies the archived source and new ports, creates/migrates only
its random schema, initializes a separate private operator, and starts only this
clone using `--settings qa_necrozma_settings.py start`. The agent retains that
process while it runs the batch. No source edits or reload of an existing
Evennia/Portal/PostgreSQL service are approved by this plan.

Separate operator input uses the reviewed `released/staff_transport.py` against
only that new telnet port. After two disposable ordinary accounts finish real
onboarding, the operator executes the exact `release_world.py` source included
in the JSON: tagged Center/arena/exits, finite stock, labelled wallets and base
hunt charts. No source Pokemon, fused rows or bag items are granted. The separate
`release_preconditions.py` may set only a tagged paired host's bound PP to0 or
HP to0, outside battle, recording full before/after SQL. These state seeds are
not presented as ordinary earned damage or PP spending. Ordinary accounts
remain Player throughout.

## Actual socket acceptance and observation

Use two independent ordinary socket sessions, with authentication input omitted
from public transcripts. Acquire both native base sources through real movement,
`+store` purchase, `+hunt` and `+item Master Ball`. At the real Center review and
confirm `+necrozma`, inspect both identities/counts, buy/equip the existing held
crystal, enter ordinary consenting PvP, switch/attack/use each existing signature,
reconnect, and inspect actual effects/SQL PP/use. Verify the unchanged reserved
companion independently of host effects.

Use normal `+use` after labelled depleted/fainted prerequisites, then separation
and repeat cycles without a PP refill. Include outside-Center rejection, a
cancelled/stale review, a real full party returning its companion to a box and a
previously boxed companion return. Extra ordinary Eevee captures can fill the
party through the same finite purchase/hunt route. Keep staff setup, ordinary
socket commands and read-only SQL observations as separate receipts. Verify the
untouched protected sentinel and each reserved companion's baseline.

## Exact cleanup

After both sources are separated, close the tagged client sessions, verify no
active pair/reservation/battle locks or orphan resources, then request teardown:

```powershell
Set-Content -LiteralPath 'H:\PokemonFusionProject\fusion2\.codex-artifacts\necrozma-20261024\released\cleanup-requested' -Value 'approved tagged native QA complete'
```

The existing supervisor runs only its clone's
`--settings qa_necrozma_settings.py stop`, verifies all five listeners closed and
drops only its own random schema. Verify no disposable schemas/public test tables
remain, then stop only the same task cluster:

```powershell
& 'H:\PokemonFusionProject\evenv\Scripts\python.exe' -B 'H:\PokemonFusionProject\fusion2\.codex-artifacts\necrozma-20261024\postgres_fixture.py' stop
```

Record the actual loaded source/candidate, exact command outcomes, independent
SQL/protected-data checks and cleanup. Only then close #831. Failed/unsupported
checks remain evidence and require a bounded fix and affected reruns. This plan
does not authorize PF2-Dev deployment, existing-service operations, human data
changes, permanent stock/charts, plot-only content or Ultra.
