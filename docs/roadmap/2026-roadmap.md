# Pokémon Fusion 2 — 2026 Roadmap

**Status:** Active  
**Target:** Closed Beta by December 31, 2026  
**Last reviewed:** August 27, 2026

## Purpose

This roadmap defines the major development priorities for Pokémon Fusion 2 for the remainder of 2026.

The goal is not to finish every possible feature or content idea before the end of the year. The goal is to move PF2 from its current alpha state into a stable, persistent closed beta with the core player-facing gameplay loops working reliably.

This roadmap is based on a repository audit of the current implementation. Existing systems should be hardened, integrated, and tested rather than rebuilt unnecessarily.

## Scope Principles

- PF2 supports Pokémon mechanics through Generation 9.
- Terastallization is the primary supported battle gimmick.
- Dynamax and Z-Moves are not part of the current scope.
- Mega Evolution may be supported through a bounded, curated set.
- PF1 parity means matching important player capabilities, not duplicating PF1's implementation.
- Progression should avoid grind loops, battle spam, command-volume rewards, and permanent veteran dominance.
- Horizontal progression is preferred over vertical power creep.
- Trainer AI should be understandable, intentional, and bounded rather than attempting unrestricted competitive prediction.
- Player-authored Trainer AI is not required for the 2026 beta target.
- New feature ideas do not automatically enter the 2026 critical path.
- Once the roadmap reaches feature freeze, new systems should be deferred unless they are necessary to fix a beta blocker.

---

# September — Alpha Completion and Core Integrity

September focuses on making the systems that already exist trustworthy, complete enough for normal player use, and safe to build on.

## Battle and Test Foundation

- `[TEST]` Fix battle test-suite order/import isolation so mandatory suites can run reliably together.
- `[HARDEN]` Make persistent battle-result processing idempotent and retryable.
- `[HARDEN]` Exercise 1v1, wild, and NPC battle edge cases involving fainting, forced switching, disconnects, reconnects, cleanup, and rewards.
- `[FINISH]` Preserve full NPC trainer teams instead of truncating generated/configured teams.
- `[FINISH]` Provide a normal player-facing NPC battle interaction path.

## Doubles and Combat AI

- `[FINISH]` Expose doubles as a normal player battle format.
- `[FINISH]` Add player target-selection UX for doubles.
- `[FINISH]` Add intentional AI switching and reserve selection.
- `[FINISH]` Add doubles AI targeting, ally targeting, and spread-move valuation.
- `[HARDEN]` Centralize legal-action candidate generation for AI.
- `[HARDEN]` Add situational AI scoring for status, setup, recovery, and Protect-style actions.
- `[FINISH]` Persist trainer/gym AI profiles and strategy configuration.
- `[TEST]` Test AI through real battle-session flows, including fainting, rebuilding, and doubles behavior.
- `[HARDEN]` Add only the weather, terrain, hazard, speed-order, or similar strategy reasoning needed by the first production gym.

PF2 already has a runtime combat AI. September work should extend and validate that system rather than replace it.

## Pokémon Lifecycle Integrity

- `[HARDEN]` Establish canonical Pokémon placement and ownership integrity before adding more ownership-changing systems.
- `[FINISH]` Complete supported evolution conditions and fix multiword item handling.
- `[FINISH]` Add safe held-item removal and replacement.
- `[TEST]` Expand storage, capture, evolution, held-item, and ownership failure/concurrency coverage.

## Terastallization and Gyms

- `[FINISH]` Complete end-to-end Terastallization, including player action, once-per-battle state, battle effects, persistence/rebuild, presentation, AI policy, and tests.
- `[CONTENT]` Replace the Alpha test leader with at least one production-quality strategy-oriented gym.
- `[HARDEN]` Make gym victory and badge delivery retryable and idempotent.
- `[HARDEN]` Define first-clear, rematch, and anti-farming reward rules for repeatable battles.

## Adventure Housekeeping

- `[FINISH]` Reconcile, review, test, migrate, and commit the existing Adventure participation/encounter/result work without expanding Adventure scope.

### September Exit Condition

PF2's existing battle and Pokémon-management foundation is trustworthy enough to support the remaining beta systems.

---

# October — Beta Systems and PF1-Parity Foundations

October focuses on the major player capabilities that are genuinely missing or incomplete.

## Trading and Marketplace

