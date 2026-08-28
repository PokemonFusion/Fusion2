# Pokemon Fusion 2 Theme Foundations

Status: PF1 carry-over research compilation and decision aid, not approved
PF2 canon.

This document gathers the theme material recoverable from Pokemon Fusion 1
(PF1), compares it with statements already made by Pokemon Fusion 2 (PF2), and
identifies the choices needed before a new PF2 theme guide can be written.

This is a preservation-first note. It records the recovered PF1 position before
PF2 revises, rejects, or replaces it, so later adjustments do not erase what the
older game actually said or implemented.

## How to Read This Document

- **Current PF2 fact** means the repository or implemented game currently says
  or enforces it.
- **PF2 working direction** means PF2 deliberately selected or strongly favors
  that direction, but it may not yet be implemented or published as final
  player-facing canon.
- **PF1 legacy canon** means PF1 presented it as setting information. It is
  historical evidence, not automatically PF2 canon.
- **PF1 coded rule** means the surviving MUF code confirms that PF1
  mechanically behaved that way. It is not automatically a PF2 balance or
  implementation requirement.
- **PF1 policy or tone** means a play guideline rather than an in-world fact.
- **Open decision** means PF2 has not established an answer in the inspected
  repository.

The guiding rule for future edits should be: preserve the useful identity of
Pokemon Fusion, but adopt no legacy detail accidentally.

## Current PF2 Baseline

The present PF2 repository establishes only a small theme baseline:

1. PF2 is a text-based multiplayer reimagining of the Pokemon world.
2. Players collect and train Pokemon, explore routes and towns, meet trainers,
   and battle in a persistent online world.
3. A fusion is an anthro Pokemon form made from a trainer and a Pokemon. It is
   explicitly not Pokemon-to-Pokemon splicing.
4. Temporary fusion is unlocked through a strong bond and later returns the
   Pokemon to the party or storage.
5. Permanent fusion requires a maximum bond. The source Pokemon becomes part
   of the character and is no longer returned as a separate Pokemon.
6. A character can leave a fusion form, retain permanently unlocked forms, and
   select among those forms later.

PF2 currently does **not** establish a named region, cosmology, historical
timeline, social status for fusions, origin of fusion, villain organization,
content rating, or detailed RP boundaries.

Current sources:

- `README.md`
- `web/templates/website/index.html`
- `world/help_entries.py`, topic `fusion`
- `commands/player/cmd_fusion.py`

## PF1 Core Premise

PF1 described an easygoing Pokemon setting centered on the Kasei Region.
Kasei had a Pokemon League, gyms and sub-gyms, settlements, wilderness, wild
Pokemon, friendly everyday life, and genuine danger. Characters could come
from many backgrounds, but unsupported claims of being the world's best or
otherwise uniquely important were discouraged.

Fusions were commonplace in Kasei and generally treated as people equal to
humans. They could not be owned or captured in Poke Balls. PF1 also allowed
people to be born as fusions rather than becoming one later.

PF1 presented Kasei as a haven and cultural melting pot for fusions. Other
parts of the world ranged from accepting to prejudiced, and some legal systems
did not recognize fusions as full equals.

### Thematic identity implied by PF1

- Partnership between humans and Pokemon is central.
- Fusion represents closeness, unity, identity, and transformation.
- Humans, Pokemon, and fusions share a world rather than occupying isolated
  gameplay categories.
- Everyday social RP and Pokemon adventure coexist.
- Acceptance versus exploitation is a recurring source of conflict.
- Player fun and story were valued above strict realism or rigid adherence to
  franchise source material.

## PF2 Population and Character Scope

### PF2 working direction: fusion remains central

PF2 will retain Fusion as its defining character concept rather than replacing
it with a separate general anthro population. The intended population remains
fundamentally humans, Pokemon, and fusions.

Fusion is a substantial inherited part of PF1's identity. It connects
human-Pokemon partnership, personal identity, battle participation, history,
and setting conflict rather than merely explaining anthro character
appearances. **Unrestricted non-Pokemon anthro species are outside the current
PF2 theme scope.** This also avoids expanding the setting and cosmology merely
to support a second anthro category.

### PF2 working direction: born fusions remain

Born fusions remain part of PF2 and provide the direct character fantasy of
playing an anthro Pokemon person without requiring a transformation-centered
concept.

