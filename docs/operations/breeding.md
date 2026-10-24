# Bounded breeding, eggs and hatching (#728)

## Player route and PF2 timing policy

Deposit two compatible hatched owned Pokemon through `+daycare`, then use:

```text
+breed check
+breed start
+breed
+breed collect CYCLE_ID
+breed hatch EGG_ID
```

`check` validates the pair without charging or revealing a random outcome. A new
cycle costs 500 existing trainer money and becomes ready after 30 wall-clock
minutes. Both parents have a 24-hour production cooldown from successful start.
Command spam, reconnect and repeated status/start do not advance time or reroll.
The parent's previous cycle history follows its Pokemon ID across new Daycare
stays and ownership changes. Daycare's separate deposit fee is unchanged.

Collect creates exactly the planned egg UUID in a free party slot, otherwise a
box. It releases the parents' active-cycle restriction while leaving them in
Daycare. The egg can hatch after another 20 wall-clock minutes in party or box.
Hatching changes `is_egg` on that same owned Pokemon; it grants no second creature,
EXP, items or currency. Hatch authority follows its current owner after consent
trading. Eggs cannot battle, fuse, enter Daycare as parents or use normal field
items. Their eventual moves/genetic state are chosen once at cycle creation.
The hatch records its current owner as original trainer and uses a PF2 friendship
baseline of 100. The original egg creator retains only the historical cycle plan,
not visibility into the recipient's later live Pokemon state.

`+breed cancel CYCLE_ID` deliberately stops an uncollected cycle and releases its
parents for retrieval. The spent fee and parent cooldown remain. Cancellation
retains the planned outcome/UUID as a historical record, creates no owned egg and
cannot be reversed into another roll or grant. Repeated cancellation/collection
and hatch requests return their recorded outcome or a clear closed-state refusal.
Interrupted writes roll back the entire charge, claim, collection or hatch; retry
uses the existing record. A full destination never evicts a party member.

These prices, guaranteed one-egg production, timing, cooldown, cancellation and
box hatching rules are deliberate PF2 beta policies. They do not reproduce picnic
odds, hatch-step grinding or PF1 credit mechanics.

## Supported inherited traits

Opposite-gender parents need a shared egg group; a single Ditto can pair with a
compatible non-Ditto. Undiscovered-group parents, two Ditto and eggs are rejected.
The ordinary mother's base evolution line supplies offspring species, or the
non-Ditto parent's line when using Ditto. Gen 9 incense babies do not require an
incense. [Compatibility and species reference](https://bulbapedia.bulbagarden.net/wiki/Pokemon_breeding).

Genetic IVs use three distinct inherited stats, or five with either parent's
Destiny Knot; each inherited stat chooses one parent. Remaining IVs roll 0–31.
[Destiny Knot reference](https://bulbapedia.bulbagarden.net/wiki/Destiny_Knot).
Power items guarantee the holder's corresponding genetic stat within that same
total; if both parents have Power items, one holder is selected.
[Power item reference](https://bulbapedia.bulbagarden.net/wiki/Power_item).
Hyper Training flags never replace stored genetic IVs during inheritance.
[Hyper Training reference](https://bulbapedia.bulbagarden.net/wiki/Hyper_Training).

An Everstone passes its holder's saved nature; two Everstones choose either
holder equally. Otherwise the nature is random.
[Everstone reference](https://bulbapedia.bulbagarden.net/wiki/Everstone).
The mother/non-Ditto parent supplies ability-slot inheritance: normal slots use
80/20 when two exist; a hidden slot passes at 60%, otherwise an ordinary slot is
chosen. Capsule/Patch changes to the saved native slot are respected; Ditto's
ability is irrelevant. [SV inheritance table](https://www.pokexperto.net/index2.php?seccion=switch/pokemon_escarlata_purpura/crianza).

Moves use explicit Gen 9 learnset codes: level-1 defaults, eligible level-up moves
both parents actively know, and eligible egg moves actively known by either.
The four-move limit prefers inherited egg moves, then shared level-up moves, then
defaults; alphabetical ties make the saved result deterministic. Older-generation
TM/HM/tutor inheritance and post-hatch Mirror Herb teaching are excluded.
[Egg move reference](https://bulbapedia.bulbagarden.net/wiki/Egg_moves).

## Intentional boundaries and helper audit

Only ordinary base forms with verified Gen 9 level-up data are enabled. Regional,
cosmetic/special inheritance and locked/battle forms are excluded before payment.
Nidoran families, Volbeat/Illumise, Indeedee, Rockruff special offspring and
Manaphy/Phione are explicitly outside this MVP. Foreign/ambiguous ability slots,
invalid genetics/natures and unknown move data require review, not a guessed egg.
No Pokeball inheritance, language/Masuda/Charm modifiers, hatch-speed abilities,
species-specific hatch durations or competitive breeding automation is promised.

The existing `pokemon/data/breeding.py` is reused for ordinary compatibility and
base-line species resolution. Its unconditional incense-baby mapping matches Gen
9; its incense comment is corrected. The old fixed special-mother mapping did
not represent random gender-counterpart outcomes, so the helper now rejects those
families and the MVP excludes them before payment. Two-Ditto and invalid-gender
acceptance are fixed in the helper as well. The durable service never adopts an
unsupported special-case result.

## Persistence and recovery

Cycle identity, both parent UUIDs, chosen traits, readiness/cooldown times and the
planned egg UUID are sealed together with the one charge. Parents retain canonical
Daycare placement and its exclusive claim; an active-cycle reference blocks
retrieval until collect/cancel. Collection and hatching use current ownership,
shared storage locks and canonical placement. Egg records retain scalar identities
after later release, so receipt replay cannot recreate a released creature.

Production-model tests separate ordinary commands, clock-controlled elapsed-time
fixtures, staff setup and injected faults. Fresh/upgrade/invalid-data migration
rehearsals remain isolated from game data. Live ordinary-player journeys and
deployment are recorded separately from these automated checks.

Staff use `audit_pokemon_breeding --cycle CYCLE_ID` for read-only inspection of
exact parent, plan, cooldown and egg/hatch identities. Recovery uses the owning
character's collect/cancel or current egg owner's hatch retry. Invalid custody
requires deliberate review; never delete cooldowns, reroll a paid plan or create
a replacement for a released egg. Terminal history survives later custody changes.
