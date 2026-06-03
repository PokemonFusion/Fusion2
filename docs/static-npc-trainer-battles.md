# Static NPC Trainer Battles

Static NPC trainer battles are the current staff-facing way to start a trainer
battle from existing `NPCTrainer` and `NPCPokemonTemplate` rows. This is a
small no-migration implementation slice, not the full NPC trainer roadmap.

## Current Commands

Builder staff can use:

```text
+npcbattle/list
+npcbattle/check <npc trainer name>
+npcbattle <npc trainer name>
+gymbattle/list
+gymbattle/list/all
+gymbattle/check <leader name|gym_key>
+gymbattle <leader name|gym_key>
```

`+npcbattle/list` lists static NPC trainers that have at least one template
Pokemon row.

`+npcbattle/check <npc trainer name>` validates whether a trainer should be able
to start a battle. It reports whether the trainer was found, template count,
ordered species and levels, template issues, and whether startup should work.

`+npcbattle <npc trainer name>` starts a trainer battle for the caller against
that static NPC trainer. It does not force another player into battle and does
not start room-wide battles. For alpha gym followers, this is also the staff
testing command.

`+gymbattle` is the Phase 4 proof-of-concept gym leader command. It starts a
static trainer battle through the same encounter pipeline, but only for
`NPCTrainer` rows that have an enabled `GymLeaderProfile`. The command checks
the caller's badge count before startup and grants the linked `GymBadge` once
when the caller wins.

`+gymbattle/list` shows enabled gym leaders. `+gymbattle/list/all` is the
content-audit view and includes disabled gym leader profiles.

## Creating Test Rows

There is no in-game NPC editor yet. Use the Evennia/Django shell or Django
admin to create test rows.

### Django Admin

The Django admin can create and edit:

- `GymBadge`
- `NPCTrainer`
- `NPCPokemonTemplate`
- `GymLeaderProfile`

`NPCTrainer` includes an inline editor for `NPCPokemonTemplate`, which is the
simplest admin path for building a trainer team. Keep the ordered template team
at six Pokemon or fewer; battle `Team` storage is capped at six slots.

Recommended admin flow:

1. Create or reuse a `GymBadge`.
2. Create an `NPCTrainer`.
3. Add ordered `NPCPokemonTemplate` rows inline on the `NPCTrainer`.
4. Create a `GymLeaderProfile` linked to that `NPCTrainer` and `GymBadge`.
5. Run `+gymbattle/check <leader name|gym_key>` before starting the battle.

Unknown move names are reported as check-command warnings. They are not hard
blockers in this workflow; current battle startup constructs the battle Pokemon
from the template data and any deeper move behavior problems should be caught
during testing.

### Alpha Gym Followers

For alpha, gym followers and gym trainers are ordinary static `NPCTrainer`
records with ordered `NPCPokemonTemplate` teams. They are optional
practice/content trainers. They do not grant badges, do not block leader access,
and do not require `GymFollowerProfile` or other durable gym grouping yet.

Suggested naming convention:

```text
NPCTrainer.name: <Gym Name> Gym Trainer - <Role/Name>
Example: Pewter Gym Trainer - Hiker Rowan
```

Suggested template key convention:

```text
NPCPokemonTemplate.template_key: <gym_key>-<trainer_slug>-<slot>
Example: pewter-hiker-rowan-1
```

Suggested description convention:

- include the gym key
- describe the strategy lesson or team theme
- include optional staff-facing notes

Manual admin setup:

1. Create an `NPCTrainer` using the follower naming convention.
2. Add ordered `NPCPokemonTemplate` rows inline on that trainer.
3. Keep the team at six Pokemon or fewer.
4. Run `+npcbattle/check <trainer name>`.
5. Run `+npcbattle <trainer name>`.
6. Win the battle and confirm no badge is granted.

Follower wins should not grant badges because alpha followers use the ordinary
static trainer path. Only gym leader encounters use `source_type="gym_leader"`
and the gym leader badge result hook.

### Evennia/Django Shell

From the project directory:

```powershell
H:\PokemonFusionProject\evenv\Scripts\evennia.exe shell
```

In the shell:

