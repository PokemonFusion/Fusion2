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
The [Mega activation design](design/mega-evolution.md) describes a proposed
Venusaurite route and optional supply recipe. It enables no current command or
stock; [all existing stone pairs remain deferred](design/mega-stones.md).
The [Z-Crystal plan](design/z-crystals.md) and
[berry growing/flavor-use design](design/berry-player-routes.md) likewise add no
current sources or commands. Growing, a Razz snack and Z activation have separate
implementation and released-player acceptance gates.

The **October 22, 2026** server configuration inspection found no enabled item
shops and no Rare Candy dispenser. The inspected server also predates the recent
item repairs. These are dated limits, not a promise of current stock everywhere.
Ask where an item is available before planning around its description. The
Itemfinder “mysterious item” message currently grants no item.

The [acquisition audit](testing/item-availability-2026-10-22.md) and
[per-item index](testing/item-availability-index-2026-10-22.json) distinguish
configured sources, tested commands, missing routes and live walkthroughs.