- A born fusion is a person, not a catchable Pokemon.
- A born fusion may ordinarily present as strongly Pokemon-shaped or anthro.
- A born fusion does not have to acknowledge or roleplay a mechanically
  available human form as part of their normal identity.
- PF2 will not add a separate `anthro Pokemon` species category alongside born
  fusions.

Most ordinary Pokemon species should be available for born-fusion concepts
unless a specific lore or design reason requires restriction. The exact
restricted-species list and access policy remain future decisions.

## PF1 Fusion Lore

### Spiritual origin

PF1's formal theme library said humans and Pokemon are spiritually related,
like two sides of the same coin. Pokemon inherited elemental forms and powers;
humans inherited emotion, ambition, and will. Training together develops a
bond capable of reuniting those halves as a fusion.

Extreme physical or emotional trauma could interfere with fusion. A human,
Pokemon, or fusion might temporarily or permanently lose the ability to form
new fusions or change forms.

### Ancient history

In ancient civilization, fusion was treated as a blessed expression of the
friendship and equality between humans and Pokemon. As human societies became
more skeptical and treated Pokemon more like animals, fusions were increasingly
regarded as strange, shunned, or forbidden. Accepting communities eventually
formed or settled places such as Kasei.

### Modern society

PF1 said fusion had become more broadly accepted in modern times, although
acceptance and legal equality varied by country and demographic. Kasei
remained unusually welcoming.

### Born fusions

PF1 treated born fusions as established members of society. Its relationship
and reproduction documentation assumed that human/fusion and fusion/fusion
families could have human or fusion-born children. These details were written
for an older adult-oriented MUCK context and should not be inherited without a
separate safety, rating, and worldbuilding decision.

### Form boundaries

PF1 used a "25 percent rule": a fusion should appear at least 25 percent human
and at least 25 percent Pokemon. The intended range ran from a gijinka-like
person with obvious Pokemon traits to a strongly Pokemon-shaped but humanoid
being. The normal height range was three to nine feet, with staff-approved
exceptions.

This was an RP and character-design policy, not an explanation of fusion
biology.

#### PF2 working direction: descriptive appearance guidance

PF2 will not retain a mathematical 25/75 percent appearance requirement. A
fusion should recognizably incorporate both human and Pokemon characteristics,
with player and staff guidance expressed through descriptive examples rather
than measured percentages. Born fusions may lean substantially toward a
Pokemon or anthro appearance while remaining people and fusions rather than
ordinary Pokemon.

## PF1 Fusion Mechanics and Play Assumptions

PF1 connected its fusion fiction directly to a substantial coded ruleset. The
following combines its player-facing explanation with confirmed **PF1 coded
rules**. It is useful evidence for how PF1 understood fusion, but PF2 may
rebalance or replace it.

### Eligibility and bond

- Both trainer and Pokemon had to want the fusion on some level, consciously or
  otherwise.
- Temporary fusion required at least 140 Bond.
- Permanent fusion required the maximum 255 Bond.
- At 250 Bond, a temporary fusion could choose the trainer's or Pokemon's
  gender each time it fused. Below that threshold it normally used the
  Pokemon's gender. A permanent fusion made its gender choice once when that
  form was created.
- `Bond` was explicitly an OOC system measurement rather than a number people
  discussed in character. It represented togetherness and the ability to
  fuse.
- Winning a battle with a participating Pokemon and completing valid RP ticks
  raised Bond. A Pokemon matching the trainer's favored type received an extra
  point, and the current temporary fusion received an additional point.
- PF1 allowed unknown personal or plot factors to make fusion or unfusion
  easier, harder, or impossible even when the numeric requirements were met.

#### PF2 working direction: bounded, non-grind Bond progression

In character, Bond continues to represent the closeness and ability of a human
and Pokemon to unite. Out of character, PF2 Bond progression must not reward
command volume, RP text volume, repetitive battle farming, or unlimited grind
loops.

Bond may eventually advance through bounded, time-aware mechanisms such as
meaningful milestones, adventures, battles, or relationship events. The exact
formula is deliberately left for later system design. Whatever model is chosen
must remain consistent with PF2's horizontal, no-grind progression philosophy.

### Temporary and permanent forms

- A temporary fusion removed the Pokemon from the active party while the form
  was in use. Unfusing returned it to an open party slot or a storage box.
