# Native Necrozma replacement release plan (#831)

**Awaiting separate operator approval; not executed.** The original approved
candidate failed an additional ordinary zero-PP check; its
[complete receipt](necrozma-released-local-2026-10-24.md) is retained. The bounded
repair and all fresh qualification results are published. Approval of the
original SHA does not authorize this replacement. The [JSON](necrozma-retry-release-plan-2026-10-24.json)
contains exact configuration and the full reviewable controller sources/hashes.

## Exact replacement

- Candidate: `e3557aadced7fc5897b7024d1377047117735a64`.
- Named environment/tag: `necrozma-release-05e2205bda484d27a13099e03698300c`.
- New archive: `H:\PokemonFusionProject\fusion2\.codex-artifacts\necrozma-20261024\released-retry\source`. All 1,116 Python identities match the repaired,
  tested committed source. Manifest: `429efb890d91e9ff73bf3a0bb70579137e6ee3b9257424adc708d8fd2cb2ec73`.
- Separate QA settings hash: `cdfbd4f6a3e5c6e0a67f0ea2d63b3234d892f368c0cd7578487fe4e598ea1edb`.
- New loopback ports: telnet 53241, HTTP 53242,
  internal web 53243, AMP 53244, WebSocket 53245.
- Database: a new random disposable schema on this task's existing verified
  loopback PostgreSQL fixture; its full framework/Pokemon graph is migrated
  through 0058. The task cluster is currently stopped and clean.

This changes no PF2-Dev checkout, existing game database/service or human
character. New source/configuration and port guards reject mismatched or
occupied targets. The old failed instance is stopped and its schema removed.

## Exact operations after approval

Record approval for this exact candidate/tag only in
`H:\PokemonFusionProject\fusion2\.codex-artifacts\necrozma-20261024\released-retry\operator-approval.json`:

```json
{"candidate":"e3557aadced7fc5897b7024d1377047117735a64","tag":"necrozma-release-05e2205bda484d27a13099e03698300c","approved_local_release_and_tagged_qa":true}
```

```powershell
& 'H:\PokemonFusionProject\evenv\Scripts\python.exe' -B 'H:\PokemonFusionProject\fusion2\.codex-artifacts\necrozma-20261024\postgres_fixture.py' resume
& 'H:\PokemonFusionProject\evenv\Scripts\python.exe' -B 'H:\PokemonFusionProject\fusion2\.codex-artifacts\necrozma-20261024\release_supervise_retry.py'
```

The supervisor creates/migrates only its new random schema, initializes a
separate private operator and starts only the new archived instance. It retains
teardown control. Authentication inputs and generated secrets stay private.
`AGENTS.md` says “Never run migrations without asking first.” These operations
have not been run for the replacement.

Two independent ordinary socket players register, select their own characters
and complete human onboarding. The separate operator runs the reviewed
`release_world_retry.py` setup through the new port: tagged Center/arena/exits,
finite stock, labelled wallets and Necrozma/Solgaleo/Lunala/Eevee base charts.
No source Pokémon, fused row or bag items are granted. Optional reviewed
`release_preconditions_retry.py` calls may label/set only each paired host's
bound PP0 or HP0 outside battle. Ordinary players remain Player throughout.

Repeat ordinary purchases, movement, hunt/capture, both exact Center reviews,
cancel/stale rejection, inspection, existing held crystals, consenting PvP,
ordinary and signature effects/PP/budgets, reconnect/end, field recovery/boosts,
full-party and previous-box/fainted separation. For the paired-host exchange,
Dusk may queue its existing Gravity while
Dawn uses its signature, preserving a real damage target without an opposing
critical attack preventing that signature. No accuracy, damage or outcome is
forced. Expected source spending is recorded from the actual commands.
Repeat the failed zero-PP
cycle in an active battle: ordinary attacks and Z inputs must reject without
declarations, turn advancement, damage or side use. Retain staff prerequisites,
ordinary input and read-only SQL/runtime observations separately.

## Exact teardown

After separation and ordinary quit, request cleanup only for this new instance:

```powershell
Set-Content -LiteralPath 'H:\PokemonFusionProject\fusion2\.codex-artifacts\necrozma-20261024\released-retry\cleanup-requested' -Value 'approved tagged replacement QA complete'
```

The supervisor stops its own archive through its dedicated AMP port, verifies
all five listeners closed, and drops only its own random schema. Verify both
companion baselines and the protected sentinel unchanged, no pair/reservation/
battle lock/orphan resources and no public tables/disposable schemas remaining.
Then stop only this task cluster:

```powershell
& 'H:\PokemonFusionProject\evenv\Scripts\python.exe' -B 'H:\PokemonFusionProject\fusion2\.codex-artifacts\necrozma-20261024\postgres_fixture.py' stop
```

Publish actual expected/observed command, effect, SQL and cleanup evidence
before closing #831. No plot-only content, Ultra, permanent source grants,
existing-service restart or shared deployment is included.
