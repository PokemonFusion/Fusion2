# Pokémon Fusion 2 Adventure System Planning Document

## 1. Feature Summary

The Adventure system is a planned PF2 feature for small, reusable, on-demand exploration content.

Instead of building a massive permanent map for every route, cave, forest, beach, or region, PF2 can use adventure instances: compact virtual areas where solo players or small groups can hunt Pokémon, complete tasks, battle NPC trainers, gather rewards, and roleplay around structured objectives.

The intended player-facing fantasy is:

> “I can go on a small Pokémon adventure by myself or with friends, explore a themed area, do something meaningful, and come back with progress.”

The intended technical model is:

> “A persistent Evennia room acts as the physical container, while the adventure area itself is virtual state rendered through commands, room display, and optional ANSI maps.”

---

## 2. Design Goals

### Primary Goals

1. Let PF2 represent many Pokémon-style areas without building a huge permanent world map.
2. Support region-themed Pokémon availability.
3. Give players structured small-group RP activities.
4. Provide controlled sources for items, TMs, rewards, and progression.
5. Support mission-style content for Rangers, researchers, breeders, battlers, and events.
6. Avoid grind loops and command-spam rewards.
7. Keep the main social world compact and populated.
8. Build the system in small, testable steps.

### Secondary Goals

1. Support gym preparation challenges.
2. Support event/story adventures.
3. Support staff-authored templates.
4. Eventually support builder-friendly content creation tools.
5. Allow future reputation tracks without requiring them in the first version.

---

## 3. Non-Goals

The first Adventure system should not try to be all of these things at once.

Do not build in the first version:

1. Procedural map generation.
2. Fully open-world exploration.
3. Player-created adventure maps.
4. Party splitting.
5. Multiple simultaneous battles inside one adventure.
6. Complex gathering/crafting chains.
7. Randomized loot economies.
8. Permanent world map mutation.
9. Competitive PvP adventure invasions.
10. A full faction system.
11. A full quest journal.
12. A full dungeon crawler.

The first goal is to prove the core loop works.

---

## 4. Core Concept

An Adventure is a temporary gameplay session using a virtual map.

Players physically enter an Adventure Instance Room, but the room display changes based on the adventure’s current virtual location.

Example:

```text
Adventure Hall
  -> Adventure Instance Room #1

Inside that room:
  Current adventure: Viridian Forest Survey
  Current virtual location: Shaded Path
  Available directions: north, east, south
```

The player is still in the same Evennia room, but the system tracks their adventure position separately.

---

## 5. Recommended First Technical Model

Use a fixed pool of permanent adventure rooms instead of dynamically creating temporary rooms.

Example:

```text
Adventure Hall
Adventure Instance Room #1
Adventure Instance Room #2
Adventure Instance Room #3
Adventure Instance Room #4
Adventure Instance Room #5
```

When a player or party starts an adventure:

1. The system finds an unused Adventure Instance Room.
2. The system creates an AdventureSession.
3. The player or party is moved into the room.
4. The room display is rendered from the AdventureSession.
5. Movement commands update virtual position, not physical room location.
6. On completion, failure, timeout, or leaving, the session is cleaned up.
7. The room returns to available status.

This avoids cluttering the database with temporary rooms while still keeping different groups separated.

---

## 6. Player-Facing Commands

### Phase 1 Commands

```text
+adventure/list
+adventure/info <adventure>
+adventure/start <adventure>
+adventure/look
+adventure/objectives
+adventure/leave
north / south / east / west
n / s / e / w
```

### Phase 2 Commands

```text
+adventure/invite <player>
+adventure/uninvite <player>
+adventure/party
+adventure/ready
+adventure/disband
```

### Phase 3 Commands

```text
+adventure/search
+adventure/hunt
+adventure/gather
+adventure/complete
+adventure/rewards
```

Command names can be adjusted later. The main concern is that the first version stays small.

---

## 7. Virtual Map Model

Start with node-based maps, not grid-based maps.

Each node is a virtual location.

Example:

```text
entrance
  north -> shaded_path

shaded_path
  south -> entrance
  east -> pond_bank
  north -> deep_grass

deep_grass
  south -> shaded_path
  north -> old_clearing
```

Each node can define:

```text
key
name
description
available directions
encounter table
objective hooks
search text
optional map coordinates
entry effects
```

Optional coordinates can be added for ANSI map rendering without making the map fully grid-based.

---

## 8. Adventure Display

The display should be compact, width-safe, and readable.

Example:

```text
Viridian Forest Survey
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Shaded Path

Tall grass presses against the trail. You hear wild Pokémon moving
somewhere nearby.

Map:
  ? ? ?
  . @ ?
  E . ?

Legend: @ group, E entrance, ? unexplored, . explored

Exits: north, east, south
Actions: search, hunt, objectives, leave

Objective:
  Scan Bug-type Pokémon: 1/3
```

