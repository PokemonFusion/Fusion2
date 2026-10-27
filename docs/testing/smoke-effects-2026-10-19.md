# Actual-effect acceptance for the remaining 374 smoke checks — 2026-10-19

Completed locally on 2026-10-19T06:22:03.573199+00:00. All **374 original smoke entries** now map to retained effect evidence: **108 moves and 265 abilities have a verified positive effect**, and **No Ability passes an explicit expected-no-effect comparison**. No unexplained effect failure remains in this scope. Historical full-catalog smoke labels and original raw evidence were preserved.

## What was actually tested

Fresh ordinary Player accounts submitted real Telnet commands to `127.0.0.1:4000`. A separate temporary staff account prepared new owned fixtures in a private QA room, set reproducible private-battle seeds, and read state. Battle choices, switching, targeting, escape and Terastallization went through the ordinary commands. No callback was replaced or forced to return success, and the global random generator was not changed.

The move plan contains **108 subjects and 137 independent fixtures**, with direct assertions or matched comparisons of HP, healing, consumed items, owned PP, stats, status, side conditions, ability copying, blocked/allowed choices, critical damage, and action order. Execution text and spent PP cannot substitute for an effect. Lock-On/Mind Reader require an unassisted miss followed by an assisted hit; Metronome requires an observed damaging called move. Natural windows without the requested branch remain retained as inconclusive attempts.

The 266 former ability smoke entries were exercised with matched control/carrier fixtures plus gap, wild, post-battle and native Terapagos cases. The 265 meaningful abilities each have a declared positive trigger in the explicit map. No Ability is a placeholder: its comparison verifies the intended absence of an effect in PvP and is not described as a positive trigger.

| Final phase | Count | Retained current result |
| --- | ---: | --- |
| Moves (subjects) | 108 | 108 outcome_verified |
| Abilities (main matched pairs) | 242 | 242 outcome_verified |
| Additional ability pairs | 18 | 18 outcome_verified |
| Ability gap pairs, including bounded windows | 95 | 82 outcome_verified, 13 chance_not_observed |
| Wild battle cases | 11 | 11 outcome_verified |
| Post-battle item cases | 10 | 9 outcome_verified, 1 chance_not_observed |
| Native Terapagos/Teraform Zero cases | 14 | 14 passed |
| No Ability matched comparison | 1 subject / 2 fixtures | Expected no effect verified |
| Standard real-login pilot | 20 | 20 passed |

Natural non-proc ability windows remain in the raw results when another qualified window proves that ability's effect. They are not silently relabeled as successful procs. The strict map contains **373 `effect_verified` and 1 `expected_no_effect_verified`**, with no pending entries.

## Diagnoses and repairs

Unexpected observations were checked against the checked-in move reference and their exact commands, preconditions and state. Fresh isolated reproductions preceded game edits. **42 move-specific failures were reproduced and grouped into 22 mechanics defects.** All 22 groups now pass their affected local effect checks on the final build.

| Affected moves | Reproduced cause, repaired and verified |
| --- | --- |
| Aromatherapy, Heal Bell | Handlers read user.party, absent on native battle objects, and fall back to only the active user instead of the participant roster. |
| Doodle | Only the user receives the ability; the living active ally is omitted. |
| Natural Gift | PrepareHit reads berry type/power but never consumes the berry or emits its use lifecycle. |
| Stockpile, Spit Up, Swallow | Stockpile does not apply its defensive stages or keep layers in checkpoint state; consuming moves cannot remove the actual gained boosts correctly. |
| Power Trick, Power Shift | Handlers toggle unused attributes/flags rather than the stored stats read by damage and checkpoint reconstruction. |
| Embargo | Residual dispatch uses the raw held item instead of the effective suppressed-item resolver, so Leftovers still heals. |
| Imprison | The foe pre-move dispatcher supplies the holder without the actor or selected move; the callback blocks every opposing choice instead of only shared moves. Functional allowed-choice reproduction is retained. |
| Baneful Bunker, Burning Bulwark, King's Shield, Obstruct, Silk Trap, Spiky Shield | Some casts status their own user; the generic protect early exit also bypasses the named guard's contact retaliation. |
| Endure | The direct damage path omits the volatile Damage guard; a protected Abra still faints from a lethal hit. |
| Foresight, Odor Sleuth, Miracle Eye | The relevant Ghost/Dark type-immunity component is not bypassed by the live identification volatile. |
| Lock-On, Mind Reader | The callbacks use inconsistent lock keys and transient target references; the accuracy consumer does not enforce the matching target's guaranteed next hit. |
| Grudge | The KO callback sets only last_move.pp to zero; the independent owned slot keeps 24 PP. |
| Electro Ball, Gyro Ball | Power callbacks read unmodified base Speed and ignore the observed Agility stages. |
| Grass Knot, Low Kick, Heat Crash, Heavy Slam | The setup move marks an unused boolean; no effective-weight consumer subtracts its stacking 100 kg reduction. |
| Return, Frustration, Pika Papow, Veevee Volley | Canonical owned friendship is not hydrated/preserved as the battle happiness value, so 0 and 255 give identical power. |
| Trump Card | The temporary damage move's PP is overwritten by the raw definition's PP capacity, hiding the authoritative remaining slot PP. |
| Defog, Tidy Up | Cleanup omits canonical side-condition/screen/terrain/substitute components. Raw setup feedback was separated from these actual missing outcomes. |
| Electrify | The same-turn conversion remains on later turns because its boolean volatile never expires. |
| Powder | The volatile does not reliably cancel the Fire action and apply its one-quarter-max-HP damage in the live pre-move path. |
| Beat Up | Party selection again falls back to the user, so adding healthy benched Pokémon produces no additional damage/hits. |
| Helping Hand | The ally's Helping Hand state is not consumed by the live damage power resolver; matched damage is unchanged. |
| Dragon Cheer | Critical resolution only reads Focus Energy/Laser Focus, omitting Dragon Cheer's species-dependent critical stages. |

