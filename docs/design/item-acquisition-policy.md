# Non-plot acquisition policy (#861)

Scope decision, not installed stock. Complete the six repairs and #859 before
publishing this policy; #860 qualifies the released item candidate. #862 owns
the first ordinary public source. Other delivery batches remain separate.

## Refreshed source boundary

The October 25 read-only PF2-Dev inspection still found clean `af0eca6e`, Pokémon
migration 0045, no enabled item shops, no nursery, and only a capture-ball
dispenser. Existing unnamed finder rates are not the named Potion rule.
Inspecting 21 source/room objects and 24 exits changed no game data. Public
Alpha Test Hub #31 is connected from Limbo #2 by `(A)lpha (H)ub`, with an
`(E)xit` return; their recorded view/traverse locks permit all. This is a
**reviewed proposed hub**, not an ordinary walkthrough or installation.
Do not use private QA rooms, Adventure instances or existing characters as fixtures.

The [current source index](../testing/item-availability-index-2026-10-25.json)
keeps 452 non-plot item capabilities separate from world availability. The
dated configuration companion records only observed shop/vendor configuration;
it does not exhaust all rewards, locks, spawn choices, player ownership or loot.
Adventure Alpha Meadow's first-clear Potion remains a once-per-character
reward. The authored Potion finder and Rattata/Oran held source are opt-in rules;
an unnamed rate/default chart is not an installed source. Growing requires a
deliberately installed nursery and real seed. Local released Necrozma/Mega/Z
proof is independent from ordinary access to native species and crystals.

## Shared source contract

Use one public hub's named exits and separate versioned counters. Inspect IDs,
marker, exact offer vectors, locks and source revision before installation.
Reject a conflicting entrance/marker/price/item set; never replace a room or
reset sold stock. Preserve buy-only/no resale and the atomic wallet/stock/bag
purchase service. Ordinary Player permission suffices; no badge, plot, quest,
Ring, story item or staff permission may be a purchase prerequisite.

The initial six-item source remains exactly finite/no-refill: Potion300×20,
Oran80×20, Fresh Water200×20, Fire Stone3000×5, Leftovers4000×2,
Smoke Ball4000×2. These are deliberate PF2 values. Ownership is the current
character's bag/Pokémon, not an account-wide inventory. Existing purchases have
no extra per-character quota: wallet, positive integer quantity and aggregate
stock limit them. Reconnect, installation retry and server startup give no stock.

Sustainability is a separate **operator-invoked replenishment design**, not a
silent change to this installer. A later versioned consumable counter may opt
into at most one refill per 24 real UTC hours, capped at its exact initial offer
quantities. Persist a source/version/window receipt in the same transaction as
the capped stock delta; serialize with purchases, reject drift/clock rollback,
and make concurrent/replayed calls idempotent. Use a rolling 24-hour elapsed
interval from the last committed refill, not a midnight date boundary that
permits two refills minutes apart. No refill debt, carryover, startup refill,
price change, player resale or unlimited stock. The first six
source stays excluded until its own reviewed version explicitly opts in.
Release/rollback and actual economy authorization remain separate from design.
The [explicit operator API](../item-replenishment.md) now implements this
separate opt-in contract. Its [disposable checks](../testing/item-replenishment-2026-10-25.md)
do not install or opt in any existing source. The original six-item counter and
the seven proposed counters below remain excluded by default.
The renewable finder and garden routes also require their own real elapsed
time, cooldown, current-cycle and final-credit acceptance, never timer grants.

## Small source deliveries

Every row below is a proposed finite buy-only counter after #862. Prices are
selected PF2 authoring values, not official cartridge prices. No row installs
the entire supported catalog. Each future issue names its route and performs
travel→discovery→funds/stock→purchase→inventory→use/equip/evolve→reconnect.

