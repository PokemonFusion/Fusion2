# Additional finite item counters

Seven explicit recipes author #877–#883. They reuse the Supply Corner's
duplicate/price/stock/exit guards and ordinary atomic purchase service.
Publishing/importing them or starting the game changes no world object.
The original six-item Supply Corner stays separate and unchanged.

| Issue | Counter / proposed exit | Exact price × initial units |
| --- | --- | --- |
| #877 | Status Medicine Counter / `statusmeds` | Antidote100×20; Paralyze Heal200×20; Awakening250×10; Burn Heal250×10; Ice Heal250×10; Full Heal600×10 |
| #878 | Recovery Medicine Counter / `recoverymeds` | Super Potion700×20; Hyper Potion1500×10; Revive1500×10; Max Revive4000×2 |
| #879 | PP Recovery Counter / `ppmeds` | Ether1200×10; Max Ether2400×5; Elixir3000×5; Max Elixir6000×2 |
| #880 | Evolution Stone Counter / `stones` | Water Stone3000×5; Thunder Stone3000×5; Leaf Stone3000×5; Ice Stone3000×5; Sun Stone3000×5; Moon Stone3000×5 |
| #881 | Vitamin Counter / `vitamins` | HP Up10000×2; Protein10000×2; Iron10000×2; Calcium10000×2; Zinc10000×2; Carbos10000×2 |
| #882 | Capacity and Ability Counter / `capacity` | PP Up9800×2; PP Max15000×1; Ability Capsule20000×1; Ability Patch30000×1 |
| #883 | Held Item Counter / `helditems` | Sitrus Berry200×10; Lum Berry600×5; Focus Sash5000×2; Choice Band5000×1; Choice Specs5000×1; Choice Scarf5000×1 |

Every return exit is `back`. Ordinary Player permissions suffice for traversal,
purchase and the existing item routes. Source revision, marker and entrance
are distinct per counter. Prices are accepted PF2 authoring values.

The explicit operator authoring API is
`FINITE_SUPPLY_ROUTES[issue_number].install(approved_hub)` from
`pokemon.services.finite_item_supply`. Before invoking it against an existing
game, publish and approve the exact build/schema, hub, entrance conflicts,
object/stock allowlist, current protected baselines and rollback plan.

A clean retry returns the existing route and preserves sold stock/links.
Changed prices, over-cap counts, missing exits, conflicting hubs or entrances
require review. A transaction/advisory lock serializes setup. Outer rollback
removes just-created rooms/exits/markers and clears marker caches. It never
replaces existing counters or resets sold stock. All seven stay finite,
buy-only and **no-refill**; none creates an operator-replenishment opt-in.

Players use the installed named exit, `+store`, **Buy items** (`1`), then the
full item name and quantity. `back`/`q` close the menu; the room's `back` exit
returns to the hub. `+inventory` and `+itemdex` inspect copies/information.
Medicine uses `+use` or existing manual `+item`; Ether/Max Ether select an
actual depleted move. Capacity items prompt for the real move. Vitamins and
ability items retain shared EV/native checks. Stones use `+evolve <full ID>
<stone>`. Held effects require `+hold 3=<item>` before an ordinary battle;
`+hold 3=` returns an uneaten reusable copy, never a consumed berry/Sash.

The [dated automated checks](testing/finite-item-sources-2026-10-25.md) cover
all 36 effects and transaction controls in disposable rooms. Shared release,
permanent stock and ordinary socket acceptance remain separate pending work.