Display goals:

1. Make it clear where the group is.
2. Show available directions.
3. Show current objectives.
4. Show available actions.
5. Avoid spam.
6. Avoid giant maps.
7. Work in both telnet and webclient.

---

## 9. Group Rules

First group implementation should use leader-controlled movement.

Rules:

1. The adventure has one leader.
2. All party members share one virtual position.
3. Only the leader can move the group.
4. Any member can use look/objectives.
5. Search/hunt permissions can be decided later.
6. If the leader disconnects, leadership can pass to another present party member.
7. No party splitting in the first version.

This keeps the system stable and RP-friendly.

---

## 10. Battle Rules

Adventures should reuse the existing PF2 battle system as much as possible.

Basic rules:

1. An adventure can trigger a wild Pokémon battle or NPC trainer battle.
2. While a battle is active, adventure movement is paused.
3. After battle ends, the adventure resumes.
4. Objective progress can update after battle.
5. Only one active battle per adventure session in the first version.

Important technical question:

The battle system must safely associate the active battle with the AdventureSession or the Adventure Instance Room. If the room-based battle data already assumes one battle per room, the fixed room pool model helps keep things simple.

---

## 11. Adventure Categories

### Hunt Adventures

Purpose: catching Pokémon and exploring themed habitats.

Examples:

```text
Kanto Forest Survey
Johto Night Pond
Hoenn Cave Route
Sinnoh Snowfield
Alola Beach Walk
Paldea Canyon Survey
```

### Mission Adventures

Purpose: complete a task.

Examples:

```text
Catch a requested Pokémon.
Defeat a rogue NPC trainer.
Find missing survey markers.
Escort a daycare Pokémon.
Investigate fusion energy readings.
```

### Training Adventures

Purpose: teach mechanics and prepare players for gyms.

Examples:

```text
Status Condition Trial
Weather Basics Trial
Hazard Control Trial
Doubles Coordination Trial
Terastallization Field Test
```

### Story Adventures

Purpose: staff-authored events and lore.

Examples:

```text
Abandoned Lab Survey
Distorted Crystal Incident
Missing Ranger Patrol
Celebi Time Ripple
Fusion Research Site
```

### Gym Prep Adventures

Purpose: optional or required prep for strategy-based gyms.

Examples:

```text
Rain Team Drill
Trick Room Simulation
Entry Hazard Workshop
Stallbreaker Challenge
Doubles Positioning Trial
```

---

## 12. Reward Philosophy

Rewards must support progress without creating infinite farming.

Good reward types:

1. Money.
2. Common items.
3. TMs.
4. Held items.
5. Evolution items.
6. Cosmetics.
7. Titles.
8. Reputation.
9. Trainer journey progress.
10. Badge prerequisite flags.
11. Controlled Pokémon encounter access.
12. Event tokens.

Avoid or tightly control:

1. Infinite XP.
2. Infinite money.
3. Repeatable rare item farming.
4. Command-volume reward loops.
5. Rewards for raw RP text length.
6. Progress that makes veterans permanently unreachable.

Recommended reward model:

```text
First clear: full reward
Repeat clear: reduced reward
Daily/weekly bonus: limited
Rare rewards: capped, gated, or pity-based
Progression rewards: milestone-based
```

---

## 13. Anti-Grind Guardrails

The Adventure system must follow PF2’s progression philosophy.

Rules:

1. No infinite XP farming.
2. No battle spam advantage.
3. No command-volume reward loops.
4. No RP text-dump farming.
5. Diminishing returns are allowed.
6. Cooldowns are allowed.
7. Weekly caps are allowed.
8. Players should still be able to use adventures for RP and catching after capped rewards are exhausted.
9. Major progression should come from milestones, not repetition.

Example:

```text
The first few weekly adventure objectives grant full trainer progress.
After that, players can still adventure for RP, catching, and reduced rewards.
```

---

## 14. Data Model Sketch

Exact implementation may change, but the concept should stay close to this.

### AdventureTemplate

```text
key
name
description
category
region
biome
min_badges
max_party_size
recommended_level
template_status
node_data
encounter_tables
objective_data
reward_table
metadata
```

### AdventureSession

```text
template
instance_room
leader
party_members
current_node
visited_nodes
objective_progress
active_battle_id
state
started_at
completed_at
expires_at
reward_claimed
metadata
```

### AdventureObjective

```text
type
target
count
required
description
progress_key
completion_rules
```

Objective types can include:

```text
catch
defeat
scan
find
gather
reach
talk
survive
complete_battle
```

### AdventureReward

```text
money
items
tm_rewards
reputation
trainer_progress
flags
cosmetics
metadata
```

---

## 15. Suggested File/Module Layout

Potential repo layout:

```text
pokemon/adventures/
  __init__.py
  models.py
  templates.py
  sessions.py
  renderer.py
  movement.py
  objectives.py
  rewards.py
  encounters.py
  commands.py
  admin.py
  constants.py
```

Possible tests:

```text
tests/test_adventure_templates.py
tests/test_adventure_sessions.py
tests/test_adventure_movement.py
tests/test_adventure_objectives.py
tests/test_adventure_rewards.py
tests/test_adventure_commands.py
tests/test_adventure_battle_integration.py
```

Keep modules small. Do not make one giant adventure file.

---

## 16. Implementation Phases

### Phase 0: Design Lock

Goal:

Lock the minimum version before coding.

Deliverables:

1. Finalize first adventure template.
2. Finalize command names.
3. Decide whether sessions live in Django models, Attributes, or a hybrid.
4. Decide how instance rooms are reserved.
5. Decide how battle integration will identify adventure battles.
6. Write acceptance criteria.

Exit criteria:

The feature has a scoped MVP and a clear first Codex task.

---

### Phase 1: Virtual Room Prototype

Goal:

Prove that a single room can display changing adventure state.

Features:

1. One hardcoded test adventure.
2. One player only.
3. Node-based movement.
4. Custom adventure look display.
5. Cardinal movement updates virtual node.
6. Leave command exits the adventure.
7. No battles.
8. No rewards.
9. No group support.

Exit criteria:

A player can start Alpha Meadow, move between virtual locations, see the display update, and leave cleanly.

---

### Phase 2: Session Persistence and Cleanup

Goal:

Make adventure sessions safe.

Features:

1. AdventureSession tracking.
2. Instance room reservation.
3. Session timeout.
4. Cleanup on leave.
5. Cleanup on disconnect if needed.
6. Staff abort command.
7. Safe recovery after reload.

Exit criteria:

Adventure sessions do not leave players stuck or rooms locked.

---

### Phase 3: Objectives

Goal:

Add meaningful tasks.

Features:

1. Objective display.
2. Reach-location objective.
3. Search/find objective.
4. Completion state.
5. Basic completion message.
6. Staff debug view.

Exit criteria:

A player can complete a simple objective and the system records completion.

---

### Phase 4: Basic Rewards

Goal:

Reward completion safely.

Features:

1. Money reward.
2. Item reward.
3. First-clear tracking.
4. Repeat-clear reduced reward or no major repeat reward.
5. Reward claim protection.

Exit criteria:

Rewards are granted once and cannot be duplicated through relogging, repeating commands, or errors.

---

### Phase 5: Encounter Integration

Goal:

Allow adventures to trigger existing battles.

Features:

1. Search/hunt command.
2. Wild encounter spawn.
3. Existing battle starts in the adventure instance room.
4. Movement pauses during battle.
5. Battle result updates objective progress.
6. Adventure resumes after battle.

Exit criteria:

A player can trigger and complete a wild battle inside an adventure without breaking the adventure session.

---

### Phase 6: Group Support

Goal:

Support small-group RP adventures.

Features:

1. Invite command.
2. Ready command.
3. Party display.
4. Leader-controlled movement.
5. Shared objective progress.
6. Leader handoff if leader disconnects.
7. Group leave/disband behavior.

Exit criteria:

A small party can enter, move, RP, complete objectives, and exit together.

---

### Phase 7: Template Loading

Goal:

Stop hardcoding adventures.

Features:

1. Staff-defined adventure templates.
2. Template validation.
3. Template list command.
4. Template preview/debug command.
5. Safe failure messages.

Exit criteria:

Staff can add a second adventure without changing core adventure code.

---

### Phase 8: Content Expansion

Goal:

Add enough content to prove the system is useful.

Initial content set:

1. One hunt adventure.
2. One mission adventure.
3. One training adventure.
4. One gym prep adventure.

Exit criteria:

The system supports more than one kind of gameplay.

---

### Phase 9: Reputation / Progress Hooks

Goal:

Connect adventures to longer-term progression.

Possible hooks:

1. Trainer Journey progress.
2. Ranger reputation.
3. Research reputation.
4. Gym prerequisite flags.
5. Event progress.
6. Badge-related unlocks.

Exit criteria:

Adventures can feed broader PF2 progression without becoming mandatory grind.

---

### Phase 10: Builder/Admin Tools

Goal:

Make the system maintainable.

Features:

1. Template validation command.
2. Active session list.
3. Abort session command.
4. Teleport to session room command.
5. Reward audit.
6. Encounter table audit.
7. Objective debug command.

Exit criteria:

Staff can manage the feature without database diving.

---

## 17. MVP Scope

The MVP should be intentionally small.

### MVP Includes

1. One adventure room.
2. One solo adventure.
3. Three to five virtual nodes.
4. Cardinal movement.
5. Look/objectives/leave commands.
6. One reach or search objective.
7. Safe cleanup.
8. No rewards or only a harmless test reward.