| Batch | Exact offers (price × initial units) | Useful route / gate |
| --- | --- | --- |
| Status medicine | Antidote100×20; Paralyze Heal200×20; Awakening250×10; Burn Heal250×10; Ice Heal250×10; Full Heal600×10 | Existing +use/manual +item only on eligible useful conditions |
| Stronger medicine/revival | Super Potion700×20; Hyper Potion1500×10; Revive1500×10; Max Revive4000×2 | Existing field/manual routes, fainted/current roster guards |
| PP | Ether1200×10; Max Ether2400×5; Elixir3000×5; Max Elixir6000×2 | Actual depleted active slots; no PP Up/Max shortcut |
| Evolution stones | Water Stone3000×5; Thunder Stone3000×5; Leaf Stone3000×5; Ice Stone3000×5; Sun Stone3000×5; Moon Stone3000×5 | Existing native +evolve rules; Fire Stone remains first counter |
| Training | HP Up10000×2; Protein10000×2; Iron10000×2; Calcium10000×2; Zinc10000×2; Carbos10000×2 | Existing EV caps/shared field checks; no stat assignment grants |
| PP capacity/ability | PP Up9800×2; PP Max15000×1; Ability Capsule20000×1; Ability Patch30000×1 | Existing selected-move/native-ability checks; no-effect no debit |
| Held staples | Sitrus Berry200×10; Lum Berry600×5; Focus Sash5000×2; Choice Band5000×1; Choice Specs5000×1; Choice Scarf5000×1 | Actual held consumption/recovery/survival/lock/stat effects |

The [seven finite source recipes](../finite-item-supply.md) now have
[disposable command/SQL checks](../testing/finite-item-sources-2026-10-25.md).
Their authoring does not install counters, opt them into refill, or complete
the separate permanent-source release/player acceptance requirement.

The operator-refill foundation, seven finite source batches, and renewable
Potion finder/Rattata-Oran acceptance become explicit implementation issues.
Existing 47-offer Mega and 34-offer Z recipes remain finite one-copy each at 10000,
behind their actual native/source registries; no additional generic source is
enabled by stocking a crystal. Their installation/released QA is a separate
bounded source issue. Nursery's Oran/Razz100×5 recipe remains unchanged;
additional seeds and the 13 flavor foods use #867/#866 exact follow-ups.

Evolution items outside the six stones, herbs/other foods, EV berries/feathers,
Bottle Caps, native legendary boosters/protected artifacts and progression
families remain **supported capability with no newly selected public source**.
Do not infer a drop from a dex field. Plan later explicit named source batches
only after real usage/currency evidence. Leader's Crest is an opponent
qualification, never a purchasable replacement for authored victories.
New EXP Candy/mint/mochi/boosters wait for their own accepted runtime issues.
No capture-ball, clutter, CAP or plot-only offers enter this policy.

## Release and acceptance

Before changing an existing world, publish exact target/build/schema, hub and
new object/stock allowlist, source fingerprints, operator commands, protected
baselines and rollback. Use existing local-dev authority only within its scope;
PF2-Dev remains read-only absent explicit new authority. A new task-owned QA
shop is tagged disposable proof, not permanent public supply. #862 cannot close
merely because a temporary fixture was installed and removed.

Prove all first six effects, no-funds/no-stock/bad-quantity handling, correct
wallet/stock/bag deltas, last-copy concurrency, post-debit rollback, installer
retry and reconnect. Protect existing human rows, source stock and unrelated
work. Rollback removes only a just-created unused source or disables its entry
after purchases pending explicit reconciliation; never delete purchased items,
reset player wallets or restore an old entire game database.

Linked follow-ups and the dated scope receipt bind delivery to this source inventory.


## Implementation follow-ups

This closes the design/scoping deliverable only. Runtime effects, source installation,
migration/release operations and ordinary acceptance remain with these open issues.

| Issue | Exact delivery | Dependencies |
| --- | --- | --- |
| [#876](https://github.com/PokemonFusion/Fusion2/issues/876) | Add explicit capped operator replenishment for opted-in sources | #861, #862 |
| [#877](https://github.com/PokemonFusion/Fusion2/issues/877) | Author a finite public source for six status medicines | #861, #862 |
| [#878](https://github.com/PokemonFusion/Fusion2/issues/878) | Author a finite public source for four stronger healing/revival medicines | #861, #862 |
| [#879](https://github.com/PokemonFusion/Fusion2/issues/879) | Author a finite public source for four PP recovery medicines | #861, #862 |
| [#880](https://github.com/PokemonFusion/Fusion2/issues/880) | Author a finite public source for six evolution stones | #861, #862 |
| [#881](https://github.com/PokemonFusion/Fusion2/issues/881) | Author a finite public source for six vitamins | #861, #862 |
| [#882](https://github.com/PokemonFusion/Fusion2/issues/882) | Author a finite public source for PP capacity and ability items | #861, #862 |
| [#883](https://github.com/PokemonFusion/Fusion2/issues/883) | Author a finite public source for six held staples | #861, #862 |
| [#884](https://github.com/PokemonFusion/Fusion2/issues/884) | Qualify named Potion finder and Rattata/Oran renewable sources | #861, #862 |

Scope/source checks: [2026-10-25 decision receipt](../testing/item-scope-decisions-2026-10-25.md).
