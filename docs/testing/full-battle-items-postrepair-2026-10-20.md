# Full local battle-item sweep after repairs — 2026-10-20

Fresh logged-in acceptance covered **all 283 retained items** on commit `af07850`. The run attempted **426 PvP effect/interaction checks in 570 retained final battle cases**, plus **eight reward-item checks against a ninth control battle**. No evidence from an earlier build was substituted for a current result.

Item outcomes: **283 verified**, **0 need work**. PvP checks: **426/426 passed**; reward effects: **8/8 verified**.

The [current 576-definition matrix](full-battle-items-postrepair-2026-10-20.json) lists every retained or excluded item and links retained items to current checks. The [earlier repair report](battle-item-repairs-2026-10-20.md) explains the source changes and existing issue groups; the earlier reports remain historical evidence.

## Execution and diagnosis

A verified local PostgreSQL dump and protected-row baseline preceded three new QA accounts and a private room. Two ordinary Player accounts submitted real localhost battle, item, attack and switch commands. A separate setup account prepared only fresh tagged fixtures and observed state. Individual probes isolate effects with prepared moves/abilities; the complete team matches use native abilities and actual local learnsets. Chance-dependent effects used 84 natural windows across 19 probes. Retries and the Psychic Gem confirmation brought actual PvP executions to 674. No hit, critical, survival, priority or flinch result was forced.

- **gem-psychicgem — runner_false_flag_expected_secondary**: The HP-delta comparison includes expected confusion self-damage. The actual second Confusion move dealt 36 HP in each battle; the held branch also lost 56 HP to confusion and could not use Splash. The Gem consumed on the first hit.

No unresolved item-effect failures or unobserved chance checks remain in the final matrix.

The Psychic Gem assertion was corrected in the private runner after its original observations were retained. A fresh matched rerun checks native direct move damage and one-use power/consumption; confusion self-damage is kept separate. No game source was changed or server reload required during this sweep.

## Independent verification

- Re-evaluated all **426** declared item checks, **570** current case archives, exact ordinary-player commands, SHA-256 hashes, runtime code identity, and cleanup: **zero audit errors**.
- Loaded-code audit before and after acceptance: **50 modules / 2,738 functions matched**; 67 generated/external functions are listed separately.
- All **20** real-login pilot scenarios and their retained-proof audit passed.
- Five complete native team matches finished by knockout with no concessions or staff cleanup; nine reward/control wild encounters also finished by knockout and were deleted normally.
- Consumed Oran Berry state remained absent after natural victory and encounter cleanup.
- The previously completed automated gates (8,213 all-options passes and 4,199 passes in each of three mandatory orders) belong to this unchanged source snapshot; they were not rerun for this live-only acceptance.

| Complete team match | Turns |
| --- | ---: |
| ordinary-full-single | 18 |
| ordinary-full-single-reverse | 20 |
| ordinary-full-double | 9 |
| ordinary-npc-single | 12 |
| ordinary-npc-double | 4 |

## Protected data and cleanup

- **All 7,037 pre-existing protected rows across 32 tables remain unchanged.** Existing characters, Pokémon, ownership, placements, storage and related protected records were not edited or deleted.
- All three fresh QA accounts are inactive; passwords are unusable, temporary staff access is removed, and the credential file is deleted. The disabled QA identities retain one newly created QA-owned Pokémon.
- The original room registry was restored exactly and its live cache refreshed; the QA-advanced battle counter was retained to avoid ID reuse. Existing unrelated battle-lock values were preserved.
- All 1,111 original nonignored project files remained byte-for-byte unchanged. Only this report and its JSON matrix were added afterward.
- The final credential scan checked 1024 files with zero matches or scan errors. Raw evidence, backups, rotating/compressed logs and runner snapshots remain in already ignored `.codex-artifacts/`; game logs are ignored too.
- No downloads, dependency installs, migrations, game-source edits, service restarts, GitHub writes, commits, pushes or remote deployments were performed for this rerun.

## Remaining acceptance boundaries

Passing this sweep verifies the declared effects for the 283 retained items. It does not implement or qualify the 293 excluded definitions, missing field `+use`/manual berry/evolution/training routes, acquisition paths, full Mega/Z functionality, or every item/ability/move combination. Probability distributions, abrupt reconnects, concurrent players, browser UI and remote deployment acceptance remain separate.

Global weather/terrain moves can still print a redundant no-effect line for an additional target after successfully applying the field. Explicit field-state, lifetime and actual-effect assertions establish the mechanics here; the misleading narration remains a presentation follow-up.

## Local evidence

Evidence is retained under `.codex-artifacts/full-items-postrepair-20261020/`: `final-item-plan.json`, `item-evidence-audit.json`, `complete-battle-evidence-audit.json`, `diagnoses/`, `pilot-final/evidence-audit.json`, `candidate01-source.zip`, both loaded-code audits, the verified pre-QA database dump, source/data/account safety reports and runner sources addressed by their recorded hashes. Future execution requires fresh QA credentials.
