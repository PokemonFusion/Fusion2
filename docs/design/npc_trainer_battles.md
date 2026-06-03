# NPC Trainer Battle System

This document is a design reference for future NPC trainer battle work. It is
not an implementation plan for one single patch. The main rule is that every
NPC trainer source should resolve into the same battle-ready encounter shape
before entering the battle engine.

## Goals

- Support PF1 parity without copying PF1's MUF property layout.
- Replace hardcoded trainer generation, including the current level 5
  Charmander trainer path.
- Support random trainer encounters, static NPC trainers, staff-forced battles,
  gym leaders, gym followers, and future event/story trainers.
- Keep the battle engine clean by feeding it battle-ready encounter data.
- Avoid progression grind loops and battle-spam rewards.
- Keep the system compatible with future AI profile work and the planned safe
  AI DSL.

## Non-Goals

- Do not implement a full visual NPC editor immediately.
- Do not port PF1 property structures directly.
- Do not make random trainers permanent database rows unless explicitly needed.
- Do not make gym follower battles mandatory grind chains by default.
- Do not make NPC trainer battles a major infinite XP/TXP farming loop.
- Do not implement advanced AI scripting in the first pass.

## PF1 Lessons

PF1 had several trainer-battle entry points, but they all tried to create a
battle with AI-controlled trainer data.

Random minor trainers came from hunt rolls. A hunt checked item and NPC rates,
looked at room trainer tables, selected a trainer class by weight, generated a
trainer roster, marked the battle as an NPC/AI battle, stored trainer display
names, and charged TP. The useful idea is not the room property layout; it is
that area configuration chose a trainer class, then a generator produced a
battle-ready trainer and team.

Staff-forced battles existed through commands similar to `+npcforce` and
`+npcforce/room`. Staff could select a trainer class, force one player into an
NPC trainer battle, or apply the same flow to eligible players in a room.

Static placed NPC battle support existed, but PF1's own source treated it as
less settled than the generated trainer path. It checked whether a target was a
placed NPC and could build a battle from that NPC's stored Pokemon data, but the
comments around that path suggest it was not the strongest foundation.

The strongest reusable PF1 idea is the NPC maker/class system:

- trainer class
- tier
- AI level
- gender ratio and name pools
- team size by tier
- Pokemon filters or species pools by tier
- generated trainer identity
- generated roster
- moves, levels, items, IVs, EVs, and battle metadata

PF2 should copy the architecture idea, not the literal MUF implementation.

## Current PF2 Gap

PF2 already has the beginning of this surface, but it is not content-complete.

- `+hunt` can currently roll `npc_chance` and start a trainer battle through
  `world.hunt_system.HuntSystem`.
- Random trainer generation now resolves through the shared trainer encounter
  service instead of the old fixed Charmander path. The compatibility wrapper
  `pokemon.battle.pokemon_factory.generate_trainer_pokemon` still exists for
  older callers.
- `NPCTrainer` and `NPCPokemonTemplate` models exist, but they may not have seed
  data in a given database.
- Static NPC trainer battles can resolve existing `NPCTrainer` and
  `NPCPokemonTemplate` rows into a shared `TrainerEncounter`.
- Multi-Pokemon static trainer battles are implemented. Battle startup carries
  the full `TrainerEncounter.team`, the first ordered template starts active,
  reserves are sent out automatically when the current NPC Pokemon faints, and
  the player wins only when the NPC roster has no usable Pokemon left.
- Reserve send-out is currently automatic battle-engine behavior, not strategic
  trainer AI switching.
- Gym leader proof-of-concept battles are implemented through
  `GymLeaderProfile`, linked static `NPCTrainer` rows, and the shared
  `TrainerEncounter` pipeline. Winning a gym leader battle grants the linked
  `GymBadge` once through the existing `Trainer.badges` storage.