- `[FINISH]` Replace immediate gift-style Pokémon transfers with consent-based, transactional trading.
- `[FINISH]` Support safe trading of party and boxed Pokémon.
- `[BUILD]` Add a transactional player marketplace with:
  - Listings
  - Purchases
  - Cancellation
  - Expiration
  - Ownership transfer
  - Recovery from interrupted/failed transactions

Trading and marketplace systems should reuse common ownership-transfer primitives instead of creating separate transfer logic.

## Daycare and Breeding

- `[BUILD]` Add a persistent Daycare MVP integrated with canonical Pokémon placement.
- `[BUILD]` Add a Breeding MVP with:
  - Pair validation
  - Egg creation
  - Essential inheritance
  - Costs and/or cooldowns
  - Hatching lifecycle
  - Failure/recovery handling

## Gyms

- `[FINISH]` Make gyms content-configurable for:
  - Battle format
  - AI profile/strategy
  - Rules
  - Rewards
  - Rematch behavior
- `[CONTENT]` Add additional strategy-gym content only as needed to validate the framework.

The goal is to make new gyms primarily a content-authoring task rather than a new implementation project.

## Fusion and Player UX

- `[HARDEN]` Improve Fusion persistence, transaction boundaries, integrity checks, and recovery behavior.
- `[UX]` Complete normal onboarding and clarify whether any staff-validation step remains necessary.
- `[UX]` Improve player guidance for storage, moves, held items, trading, gyms, and battle formats.
- `[HARDEN]` Verify communication read state, account ownership, and character/web-sheet consistency.

## Adoption

- `[DECISION]` Confirm whether Adoption was a core PF1 player capability.
- `[BUILD]` Implement an Adoption MVP only if PF1 parity requires it.

### October Exit Condition

The major PF1-parity player systems needed for beta exist end to end and share safe persistence/ownership foundations.

---

# November — Adventure Vertical Slice

November turns the existing Adventure engine into a complete player-facing gameplay loop.

The existing session, movement, search, objective, reconnect, and lifecycle systems should be built upon rather than replaced.

## Adventure Integration

- `[HARDEN]` Enforce consistent battle interlocks across movement, search, leave, expiration, and reconnect.
- `[HARDEN]` Make Adventure result dispatch and reward delivery idempotent and retryable.
- `[BUILD]` Add a player-facing mission/job-board acquisition flow.
- `[FINISH]` Add explicit repeatability, cooldown, first-clear, and anti-grind policies.
- `[HARDEN]` Resolve simultaneous-session privacy and instance ownership.
- `[HARDEN]` Make Adventure content installation and upgrades deployment-safe and idempotent.

## Adventure Content

Deliver one polished Adventure slice containing:

- `[CONTENT]` One usable region/area
- `[CONTENT]` Authored missions/objectives
- `[CONTENT]` Search/investigation interactions
- `[CONTENT]` Wild Pokémon encounters
- `[CONTENT]` NPC trainer encounters
- `[CONTENT]` Success and failure conditions
- `[CONTENT]` Abandonment behavior
- `[CONTENT]` Rewards
- `[CONTENT]` Repeatability rules

The intended loop is:

**Take mission → enter Adventure → explore/search → encounter Pokémon/trainers → complete objective → return → receive result/reward**

## Deferred from Critical Path

Faction and reputation systems fit Adventure Mode well, but they are not required to prove the closed-beta gameplay loop. They may be added later if time and scope permit.

### November Exit Condition

A normal player can enter PF2 and complete a meaningful Adventure gameplay loop without staff intervention.

---

# December — Beta Hardening and Feature Freeze

December is primarily for proving reliability, recoverability, onboarding, and deployment readiness.

## Feature Freeze

Target feature freeze: **December 15, 2026**

After feature freeze, work should be limited primarily to:

- Critical bugs
- Data-loss or duplication defects
- Exploits
- Broken player UX
- Recovery tooling
- Documentation/help
- Regression testing
- Deployment and migration fixes

New gameplay systems and significant feature expansion should be deferred.

## Player Experience

- `[UX]` Finish onboarding, command discovery, help text, and error messages.
- `[UX]` Verify ANSI width behavior and screen-reader accessibility.
- `[TEST]` Verify in-game and website character-sheet consistency and permissions.

## Recovery and Integrity

- `[HARDEN]` Add audits and repair tools for:
  - Storage/placement
  - Capture
  - Trade
  - Marketplace
  - Fusion
  - Undelivered rewards
