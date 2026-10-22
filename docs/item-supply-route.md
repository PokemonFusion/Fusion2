# Optional six-item supply location (#781)

The versioned [recipe](../world/item_supply.json) authors **Item Supply Corner**,
reachable through a labeled **supplies** exit at one explicitly selected public
hub, with **back** returning to that hub. Its room sign explains `+store`,
inventory/itemdex, medicine/berry/food use, Fire Stone evolution, held effects
and Smoke Ball escape. Coordinate broader guidance with #731.

| Item | Selected PF2 price | Initial stock |
| --- | --- | --- |
| Potion | 300 | 20 |
| Oran Berry | 80 | 20 |
| Fresh Water | 200 | 20 |
| Fire Stone | 3,000 | 5 |
| Leftovers | 4,000 | 2 |
| Smoke Ball | 4,000 | 2 |

These are deliberate authoring values, not global catalog prices. Stock is
finite, with **no automatic refill or player resale**. Buy-only policy keeps
this bounded source independent of the older sale/restock system. A later
refill or price/content change needs explicit content review; rerunning setup
never grants inventory or resets sold stock.

## Explicit builder setup, separate from normal play

`ItemSupplyRoute.recipe()` validates all six full definitions, positive prices
and quantities before writing anything. `ItemSupplyRoute.install(hub)` is an
explicit setup operation for an authorized builder, **never a startup hook**.
Supply an actual reviewed public hub object; no implicit dbref or existing
Adventure setup is reused. Example builder expression, after separate approval
to configure that environment:

```python
from pokemon.services.item_supply import ItemSupplyRoute
ItemSupplyRoute.install(here)
```

One transaction/advisory lock protects concurrent installation. A tagged route,
hub receipt and exact linked exits prevent duplicate locations. Repeating the
same valid setup returns the existing room without touching current stock or
characters; conflicting hub/entrance/receipt/exits fail for review. It neither
duplicates Alpha Meadow nor changes first-clear rewards, Crest qualification,
Candy/PP/training sources, Mega/Z or farming. No migration is required.

Normal players need no staff permission: enter `supplies`, read its sign, use
`+store` -> Buy -> `<item> <quantity>`, then leave through `back`. Money, stock
and bag credit use the atomic purchase service (#813), including failed writes,
insufficient funds/stock and competing customers. Each item's useful normal
field/evolution/held/escape route must be verified separately; buying or owning
an item alone is not effect acceptance.

The local walkthrough uses tagged disposable hub/shop/player fixtures and
separate setup evidence. A source recipe is not current live stock. Existing
human characters, the running world, deployment/restarts and released live
acceptance remain outside installation tests and are handled separately in #782.
