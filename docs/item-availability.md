# Finding and using items

## October 29 repair candidate

The [held-item guide](held-item-repairs.md) describes the repaired stat,
indirect-damage, residual-healing and Berserk Gene behavior. The
[manual medicine policy](battle-recovery-items.md) includes target-specific
Embargo checks. Their [dated evidence](testing/item-repairs-2026-10-29.md) keeps
offline tests, captured command/SQL observations, publication and deployment
separate. The [new source-only index](testing/item-availability-repairs-index-2026-10-29.json)
contains 642 definitions and 494 scoped items, including Link Cord. Its coarse
capability labels are not complete facet acceptance; no fresh world snapshot was
supplied, so all 494 current-world availability entries remain unverified.

Ordinary [consent trades](operations/consent-trading.md) use `+trade` without
automatic evolution. [Link Cord](link-cord-evolution.md) is consumed from the bag
by `+evolve <id> Link Cord` for its 14 exact mappings. Existing trade-held item
evolutions keep their held-item route. Public acquisition remains a separate check.

## Current public counters (October26 release)

At Alpha Test Hub31 these ordinary exits reach finite buy-only counters. Use
`+store`, choose **Buy items** and inspect actual quantities; `back` returns to
the hub. There is no automatic refill or resale.

| Exit | Supplies |
| --- | --- |
| `supplies` | Potion, Oran Berry, Fresh Water, Fire Stone, Leftovers, Smoke Ball |
| `statusmeds` | Six status medicines |
| `recoverymeds` | Super/Hyper Potion, Revive/Max Revive |
| `ppmeds` | Ether/Max Ether, Elixir/Max Elixir |
| `stones` | Water, Thunder, Leaf, Ice, Sun and Moon Stone |
| `vitamins` | HP Up, Protein, Iron, Calcium, Zinc and Carbos |
| `capacity` | PP Up/Max and Ability Capsule/Patch; sold out at acceptance |
| `helditems` | Sitrus, Lum, Focus Sash and Choice items; Choice offers sold out |
| `seeds` | Cheri, Pecha, Rawst and Aspear; plant/water four real-hour stages here |
| `expcandy` | XS, S, M, L and XL; XL sold out at acceptance |
| `mints` | All21 nature mints; sold out at acceptance |

The [released report](testing/remaining-item-released-player-2026-10-26.md) and
[dated per-item index](testing/item-availability-released-index-2026-10-26.json)
record72 offers:43 in stock and29 sold out at final observation. Later sales
can deplete them. The other421 scoped definitions remain world-unverified.
Real nursery harvest/use, Candy progression/learning, mint genetics and both
native Ultra lifecycles passed ordinary-player checks. Live QA fixtures and
temporary capture/crystal helpers were removed; sealed audit histories remain.
Temporary helpers do not certify permanent public acquisition. Earlier dated
source-only reports and then-pending gates below remain historical evidence.

Use `+store` in a shop, choose **Buy items**, then enter the complete displayed
item name and amount, such as `Potion 1`. The shop needs stock and you need
enough money. `+itemdex` describes items; it does not tell you where they are
sold. `+inventory` shows the copies you actually own.

Use `+vend <machine name> 1` when a dispenser is present. Some machines give a
bundle per request. A dispenser's label and stock determine what it provides.
The alpha build recipe includes a Rare Candy dispenser, but building the recipe
and having that dispenser in the current world are separate steps.

The authored Alpha Meadow Survey gives one Potion on your character's first
completion. Use `+adventure/list`, `+adventure/info alpha_meadow`, then
`+adventure/start alpha_meadow` where Adventures are available. Follow its
objectives and use `+adventure/claim` if a completed reward is pending. Repeating
the Adventure does not give another first-clear Potion.

| What you own | Example action | Main limit |
| --- | --- | --- |
| Medicine, food or recovery berry | `+use Potion=3`, `+use Fresh Water=3`, `+use Oran Berry=3` | Outside battle; target must currently be eligible |
| Revival medicine | `+use Revive=3`, `+use Sacred Ash=party` | Needs a fainted target; Sacred Ash targets the eligible party |
| PP recovery or capacity | `+use Ether=3/Water Gun`, `+use PP Up=3` | Capacity items then ask for an actual active move |
| EV berry or training item | `+use Pomeg Berry=3`, `+use Protein=3` | Only useful changes consume a copy; stat/total caps apply |
| Ability or Hyper Training item | `+use Ability Capsule=3`, `+use Bottle Cap=3/Atk` | Native ability eligibility; Hyper Training requires level 50+ |
| Bag evolution item | `+evolve <full-pokemon-id> Fire Stone` | Species and other evolution conditions still apply |
| Sweet or trade-held evolution item | `+hold 3=Strawberry Sweet`, then `+evolve <full-pokemon-id>` | Equip the real copy first; see [evolution](evolution.md) |
| Reusable held effect | `+hold 3=Leftovers` or `+hold 3=Odd Incense` | The acting holder needs the item; suppression can disable it |
| Smoke Ball | `+hold 3=Smoke Ball`, then `+flee` in battle | Eligible wild battles only; trainer/PvP restrictions still apply |
| Gimmighoul Coin | `+evolve <full-pokemon-id> Gimmighoul Coin` | Native Chest form at level 2–100; consumes 999 bag coins; [PF2 manual equivalent](gimmighoul-evolution.md) |
| Rage Candy Bar / Hopo Berry | `+use Rage Candy Bar=3`, `+use Hopo Berry=3/Water Gun` | [Field-only status/selected-move PP equivalents](recovery-equivalents.md); no held Hopo effect |

