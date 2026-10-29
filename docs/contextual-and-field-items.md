# Contextual evolutions and field item effects

These are bounded player routes. Source recipes require an explicit selected
hub or reviewed existing location; importing a service installs nothing.
Authored activity entrances and return exits retain Evennia's base exit
security locks, including `call:all()` for command discovery. Retry refuses
missing public access instead of silently repairing existing content.

## Day and night evolution locations

Day Grove supplies `time_of_day=day`; Night Grove supplies `time_of_day=night`.
Their public entrances are `daygrove` and `nightgrove`, with `back` exits.
Equip a real held item using `+hold <slot>=<item>`, travel to the correct grove,
then use `+evolve <full ID>`:

| Native source | Held item | Context | Target |
| --- | --- | --- | --- |
| Happiny | Oval Stone | Day | Chansey |
| Sneasel | Razor Claw | Night | Weavile |
| Gligar | Razor Fang | Night | Gliscor |

The existing entries have no species-specific minimum level, so valid saved
levels 1–100 work. Evolution grants no level and consumes the held item only
on a committed success. Ownership, eggs, battle, placement, Fusion and other
reservations retain their existing guards. Native regional rules retain
precedence: Hisuian Sneasel keeps its distinct existing day branch. Its public
companion/source acceptance is outside this first three-species matrix.

Evolution reads the actual saved current room and its context, and locks the
character before storage so movement cannot race that lookup. A stale room
pointer cannot supply a missing day/night condition. Invalid saved levels
refuse before any evolution item is consumed.

Optional finite source authoring is `world/contextual_evolution_counter.json`:
Oval Stone 2,000×5, Razor Claw 5,000×5 and Razor Fang 5,000×5. It has no refill
or resale. Native companion availability and other regional/magnetic contexts
remain world-unverified.

## Soothe Bell

A genuine held Soothe Bell is reusable. It increases only the existing positive
friendship event from the six EV-reducing berries: pre-use base deltas 10/5/2
become 15/7/3, rounded down before the 255 friendship cap. EV removal, HP deficit,
no-effect conservation and ordinary field eligibility remain unchanged. A Bell
in the bag supplies no bonus. Current Fusion remains eligible; inactive forms
and other reservations do not.

For example, a native Golbat at friendship 153 gains seven from a useful EV
berry while holding a Bell, reaches the existing 160 threshold and can use
`+evolve <full ID>` to become Crobat. The Bell stays held. Herbal friendship
losses keep their existing values. No walking, level-up, hatch or battle
friendship service is introduced. Klutz and battle-only item suppression do not
erase this out-of-battle feeding condition.

Optional source authoring is `world/soothe_bell_counter.json`, finite 4,000×2.
Source installation is a separate operation.

## Mirror Herb teaching

At a server-configured Daycare (`is_daycare=True`), keep two owned hatched
ordinary party members with you. The recipient holds a Mirror Herb and has an
empty active move slot. Use:

```
+daycare herb 3=6/Wish
+daycare herb confirm
```

The first command reviews exact recipient/donor/move/slot/PP consequences.
Confirm within five minutes, or use `+daycare herb cancel`. A moved character,
changed held item, owner, species, move set, knowledge or PP invalidates the
review. There is no fee or waiting period to earn a move. The review expiration
only prevents an old confirmation from changing a newer state.

The donor must actually know the selected move in an active slot; zero PP is
allowed. Gender, species and Egg Groups need not match. The recipient's exact
native egg species must have that move marked `9E` in verified Gen 9 data.
The resolver follows validated pre-evolutions, including regional identities;
unknown, ambiguous, battle-only, CAP and custom data refuse. For example,
Umbreon uses Eevee egg data, while Alolan Ninetales uses Alolan Vulpix data.

One confirmation adds one learned move, one empty active slot and its matching
saved-set slot with ordinary new-move PP. It preserves the reusable Herb, donor,
existing PP, other saved sets and all unrelated resources. Already-known moves
use the normal moveset route and cannot refresh PP here. No egg is generated.
Both targets must remain outside battle, Fusion, other reservations and native
Necrozma move restrictions. Existing competitive Mirror Herb boost copying is
unchanged.

`MIRROR_HERB_DAYCARE` in `pokemon/services/daycare_teaching_location.py` provides
optional explicit Classroom authoring. A reviewed existing Daycare can supply
the same server-owned flag. Public item/donor acquisition and world placement
are separate from the prepared ordinary-party command acceptance.

## Amulet Coin and Luck Incense

Either genuine held item can qualify its trainer for double the existing
standard NPC trainer prize. Eligible initial/normal active entry or a completed
ordinary move while held records the condition with the battle's saved owner
and outcome identity. A benched-only holder does not qualify. Any number of
holders and both names together still give a maximum multiplier of two.

Receiving a Coin during one's own Trick requires later entry or an ordinary
move to qualify. Once earned, fainting or a later transfer away preserves the
condition. Restoring a battle grants no new participation from current gear.
Prize receipts seal the base amount, multiplier and earned participation; final
gear edits cannot create or erase an already recorded bonus. Retry pays the
same outcome once. Zero/loss behavior and the original NPC base formula remain
unchanged.

The first effect applies only to standard `static`/`random` NPC `TRAINER`
encounters. Wild, PvP/Multi, scripted/gym/Adventure prizes, Pay Day, first-clear
items, other currencies, fees, transfers and resale receive no new bonus.
Physical prize qualification is independent of Klutz/Magic Room/Embargo battle
suppression. Both items stay reusable and retain ordinary item-transfer rules.

Optional source authoring is `world/npc_prize_item_counter.json`, finite
10,000×1 for each item, with no refill or resale.
