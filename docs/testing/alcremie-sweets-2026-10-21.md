# Existing Sweet evolution — issue #756

The seven existing Sweets now support Milcery evolution through ordinary
`+party`, `+hold` and `+evolve` commands. The
[action and form-selection contract](../alcremie-evolution.md) records PF2's
non-plot spin equivalent and the nine supported cream targets. The base target
is Vanilla Cream; the other eight names come from Alcremie's checked-in cosmetic
metadata. No dex entries or schema fields are added, and Gmax remains unavailable
through this route.

## Player route

```text
+party 3
+hold 3=Strawberry Sweet
+evolve <ID copied from the sheet>=Alcremie-Ruby-Cream
+party 3
```

The detailed party sheet now exposes the full ID needed by the existing evolution
command. In the recorded walkthrough, the evolution response is:

```text
Cream evolved into Alcremie (Ruby Cream; Strawberry Sweet)!
```

The reloaded party sheet shows Ruby Cream / Strawberry Sweet and Held: Nothing.
One of the original two bag copies remains: equipping debits one bag item, then
evolution consumes that actual held Sweet without debiting the bag again.
The automated test obtains the ID from real rendered command output; the session
adapter removes terminal color formatting when reading it, as a text client does.

## Implementation and state

`EvolutionService` reuses its existing storage/trainer/Pokemon locks, fresh SQL
reads, ownership/placement/reservation checks, atomic save and replay receipt.
The service also rechecks the existing battle guard inside the locked transition.
`pokemon/data/evolution.py` admits only the exact Milcery-to-Alcremie Sweet
exception; other unsupported `other`/trade conditions continue to fail closed.
Bag-only Sweet requests, wrong items/species, partial/unknown targets and Gmax
cannot trigger or consume an item.

Alcremie's battle species remains canonical `Alcremie`, retaining native stats,
typing, move behavior and ability-slot mapping. Cream and decoration are two
bounded result-metadata tags in the owned model's existing `flags` array.
They never grant evolution eligibility: forged cosmetic/spin tags without a real
held Sweet cannot evolve. Unrelated flags remain preserved. `OwnedPokemon` has
no JSON metadata field; this implementation requires no migration.

Success preserves the UUID, owner, placement, nickname, gender, nature, IVs, EVs,
friendship, EXP, HP, major status, moves and PP. Both native ability slots are
exercised, with a separate legacy-ability fallback check. A failed save restores
the held Sweet, appearance, receipt and shared cached instance. Concurrent
identical PostgreSQL requests serialize to one success and one replay, consuming
the held item once. Replaying with a new Sweet or another cream cannot redecorate
the completed evolution or consume the new held item.

## Validation and evidence

The [JSON report](alcremie-sweets-2026-10-21.json) contains exact commands, test
results, source/log hashes, all 63 named combinations and seven recorded player
walkthroughs. The production-model suite is
[`tests/integration/alcremie_cases.py`](../../tests/integration/alcremie_cases.py).
It uses the production factory, actual player ID lookup, command parsers/functions,
ordinary battle guard, held-item/evolution transactions, canonical placement,
fresh SQL reads and a discarded/reloaded model instance. Only the session
transport is adapted; no effects or persistence writes are mocked for success.
Save-failure injection is a separate negative control.

| Check | Scope |
| --- | --- |
| Alcremie PostgreSQL flow | 76 tests: 63 Sweet/cream combinations plus 13 eligibility, rollback, replay, concurrent-write and battle-adapter checks |
| Existing evolution/equip PostgreSQL regression | 28 tests, including stones, level-held items, inventory aliases, ownership, rollback and concurrent retries |
| Existing UI PostgreSQL regression | 14 tests for player sheets, Fusion and nickname flows |
| Focused pytest selection | 152 rule, command, party and display checks |
| Mandatory gate | Combined, repeat and battle-first each passed 4,369 tests, with 4,014 skipped each |

All checks above passed. Final gate durations were 217.35, 184.61 and 177.44
seconds respectively. Skipped cases remain outside the enabled gate's scope;
PostgreSQL proof is recorded separately above. Existing Django model-reload and
shared pytest-cache permission warnings remain in the retained logs.

The new production-model suite is included in the existing PostgreSQL lifecycle
CI workflow. Local execution is distinct from hosted CI completion.

## Diagnosis and boundaries

An initial fixture assumed the JSON field on the other Pokemon model also
existed on `OwnedPokemon`. Production-model checks rejected that fixture; the
result metadata was moved to the owned model's existing bounded tags before
qualification. A later ID-discovery assertion was corrected to strip real
terminal formatting before parsing the displayed UUID. Earlier fixture-error
logs are retained separately. The pre-ID-discovery full gate was superseded
and stopped; only the finalized gate qualifies the published source.

All ORM work uses generated schemas in a new private local PostgreSQL cluster.
The game database, existing characters/Pokemon and running game services are not
used. No migration runner, deployment or game-service reload is required.
Cleanup and final gate results are recorded in JSON before publication.

This is automated production-command/model proof, including actual database
reloads. It is not a live logged-in player session, a main-branch merge or a
remote deployment. Plot items, contests, acquisition, breeding, new Sweet
definitions and cosmetic forms absent from PF2 data remain out of scope.
Player-facing help is updated in the command, the existing guide entry and
[evolution documentation](../evolution.md), coordinated with #731's guidance scope.