```python
from pokemon.models.trainer import NPCPokemonTemplate, NPCTrainer

trainer, _ = NPCTrainer.objects.get_or_create(
    name="Test Trainer",
    defaults={"description": "Temporary static trainer for battle testing."},
)

NPCPokemonTemplate.objects.update_or_create(
    npc_trainer=trainer,
    template_key="lead",
    defaults={
        "species": "Pikachu",
        "level": 8,
        "ability": "Static",
        "nature": "Hardy",
        "gender": "F",
        "ivs": [0, 0, 0, 0, 0, 0],
        "evs": [0, 0, 0, 0, 0, 0],
        "held_item": "",
        "move_names": ["Thunder Shock", "Quick Attack"],
        "sort_order": 1,
    },
)
```

Then verify and start:

```text
+npcbattle/check Test Trainer
+npcbattle Test Trainer
```

For a gym leader proof of concept, also create or reuse a `GymBadge`, then link
the static trainer with `GymLeaderProfile`:

```python
from pokemon.models.trainer import GymBadge, GymLeaderProfile

badge, _ = GymBadge.objects.get_or_create(
    name="Test Badge",
    region="Test League",
    defaults={"description": "Temporary proof-of-concept badge."},
)

GymLeaderProfile.objects.update_or_create(
    npc_trainer=trainer,
    defaults={
        "badge": badge,
        "league_key": "test_league",
        "gym_key": "test_gym",
        "badge_key": "test_badge",
        "required_badge_count": 0,
        "is_enabled": True,
        "sort_order": 1,
    },
)
```

Then verify and start:

```text
+gymbattle/check test_gym
+gymbattle test_gym
```

For content audits:

```text
+gymbattle/list
+gymbattle/list/all
+npcbattle/list
+npcbattle/check Test Trainer
```

## Runtime Behavior

Static trainer battles use the shared `TrainerEncounter` shape from
`pokemon.services.trainer_encounters`.

At battle start, each `NPCPokemonTemplate` is copied into a battle-scoped
`EncounterPokemon` row. The template rows are not mutated by the battle.

The battle startup adapter now passes the full encounter team into the NPC
trainer participant. The first ordered template starts active. When an NPC
trainer's active Pokemon faints, the next unfainted team member is sent out.
The player wins only after all NPC trainer team members have fainted.

Reserve send-out is automatic battle-engine behavior. It is not strategic
trainer AI switching, and it does not inspect matchup, move, item, or ruleset
context yet.

Random trainer encounters still use the same shared `TrainerEncounter` shape.
One-Pokemon random and static trainer battles continue to work as before.

Gym leader encounters also use the same shared shape with
`source_type="gym_leader"` and gym metadata attached to the encounter. Badge
granting happens in the battle result hook only when the player side wins.
Losing, conceding, or admin cleanup does not grant the badge. Re-winning the
same leader does not duplicate the badge.

Alpha gym followers use the ordinary static trainer path and are tested with
`+npcbattle/check` and `+npcbattle`. They do not grant badges or block gym
leader access.

## Current Limits

The current models are intentionally narrow:

- `NPCTrainer` only has `name` and `description`.
- `NPCPokemonTemplate` stores Pokemon template data and ordering.
- `GymLeaderProfile` stores gym metadata separately from `NPCTrainer` so the
  static trainer remains reusable.
- `GymLeaderProfile.badge_key` is transitional because `GymBadge` does not yet
  have a durable key field.
- Battle `Team` storage remains capped at six slots.
- Check commands warn when a trainer has more than six template Pokemon.
- Check commands warn on unknown template move names but do not treat them as
  hard blockers.
- Trainer class, AI profile, battle format, ruleset, reward profile, intro
  text, victory text, and defeat text are metadata defaults unless a future
  migration adds fields.
- Existing generic trainer money rewards may still apply to gym leader battles.
  Gym-specific reward profiles are future work.
- Alpha gym followers are represented by naming and documentation conventions,
  not by a durable `GymFollowerProfile`.

Not implemented in this slice:

- full gym progression beyond the proof-of-concept badge gate
- leader rewards
- durable gym follower grouping/profile data
- gym follower room placement or interaction hooks
- rewards, TXP, cooldowns, and rematch policy
- AI DSL behavior
- strategic trainer AI switching
- room-wide staff forcing
- NPC editor UI
- full player-side party switching UX beyond the existing battle engine flow