### MVP Does Not Include

1. Group support.
2. Wild battles.
3. NPC trainer battles.
4. Complex rewards.
5. Reputation.
6. Region-wide encounter systems.
7. Procedural maps.
8. Crafting materials.
9. Player-created adventures.

MVP purpose:

> Prove the illusion of virtual exploration works and feels good in Evennia.

---

## 18. Beta-Ready Scope

This feature is probably not required for beta unless beta scope changes.

If included in beta, beta-ready should mean:

1. At least one stable solo adventure.
2. Safe cleanup.
3. At least one useful reward.
4. At least one Pokémon encounter or mission objective.
5. Staff abort tools.
6. No known duplication bugs.
7. No player-stuck bugs.

Group adventures can come after beta unless they are specifically prioritized.

---

## 19. Risk List

### Technical Risks

1. Battle system integration may be harder than expected.
2. Adventure sessions may not survive reloads cleanly.
3. Players may get stuck if cleanup fails.
4. Room display overrides may conflict with normal commands.
5. Multiple groups may accidentally share state.
6. Disconnects may create edge cases.
7. Rewards may duplicate if completion is not atomic.

### Design Risks

1. The system may become too broad.
2. Rewards may turn it into a grind.
3. Players may expect full maps instead of compact scenes.
4. Content creation may become a bottleneck.
5. Group movement may annoy non-leaders.
6. Too many adventure categories may dilute focus.

### Community Risks

1. Players may assume every region will be available quickly.
2. Players may expect rare Pokémon from day one.
3. Players may compare it to full MMO dungeons.
4. If rewards are too strong, non-adventure play may feel pointless.
5. If rewards are too weak, adventures may feel cosmetic only.

---

## 20. Risk Mitigation

1. Start with a tiny prototype.
2. Keep first adventure solo.
3. Use a fixed room pool.
4. Use leader-controlled group movement only when groups are added.
5. Add rewards after cleanup is proven.
6. Add battles after movement/objectives are proven.
7. Add staff abort tools early.
8. Avoid procedural generation until templates are stable.
9. Keep reward caps clear.
10. Communicate that adventures are compact scenes, not full regions.

---

## 21. Open Questions

These should be answered before major implementation.

1. Should AdventureSession be a Django model, Evennia Attribute data, or hybrid?
2. How many adventure instance rooms should exist at launch?
3. Should all adventures start from one Adventure Hall?
4. Should players be allowed to start adventures from anywhere later?
5. Should hunt/search be separate commands?
6. Should group members be able to trigger encounters or only leaders?
7. Should rewards be granted immediately or claimed at the end?
8. Should leaving early fail the adventure, pause it, or allow return?
9. How long should an inactive adventure remain open?
10. How should staff preview/debug a virtual node?
11. How should battle watchers behave inside adventure rooms?
12. Should adventure RP logs or summaries be saved?
13. What is the first real adventure template?
14. What is the first player-visible reward?
15. What is the maximum party size?

---

## 22. Recommended First Adventure

Use a simple non-lore-heavy test adventure.

### Alpha Meadow Survey

Category:

```text
Hunt / tutorial
```

Size:

```text
4 virtual nodes
```

Nodes:

```text
Meadow Entrance
Tall Grass Path
Small Pond
Old Tree
```

Objectives:

```text
Reach the Old Tree.
Search the Old Tree.
Return to the entrance.
```

Optional later objective:

```text
Find signs of wild Pokémon activity: 0/2
```

Why this adventure:

1. It is simple.
2. It does not require battle integration.
3. It tests movement.
4. It tests objectives.
5. It tests returning/cleanup.
6. It can later support wild encounters.

---

## 23. Success Criteria

The feature is successful if:

1. Players understand where they are.
2. Players understand what they can do next.
3. The system supports RP instead of interrupting it.
4. Staff can author content without touching core systems.
5. Rewards are useful but not abusable.
6. The main world stays compact.
7. The system can represent multiple regions through small templates.
8. The code stays modular and testable.
9. The feature does not block PF2’s core parity roadmap.

---

## 24. Hard Guardrails

1. No infinite farming.
2. No command-volume progression.
3. No required daily chore loop.
4. No procedural generation in MVP.
5. No party splitting in MVP.
6. No full crafting economy in MVP.
7. No player-created adventure maps in MVP.
8. No combat reward duplication.
9. No permanent progression advantage from spam.
10. No future-generation Pokémon mechanics beyond PF2’s Gen 9 scope.

---

## 25. Development Rule

Every implementation step should be small enough to test manually in-game.

Each Codex task should include:

1. Goal.
2. Files touched.
3. Unified diff.
4. Reload steps.
5. Manual test steps.
6. Rollback steps.

No kitchen-sink adventure patch.