- Django admin can create and edit `GymBadge`, `NPCTrainer`,
  `NPCPokemonTemplate`, and `GymLeaderProfile`; `NPCTrainer` exposes template
  Pokemon inline for content setup.
- Staff check commands warn about teams over six templates and unknown template
  move names.
- `Team` remains capped at six slots.
- Full gym progression, leader reward profiles, rematch/cooldown policy, gym
  followers, richer reward profiles, and AI DSL behavior are still future work.

## Core Architecture

All NPC trainer battle sources should resolve into a shared service/dataclass
concept before battle startup. The exact class name can change during
implementation, but the design intent should remain stable.

Suggested concept:

```python
@dataclass
class TrainerEncounter:
    display_name: str
    trainer_class: str
    source_type: str
    battle_format: str
    ai_profile: str
    team: list[BattleReadyPokemon]
    reward_profile: RewardProfile
    ruleset: BattleRuleset
    intro_text: str
    victory_text: str
    defeat_text: str
    metadata: dict[str, object]
```

Suggested `source_type` values:

- `random`
- `static`
- `staff_forced`
- `gym_leader`
- `gym_follower`
- `event`

The battle engine should not care whether an encounter came from a hunt roll, a
room-placed NPC, a staff command, a gym leader, or an event script. It should
receive a battle-ready trainer encounter with resolved display text, resolved
team, resolved AI profile, and resolved reward/rules metadata.

## Random Minor Trainers

Random minor trainers should be generated from profiles, not from a single
hardcoded Pokemon.

Possible profile model names:

- `NPCTrainerClass`
- `TrainerEncounterProfile`
- `RandomTrainerProfile`

A random trainer profile should define:

- trainer class
- tier
- team size min/max
- level min/max or scaling policy
- AI profile
- species pool
- type filters
- area tags
- name list
- reward profile
- enabled flag
- encounter weight

Random trainers should usually be ephemeral and generated when needed. The
profile is persistent; the individual trainer and roster usually do not need to
be persistent beyond the battle and audit/debug records.

Room or area encounter tables should eventually support weighted trainer
classes, for example:

```text
Hiker: 40
Backpacker: 30
Ace Trainer: 10
None: 20
```

For alpha, this can start simple:

- a small number of global trainer classes
- a basic level range from the room or spawn profile
- one or two Pokemon per trainer
- modest no-frills rewards
- no visual editor

## Static Feature NPC Trainers

Static feature trainers should use or extend `NPCTrainer` and
`NPCPokemonTemplate`.

Static NPC trainers should support:

- name/display name
- trainer class/title
- battle role
- battle format
- AI profile
- intro/victory/defeat text
- rematch policy
- reward profile
- team templates
- enabled flag
- optional room placement or activation hooks

Use cases include:

- story NPCs
- staff-run NPCs
- placed room NPCs
- event challengers
- recurring daily/weekly trainers

Unlike random trainers, static trainers should generally have stable database
records. Their battle Pokemon may still be copied into ephemeral encounter rows
at battle start so battle state can mutate without damaging the template team.

## Staff-Forced Battles

Staff workflows should call the same trainer encounter pipeline as normal
content. Staff commands should not have a separate battle construction path.

Intended workflows:

- Force one player into a battle with a named static NPC trainer.
- Force everyone in a room into battles with a named static NPC trainer.
- Eventually allow selecting a random trainer class/profile.
- Allow no-reward or custom-reward modes for testing and events.

Possible commands:

- `+npcforce <player> = <npc>`
- `+npcforce/room <npc>`
- `+npcbattle <npc>`

Exact command names can change later. The important rule is that staff commands
resolve a `TrainerEncounter` and hand it to the same battle-start service used
by hunts, static NPCs, gyms, and events.

## Gym Leaders

Gym leaders should be static NPC trainers with special badge/progression
metadata, not a separate battle engine.

A gym leader should eventually include:

- league
- badge granted
- badge requirement
- level cap/ruleset
- battle format
- first-clear reward
- rematch reward
- challenge cooldown/rematch policy
- victory/defeat text
- unlock hooks

