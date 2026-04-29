# Combat Items

This document defines the held-item policy for Fusion2 combat.

## Scope

Fusion2 uses a battle-first item policy:

- Keep held items that add clear tactical value in battle.
- Treat battle-runtime behavior as supported only when it is covered by battle-level tests.
- Defer or omit low-value canon baggage that does not improve MUD combat.

## Core Held Items

These item families are part of the supported combat surface and should keep battle coverage:

- Sustain and recovery: `Oran Berry`, `Sitrus Berry`, `Aguav Berry`, `Berry Juice`, `Leftovers`, `Black Sludge`
- Simple offensive and defensive staples: `Life Orb`, `Focus Sash`, `Assault Vest`, `Eviolite`, `Choice Band`, `Choice Scarf`, `Choice Specs`
- Readable tactical triggers: `Air Balloon`, `Rocky Helmet`, `Absorb Bulb`, `Cell Battery`, `Luminous Moss`, `Snowball`
- Terrain triggers when terrain support is active: `Electric Seed`, `Grassy Seed`, `Misty Seed`, `Psychic Seed`
- Type-resist berries when the one-shot super-effective trigger is implemented and tested
- Identity items only when their move or species mechanic is already supported: Plates, Memories, Drives, Natural Gift berries, Red/Blue Orb, forced-forme items

## Deferred Or Omitted

The following categories are not worth chasing for combat completeness unless a later feature explicitly needs them:

- Legacy transformation items for unsupported systems, including most Mega and Z-era item sets
- Mail, Apricorns, fossils, shards, and other non-combat inventory clutter
- Capture-only items in combat scope
- Redundant incense or one-off generational gimmicks that do not add meaningful battle decisions

## Support Rule

An item callback existing in `pokemon/dex/functions/items_funcs.py` is not enough to claim support. An item is only considered implemented when:

- the battle engine can reach its runtime hook through normal combat flow, and
- there is a battle-level test that proves the trigger, effect, and one-shot state handling work.