- `[HARDEN]` Review economy duplication, farming, and concurrent-transaction exploits.
- `[HARDEN]` Exercise disconnect/reconnect and stale-state cleanup across all persistent gameplay loops.

## Testing and Operations

- `[TEST]` Make required battle semantic, engine, and selected generated-contract tests coexist in one clean mandatory run.
- `[TEST]` Run fresh-install migration rehearsals.
- `[TEST]` Run upgrade migration rehearsals against representative database copies.
- `[BUILD]` Establish documented backup/restore procedures.
- `[TEST]` Perform and verify at least one successful restore.
- `[TEST]` Run a complete player journey without Builder commands.

The full player-journey test should cover:

**Chargen → Pokémon management → wild battle/capture → NPC battle → doubles → Terastallization → gym → trade → daycare/breeding → marketplace → Adventure**

### December Exit Condition

PF2 is ready for a persistent closed beta with no known unresolved critical data-loss, duplication, or state-corruption defects.

---

# PF2 Closed Beta Gate

PF2 should not be declared closed beta until all of the following are true:

- [ ] Player 1v1, doubles, wild, and NPC battles work without staff launch commands.
- [ ] Doubles has usable target selection, switching, AI, and encounter/gym configuration.
- [ ] Terastallization works end to end and survives persistence/reconnect.
- [ ] Battle results, rewards, Adventure results, and badge awards are idempotent and retryable.
- [ ] Catching, party/storage, move learning, evolution, and held-item transitions do not have known duplication or loss defects.
- [ ] Trading requires recipient consent and completes safely.
- [ ] Breeding, Daycare, and player Marketplace MVPs are player accessible and recoverable.
- [ ] Adoption has been resolved against PF1 parity and implemented if required.
- [ ] At least one strategy-oriented gym is fully player accessible with correct victory, loss, rematch, and badge behavior.
- [ ] Combat AI selects legal actions, handles core battle state correctly, supports switching and doubles targeting, and can execute the first gym's intended strategy.
- [ ] Fusion creation/state transitions are persistent, recoverable, and adequately explained during onboarding.
- [ ] One polished Adventure loop includes acquisition, encounters, objectives, failure/abandonment, reconnect, rewards, and cooldown rules.
- [ ] Adventure movement, expiration, exit, and reconnect cannot bypass or corrupt active battles.
- [ ] Reward/progression rules prevent obvious command grinding and repeatable farming exploits.
- [ ] Normal onboarding and principal gameplay loops do not require staff intervention.
- [ ] Staff can inspect and recover stalled battles, Adventures, transfers, placements, and undelivered rewards.
- [ ] Fresh-install and upgrade migrations pass on representative databases.
- [ ] Backup restoration has been successfully demonstrated.
- [ ] Mandatory test suites run together without order-dependent failures.
- [ ] No unresolved known data-loss, duplication, or persistent-state corruption defect remains.

---

# Explicitly Deferred / Not Closed-Beta Gates

The following are not required to declare PF2 closed beta:

- Multiple complete leagues
- Large numbers of finished gyms
- Faction/reputation systems
- Safari-style area
- Player-authored Trainer AI
- Sophisticated competitive battle prediction
- Large-scale procedural Adventure generation
- Extensive website redesign
- Every possible Fusion description/customization feature
- Every curated Mega Evolution
- Dynamax
- Z-Moves
- Generation 10 or later mechanics

These may be considered after the beta foundation is stable, but they should not delay the 2026 closed-beta target.

---

# Roadmap Change Policy

This roadmap is a planning constraint, not an immutable prediction.

Changes are appropriate when repository evidence, testing, or player feedback demonstrates that:

- A listed task is already sufficiently complete.
- A hidden dependency or correctness issue must be resolved first.
- A feature is not actually required for the stated milestone.
- A beta-critical capability was omitted.

New ideas and feature requests should normally enter the backlog rather than automatically joining the active 2026 roadmap.

Roadmap feedback should focus primarily on whether the stated milestones are missing something necessary to reach a stable closed beta.

---

# Review Cadence

At the end of each month:

1. Compare the roadmap against the actual repository state.
2. Mark completed work.
3. Identify work that slipped or changed scope.
4. Reconcile the next milestone with current implementation reality.
5. Avoid reopening already-completed systems without a concrete reason.
6. Keep post-beta ideas out of the active critical path unless they become genuine blockers.
