# Existing trade-held evolution — issue #755

The 14 existing trade-held items now support all 17 matching checked-in evolution
transitions through `+party`, `+hold` and `+evolve`. The
[PF2 rule and mapping contract](../trade-held-evolution.md) selects the explicit
non-transfer equivalent allowed by #755. Nohface's existing Metal Coat transition
is included alongside the standard species. No new item definitions are needed.

## Dependencies and gameplay decision

Fresh source and GitHub review on October 21 found #722 (shared transactional
ownership transfer) and #725 (consent trading) still open and unimplemented.
`CmdTradePokemon` still refuses all transfers. Those dependencies remain required
for actual trading. This direct equivalent retains the same owner, canonical
placement and compatibility mirrors and adds no transfer callback or receipt.
Future trading must define its evolution ordering/policy explicitly.

Current #723 Fusion reservations remain protected by the shared placement checks.
The command help, guide entry and evolution documentation now describe the new
route; #731 retains the broader player-guidance acceptance work.

## Recorded player route

```text
+party 3
+hold 3=Metal Coat
+evolve <full ID copied from the sheet>
+party 3
```

For Scyther, the command reports `Buddy evolved into Scizor!`. After discarding
the shared instance and reloading SQL, the party sheet shows Scizor, the same
complete ID and Held: Nothing. One of the original two bag copies remains.
Equipping debits one bag copy; evolution consumes that held copy without another
bag debit. A separate case proves that no spare bag copy is required.

Every one of the 17 mappings has its own recorded command walkthrough. Branches
follow the held item: Clamperl's Scale selects Gorebyss and Tooth selects Huntail.
At the same level, Porygon's second evolution needs a new explicit request:
equip Dubious Disc, then `+evolve <id>=Porygon-Z`. An implicit retry cannot spend
the next stage's newly equipped item.

## Integrity and preserved state

The exact source/target/item allowlist is checked against the actual held item
and dex metadata, with ordinary level, condition, gender and region predicates
still applied. Unknown mappings, types and conditions remain blocked. Passing a
bag item, a partial target, a wrong species/form or an incompatible held item
cannot consume anything. Non-item and partner-species trades remain unsupported.

The existing service locks storage, trainer and Pokemon, reads fresh saved state,
checks ownership/placement/reservations/battles, then atomically saves species,
the matching ability slot, held-item consumption and the existing retry receipt.
Owner, UUID, placement and mirrors are unchanged, along with nickname, HP, PP,
major status, sleep counter, EXP, IVs, EVs, friendship, nature, gender and other
flags. Boxed evolution preserves its box and position. Everstone, eggs, battles,
Fusion reservations and foreign/conflicting ownership still reject the request.

A failure injected after the SQL save rolls back every changed field and restores
the shared model cache. Concurrent identical completions produce one evolution
and one replay. Competing held removal either returns or consumes the held copy;
it cannot do both. Competing Fusion reservation yields one legal serialized
order without ownership changes or duplication. Newly equipped copies survive
repeated completion requests. Existing Sweet and battle behavior are preserved.

## Checks and proof boundary

The [JSON evidence](trade-held-evolution-2026-10-21.json) records exact commands,
all mapping outcomes, 17 walkthroughs, source/log hashes, failure controls,
test counts and cleanup. The new suite is
[`tests/integration/trade_held_cases.py`](../../tests/integration/trade_held_cases.py).

| Check | Passing scope |
| --- | --- |
| Trade-held PostgreSQL | 33 tests: 17 mapping/player-flow cases and 16 integrity/failure/concurrency cases |
| Existing evolution/equip PostgreSQL | 28 tests |
| Existing Alcremie PostgreSQL | 76 tests, including all 63 Sweet/cream pairs |
| Total PostgreSQL | 137 production-model checks |
| Focused pytest | 115 rule, command and disabled-trade checks |
| Mandatory gate | Combined, repeat and battle-first each passed 4,392 tests; 4,014 skipped each |

All checks passed. Skipped cases are outside the enabled mandatory gate scope;
production-model PostgreSQL proof is recorded separately. Existing model-reload
and pytest-cache permission warnings are retained in the logs. The new suite and
rule tests are wired into the existing lifecycle CI workflow; local success does
not claim hosted CI completion.

An initial helper miscounted a replay fixture's pre-existing bag copy. That was a
test expectation error; the helper was corrected without changing product code,
and all 33 cases reran successfully. The preliminary log remains retained and is
excluded from qualifying proof.

These checks run real ordinary command parsing/functions, complete-ID ownership
lookup, inventory/evolution services and production models. Only session
transport is captured; fixture setup is separate from the player flow, and no
successful gameplay effects or saves are mocked. This is automated local command
acceptance, distinct from a logged-in live session, main merge or deployment.

All ORM work used generated schemas in a fresh loopback-only PostgreSQL cluster.
All generated schemas were removed, public tables remained empty, and that
private test cluster was stopped. The game database, existing characters/Pokemon
and running game services were not used. No migration runner or game reload ran.
Unrelated work, plot-only content, acquisition and battle runtime changes are
outside this commit.