Gym leaders should use the same common trainer encounter pipeline as other NPC
trainers. Badge grants, first-clear checks, and rematch rewards should live in
the reward/progression layer after the battle result is known.

The current proof of concept uses `GymLeaderProfile` linked one-to-one to an
`NPCTrainer`, linked to an existing `GymBadge`, and keyed by league/gym/badge
metadata. `badge_key` is transitional because `GymBadge` does not yet have a
durable content key field. The battle result hook grants the badge once on
player victory. Existing generic trainer money rewards may still apply until
gym-specific reward profiles are implemented.

## Gym Followers / Gym Trainers

Gym followers should be optional practice/content NPCs by default. For alpha,
they are represented as ordinary static `NPCTrainer` records with ordered
`NPCPokemonTemplate` teams. They do not grant badges, do not block leader
access, and do not require durable gym grouping yet.

Alpha convention:

- `NPCTrainer.name`: `<Gym Name> Gym Trainer - <Role/Name>`.
- Example: `Pewter Gym Trainer - Hiker Rowan`.
- `NPCPokemonTemplate.template_key`: `<gym_key>-<trainer_slug>-<slot>`.
- Example: `pewter-hiker-rowan-1`.
- `NPCTrainer.description` should include the gym key, the strategy
  lesson/theme, and any optional staff-facing notes.
- Staff should validate followers with `+npcbattle/check <trainer>`.
- Staff can test followers with `+npcbattle <trainer>`.
- Winning a follower battle should not grant a badge because only gym leader
  encounters use `source_type="gym_leader"`.

Design goals:

- Gym followers are static NPC trainers.
- Their teams are built with ordered `NPCPokemonTemplate` rows.
- They teach or demonstrate parts of the gym leader's strategy.
- They may provide hints or optional practice.
- They should not become mandatory grind walls by default.

Examples:

- Weather gym follower teaches Rain setup.
- Trick Room follower demonstrates slow-speed advantage.
- Doubles follower demonstrates support and targeting.
- Hazard follower demonstrates entry hazard pressure.

Future gyms may require a single qualifier battle, puzzle, or trial when that
fits the design, but every gym should not default to a forced gauntlet.

Add a durable `GymFollowerProfile` only when code needs follower grouping, hint
text, gym ordering, leader-check integration, room placement, or follower
prerequisites.

## AI Profiles

Trainer identity and AI behavior should be separate.

Suggested early AI profiles:

- `basic`
- `aggressive`
- `defensive`
- `setup`
- `weather`
- `trick_room`
- `doubles_support`
- `gym_leader`
- `staff_scripted`

Early implementation can use an enum/string stored on the trainer profile or
static trainer. Later implementation should connect AI profiles to the planned
safe AI DSL system.

The battle engine should receive the resolved `ai_profile` with the encounter.
The AI subsystem can then choose whether that profile maps to simple heuristics,
profile-specific move scoring, or a staff-authored script.

## Rewards and Anti-Grind Rules

Rewards should be separate from trainer generation. A trainer generator should
produce the opponent; a reward profile should decide what the player earns.

Reward profiles may define:

- money
- TXP
- Pokemon EXP
- item rewards
- badge rewards
- first-clear-only rewards
- repeatable rewards
- cooldowns
- diminishing returns

Design constraints:

- Random trainers should give modest rewards.
- Repeatable battles should not become infinite XP/TXP farming.
- Gym leader badge rewards should not duplicate.
- Rematches may exist but should use reduced or controlled rewards.
- Staff-forced battles should have configurable rewards, including no-reward
  mode.
- Reward logic should have enough battle context to distinguish first clear,
  rematch, staff test, event battle, and random encounter.

## Suggested Implementation Phases

### Phase 1: Foundation

- Add a common trainer encounter service/dataclass.
- Replace hardcoded random trainer Pokemon generation.
- Add basic random trainer profile generation.
- Update the hunt NPC trainer path to use the generator.
- Add focused tests for encounter generation and hunt integration.

