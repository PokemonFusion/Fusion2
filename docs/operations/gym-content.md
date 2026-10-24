# Versioned gym content (#729)

Gym authors use one JSON definition and the existing gym/trainer, launch and
victory services. Tempo remains the first production strategy gym tracked by
#712. `world/content/gyms/validation_singles.json` is optional validation content,
not a new league or a gym automatically enabled by the Tempo installer.

## Author route

After the separately approved schema rollout, validate a file without writes:

```text
evennia install_gym_content world/content/gyms/tempo.json --check
```

Install the reviewed definition deliberately:

```text
evennia install_gym_content world/content/gyms/tempo.json
```

The existing `evennia seed_production_gym` uses the same installer for Tempo and
continues disabling the old Alpha test gym. It does not install validation
singles. No deployment or existing game database change follows from local tests.

Copy a definition, choose distinct stable league/gym, leader and badge identities,
and validate before installation. Unknown keys are rejected instead of silently
ignored. Files are limited to 256 KiB. The command reports concrete author errors
and the installed profile, version and SHA-256 fingerprint.

## Supported configuration

| Section | Contract |
| --- | --- |
| `version` | Positive integer. Repeat the exact definition at the same version; increase the version for a changed definition. Downgrades and different same-version content are refused. |
| `league_key`, `gym_key` | Stable lowercase keys, up to 80 characters. They select the existing durable profile, not a new player command. |
| `leader` | Unique name and description. One gym owns this trainer and its keyed roster. Existing unrelated trainers/teams are never commandeered. |
| `badge` | Name, region and description. Existing badge identity and `profile.badge_key` remain stable across updates, preserving earned badges and pending rewards. |
| `profile` | Explicit enablement, sort order, badge-count eligibility, format, AI, strategy, stage, reward policy, cooldown and presentation text. Every field in the examples is required. |
| `team` | One to six authored members; doubles requires at least two. Each has a unique template key, species, level 1–100, native ability, nature, gender, six genetic IVs 0–31, six EVs 0–252 totaling at most 510, held item and one to four distinct known moves. No automatic level scaling or invented moves. |

Formats are `single` and `double`. AI keys come from the existing profile registry;
bounded `trick_room` requires `gym_trick_room` and doubles. An empty strategy uses
an existing non-strategy profile. This adds no AI language, four-controller format,
NPC Mega activation or new battle rules. Forms requiring a pre-battle activation
are refused. Ordinary held items must resolve to supported catalog entries.

New authored content uses `badge_only`: first clear awards the existing badge
once; rematches are practice and award no duplicate badge, money, items, Pokemon
XP, EVs or trainer XP. Cooldown is an integer from zero to seven days, measured
from the latest confirmed victory when that badge is already earned. Losses and
concessions have no cooldown or rewards. Pending badge delivery blocks another
challenge until the player uses `+gym claim`. These bounded policies reuse the
existing ledger; arbitrary monetary/item rewards and loss penalties are rejected.

`rules_text` and intro/victory/defeat text describe supported mechanics; they do
not execute rules. Keep their prose consistent with the selected team, format,
eligibility and reward policy. New keys such as item bans, level caps, weather
scripts or unsupported strategies require implementation before they can be
authored. Existing battle item/Tera behavior remains governed by the engine.

## Updates, snapshots and recovery

Installation locks the gym identity, profile and owned leader, and updates all
roster/settings/version writes atomically. Repeating installation preserves
trainer, profile, badge and team row identities and never resets GymVictory rows
or trainer progression. Duplicate/unrecognized roster rows stop installation
for review; the installer does not guess which rows to delete. Removing a roster
key therefore needs an explicit content review, rather than automatic deletion.

Existing unversioned gyms remain compatible. A deliberate installation can adopt
matching existing gym/leader/badge identities; mismatches are rejected. Subsequent
launch validates the installed definition/fingerprint against its live profile,
leader, badge and roster. Direct row edits fail before battle allocation. Restore
the approved same-version definition, or publish a higher reviewed version.

At launch, metadata snapshots the full definition, version, fingerprint, rules,
team, AI, reward policy, texts and badge ID. The engine's room checkpoint carries
that snapshot through rebuild. A later installed version affects new challenges;
it cannot replace a running encounter's team or redirect a pending victory to a
different badge. `+gym claim` continues retrying the existing saved victory once.
The current configured cooldown controls the next challenge's availability.

## Acceptance boundary

The original `production_gym_cases.py` retains Tempo's separate first-gym checks.
`gym_content_cases.py` covers an actual ordinary User/Account and Player permission
through `+gym check/challenge/claim`, a distinct singles fixture, rebuild after an
author update, first clear, immediate practice, idempotent/concurrent installs,
raw-content drift and real-write rollback. Its standalone object-search facade
is bound to real ORM dbref queries; outbound transport is captured. These local
automated checks do not claim a live socket walkthrough or deployed content.
