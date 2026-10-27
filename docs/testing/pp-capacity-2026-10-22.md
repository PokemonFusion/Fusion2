# PP Up and PP Max field-use acceptance - October 22, 2026

Issue: #765. Source baseline: `40e536a0864f5d670613e1ef07c0c211b426d611` on `staging`.

PP Up now advances one of three integer-rounded fifth-of-base capacity stages; PP Max fills the remaining boost. Tackle 35 reaches 42/49/56 with three Ups or 56 with one Max, including partial boosts. Current PP increases by the capacity difference, preserving spent PP. Five-PP moves reach 6/7/8; the four dex `noPPBoosts` moves and base PP below 5 are rejected without debit.

The ordinary prompt stores stable Pokemon, placement, active-slot/move and raw-boost identities. Confirmation rechecks fresh owner, party/current Fusion, eggs, battle guards, exact active move identity and inventory under field locks. Slots 1/3 remain 1/3: nonexistent 2 cannot select 3. Names use exact normalized matches; ambiguous choices fail. A consumed/replaced/stale prompt cannot be replayed. A new intentional prompt permits the next paid Up.

Boost rows, affected current PP and bag debit commit together. False/partially false debits and failures after real SQL writes roll back all effects. Postcommit notices and cache synchronization reuse the Rare Candy boundary. Testing also found and repaired the inventory callback lookup: current Evennia User objects expose their updater directly, without the legacy `.typeclass` wrapper. Success and rollback now check actual User inventory caches.

## Current proof

- **37 new PostgreSQL cases** cover actual `+use` prompt/selection, inventory and party discovery, SQL reload, aliases, canonical gaps, normal deposit, release/owner/egg/reservation/move/boost changes, exact and ambiguous targets/moves, low PP, legacy rows, missing stock, fault injection, caches and independent-connection contention.
- **334 PostgreSQL cases total** passed: pp_capacity 37; name_resolution 8; capture_ether 21; status_item 9; rare_candy 25; field_item 23; field_berry 26; field_food 70; remaining_item 8; capture_pp_item 16; leader_crest 29; evolution 28; progression 11; cloud_gameplay 9; ui 14.
- **234 focused pytest tests** passed, including PP restoration/persistence/serialization, move learning/management/menus, command routing, inventory, import isolation and related field/evolution checks.
- **Mandatory fresh-process gate:** combined: 4616 passed / 4014 skipped; repeat: 4616 passed / 4014 skipped; battle-first: 4616 passed / 4014 skipped.
- **967 frozen Python files** remained unchanged during final verification. The JSON pins 34 relevant source/test/workflow/help hashes for committed-blob comparison.
- Warnings in local logs are recorded separately from pass counts; these checks do not claim a warning-free environment.

## Ordinary player flow

Tagged disposable setup creates normal User characters, canonical party slot 3, active move slots 1/3 and bag stock through production writers. The player discovers items with `+inventory` and their Pokemon with `+party 3`, enters `+use PP Up=3`, then `+use 1` or the exact move name. SQL reads confirm the raw bonus, current PP and inventory. Fresh intentional prompts reach 42, 49 and 56; a fourth Up spends nothing. Separate PP Max flows reach 56 from raw bonuses 0/7/14. Slot 3 and `WATER  GUN` select the actual Water Gun slot; `2` fails and can retry.

A real `+box/deposit <Pokemon ID>` between prompt and confirmation removes eligibility. Foreign ownership, eggs, release, inactive/current-Fusion changes, changed active identities and changed bonuses likewise cannot apply the old prompt. Concurrent final-copy confirmations buy one gain; even two copies cannot replay one captured prompt. Independent model-level Up writers serialize and observe fresh bonus/current PP.

The [JSON report](pp-capacity-2026-10-22.json) embeds command inputs, output and SQL before/after rows, exact test commands, durations, log hashes, fault diagnoses and cleanup proof. Success effects use production code; only negative-case faults are injected.

## Legacy compatibility and source review

The catalogue audit reads source definitions and disposable saved rows only. MOVEDEX has 1,904 alias keys representing 952 normalized moves. All boostable base PP values are divisible by five; rounding tests separately exercise a hypothetical base 7. Revival Blessing, Sketch, Struggle and Trump Card carry `noPPBoosts`; other base-1 special moves also cannot gain PP.

Stored `bonus_pp` remains raw extra PP. Source consumers in `OwnedPokemon.get_max_pp`, battle PP restoration and move management already add those units directly. A valid Water Gun +15 still restores to 40. Disposable probes cover Tackle raw +1/+3/+6/+7/+14/+21/+22. Legal stages advance normally; nonstandard in-range bonuses reject PP Up and can explicitly use one PP Max to fill to +21. Maxed, out-of-range and unboostable rows remain unchanged. No blind multiplication, automatic refund or migration is attempted because raw values do not prove historical use counts. No existing human/game database was queried or modified.

Mechanics were checked against the [PP Up/PP Max reference implementation](https://github.com/pret/pokeemerald/blob/master/src/pokemon.c) (capacity-delta current PP, up to three stages) and [Showdown calculatePP](https://github.com/smogon/pokemon-showdown/blob/master/sim/battle.ts) (base fifths and noPPBoosts), alongside this repository's authoritative dex. PF2 retains integer storage, modern 1.6x maximum, and its existing NULL-current-PP full initialization convention.

## Limits and preservation

This is automated local production-command/model acceptance with real private PostgreSQL and captured session transport. It is separate from a fresh Telnet/WebSocket login, hosted CI, main merge, deployment and live item availability. No existing game service, database or human character was touched. Disposable schemas were removed and the private cluster stopped.

Rare Candy, field medicine, berries/foods, battle PP restoration and move-management regressions passed. Battle runtime and generated dex data are unchanged. No new item definitions, plot-only content, migrations or unrelated WIP are included. The lifecycle CI workflow now runs the new PP suite; its future hosted outcome is not asserted here.

Preliminary fixture failures and the confirmed inventory-cache lookup correction are diagnosed in JSON. Only final frozen-build results count as acceptance. Raw runner/cluster logs remain under ignored `.codex-artifacts/pp-capacity-20261022/`; the committed report contains no credentials.
