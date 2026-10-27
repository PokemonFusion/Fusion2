# Repaired item local release plan (2026-10-25)

Issue #860. Candidate: **ddc56bfaf32261e47551ad893e0592fca3e86311**. The archived source contains exactly the
1,135 Python files accepted by the final #863 gate (three fresh orders of
6,153 passed / 4,028 skipped). This is a new task-owned loopback release,
not a change to the existing local game or PF2-Dev.

The user's existing explicit local-dev authority and current remaining-item
request cover this bounded operation. The [controller receipt](item-repair-release-plan-2026-10-25.json)
publishes exact sources, hashes, candidate, unique tag, paths and ports before
execution; it does not represent a new human approval.

## Exact target and commands

Release root:
H:\PokemonFusionProject\fusion2-necrozma-items\.codex-artifacts\item-release-860-20261025.
The archived game is its released/source child. All game listeners bind only
127.0.0.1: telnet 53301, HTTP 53302, internal web 53303, AMP 53304, WebSocket 53305.
Pre-bind guards refuse a conflicting listener. The existing task-owned
PostgreSQL fixture is the one at
H:\PokemonFusionProject\fusion2\.codex-artifacts\necrozma-20261024\postgres.
Its prepared fixture controller verifies that exact path and stopped state;
no machine service, existing game database or other cluster is a fallback.

Run with H:\PokemonFusionProject\evenv\Scripts\python.exe -B:

1. Existing task fixture controller: postgres_fixture.py resume.
2. This release's supervise.py: create a fresh random
   pf2_recovery_test_<uuid> schema, run MigrationExecutor only within that
   schema through the archived migration graph (Pokémon 0058), initialize a
   separate private operator in the empty schema, and start only the five
   archived instance ports using qa_item_repair_settings.py.
3. released/socket_driver.py: create two accounts through ordinary sockets,
   go IC and complete ordinary onboarding. Never elevate their Player permissions.
4. Separate staff_transport.py command executes the published world.py through
   its exact path. It creates only tagged finite QA stock, public trail/arena
   exits and a protected sentinel, labels 500,000-money fixture wallets, and
   grants zero Pokémon, learned moves, bag copies or native combinations.
   All later hunt/capture, naming, teaching, moveset, purchase and item actions
   are ordinary inputs. The capture-ball fixture is a test prerequisite,
   not new capture support or permanent public stock.
5. observer.py takes read-only repeatable SQL snapshots of this exact schema.
   staff_transport executes runtime.py only for in-process read-only source
   attribution and live battle observations. Exact loaded module paths/hashes,
   source archive, process, declared build, effects and persistent rows must agree.
6. When needed, separate prerequisites.py may only label HP0 or selected-slot
   PP0 on these tagged ordinary players' currently owned, out-of-battle Pokémon.
   It refuses companions, foreign ownership or existing game data. It records
   all before/after state and grants no item effect, move, level or refill.
7. Run the bounded ordinary walkthrough and preserve exact expected/observed
   commands, failed attempts, effect/PP/item/ownership/checkpoint state, reconnect
   and end. Native stat/crit and legendary bonus representatives, matched native
   versus nickname theft, all three repaired berries, medicine/PP/evolution,
   Mega/Z and both existing native Necrozma lifecycle regressions are planned.
   No forced RNG or directly applied cure/damage counts as ordinary proof.

## Cleanup and limits

Finish/concede battles normally, return equipment where applicable, separate
native pairs and record companion baselines. Confirm the protected sentinel,
Player permissions, wallet/stock/bag conservation and runtime attribution.
Create released/socket-stop to close only test sockets, then
released/cleanup-requested so the supervisor stops its exact archived instance.
Only after all five task ports close may IsolatedPostgres drop its own generated
schema. The PostgreSQL fixture controller then verifies no disposable schema or
public table remains and stops that task fixture only.

Retain redacted command/effect evidence and controller/log hashes. Never publish
credentials or runtime-private configuration. A failure retains its diagnosis;
source corrections require fresh qualification and a new candidate/release plan.

This temporary QA counter is removed with the disposable schema. It provides no
permanent public supply and cannot close #862. No deployment/restart/migration,
world installation, existing human character/Pokémon edit, or cleanup on PF2-Dev
is authorized by this local plan. Plot-only, CAP, clutter and unrelated work
remain excluded. The final report must identify the bounded representatives
actually replayed rather than imply every catalog item was tested live.
