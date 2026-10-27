# Nature mint training contract (#869)

Accepted design scope after the repair/report gates. The scoped implementation
is described in [the player guide](../nature-mints.md); publication, isolated
migration qualification, source installation and released acceptance remain
separate. Design closure alone does not establish those later gates.

The [official mint description](https://swordshield.pokemon.com/en-au/gameplay/features-raise-pokemon/)
distinguishes changed stat growth from unchanged actual Nature. Pin the twenty
nonneutral mints and Serious Mint against the reviewed RHH
[item table](https://github.com/rh-hideout/pokeemerald-expansion/blob/44bc3e0473b85d8e254c8dbc9004ac2d7b0a5fb3/src/data/items.h).
These references inform effects; command/storage/economy decisions below are
selected PF2 policy.

## Exact allowlist and data boundary

| Implementation batch | Exact names, each suffixed Mint |
| --- | --- |
| Attack and neutral | Lonely, Adamant, Naughty, Brave, Serious |
| Defense | Bold, Impish, Lax, Relaxed |
| Special Attack | Modest, Mild, Rash, Quiet |
| Special Defense and Speed | Calm, Gentle, Careful, Sassy, Timid, Hasty, Jolly, Naive |

Split the last eight into two four-item implementation issues. There are21
mints total, not25; Hardy/Docile/Bashful/Quirky Mint are not introduced. Existing
Mint Berry remains an independent sleep-curing berry. Each nonneutral modifier
uses the existing named Nature's +10%/−10% stat mapping; Serious is neutral.

Add a distinct nullable/empty `trained_stat_nature`, validated against this
allowlist. Blank legacy rows use their existing genetic `nature`. A migration
must not rewrite or infer training from that old value. One resolver computes
effective stat nature; keep the saved genetic Nature immutable under mint use.
Unknown/malformed training must fail visibly, never silently adopt a default.
Validate the existing genetic Nature against its25 canonical values too;
mint use cannot repair an invalid genetic row by overwriting or hiding it.

## Consumer audit and selected semantics

| Consumer | Value to use | Required change/proof |
| --- | --- | --- |
| `pokemon.helpers.pokemon_helpers` stats/refresh | Effective trained stat nature | All five non-HP modifiers; project stat helpers and cache invalidation |
| Owned→battle builder; Pokemon constructor/checkpoint | Effective stat nature plus separate genetic value | No later restore reverts training; reject malformed serialized values |
| Trainer-Fusion and native battle forms | Same owned trained stat nature | Form recalculation/end cannot overwrite genetic/trained fields |
| Breeding, Everstone and source capture genetics | Genetic Nature | Inheritance never consumes minted stat preference |
| Nature-based evolution, including Toxtricity | Genetic Nature | Mint cannot alter a native evolution condition |
| Flavor-berry confusion/preferences | Genetic Nature | Preserve reviewed nature-confusion rules |
| Party/sheet/moves inspection | Show genetic Nature and trained stat preference distinctly | Avoid displaying a genetic rewrite |
| Necrozma pair lifecycle | Host training only if the shared field contract allows it | Companion frozen; separation preserves host training |

The October 25 source audit found the following concrete consumers (baseline
`65e8e24`; source paths are repository-relative):

| Current source / symbol | Current behavior and implementation requirement |
| --- | --- |
| `pokemon/models/core.py:33` / saved `nature` | Genetic field; preserve it and add a distinct nullable trained field |
| `pokemon/helpers/pokemon_helpers.py:90` / `_calculate_from_data` | Reads `pokemon.nature`; resolve trained modifier only for stat calculation; explicit `_cached_stats` must not bypass refresh |
| `pokemon/models/stats.py` / `calculate_stats`; `pokemon/battle/pokemon_factory.py:43,116` | Stat entry points must receive the effective modifier through the shared helper, never regenerate random fallback stats |
| `utils/pokemon_utils.py:186,200,259,424,437` | Owned/runtime/encounter builders and raw fallback must preserve both genetic and trained state; encounter genetics start untrained |
| `pokemon/battle/battledata.py:254,280,877,1068,1110,1144,1188,1219` | Constructor, form changes, serialization and SQL restore currently have one nature; retain separate genetic/trained fields and validate legacy fallback |
| `pokemon/battle/mega_evolution.py:139`; `pokemon/battle/native_forms.py:43` | Temporary form stat data must carry the effective modifier without rewriting native identity |
| `pokemon/battle/item_effects.py:164-175` / `flavor_berry` | Current nature comparison controls confusion; keep genetic nature even after minted stats |
| `pokemon/services/breeding_rules.py:44,98-99`; `pokemon/services/breeding.py:182,228` | Validate/inherit genetic nature, including Everstone, and preserve source baseline checks |
| `pokemon/data/evolution.py:180-195,220`; `pokemon/services/evolution.py:154` | Toxtricity and evolution context use genetic nature; mints cannot redirect the result |
| `utils/fusion.py:224`; `utils/party_view.py:125,154`; `utils/display.py:152,228,238,432,659,701` | Trainer-Fusion propagation/stat construction uses effective modifiers; inspection labels genetics and training separately |
| `pokemon/services/capture.py:249`; `pokemon/services/onboarding.py:154,167,172`; `pokemon/helpers/starter_helpers.py:27` | Newly generated/captured sources retain their chosen genetic nature with no inferred mint state |
| `pokemon/services/trade_snapshot.py:29`; trading/marketplace summaries | Custody review must show training separately and bind it in stale-review checks; never lose it on transfer |
| `pokemon/services/necrozma.py`; `necrozma_moves.py`; `necrozma_audit.py` | Host field training and separation must preserve its current trained value; companion remains frozen and its genetics/training baseline cannot change |

Implementation must refresh this map against its exact candidate and prove each
consumer, including legacy snapshots and both native combination forms. A
single helper change without consumer/serialization proof does not release
mints. Hyper Training is the precedent for effective versus genetic values,
not permission to overload its IV bitset.

## Ordinary flow, state and delivery

`+use Adamant Mint=3` uses fresh shared ownership/party/current-Fusion checks,
egg/box/battle/reservation rejection and one transaction. A mint whose stat
modifier already matches is a no-effect/no-debit result, including neutral
equivalence. Another useful mint replaces only trained stat Nature. Preserve
genetics, earned progression, EVs/IVs, abilities, held item and status. Refresh
stats/HP through project helpers, preserving legal HP deficit and fainted HP0.
Debit, training write and refreshed state roll back together; resynchronize
caches and defer success notifications to outer commit. Stale/replayed targets
and two final-copy users cannot spend twice or overwrite another request.

Create foundation/schema/resolver and consumer/serialization issues first,
then the five explicit item batches above and ordinary/released acceptance.
Each batch needs useful/no-effect/neutral/invalid/stale/rollback/concurrent
`+use`, reconnect and subsequent native battle stat proof. Migration rehearsals
are isolated and require their applicable approval; deployment is separate.
An optional future counter may offer each mint at20000/stock1, finite buy-only
without refill; its installation/affordability review remains source work.

No plot unlock, new genetics, nature evolution shortcut or live availability
is implied. Implementation follows the linked issues below; this consumer audit
is design evidence and does not mark any runtime consumer repaired.


## Implementation follow-ups

This closes the design/scoping deliverable only. Runtime effects, source installation,
migration/release operations and ordinary acceptance remain with these open issues.

| Issue | Exact delivery | Dependencies |
| --- | --- | --- |
| [#897](https://github.com/PokemonFusion/Fusion2/issues/897) | Store mint training separately from genetic Nature | #869 |
| [#898](https://github.com/PokemonFusion/Fusion2/issues/898) | Integrate trained Nature across stats, forms, displays and custody | #869, #897 |
| [#899](https://github.com/PokemonFusion/Fusion2/issues/899) | Add nature mint item batch 1 | #869, #898 |
| [#900](https://github.com/PokemonFusion/Fusion2/issues/900) | Add nature mint item batch 2 | #869, #898 |
| [#901](https://github.com/PokemonFusion/Fusion2/issues/901) | Add nature mint item batch 3 | #869, #898 |
| [#902](https://github.com/PokemonFusion/Fusion2/issues/902) | Add nature mint item batch 4 | #869, #898 |
| [#903](https://github.com/PokemonFusion/Fusion2/issues/903) | Add nature mint item batch 5 | #869, #898 |
| [#904](https://github.com/PokemonFusion/Fusion2/issues/904) | Qualify all21 mints across training, genetics and released gameplay | #869, #899, #900, #901, #902, #903 |

Scope/source checks: [2026-10-25 decision receipt](../testing/item-scope-decisions-2026-10-25.md).