Use `+party 3` to inspect the target and copy its full ID. Use `+hold 3=` to
return an uneaten held item to your bag. Having a bag copy does not activate a
held effect. Manual `+item` battle use supports standard medicine and the
[32 reviewed recovery foods/berries](battle-recovery-items.md), for example
`+item Fresh Water=3` and `+item A1 Leppa Berry=3/Water Gun`. Flavor/EV berries
and Sacred Ash remain excluded. Unsupported battle items are rejected before
spending an action. The linked #772 acquisition snapshots remain dated evidence;
#773's report records this later capability extension separately.

Leader's Crest is an opponent qualification for Bisharp's Kingambit route. Your
Pokémon must defeat the required authored leaders; buying or holding your own
Crest does not replace those victories. Mega Stones, Z-Crystals and berries
without a feeding effect do not imply that Mega/Z activation or growing works.
The later [47-pair Mega route](mega-evolution.md) supplies ordinary `+mega` before
`+attack`, native/held validation, durable form state and an optional finite
10,000-price Counter recipe. Its local automated acceptance is separate from
deployment and permanent public stock; the [per-stone matrix](design/mega-stones.md)
records accepted effects, source limits and the remaining CAP/required-move exclusions.
The later [Z route](z-moves.md) accepts63 explicit source mappings on35
existing crystals through `+zmove`, including 14 status sources,16 unchanged
signatures and one separately guarded [Ultra signature](ultra-burst.md).
The [matrix](design/z-crystals.md) names the older exact native/source
limits; other unreviewed source moves remain deferred. The native
[Necrozma combine/separate route](necrozma.md) accepts two real owned sources
and the matching Dusk-Mane/Sunsteel or Dawn-Wings/Moongeist signature, with
durable native-pair proof. Its [released local acceptance](testing/necrozma-released-retry-2026-10-24.md)
does not certify a shared game or a newer item-repair candidate. The optional
10,000-price/stock1 Counter and configured native hunt/capture routes have
local automated [acceptance](testing/z-special-2026-10-23.md), separate from
live deployment, authored chart availability and permanent public stock.
The later [berry nursery](berry-nursery.md) adds one private durable Oran bed and
the independent `+berry snack Razz Berry=<target>` HP equivalent. The same guarded
snack route later accepts thirteen explicitly named flavor berries for up to
10 HP; see [the current snack list](berry-nursery.md). Its optional
100-per-berry, five-copy source is checked-in content, with local command/SQL
acceptance; it does not establish deployed commands or permanent public stock.

The **October 22, 2026, 20:04 UTC** configuration snapshot found no enabled item
shops or Rare Candy dispenser on the older checkout. A later approved PF2-Dev
release and [nine-item live walkthrough](testing/item-live-2026-10-22.md) verified
finite tagged QA shops, actual purchases/effects and reconnect. Those disposable
shops were removed afterward; the walkthrough does not establish permanent
public stock. Confirm where an item is available before planning around it.

After PP Up or PP Max, `+party 3` and `+party/moves 3` show the current PP and
boosted maximum. Evolution notices identify the original species or nickname
before the destination species. The later [feedback repair](testing/item-feedback-2026-10-22.md)
corrects the two display defects found in that walkthrough; its automated
command/SQL evidence is separate from the earlier released-build evidence.
Use `+store` then **Buy items** (`1`) to view stock; the older room hint
`+store/list` opens that same menu. Close it with `q` before taking an exit.

The old Itemfinder message-only result has been replaced by an explicitly
configured [Potion finder](hunt-item-sources.md). The same guide specifies one
opt-in Rattata/Oran Berry wild source; default charts grant no held item.
The [six-item Supply Corner](item-supply-route.md) is a duplicate-safe
authored source with finite stock. Its [October 25 permanent release](testing/item-source-released-player-2026-10-25.md)
verified ordinary travel from Alpha Test Hub #31 through `supplies`, all six
purchases/effects and retry/reconnect. The counter remains buy-only, with no
automatic refill; dated remaining stock is Potion19, Oran19, FreshWater19,
FireStone4, Leftovers1 and SmokeBall1. `back` returns to the hub. Later sales can
deplete these quantities. This is proof for those six offers only.
The October 22 released QA walkthrough verifies only
the nine named items at its deliberately authored sources, which were cleaned up.
Finder/wild-held sources and permanent world population require their own checks.