- The coded temporary-unfusion command failed if no party or storage position
  was available. The help permitted players to roleplay unfusing anyway, while
  warning that carrying more than six Pokemon outside a Pokemon Center violated
  League rules.
- Permanent fusion made the source Pokemon part of the character forever. That
  Pokemon could not be recovered later as a separate party member.
- Permanent forms remained available to the character, and the `+fusion`
  command allowed switching among retained forms.
- Fusion-born characters did not have to treat the system's available human
  form as part of their fiction. It existed for mechanical convenience.
- Fusion, unfusion, and form switching were blocked during battle. A Pokemon
  could not fuse while holding an item, carrying an egg, or otherwise locked by
  breeding. Form changes preserved the character's current proportion of HP.

### Combat bonus and participation

- A fused character could enter battle as a Pokemon combatant, lead with
  themselves, learn moves, and view the active form's Pokemon statistics and
  attacks.
- Fusion granted a 10 percent increase to Attack, Defense, Special Attack,
  Special Defense, and Speed over the corresponding Pokemon form.
- The fusion bonus did not apply to HP, Accuracy, or Evasion. The MUF stat
  routine returned those values before applying the five-stat multiplier.

The 10 percent increase is both a balance rule and an in-world claim. PF1's
help said that the increase was difficult for ordinary people to measure and
often went unnoticed except by skilled trainers.

#### PF2 working direction: drop the inherent stat bonus

PF2 will drop PF1's inherent 10 percent Fusion bonus. Fusion is a character
identity and participation mechanic, not a vertical power upgrade. A player
should not gain a competitive advantage merely because their trainer is fused;
this follows PF2's horizontal-progression philosophy.

### PF2 Combat Direction

**PF2 working direction:** A fusion may personally participate in Pokemon
battles as a Pokemon combatant, but doing so does not create an additional
combatant beyond the battle format's normal roster or participation limit.

- When a trainer fights personally as a fusion, the fusion occupies one of the
  side's normal combatant or party positions for that battle.
- A human or fusion trainer who does not fight personally may still use the
  normal number of Pokemon allowed by the format.
- Temporary fusion should use the source Pokemon's existing level, statistics,
  moves, ability, and related battle state wherever practical.
- Fusion changes who represents that Pokemon combatant, not how much combat
  power or roster capacity the player receives.

For a six-position format, this would mean six Pokemon for a trainer who stays
out of the battle, or the trainer's fusion form plus five Pokemon when the
trainer fights personally. The general rule is consumption of one normal slot,
not a universal requirement that every battle format use six positions.

### Fighter experience

PF1 tracked a trainer's Pokemon-like combat growth as Fighter XP (FXP):

- A temporary fusion used the lower total of the trainer's TXP or the source
  Pokemon's XP when determining its fighting level.
- Permanently fusing added one third of the source Pokemon's XP to the
  character's shared FXP pool.
- Every permanent form used that shared FXP total, but forms could have
  different levels because species used different growth rates.

#### PF2 working direction: do not restore Fighter XP by default

PF2 will not recreate Fighter XP merely for PF1 compatibility. Temporary
fusion should preferably rely on the source Pokemon's existing level,
statistics, moves, ability, and related battle state rather than introduce a
second progression calculation.

Progression for permanent fusions and born fusions remains an **open mechanical
decision** because those characters may not have an independent source Pokemon
record. This document does not select that progression model.

### Starting as a fusion

Character generation allowed a player to begin as a fusion rather than a human
trainer. A starting fusion received no separate starter Pokemon, selected an
approved fusion species, ability, nature, gender and initial moves, and divided
2,500 starting experience between TXP and FXP. The chosen species was stored as
a retained permanent form.

These exact thresholds, bonuses, XP conversions, and command limitations are
preserved here as PF1 history. They should be reviewed as game design rather
than silently carried into PF2 theme canon.

## PF1 Cosmology

The Kasei creation legend described a many-handed Creator that existed before
the universe. The Creator formed elemental forces, then created the "True
Legendaries." Conflict among those Legendaries unintentionally formed galaxies,
planets, and stars. Exhausted, they withdrew behind creation while the Creator
watched over them.

The text did not explicitly identify the Creator as Arceus or reconcile the
legend with later official Pokemon cosmology. It is best treated as an in-world
Kasei religious story unless PF2 deliberately chooses otherwise.

