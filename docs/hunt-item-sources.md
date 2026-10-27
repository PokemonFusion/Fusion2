# Bounded hunt acquisition (#779/#780)

These sources are **explicitly opt-in authored PF2 rules**. Default room and
species metadata grants no item. This reference does not edit live rooms or
populate the world.

## Potion finder

An authored hunting room may set `allow_hunting=True`, `noitem=False`,
`itemfinder_item="Potion"` and integer `itemfinder_rate=5` (percent). The only
accepted finder item is **Potion**, one bag copy per successful ordinary
`+hunt`. A rate without the named source no longer produces a phantom-item
message. Excluded/unknown items, malformed rate, `noitem`, disabled hunting and
failed rolls grant nothing; normal encounter resolution continues when no
item is found. A successful finder result replaces that hunt's encounter and
retains the existing no-training-point-charge behavior for finder outcomes.

The existing three-second hunt interval is reinforced by a persistent per-owner
finder receipt: server-created attempt identity/time, source room and result.
Claim and inventory credit commit together under owner/trainer locks. The same
attempt cannot grant twice; competing attempts inside the interval are refused,
including reconnects. New deliberate hunts after the interval remain valid.
Earlier attempt replay cannot replace a newer receipt. Only one latest receipt
is retained; old timestamp/identity checks prevent a growing receipt catalog.
Failed inventory/receipt writes leave no credit or claimed result. Public
success names the actual Potion and its inventory destination.

## Authored wild Oran Berry

One reviewed native source is **Rattata holding Oran Berry**:

```json
{"name":"Rattata","min_level":5,"max_level":5,"weight":1,
 "held_item":"Oran Berry","held_item_chance":5}
```

The item chance is a separate integer percent 0–100; omitted/zero means empty.
The room's `noitem` restriction also forces empty held state.
The authored 5% is a PF2 availability choice, not a cartridge distribution claim.
Only exact native Rattata/Oran Berry is accepted. Rattata-Alola, other species,
other items, plot items, Leader's Crest, partial names, booleans and string
chances remain empty. No bulk dex-derived tables, NPC loot, Thief expansion,
new capture mechanic or Crest qualification shortcut is added.

Selection reaches both the real wild runtime and EncounterPokemon SQL before
battle begins. An item-bearing encounter must have real persistent identity;
its creation failure cannot fall back to a phantom runtime. Existing complete
turn/checkpoint and capture paths preserve its **current** held state, including
explicit empty state after eating/removal. A consumed item never reappears on
rebuild or capture. Capture still uses existing legality/receipt/owner/placement
and rollback rules.

## Player acceptance and limits

Finder walkthrough: discover a deliberately configured hunting source ->
`+hunt` -> `+inventory` -> damage an eligible fixture through normal play ->
`+use Potion=3` -> SQL/reconnect. Verify exact one-copy credit, useful heal,
noitem/disabled/no-roll guards and post-write failure/replay/contention.

Wild walkthrough: ordinary `+hunt` -> actual encounter held item -> normal
capture -> party/held display -> `+hold <slot>=` -> bag -> useful
`+use Oran Berry=<slot>` -> reload. Include consumed/removed item, failed capture,
capture replay/post-save failure and empty/invalid source controls. Staff source
and capture-ball setup are separate evidence; neither items nor source rooms
are claimed live merely because these recipes exist. The six-offer supply
location (#781) and intentionally released walkthrough (#782) are separate.
