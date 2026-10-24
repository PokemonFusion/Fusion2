# Native Necrozma combinations

This route is undergoing local acceptance for #825–#830. Released-build
acceptance is tracked separately in #831; it is not deployed by these docs.

Bring your own **base Necrozma and Solgaleo or Lunala** to a Pokémon Center.
Remain in human form and finish any battle or conflicting activity first.
Both sources must be conscious native non-eggs belonging to this character.
Combining is free and reusable. It needs no story item, quest, Ring or currency.
This is separate from your trainer's `+fuse` route.

| Sources | Host form | Temporary source move | Matching held crystal and Z signature |
| --- | --- | --- | --- |
| Necrozma + Solgaleo | Necrozma-Dusk-Mane | Sunsteel Strike | Solganium Z → Searing Sunraze Smash |
| Necrozma + Lunala | Necrozma-Dawn-Wings | Moongeist Beam | Lunalium Z → Menacing Moonraze Maelstrom |

```
+necrozma
+necrozma inspect 3
+necrozma combine 3=5/2
yes
+necrozma separate 3
yes
```

The example puts the form move in actual move slot 2 and reserves the companion
from party slot 5. Party slots retain their gaps. Boxed sources use their full
owned UUID in place of a party slot; names and nicknames are not selectors.
Use `+box`, `+pokemon <UUID>` or `+necrozma inspect <UUID>` to inspect your sources.

Review both identities, current placements, held items, chosen move slot,
displaced move's PP and return rules before answering **yes** or **no**. Reviews
expire after five minutes. A changed target, location, item, move or source
state requires a new review. After reconnecting, `+necrozma` lists your pending
reviews; `+necrozma review <request UUID>` reopens one.

Necrozma keeps its own identity, genetics, nickname, held item and progression.
The companion remains a second owned Pokémon. It can be inspected, and appears
in the owned count, but cannot battle, receive items or training, learn moves,
move into party/boxes, enter Daycare, transfer, release or become your trainer's
Fusion until separation. Its held item and all saved state remain its own.

The host can heal, use existing PP and training items, gain EXP, and change its
held item. Ability, species, moveset/slot, ownership, trainer-Fusion and placement
changes require separation. Earned base Necrozma level-up knowledge is stored;
active moves and learning prompts wait until separation.

The form move starts with base PP 5 on its first legitimate introduction. Later
cycles restore its saved PP, including zero. PP Up/Max bonuses persist. Ether,
Elixir, Leppa and healing affect active moves; neither a dormant form move nor
the displaced move can be healed while hidden. Separation restores only the
chosen displaced move and its saved PP, or its original empty gap. It retains
other moves' current PP and the host's current health, status and progression.
A fainted or statused host can separate without being healed first.

A party companion returns to its previous slot if free, then the first free
slot, then a box. A previously boxed companion prefers its previous box if it
still exists. Occupants are never evicted and party gaps are never compacted.

In human Wild, Trainer and PvP singles or two-controller doubles, use ordinary
attacks/items/flee or the matching existing [Z signature](z-moves.md). The crystal
is reusable; normal Z prevention, one source PP and one use per side apply.
Switching, fainting, revival, reconnecting and ending battle preserve the native
pair. Only explicit field separation releases the companion. This initial
route excludes Mega, Tera, Dynamax, Ultra and four-controller Multi Battles.

The feature adds no source Pokémon, spawn chart, shop, crystal, live stock or
plot content. Availability depends on the world's existing authored sources.
