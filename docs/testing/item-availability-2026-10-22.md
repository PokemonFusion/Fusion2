# Obtainable item audit (#772) — October 22, 2026

The current code supports item effects without making the whole catalog obtainable. This audit reviews **451 non-plot definitions** out of **597 loaded definitions**; 368 have a declared command capability with bounded evidence, and 83 Mega/Z definitions remain deferred. These are not obtainable totals.

Local source baseline: `4b6b6d60d6612376c87959b71ae2db5965b04859` plus the audit/test/help files in this change. The [per-item index](item-availability-index-2026-10-22.json) separates definition identity, commands, historical evidence, fresh checks, authored sources and live availability. The [JSON report](item-availability-2026-10-22.json) retains commands, SQL/runtime observations and source/log hashes. [Player guide](../item-availability.md).

## Current world and authored sources

Read-only SSH/process inspection found the running remote processes in `/home/evennia/testing/fusion2`, started October 16; its clean checkout is **`b7637cb8d810c5d1706b4ebade8ec4099c553c08`**, predating the item repairs. The source checkout and process working directory were inspected; loaded Python bytecode was not independently fingerprinted. The service unit reported inactive while game processes existed, so that unit status is not used as runtime acceptance.

The explicit read-only database snapshot at **2026-10-22 20:04:00.522329+00:00** found **zero enabled item shops**, **one Poké Ball dispenser**, **no Candy dispenser** and **no NPC held-item templates**. No character inventories were queried. Primitive room/vendor configuration was read without constructing game objects, in a verified read-only repeatable-read transaction. [Sanitized source snapshot](item-world-snapshot-2026-10-22.json) retains source/configuration hashes; non-source room/exit labels are redacted.

| Source | Current local source capability | Dated world / acceptance limit |
| --- | --- | --- |
| Configured shop | `+store` -> Buy -> stock/wallet -> bag; 29 real menu purchase observations | Defaults empty; no enabled remote shops. Single-customer purchases proved; contention/economy not certified |
| Alpha Candy dispenser | Alpha recipe authors bundles of five Rare Candy; fixture `+vend` -> `+use` passed | Recipe is not world population; absent in inspected remote world |
| Alpha Meadow reward | Authored one Potion on first completion; reward recovery/replay tests rerun | Not a repeatable supply. Full new live completion/claim/use walkthrough unverified |
| Itemfinder | Normal `+hunt` can display “You found a mysterious item!” | Reproduced no inventory credit: #779 |
| Wild held items / capture | Capture persists an actual encounter-held item | Normal hunt ignores chart `held_item`; no automatic/authored wild source established: #780 |
| Native post-battle abilities | Honey Gather and Ball Fetch have bounded existing persistence controls | Honey is outside this scoped useful-item inventory; Ball Fetch recovers a thrown ball. Neither supplies the 451-item set |
| Kingambit qualification | Existing Crest opponent evidence/evolution route | No player-owned Crest needed; source authoring and eligible opponents are separate from possession |
| Trading / growing | Existing-item effects do not create these acquisition systems | Actual transfer remains #722/#725; growing/flavor routes remain #776 |

**No specific reviewed shop/vendor/reward source was found for 449 scoped definitions.** Rare Candy and Potion have the two named source-authored routes above, both with live limits. Every scoped row has `no_observed_shop_or_vendor_source` for the inspected remote snapshot. This does not mean no player owns those items or that no other source can exist; existing human possessions, player-to-player transfer and every possible custom/scripted source were not audited.

## Fresh representative acquisition acceptance

**32 PostgreSQL command-flow cases**, **30 distinct items** and **63 receipts** passed. The actual `+store` command and bound EvMenu input debit room stock and wallet, credit inventory, then run actual `+use`, `+hold`, `+evolve` or `+flee`, with independent SQL reads and cache-discarding reloads. No successful effect callback, inventory writer, damage or RNG outcome is substituted.

- Medicine/revival/PP/herbs: Potion, Revive, Ether, Energy Root, Revival Herb, Rare Candy, PP Up and PP Max.
- Berries/training: Oran, Pecha, Leppa, Mystery, Pomeg, Protein, Health Feather, Ability Capsule/Patch, Bottle Cap/Gold Bottle Cap.
- Food/revival equivalents: Fresh Water, Max Honey and Sacred Ash.
- Evolution: Fire Stone, Peat Block, both Kubfu Scrolls, Strawberry Sweet and Metal Coat.
- Held effects: purchased Leftovers heals 1 -> 11 HP and persists; purchased Smoke Ball survives a restored wild session, succeeds via `+flee`, then returns to the bag.

Disposable setup supplies tagged identities, native targets, money and deliberate room stock (test price $100). These are **automated production-command/model flows with captured transport**, not live logins, natural species acquisition, approved economy prices or live world stock. No item is granted to the ordinary test bag before the acquisition being proved. Prepared held-batch teams remain a separate evidence category.