Fixture and observer issues were diagnosed separately. These included demanding permanent ownership changes for temporary battle item swaps, inspecting a replacement Pokémon instead of the fainted original, allowing Copycat to copy a later Splash, checking the wrong PP slot in controls, a spaced moveslot lookup, an insufficient Metronome window, and a tuple/list audit serialization mismatch. Natural critical controls and ordinary accuracy misses were kept separate from defects. The log scanner was also corrected so normal “critical capture” text does not count as a CRITICAL severity error; its false flag and successful fresh replay are retained.

Added regressions cover the repaired effects and relevant negatives, including berry reuse, enemy-versus-party cures, shared-only Imprison, contact avoidance, Endure versus indirect damage, lock target/expiry/Protect, stockpile consumption, checkpoints, owned PP and friendship. Six older test fixtures were updated for the actual repaired contract rather than weakening the rules.

## Validation and build identity

The final candidate passed **3,891 tests in each of three clean processes**: combined, repeat, and battle-first. Each run skipped 4,010 optional tests; those skips are not represented as gameplay coverage. The focused repair/runner group passed 88 checks, and the gate-fixture review passed 377.

An authorized local reload loaded the candidate. Read-only structural auditing compared **2,238 source-defined functions across 45 loaded modules**, with zero source mismatches; 46 runtime source files and 112 changed/local Python files were pinned. Every final retained gameplay observation uses the same loaded version group:

`58a050cf4cca3ff84e3679b8de89c86fab833301281aef032689131166ff9867`

The independent final audit checked **904 current records** and **3121 observations**, exact evidence checksums, ordinary battler identities, callback failures, cleanup, saved move-effect rules, gap comparisons and the pilot. All passed. Diagnostic/pre-repair evidence lives in separate archives and is excluded from the final build claim.

## Existing data and cleanup

Verified PostgreSQL backups preceded initial QA preparation and the reload. All **5,850 pre-existing gameplay/object rows**, including existing characters and Pokémon, remain byte-for-byte equivalent under the saved row fingerprints. The four unrelated work-in-progress files remain unchanged. The unrelated out-of-character connection retained the same portal session across the reload; it was never puppeted, disconnected, or used for commands.

Only this task's fresh QA accounts **43, 44 and 45** were used. They are now disabled, their staff/superuser rights are removed, their passwords are unusable, and the temporary credential file is deleted. Exact secret-byte scans before and after deletion passed in one process. No downloads, dependency installs or migrations occurred.

Large transcripts rotate and compress. All run artifacts are under the existing ignored `.codex-artifacts/` tree, and runtime `*.log` files are already ignored; no additional broad ignore rule was needed.

## Reuse and limits

Reusable move plans, effect evaluation, guarded observations and strict mapping live in `tools/live_smoke_effects_cases.py`, `tools/live_smoke_effects.py`, `tools/live_smoke_effects_server.py`, and `tools/live_smoke_effect_coverage.py`; regressions live in `tests/test_live_smoke_effects.py` and `pokemon/battle/tests/test_smoke_discovered_effects.py`. The local ability orchestration and exact retained plans are alongside this run's proof.

A future run must prepare a **new** guarded QA manifest and accounts; completed accounts must stay disabled. `run --rerun-all` requests fresh move evidence; `audit` reassesses saved exact probes and checksums. The coverage tool's `--require-complete` enforces all 374 mappings and phase audits.

This proves the declared effects with prepared local fixtures. It does not prove every species/move/ability interaction, generation variant, chance distribution, natural learnset or progression route, browser UI, multiplayer concurrency, or deployment. The earlier full-catalog sweep remains historical evidence for its own build; this run did not repeat all 2,693 catalog entries.

Private retained evidence: `.codex-artifacts/smoke-effects-20261019/`. Key indices are `smoke-effect-coverage.json`, `mechanics-diagnoses-before-fixes.json`, `mechanics-repair-acceptance.json`, `final-independent-audit.json`, and `final-account-safety.json`. All source changes remain local and uncommitted.