## PF1 True Legendaries and Slivers

PF1 distinguished the singular beings of legend from legendary Pokemon that
trainers could encounter, catch, own, and fuse with.

### The distinction

- A **True Legendary** was the unique, earth-shaking being behind a species'
  legends. True Legendaries were effectively uncatchable and ordinarily beyond
  the reach of trainers.
- A trainer could catch a Dialga, and exceptional trainers could even possess
  more than one, but they would not possess **the** singular Dialga of legend.
- Catchable legendary Pokemon were fragments or manifestations of a True
  Legendary's power. PF1 called them **slivers** in its clearest IC account.
- Other PF1 records described the same beings as aspects, reflections,
  mimicries, or splinters. The term **legendary avatar** was not found in the
  surviving database, help, or MUF files.

### Power and identity

Slivers were powerful Pokemon in their own right, but carried only a small
portion of the True Legendary's power. The surviving IC explanation used two
examples:

- a captured Dialga could not move freely backward and forward through time;
- a captured Jirachi could not grant wishes.

Legendary Beacon encounters were also explicitly described as aspects of the
greater Legendary rather than the unique being upon which the legend was
based. This allowed legendary species to participate in ordinary trainer play
without making every owner the captor of a singular godlike entity.

### Evidence strength

This distinction is supported by three complementary PF1 records:

1. The `News - IC` post **Recent Events in Kasei** called player-catchable
   legendaries fragments and slivers with only a small portion of a True
   Legendary's power.
2. The staff post **Theme notes from Yin** distinguished unique, uncatchable
   Legendaries from catchable aspects, reflections, or mimicries and used the
   multiple-Dialga example.
3. The public announcement **Award Market Beta!** applied the same distinction
   to legendaries summoned through regional Beacons.

The formal five-article Theme Encyclopedia established the Creator and True
Legendaries but did not include the sliver explanation. No dedicated
legendary-lore help topic or local wiki export supplied a competing account.
The board and IC news material therefore provide strong PF1 carry-over
evidence. The PF2 decision layer below records how that evidence will be used.

### PF2 working direction: retain True Legendaries and slivers

PF2 will retain the distinction and the term **sliver** rather than replace it
with `avatar`.

- True Legendaries are the singular beings behind the legends and are not
  ordinarily catchable or playable.
- Slivers are lesser fragments, aspects, manifestations, reflections, or
  offshoots of a corresponding True Legendary's power.
- Multiple slivers associated with the same True Legendary may exist.
- Slivers may be caught and owned as Pokemon where appropriate, and may
  participate in fusion.
- A sliver does not possess the True Legendary's unique world-altering
  authority. A Dialga sliver cannot freely control time, and a Jirachi sliver
  cannot simply grant wishes.
- A legendary-species fusion derives from a sliver, not from the True
  Legendary.

Capitalization is not the formal distinction. Player-facing language should
prefer constructions such as **True Mewtwo** and **Mewtwo sliver** rather than
attempting to distinguish `Mewtwo` from `mewtwo`.

### PF2 working direction: restricted concepts are horizontal unlocks

Most ordinary Pokemon species should be usable for born-fusion concepts unless
a specific lore or design reason requires restriction. Some unusual species
may require restricted-character approval or an account-level unlock.

Legendary or Mythical fusion characters, where allowed, represent slivers.
Access to a restricted or sliver species is a horizontal character-concept
reward: it grants new roleplay and identity options, not superior battle
strength. A veteran gaining access to such a concept should not receive an
automatic mechanical advantage.

A future policy may classify concepts as **Open species**, **Restricted
species**, **Legendary/sliver species**, or **Non-player concepts**. This note
does not define the lists or invent account-age, badge, League, or progression
requirements.

## PF1 Science and Artificial Fusion

PF1 combined spiritual and scientific explanations without resolving them.
Modern science found strong genetic similarity between humans and Pokemon but
could not fully isolate or explain fusion. Genetic experiments tended to end
badly.

Kasei outlawed technology designed to manipulate fusion after Team Rocket used
an artificial-bond machine to force immediate fusions. Research in this field
carried strict penalties, while criminal organizations continued pursuing it.

This gives PF2 a useful thematic distinction:

- consensual, bond-based fusion as partnership;
- forced or engineered fusion as exploitation.

That distinction is strongly present in PF1, but PF2 has not yet made it canon.

