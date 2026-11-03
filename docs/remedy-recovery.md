# Remedies and Jubilife Muffin

Use these four field medicines from your bag on an eligible owned party member
or your current Fusion. Inspect the item with `+itemdex <name>` and the target
with `+party 3`, then use `+use <name>=3` or `+use <name>=fusion`.

| Item | Useful effect | Friendship cost on success |
| --- | --- | --- |
| Remedy | Restore up to 20 HP to a living target | 5 below friendship 200; 10 at 200+ |
| Fine Remedy | Restore up to 60 HP to a living target | 10 below 200; 15 at 200+ |
| Superb Remedy | Restore up to 120 HP to a living target | 15 below 200; 20 at 200+ |
| Jubilife Muffin | Cure one living target's major status | None |

Remedies retain the target's existing major status. Muffin preserves HP and
clears the same major statuses as the existing Full Heal equivalent, including
persisted sleep state. HP caps at the target's actual maximum; friendship caps
at zero on a penalty. Healthy/fainted/no-effect requests spend no bag copy and
apply no friendship cost. Exactly one useful use consumes one bag copy. A
separate held copy stays held.

These are field-only routes. `+item` does not queue them as battle medicine, and
equipping them adds no held effect. Existing owner, egg, box, battle, current
Fusion and reservation checks apply. Use complete item and target identities;
these four items do not accept a move selector.

PF2 selects the modern `GEN_7+` 20/60/120-HP amounts and the explicit bitter
friendship tiers in the pinned primary
[item effects](https://github.com/rh-hideout/pokeemerald-expansion/blob/8654616bd38d9b28cc7dd8f3d0b4cb030aa2d40c/src/data/pokemon/item_effects.h)
and [definitions](https://github.com/rh-hideout/pokeemerald-expansion/blob/8654616bd38d9b28cc7dd8f3d0b4cb030aa2d40c/src/data/items.h).
Reference prices are 150/150/750/250 respectively. They author metadata for
future finite supply review; no permanent public offer or stock is installed.
The [dated test receipt](testing/item-additions-2026-10-29.md) separates local
command/SQL evidence from live availability and deployment.