### Phase 2: Static Trainers

- Use or expand `NPCTrainer` and `NPCPokemonTemplate`.
- Add staff command support to start a battle against a static NPC trainer.
- Add minimal seed/test trainer data.
- Ensure template Pokemon are copied into battle-scoped encounter rows.

### Phase 3: Multi-Pokemon NPC Trainer Battle Support

- Carry the full `TrainerEncounter.team` into battle startup.
- Start with the first ordered NPC team member.
- Automatically send out the next unfainted NPC team member when the active NPC
  Pokemon faints.
- End the battle only when the NPC trainer has no usable Pokemon left.
- Preserve random trainer and one-Pokemon trainer behavior.
- Keep reserve send-out automatic for now; strategic trainer AI switching is a
  later AI/profile feature.

### Phase 4: Gym Leaders

- Add gym leader metadata and badge reward handling. Implemented as
  `GymLeaderProfile` linked to static `NPCTrainer` and existing `GymBadge`.
- Add challenge eligibility checks. Implemented with a minimal
  `required_badge_count` gate.
- Add a staff/test command for proof-of-concept gym leader battles.
- Add tests that prove badges do not duplicate. Implemented for the badge grant
  service/result hook.
- Add practical admin/content tooling. Implemented with Django admin
  registration, NPC trainer template inlines, validation warnings, and
  `+gymbattle/list/all` audit mode.
- First-clear/rematch reward distinction beyond badge dedupe remains future
  reward-profile work.

### Phase 5: Gym Followers Alpha

- Document gym followers as ordinary static `NPCTrainer` records by convention.
- Use ordered `NPCPokemonTemplate` rows for follower teams.
- Validate and test follower battles through `+npcbattle/check` and
  `+npcbattle`.
- Keep followers optional by default; they do not grant badges or block leader
  access.

### Phase 5B Or Later: Durable Gym Followers

- Add `GymFollowerProfile` only when code needs durable follower grouping, hint
  text, gym ordering, leader-check integration, room placement, or follower
  prerequisites.
- Consider future gym trial support separately from optional follower battles.

### Phase 6: AI Expansion

- Replace simple move choice with AI profiles.
- Add profile-specific move and target scoring.
- Later connect AI profiles to the safe staff-authored DSL.

## Manual Test Checklist

Use this checklist when implementing or reviewing NPC trainer battle work:

- Random hunt trainer can spawn.
- Random trainer does not always use hardcoded Charmander.
- Trainer team size respects profile rules.
- Trainer levels respect profile, area, and player constraints.
- Static NPC trainer battle can be started by staff.
- Static NPC uses template team.
- Gym leader can grant badge once.
- Repeated gym leader win does not duplicate badge.
- Gym follower can be battled through `+npcbattle` without blocking the leader
  or granting a badge by default.
- Rewards obey cooldowns and first-clear rules.
- Staff-forced battles can run with no rewards.
- Battle logs remain readable and not spammy.
- Generated encounter Pokemon are cleaned up or retained only as intended.
- Existing wild battle and PvP flows continue to work.

## Related Current Code

Useful PF2 starting points for future implementation:

- `world/hunt_system.py` - current hunt flow and `npc_chance` trainer hook.
- `pokemon/battle/pokemon_factory.py` - current hardcoded trainer Pokemon
  generation.
- `pokemon/models/trainer.py` - `NPCTrainer` and `NPCPokemonTemplate`.
- `utils/pokemon_utils.py` - `spawn_npc_pokemon` template helper.
- `pokemon/battle/battleinstance.py` - battle session startup and AI
  auto-queue integration.
- `pokemon/battle/engine.py` - current simple AI action selection.

Useful PF1 reference materials already copied into `docs/reference/`:

- `docs/reference/battletypes.txt`
- `docs/reference/battleinterface.txt`