## PF1 Team Rocket History

PF1's final theme library described the following sequence:

1. Giovanni visited Kasei approximately sixty-five years before the setting's
   present and saw the military potential of fusions.
2. Team Rocket built a secret research headquarters in Chugoku, north of
   Kasei, and kidnapped fusions from northern Kasei.
3. After five years, Rocket scientists created a machine that forged an
   artificial bond and allowed forced immediate fusion.
4. Rocket fused powerful Pokemon with grunts, built an army, and invaded
   Kasei, occupying much of the north.
5. An unidentified hero infiltrated the headquarters. The hero and Giovanni
   disappeared after their confrontation.
6. Kasei's adventuring teams and strongest trainers drove Team Rocket back.
7. Executive Thorn later led Team Rocket. A Neo Genesis faction believed
   Giovanni would return.

This is extensive PF1-specific continuity. Neither Kasei nor this Team Rocket
history currently appears in PF2's setting-facing material.

## PF1 Everyday World Assumptions

### Economy

PF1 separated ordinary money from Pokemon League Credits. Ordinary wealth
could buy normal lifestyle goods, while trainer supplies used League-regulated
Credits. This kept rich and poor characters mechanically level at the start of
their Pokemon journeys.

### Transportation and environment

Local travel favored walking, bicycles, small electric personal transport,
public transit, and Pokemon abilities. Sea and air handled travel between
regions. Large gasoline vehicles were discouraged because Pokemon-dependent
society valued ecological health.

### Language

PF1's default assumptions were:

- ordinary humans generally could not understand ordinary Pokemon;
- permanent and born fusions generally could understand Pokemon in any form;
- temporary fusions could understand Pokemon while fused;
- Pokemon understood human communication to varying degrees;
- fusions could speak human or Pokemon languages;
- character-specific exceptions were allowed when useful for story and noted
  for RP partners.

### Trainers and fusion abilities

PF1 board drafts suggested that fusion trainers could train their own Pokemon
abilities and develop finer control or distinct uses suited to a partly human
body. This idea appeared in discussion material but was not found in the final
five-article theme library, so its canon status is weaker.

## PF1 RP Tone and Governance

PF1 called its theme easygoing and favored plot and fun over strict realism.
That flexibility existed alongside concrete social rules:

- The overall public-space rating was PG-13, with separately restricted adult
  spaces in PF1.
- Players were expected to stop behavior that made others uncomfortable.
- Rivalries required the other player's agreement and could not become OOC
  conflict.
- Public violence, gore, nudity, and language were limited by the rating.
- Villains were expected to generate meaningful RP, have coherent motives,
  accept losses, keep IC conflict separate from OOC behavior, and contribute
  to shared stories rather than indulge in consequence-free disruption.
- PF1's villain approval and one-villain-per-player procedures were operational
  policies, not setting truths.

The valuable theme principle is collaborative, consent-aware storytelling.
The old enforcement model and adult-area model require a fresh PF2 policy
decision.

## Conflicts and Reliability Problems in PF1

PF1's material should not be copied as a single internally consistent canon.

### Ancient fusion versus modern first appearance

The formal history says fusion was known in ancient civilization. The general
theme help says fusions first appeared in the late 1950s or early 1960s. Both
cannot be literally true without an explanation such as fusion disappearing
and re-emerging.

#### PF2 working direction: ancient fusion and modern rediscovery

Fusion is ancient. Its knowledge and practice later became rare, hidden,
suppressed, forgotten, or culturally marginalized across much of the wider
world. The mid-20th-century development was a modern public rediscovery or
renewed recognition, not the first fusion in history.

The exact cause of fusion leaving common awareness remains open, as does the
precise calendar year of its modern return.

### Timeline ambiguity

The technology article refers to a Team Rocket war sixty years ago, while the
Rocket article begins Giovanni's involvement sixty-five years ago and includes
five years of research. This may be intentional arithmetic, but PF2 would need
a defined present year or a relative chronology that does not age poorly.

### Franchise and real-world references

The legacy text directly invokes Japan, Chugoku, Giovanni, Team Rocket, the
Pokemon fandom, modern countries, Nigeria, and recognizable modern transport.
PF2 must decide whether it is an alternate modern Earth, a self-contained
Pokemon world, or a looser social RP setting.

### Cosmology status

