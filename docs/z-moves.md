# Z-Moves

Each of the 18 generic crystals accepts one reviewed damaging source in the
[current matrix](design/z-crystals.md). For example **Normalium Z + an actual
active Tackle slot → Breakneck Blitz**, 100-power Physical Normal damage. Other
source moves, status moves and signatures remain deferred. These are bounded
routes; holding a crystal does not enable every move of its type.
[Acceptance](testing/z-core-2026-10-23.md).

Equip your reusable crystal with `+hold <party slot>=Normalium Z`. During battle:

```
+zmove
+zmove Tackle=B1
+zmove 4=B1
+zmove A2 Tackle=B1
```

The first command shows current choices, real gapped move slots, remaining PP
and side use without choosing an action. Select a displayed slot or full move
name. Doubles require your acting A1/A2 or B1/B2 label. Target labels refer to
current battle slots. `+zmove` queues your one move; wait for the other actors.

Each side gets one activation per battle. Sleep and other normal move
prevention spend no Z use or PP. After the move begins, one source PP is spent,
including under Pressure, immunity or protection. Protect quarters otherwise
effective damage; it does not grant ordinary contact retaliation. The source
move, crystal, species and ability stay yours. Switching, revival and reconnects
do not refill the side use. A new battle starts a fresh budget.

Use native owned party members or your current Fusion in existing human
Wild/Trainer/PvP singles and two-controller doubles. Same-Pokémon Mega/Tera/Z
stacking is unavailable; different allies have separate mechanic budgets.
Holding any Z-Crystal prevents Terastallization. Klutz, Embargo and Magic Room
do not disable activation of the actual matching crystal.

An optional Z-Crystal Counter recipe supplies one of each accepted generic crystal for 10,000 each,
without automatic refill. It must be deliberately installed at a chosen hub;
this change does not add shops or stock to a running world. The published
evidence uses disposable PostgreSQL and production commands with a captured
player transport. Live deployment and socket acceptance are separate.
