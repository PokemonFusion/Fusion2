# Rage Candy Bar and Hopo Berry field equivalents (#778)

The later [four remedies/Muffin](remedy-recovery.md) use the same guarded field
boundary. This original two-item policy retains its dated scope.

Recorded before implementation, October 22, 2026. PF2 selects exactly two
non-plot **field recovery equivalents** through ordinary `+use`:

| Item | Selected effect | Reference price / category |
| --- | --- | --- |
| Rage Candy Bar | Cure one living owned Pokemon's major status; no HP restoration | 350 / Medicine |
| Hopo Berry | Restore up to 10 PP to one selected active move, respecting its boosted cap | 300 / Berries |

These are deliberate PF2 medicinal policies: Rage Candy Bar follows the modern
status-cure role specified by #778, rather than its older HP or story behavior;
Hopo adopts its selected 10-PP field function. Prices are PF2 reference values,
not claims about cartridge or current shop prices. The implementation records
these rules directly; no secondary reference is treated as runtime proof.

Use complete normalized names, for example:

```text
+inventory
+itemdex Rage Candy Bar
+use Rage Candy Bar=3
+use Hopo Berry=3/Water Gun
+use Hopo Berry=3/4
```

The last example selects actual active move slot 4; gapped slots are not
renumbered. A bare Hopo target cannot choose an arbitrary move. Shared field
checks require a fresh eligible owned party/current Fusion, no egg, battle or
reservation, exact unambiguous target and active move identity. Fainted targets,
healthy/no-status targets, full-PP moves and illegal/stale selections spend
nothing. A held copy is independent and cannot fund bag use.

Exactly one useful effect and one bag copy commit together under the existing
field medicine transaction. Selected PP recovery preserves PP Up/Max capacity;
status recovery clears persisted sleep/toxic counters as applicable. Failures
after real debit or effect/save, outer rollback and final-copy contention leave
no partial SQL/cache state. Preserve HP/genetics/EVs/level/EXP/friendship, held
effects and other moves. No cure of volatile battle effects is added.

Both additions are **field-only**: `+item` rejects them before reserving an
action; equipping Hopo does not invent an automatic held trigger. Current
held berries, the 32 battle recovery foods/berries, PP-capacity and field
medicine rules remain separate. No Darmanitan unlock, key/story use, lure,
wild capture bonus, crafting recipe or other new item is included.

Deliberate acquisition uses the existing shop/reward interfaces. An optional
Recovery Counter recipe may offer Rage Candy Bar at 350/stock10 and Hopo Berry
at 300/stock10, finite with no automatic refill. The actual normal `+store`
purchase, inventory/itemdex, use and SQL/reconnect routes must be tested from
empty bag stock. This reference content is not automatic live stocking or an
extension of #781's six-item location. Configured supply, local command/model
acceptance and released live walkthroughs (#782) remain distinct.
