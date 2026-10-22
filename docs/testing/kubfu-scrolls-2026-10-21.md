# Functional Kubfu Scrolls — issue #762

Both existing Urshifu styles now have non-plot bag-item routes through ordinary
`+evolve`: Scroll of Darkness selects `Urshifu` (Single Strike), and Scroll of
Waters selects `Urshifu-Rapid-Strike`. Exactly one chosen bag copy is consumed
on success. An optional exact target must agree with the Scroll. Missing items,
target-only requests, held-only copies and incomplete names cannot supply the
trigger. Existing Urshifu cannot switch style using a Scroll.

The [PF2 rule contract](../kubfu-evolution.md) was recorded before code changes.
The #747 existing-item gate and closed #755/#756 dependencies were refreshed
first. The modern [Darkness](https://bulbapedia.bulbagarden.net/wiki/Scroll_of_Darkness#Effect)
and [Waters](https://bulbapedia.bulbagarden.net/wiki/Scroll_of_Waters#Effect) bag
items select the same species branches. PF2's consumable Evolution Items,
10000 reference prices and opt-in shop/reward acquisition are explicit policy
choices. No cartridge consumption/price equivalence is claimed. Plot-only
props, tower/quest content, legendary acquisition and Gigantamax are excluded.

## Bounded implementation

`KubfuEvolution` allows only exact native Kubfu and the two reviewed target
names, expected form metadata, `other` type and original tower condition strings.
It explicitly handles the existing Rapid Strike `baseSpecies` / `forme` row
without admitting arbitrary forms. The shared evaluator supplies the selected
Scroll requirement and retains source `evos`, target `prevo`, any explicit dex
level/gender/region and Everstone checks. Generic tower and other-condition
evaluation remains false; flags or command text cannot grant permission.

Both complete item definitions supply descriptions, Evolution Items category,
reference costs and ordinary normalized lookup/display/equip behavior. The
price CSV and generated dex files are unchanged. Existing shop/reward tooling
can deliberately stock the items; no live stock, rewards or grants were added.

The shared evolution service is unchanged. It locks storage, trainer and a fresh
owned row, checks ownership/placement/reservation/egg/battle context, debits the
real item, saves the same Pokemon and records the normal evolution receipt in
one transaction. Actual post-debit and post-save failures roll back both item
quantities, species and receipt, then restore shared cached state. Concurrent
opposite-style requests choose one legal result and debit only its item.

UUID, owner, nickname, canonical party/box placement, mirrors, held item, current
HP/status/sleep, EXP, IVs/EVs, friendship, moves/PP and unrelated flags are
preserved. Canonical species, mapped ability (`Inner Focus` to `Unseen Fist`),
derived types/stats and the ordinary evolution receipt change. Current HP is
unchanged; maximum HP follows species normally, without healing/rescaling.
No automatic signature-move grant or capability unlock was added.

## Ordinary player proof

Four complete automated command/menu walkthroughs cover both styles at levels
1 and 100, friendship zero and absent room context. Separate fixture setup
creates tagged disposable owners, native Kubfu, a gapped canonical party and
shop stock. Ordinary actions use the shipped purchase menu, `+inventory`,
`+itemdex <Scroll>`, `+party 3`, `+evolve <full ID> <Scroll>[=<target>]`, SQL reload,
`+party 3`, same-request retry and an unsuccessful other-style request. Each
buys two copies for 20000, consumes one, preserves the other Scroll stock and
keeps the same ID, placement, held item, saved state and mapped ability.

The 56-case PostgreSQL suite runs the same 28 checks separately for each style.
It covers missing/held-only items, separate equipped copies, fake tower flags,
Everstone, eggs, reservations, battle locks, foreign/conflicting ownership,
mismatched/partial/unknown/Gmax targets, wrong sources/nicknames, unreviewed
conditions, real post-save/debit failures, stale model references, boxed
placement, legacy inventory aliases, reload/replay and `+use` rejection.
Independent-connection races cover duplicate completion, opposite Scrolls,
two Kubfu competing for one copy, Fusion reservation and box deposit.

The first focused check incorrectly changed only dex raw fields for `evos` and
`evoLevel`; the runtime dex exposes parsed `evos` / `evo_level` attributes. The
fixtures were corrected to change the actual evaluated attributes. No gameplay
failure was diagnosed from those three assertion failures. All 56 PostgreSQL
cases passed on their first run; the final frozen-source rerun is recorded below.

The new production-model suite is wired into lifecycle CI. It uses real rules,
models, inventory, locks and transactions; session output is captured and shop
configuration is separate disposable setup. No migration runner or game
database/service is used. This is automated ordinary-command/model acceptance,
separate from a live login, hosted CI completion, main merge or deployment.

## Final validation

| Check | Passing result |
| --- | --- |
| PostgreSQL kubfu | 56 cases |
| PostgreSQL leader crest | 29 cases |
| PostgreSQL battle recovery | 36 cases |
| PostgreSQL progression | 11 cases |
| PostgreSQL trainer challenge | 10 cases |
| PostgreSQL player doubles | 10 cases |
| PostgreSQL adventure lifecycle | 9 cases |
| PostgreSQL evolution | 28 cases |
| PostgreSQL alcremie | 76 cases |
| PostgreSQL trade held | 33 cases |
| PostgreSQL peat block | 29 cases |
| PostgreSQL ui | 14 cases |
| PostgreSQL smoke ball | 17 cases |
| PostgreSQL remaining item | 8 cases |
| PostgreSQL field food | 70 cases |
| Total PostgreSQL | 436 cases |
| Focused pytest | 283 tests |
| Mandatory combined, repeat and battle-first | 4,596 passed / 4,014 skipped in each process |

All processes exited successfully. All 961 frozen Python files remained unchanged through final validation. All test schemas were removed, public tables remain empty, and the private cluster was stopped. Skipped checks remain outside enabled scope; existing warnings are retained.

The [JSON report](kubfu-scrolls-2026-10-21.json) retains source/output hashes,
commands, four walkthroughs, process results and private-cluster cleanup.
Historical reports and the #757 matrix remain unchanged pinned snapshots;
the evolution guide links this later addition separately.
