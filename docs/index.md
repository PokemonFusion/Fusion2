# Fusion2 documentation

Start here to find a system's guide, implementation, design, or verification
history. Existing feature documents and dated reports retain their paths.

## Start working

| Task | Start here |
| --- | --- |
| Install dependencies and choose a test command | [Contributing](../CONTRIBUTING.md), [original Evennia setup notes](../README.instructions.md) |
| Find a feature's commands, logic, models, and tests | [Code map](code-map.md) |
| Find application tests by feature or guarded integration runners | [Test source index](../tests/README.md) |
| Find QA runners, audit tools, and data generators | [Tools index](../tools/README.md) |
| Learn a player or builder workflow | [Feature guides](guides.md) |
| Understand a design contract or planned scope | [Design index](design/README.md) |
| Check persistence, permissions, and operator procedures | [Operations index](operations/README.md) |
| Find a dated test report or acceptance checklist | [Testing and evidence index](testing/README.md) |
| Run offline battle checks | [Offline battle testing](offline-battle-testing.md) |
| Find planning milestones | [2026 roadmap](roadmap/2026-roadmap.md) |
| Find original battle reference material | [Reference index](reference/README.md) |
| Keep local test folders manageable | [Workspace hygiene](workspace-hygiene.md) |

## Common starting points

- Battles: [presentation and HP visibility](battle-interface.md),
  [doubles](player-doubles.md), [Multi Battles](multi-battles.md),
  [recovery](battle-recovery.md), and [coverage inventory](battle-coverage-report.md).
- Pokemon ownership: [party placement](operations/pokemon-placement.md),
  [transfers](operations/pokemon-transfers.md),
  [consent trading](operations/consent-trading.md), and
  [Fusion transitions](operations/fusion-transitions.md).
- World activities: [Adventure](adventure-operations.md),
  [NPC trainers](static-npc-trainer-battles.md),
  [gyms](production-strategy-gym.md), and [training grounds](training-grounds.md).
- Items: [support and acquisition](item-availability.md),
  [combat use](combat-items.md), [field use](field-items.md),
  [evolution](evolution.md), and [berry nursery](berry-nursery.md).
- Special battle forms: [Mega Evolution](mega-evolution.md),
  [Terastallization](terastallization.md), [Z-Moves](z-moves.md),
  [Necrozma](necrozma.md), and [Ultra Burst](ultra-burst.md).

## Reading the evidence

Feature guides describe workflows and their boundaries. Designs can include
unimplemented proposals. Reports under `testing/` describe a particular build,
date, and environment; release plans describe proposed actions. An offline
pass, disposable database check, local player walkthrough, and deployed server
acceptance establish different things. Follow the linked report for its exact
scope, fixtures, exclusions, and later corrections.

## Keeping this documentation findable

Add links to the matching feature or directory index when adding a document.
Update the code map when entry points change. Keep dated reports and companion
JSON receipts together at their existing paths, and cross-link later evidence
instead of rewriting an older result into a broader claim.
