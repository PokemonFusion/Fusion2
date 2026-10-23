# Finding and using items

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
The later [Venusaurite slice](mega-evolution.md) supplies ordinary `+mega` before
`+attack`, native/held validation, durable form state and an optional finite
10,000-price Counter recipe. Its local automated acceptance is separate from
deployment and permanent public stock; [other stone pairs remain gated](design/mega-stones.md).
The [Z-Crystal plan](design/z-crystals.md) retains its implementation gates.
The later [berry nursery](berry-nursery.md) adds one private durable Oran bed and
the independent `+berry snack Razz Berry=<target>` HP equivalent. Its optional
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
The [six-item Supply Corner](item-supply-route.md) is an optional, duplicate-safe
authored source with finite stock. The released QA walkthrough verifies only
the nine named items at its deliberately authored sources, which were cleaned up.
Finder/wild-held sources and permanent world population require their own checks.

The [acquisition audit](testing/item-availability-2026-10-22.md) and
[per-item index](testing/item-availability-index-2026-10-22.json) distinguish
configured sources, tested commands, missing routes and live walkthroughs.