The [acquisition audit](testing/item-availability-2026-10-22.md) and
[per-item index](testing/item-availability-index-2026-10-22.json) distinguish
configured sources, tested commands, missing routes and live walkthroughs.

The [October25 current index](testing/item-availability-physical-status-z-index-2026-10-25.json)
and [reconciliation receipt](testing/item-availability-2026-10-25.md) read the
current field/manual services and explicit Mega/Z registries. They also link the
six native-item/status-berry repair receipts. Their scope contains 452 non-plot
items out of 600 deduplicated definitions, with Crucibellite and Vile Vial
explicitly excluded as CAP. This source-only index supplies no current world
snapshot: all 452 world-availability entries remain unverified.

Authored shop recipes, optional hunt/finder rules, a nursery's timed Oran yield
and a dated local test are different evidence. An uninspected world is unknown;
an observed depleted source differs from an absent or disabled source. None of
these labels replenishes stock or proves ordinary travel, locks or purchases.
The 576-definition battle matrix and earlier dated reports remain historical.
The [two-source Z receipt](testing/z-existing-sources-2026-10-25.md) records
the later Flamethrower/Surf expansion; the first reconciliation index and its
dated world snapshot remain unchanged. The later [six special sources](testing/z-six-special-sources-2026-10-25.md)
extend the explicit registry to 50 mappings on the same 34 crystals; earlier indices remain immutable.

The later [thirteen flavor snacks](testing/flavor-snacks-2026-10-25.md) use the
selected berry through `+berry snack`, each healing up to 10 HP. Their explicit
field support adds no nursery offers, growing species or public stock. The
earlier Z-source index remains the receipt for its dated candidate.
The [separate released snack walkthrough](testing/flavor-snacks-released-player-2026-10-25.md)
verifies all thirteen names through normal purchases and socket inputs, with
43 effect/conservation checks. Its stock and schema were disposable and removed.

The [October 25 deliberately released local walkthrough](testing/item-repair-released-player-2026-10-25.md)
qualifies the repaired candidate through 716 ordinary commands and 102 independent
effect/conservation checks. It replays named native bonuses, nickname theft,
all three repaired held berries, medicine/PP/evolution, Mega, both new generic Z
sources and both native Necrozma signatures, including zero-PP refusals.
The report separates its bounded representatives from the complete per-item
automated matrices. Both Player accounts, tagged stock and base-source charts
were disposable; the instance/schema were removed. This creates no permanent
public supply. The later [#862 acceptance](testing/item-source-released-player-2026-10-25.md)
separately verifies the six permanent public offers and removes its own QA fixtures.

The later [physical](testing/z-six-physical-sources-2026-10-25.md) and
[status](testing/z-six-status-sources-2026-10-25.md) batches bring the
explicit registry to 62 mappings on 34 crystals. Their source-only index
keeps world availability unknown; the dated permanent six-item Supply
Corner acceptance remains separate. No new crystal/source is stocked by these changes.

The later [seven finite counter recipes](finite-item-supply.md) author 36
specific status/recovery/PP/stone/training/ability/held offers and test their
ordinary routes. Their [source index](testing/item-availability-finite-sources-index-2026-10-25.json)
records authored stock separately from unknown world access. They are not
installed in PF2-Dev by code publication. The original permanent six-item
counter and its dated acceptance remain separate; all new recipes are no-refill.

The later [seven mochi](ev-mochi.md) reuse safe field training, and
[Cheri/Pecha/Rawst/Aspear growing](berry-nursery.md) reuses the private nursery
lifecycle. The [updated source index](testing/item-availability-field-training-seeds-index-2026-10-25.json)
keeps459 world entries unknown, preserves the earlier452 definition fingerprints
and names their optional finite recipes. Controlled-clock growing and captured
command/SQL effects do not complete #893's four real elapsed hours or certify
permanent public stock.

The later EXP Candy, manual battle boosters and21 nature mints retain their
separate guides and dated local receipts. The newest [source-only index](testing/item-availability-ultra-index-2026-10-25.json)
preserves all493 scoped definition fingerprints and adds the explicitly guarded
[Ultra route](ultra-burst.md):63 mappings on35 crystals, including the unchanged
16 signatures and one separate native Ultra profile. All493 world entries stay
unverified in this source-only artifact. [Ultra qualification](testing/ultra-burst-2026-10-25.md)
does not replace #888's deliberately released gate; mint #904 and the finite
counter/nursery/EXP source releases also remain separate.