Empty/absent shops and insufficient money/stock leave wallet/inventory unchanged. Itemfinder and ignored chart-held metadata are retained as confirmed gaps. Preliminary harness errors are listed in the JSON report and corrected; they are not reported as item defects. The interrupted preparation/gate attempt is nonqualifying; only the final unchanged-source run below qualifies.

## Held support freshness and bounds

**15 of 126** historically pinned runtime files differ by bytes. Raw-byte comparison includes checkout newline differences; it does not itself identify a mechanics regression. The changed surfaces are listed below and in JSON. Five prior reports/matrix files are unchanged; 570 PvP and nine reward archives pass integrity checks. **Those checksum checks are not fresh battles.**

The four established **stat-type-1 through stat-type-4** batches were freshly replayed through production commands and real owned models: **91 items / 94 declared effect checks**, keeping the original 25-item/50-template bounds and zero-new-check budgets. The [pinned plan](item-stat-type-plan-2026-10-22.json) publishes the exact original fixtures/rules/seeds; current per-item statuses and source identities are in the index/report. Matching controls, native form/stat assertions, actual HP/PP, held ownership after cleanup and finite natural critical windows are retained. Chance misses cannot qualify as positive proof.

Current incense, suppression, hit/berry, accuracy/priority, trapping, form, reward, medicine and checkpoint regressions were also rerun in the focused/PG/gate suites. The **other 14 historical batches were not freshly replayed as full retained-template or live Telnet batches**; their historical results stay explicitly historical. #782 owns deliberately released live acceptance and exact batch accounting, without claiming all 283 retained items currently obtainable.

Changed runtime surfaces: `pokemon/battle/actionqueue.py`, `pokemon/battle/battledata.py`, `pokemon/battle/battleinstance.py`, `pokemon/battle/engine.py`, `pokemon/battle/logic.py`, `pokemon/battle/native_forms.py`, `pokemon/battle/player_choices.py`, `pokemon/battle/pokemon_factory.py`, `pokemon/battle/state.py`, `pokemon/battle/turn.py`, `pokemon/battle/turns.py`, `pokemon/helpers/pokemon_helpers.py`, `pokemon/services/battle_items.py`, `pokemon/services/battle_rewards.py`, `pokemon/services/evolution.py`.

## Final verification and cleanup

**822 PostgreSQL tests** passed, including the four batch tests above; the 94 independent batch effect checks are not added again to this test total. **814 focused tests** passed. **983 Python sources** stayed unchanged throughout the qualifying run. All three mandatory fresh-process orders passed:

| Order | Passed | Skipped |
| --- | --- | --- |
| combined | 4669 | 4014 |
| repeat | 4669 | 4014 |
| battle-first | 4669 | 4014 |

Skipped cases are outside the enabled gate scope. Existing model-reload/cache warnings are retained. All disposable schemas were removed, public test schema tables are zero and the private PostgreSQL cluster is stopped. No migrations, source edits on the server, deployments, service restarts, live stock grants or existing-human changes occurred. Hosted CI completion, main merge and public-server gameplay are not claimed.

Reproduction: set an explicit disposable `PF2_TEST_POSTGRES_DSN`, then run `python tests/integration/item_availability_cases.py`. Run `PF2_ITEM_SUPPORT_BATCH=stat-type-N python tests/integration/item_stat_batch_cases.py` for N=1..4. The standalone suites create/drop only random guarded schemas; they never fall back to game database settings. `PF2_AVAILABILITY_EVIDENCE` and `PF2_ITEM_BATCH_EVIDENCE` optionally retain JSON receipts. Run `python tools/audit_item_availability.py --snapshot docs/testing/item-world-snapshot-2026-10-22.json --output <output.json>` to regenerate the base index; report enrichment adds the fresh evidence pointers. Exact commands, environment boundaries and log hashes for every suite are in JSON.

## Remaining work and classification

| Follow-up | Classification / bounded next step |
| --- | --- |
| [#779](https://github.com/PokemonFusion/Fusion2/issues/779) | Fix Itemfinder’s message-only result with one reviewed real drop/credit route |
| [#780](https://github.com/PokemonFusion/Fusion2/issues/780) | Define one authored wild held-item acquisition slice and preserve source/consumption through capture |
| [#781](https://github.com/PokemonFusion/Fusion2/issues/781) | Author one discoverable supply route with at most six existing representative items, deliberate costs and stock |
| [#782](https://github.com/PokemonFusion/Fusion2/issues/782) | Fresh ordinary-player acquire-to-effect acceptance after a deliberate release and source setup |
| #773–#778 | Existing manual battle food/berry, Mega/Z, growing/flavor and missing non-plot additions stay open |
| [#731](https://github.com/PokemonFusion/Fusion2/issues/731) | Wider help/website/onboarding agreement and live walkthroughs stay open; this audit adds discoverable item guidance |

The explicit reviewed scope is four entries larger than the previous hand-selected 447: existing Iron Ball, Light Ball, Crucibellite and Vile Vial are now accounted for. The last two are CAP catalog content; no canonical acquisition is implied. No definitions or plot-only/key/quest/story content were added, and no unrelated work is included.