The creation story is presented as a Kasei legend, while the fusion-origin
article sometimes speaks as objective truth. PF2 must distinguish religious
belief, historical consensus, scientific theory, and authorial fact.

### Consent and personhood questions

PF1 strongly opposed forced fusion but did not consistently explain whose
mind, agency, memories, and consent persist in temporary or permanent fusion.
PF2's permanent-fusion mechanic consumes the separate Pokemon record, making
this an essential theme question rather than optional flavor.

### Dated material

Some wording, identity terminology, sexual content, staff authority language,
and social assumptions reflect PF1's era. They should remain historical source
material only and should be rewritten or rejected through a modern safety and
inclusion review.

## PF2 Decision Status

This section separates selected **PF2 working directions** from questions that
remain genuinely unresolved. Working directions are not claims of current
implementation or final published canon.

### Working directions already chosen

- Fusion remains PF2's central concept, with humans, Pokemon, and fusions as
  the fundamental population. PF2 is not adding an unrestricted non-Pokemon
  anthro category.
- Born fusions remain and support anthro-Pokemon character concepts without
  requiring transformation-focused identities.
- Fusions are people, cannot be owned or captured, and may train Pokemon or
  personally battle as Pokemon combatants.
- Personal fusion participation consumes one normal combatant slot and grants
  no extra roster capacity.
- PF2 drops PF1's inherent 10 percent fusion stat bonus.
- Temporary fusion should reuse the source Pokemon's battle profile wherever
  practical. PF1 Fighter XP will not return merely for compatibility.
- Bond remains the thematic expression of closeness, but its OOC progression
  must be bounded and resistant to command, text, or battle spam.
- PF2 retains singular True Legendaries and lesser slivers, keeps the term
  `sliver`, and treats legendary-species fusions as sliver-derived.
- Restricted and sliver character concepts are horizontal identity options,
  not superior combat choices.
- PF2 replaces PF1's numerical appearance rule with descriptive guidance while
  keeping recognizable human and Pokemon characteristics.
- Fusion is ancient and later underwent modern public rediscovery or renewed
  recognition.
- Consensual, bond-based fusion remains partnership; coercive fusion remains
  exploitation.

### Genuinely unresolved decisions

#### World model

- Is PF2 set in continued Kasei, revised or rebooted Kasei, a new region, or a
  region-neutral hub?
- Is the wider world the official Pokemon world, an alternative continuity, or
  a setting with real-world geography?
- Which official regions, characters, organizations, and events exist?

#### Fusion consciousness and identity

- How much consciousness does each participant retain?
- Is the fused mind one consciousness, two cooperating identities, or variable?
- How are memories shared, who controls the body, and can the participants
  communicate internally?
- Do the answers differ among temporary, permanent, and born fusions?
- Can all humans and Pokemon fuse, or only some?
- Is fusion fundamentally spiritual, biological, technological, some
  combination of these, or deliberately mysterious?
- Can trauma block fusion, and should that remain lore rather than a mechanic?

PF1 draft evidence allowed the answers to vary, but that draft is not promoted
to PF2 canon.

#### Consent details

- What constitutes informed consent for temporary and permanent fusion?
- Can either participant revoke consent, and what happens if consent changes
  during fusion?
- How should society identify and respond to coercion?

#### Permanent fusion

- What happens to the source Pokemon's independent consciousness and
  personhood?
- Is permanent fusion metaphysically irreversible, or could extraordinary plot
  circumstances reverse one?
- How should permanent-fusion combat progression work?

#### Cosmology

- Is PF1's complementary human-Pokemon creation explanation objective truth,
  a religious belief, or one cultural explanation among several?
- Is the Creator Arceus?

The creation legend remains distinguishable from established physical fact.

#### Team Rocket history

- Should PF2 preserve PF1's Rocket war, revise it, or replace some or all of it
  with original factions?
- If retained, how much does the war shape present locations and institutions?

#### Artificial fusion

PF2 retains the thematic distinction between consensual bond-based fusion and
coercive forced fusion. It remains open whether all fusion-related technology
is inherently unethical, only coercive manipulation is unethical, or ethical
technological assistance can exist.

#### Progression and restricted-concept policy

- What progression model should permanent and born fusions use?
- What bounded Bond formula should PF2 implement?
- Which species belong in Open, Restricted, Legendary/sliver, and Non-player
  classifications?
