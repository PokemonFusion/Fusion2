# Pokemon Fusion 2 Theme Foundations

Status: research compilation and decision aid, not approved PF2 canon.

This document gathers the theme material recoverable from Pokemon Fusion 1
(PF1), compares it with statements already made by Pokemon Fusion 2 (PF2), and
identifies the choices needed before a new PF2 theme guide can be written.

## How to Read This Document

- **Current PF2 fact** means the repository or implemented game currently says
  or enforces it.
- **PF1 legacy canon** means PF1 presented it as setting information. It is
  historical evidence, not automatically PF2 canon.
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

## PF1 Cosmology

The Kasei creation legend described a many-handed Creator that existed before
the universe. The Creator formed elemental forces, then created the "True
Legendaries." Conflict among those Legendaries unintentionally formed galaxies,
planets, and stars. Exhausted, they withdrew behind creation while the Creator
watched over them.

The text did not explicitly identify the Creator as Arceus or reconcile the
legend with later official Pokemon cosmology. It is best treated as an in-world
Kasei religious story unless PF2 deliberately chooses otherwise.

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

## PF2 Decisions to Make

The following decisions should be settled before publishing player-facing
canon.

### 1. World model

- Is PF2 set in Kasei, a revised Kasei, a new region, or a region-neutral hub?
- Is the wider world modern Earth, the franchise Pokemon world, or an original
  Pokemon-inspired continuity?
- Which official regions, characters, organizations, and events exist?

### 2. Fusion ontology

- Is fusion spiritual, biological, technological, or deliberately mysterious?
- What happens to each participant's mind, memories, and agency?
- Does a permanent fusion remain one person, become a new person, or contain
  two cooperating identities?
- Can all humans and Pokemon fuse, or only some?
- Can trauma block fusion, and should that remain lore rather than a mechanic?

### 3. Consent and ethics

- What constitutes informed consent for temporary and permanent fusion?
- Can a Pokemon revoke consent?
- How does society distinguish partnership from coercion?
- Is artificial fusion always coercive, or can ethical technology exist?

### 4. Fusion society

- Are fusions commonplace, rare, or newly emerging?
- Are born fusions part of PF2?
- Are fusions legally full people everywhere, only locally, or not yet?
- Can a fusion own, train, or battle other Pokemon?
- Do the legacy appearance boundaries remain useful?

### 5. History and conflict

- Keep, revise, or discard the ancient fusion history?
- Keep, revise, or discard the Rocket war?
- If retained, how much does the old war shape present locations and factions?
- Should PF2 use franchise villains, original factions, or both?

### 6. Everyday setting

- Keep League Credits as a trainer-only economy?
- Keep PF1's ecological and transportation assumptions?
- Establish a default language model?
- Define technology level, education, government, healthcare, and Pokemon
  personhood.

### 7. Play tone and boundaries

- Is PF2 primarily cozy social RP, adventure, competitive training, dramatic
  conflict, or an explicit blend?
- What public content rating applies?
- Are private or adult-rated spaces part of PF2 at all?
- What consent tools and villain-play expectations should be formalized?

## Recommended Starting Direction

This is a proposal for discussion, not canon:

1. Preserve the heart of PF1: fusion is a consensual expression of a deep
   human-Pokemon bond, and fusions are people rather than property.
2. Make PF2's central play promise "shared life and adventure in a society
   where humans, Pokemon, and fusions coexist."
3. Use Kasei only after deciding whether PF2 is a continuation or reboot. A
   revised Kasei offers continuity; a new region offers freedom from timeline
   and franchise-character baggage.
4. Treat the creation legend as an in-world belief, not confirmed cosmology.
5. Retain the thematic contrast between bond-based fusion and coercive fusion,
   but reconsider whether Team Rocket specifically should own that history.
6. Define agency and consent before adding story content about permanent or
   artificial fusion.
7. Retain a flexible appearance spectrum, but replace the numerical 25 percent
   rule with clear examples unless a quantitative boundary proves useful in
   character approval.
8. Write a new, explicit PF2 safety and RP policy rather than adapting PF1's
   adult-area and staff-edict language.

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
  - 000 Muck Rules - Code of Conduct
  - Breeding
  - Villains Characters and You
- `legacy_pf1/game/data/std-db.db`, development-board theme drafts and change
  logs, including Theme Drafts 1 through 4.
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