- What approval or account-level unlock process should restricted concepts use?

No exact account-age, badge, League, or progression requirements are selected
here.

#### Society and everyday setting

- How common are temporary, permanent, and born fusions in different places?
- How consistently does the wider world's law recognize fusions as full people?
- Should PF2 keep League Credits, PF1's ecological and transportation
  assumptions, or its default language model?
- What are the setting's technology, education, government, healthcare, and
  Pokemon-personhood assumptions?

#### Play tone and boundaries

- Is PF2 primarily cozy social RP, adventure, competitive training, dramatic
  conflict, or an explicit blend?
- What public content rating and consent tools apply?
- Are private or adult-rated spaces part of PF2?
- What villain-play and player-conflict expectations should be formalized?

## PF2 Working-Direction Summary

The current working direction, still distinct from implemented or published
canon, is:

1. Retain Fusion as PF2's defining character concept.
2. Retain born fusions for anthro-Pokemon character concepts without adding a
   separate anthro race.
3. Keep unrestricted non-Pokemon anthros outside the core setting scope.
4. Keep fusion consensual and bond-based; coercive fusion remains exploitation.
5. Treat fusions as people who cannot be owned or captured.
6. Allow fusions to train Pokemon and personally participate in Pokemon
   battles.
7. Make personal fusion participation consume one normal combatant slot.
8. Drop PF1's inherent 10 percent fusion stat bonus.
9. Do not restore Fighter XP unless later implementation demonstrates a genuine
   need.
10. Replace grindable Bond advancement with bounded PF2-compatible progression.
11. Retain the True Legendary/sliver model and `sliver` terminology.
12. Treat restricted and sliver character access as horizontal progression,
    not increased battle power.
13. Replace the numerical appearance rule with flexible, recognizable human
    and Pokemon characteristics.
14. Treat fusion as ancient, followed by modern public rediscovery or renewed
    recognition.
15. Leave consciousness, permanent-fusion metaphysics, Kasei continuity,
    Rocket history, artificial-fusion details, objective cosmology, and
    permanent/born progression for later decisions.

## Proposed Canon Deliverables

Once the decisions above are made, split approved material into smaller,
player-readable documents:

1. **Theme at a Glance** - the one-page premise, tone, and character promise.
2. **The World** - region, society, technology, economy, and travel.
3. **What Is Fusion?** - ontology, forms, agency, consent, and appearance.
4. **History and Beliefs** - chronology, legends, factions, and disputed facts.
5. **Character Guidelines** - allowed origins, power scale, born fusions, and
   special concepts.
6. **RP and Safety Guide** - rating, consent, conflict, villains, and public
   versus private boundaries.

## Source Inventory

### PF1 primary sources

- `legacy_pf1/game/data/std-db.db`, object `themeobject` (`#1454`):
  - Creation Legend
  - Origin of Fusion
  - History of Fusion
  - Fusing and Technology
  - Team Rocket
- `legacy_pf1/game/data/std-db.db`, help object containing:
  - A Theme by any other Theme!
  - Commands 00 - Fusion Basics
  - 000 Muck Rules - Code of Conduct
  - Breeding
  - Villains Characters and You
- `legacy_pf1/game/data/std-db.db`, development-board theme drafts and change
  logs, including Theme Drafts 1 through 4, Theme notes from Yin, and the
  Fusion: Overview and Fusion: Clothing drafts.
- `legacy_pf1/game/data/std-db.db`, `News - IC` post Recent Events in Kasei,
  containing the clearest definition of legendary slivers.
- `legacy_pf1/game/data/proto.new`, Announcements post Award Market Beta!,
  applying the True Legendary distinction to Beacon encounters.
- `legacy_pf1/game/muf/43.m`, `48.m`, `64.m`, and `87.m`: character creation,
  stat calculation, RP-tick Bond awards, and fusion/unfusion implementation.
- `legacy_pf1/game/data/help.txt`: generic ProtoMUCK help; it explains the help
  system but does not contain Pokemon Fusion setting canon.
- `legacy_pf1/game/data/news.txt`: contains only `No news is set.`

No local PF1 wiki export was found in the inspected workspace. The database
objects above appear to be the strongest surviving primary source.

### PF2 primary sources

- `README.md`
- `web/templates/website/index.html`
- `world/help_entries.py`
- `commands/player/cmd_fusion.py`

