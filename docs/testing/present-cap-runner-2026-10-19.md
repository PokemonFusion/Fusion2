# Present full-HP healing-cap runner repair — 2026-10-19

Present's game behavior was already correct. Its natural healing branch restores one-quarter maximum HP, capped by missing HP; at full HP this correctly restores zero and the game reports no effect. The old generic observer retained only move name/type, so it could not identify that branch. No game mechanics were changed.

## Runner change

`tools/live_dex_server.py` now records the executed move's actual `power` and `heal` alongside name/type. `tools/live_dex_runner.py` recognizes the cap only in the isolated one-turn Present/Splash probe when the selected branch is Present/Normal, power 0, heal 0.25; the same owned target remains at the same full maximum HP; exactly one owned PP is spent; a real turn resolves; and the ordinary fixture has no competing status, item, ability, protection, field effect or unexplained failure. Existing callback/server-error checks and declared assertions still apply.

The result is `expected_failure` with `expected_healing_cap_verified=true` and `positive_outcome_verified=false`. A zero heal is expected-negative proof, never positive healing proof. Missing branch data cannot retroactively identify an old random roll, and the earlier full-sweep evidence and reports remain unchanged. Damage-branch no-effect, missing injured-target healing, wrong target, wrong branch, missing PP and other unexplained failures remain diagnoses.

## Fresh local gameplay

Two fresh ordinary QA players issued real Telnet battle commands on localhost. A separate guarded staff account supplied only new QA fixtures and read-only observations. Present's damage/healing selection used natural, unpatched random rolls; the private battle seed is not claimed to force that selection.

| Check | Fresh result |
| --- | ---: |
| Present independent battles | 48 |
| Observed full-HP healing caps | 3 expected negatives: 430 → 430 / 430 HP |
| Observed positive injured-target healing | 3: 305 → 457 / 610 HP (floor(610 / 4) = 152) |
| Observed damage branches | 42 damaging results; powers 40, 80 and 120 all observed |
| Neighbor regressions | 4 / 4: Recover, Heal Pulse, Tackle, Plasma Fists |
| Behavioral pilot | 20 / 20 passed, including Flash Fire and Fly |
| Unresolved game/runner flags | 0 |

The Present window used the exact full-health catalog fixture for 28 battles, followed by 20 independent injured-target battles with No Guard to remove accuracy noise while leaving branch selection natural. All attempts are retained, including legitimate knockouts. The first evidence-helper check encountered the ended battle's empty active slot; it was corrected to follow the original Pokémon in the ended party. The original successful damage result was retained and requalified; no game or frozen runner change was needed.

The generic Present records retain their honest raw smoke classifications when they do not declare positive assertions. A separate branch/HP qualification index proves the observed healing and damage effects. These qualifications do not relabel smoke as comprehensive move coverage or prove the random distribution.

## Automated tests and evidence

`tests/test_live_dex_present.py` adds 31 regressions for the expected cap, JSON fixture round trips, absent/wrong healing and damage branches, injured/changed targets, competing effects, unexplained failure text, PP/turn requirements, callback/server exceptions and positive healing/damage controls. Focused runner suites passed **117 tests**. A fresh mandatory gate passed **3,973 tests in each of three clean suite orders** (combined, repeat, battle-first), with **4,010 skipped per order**; its controller exited 0. Existing model-registration warnings remain in the retained log.

The independent audit re-evaluated **72 records / 147 observations**, every exact saved fixture, selected Present branches and HP results, owned PP, ordinary-player identities, normal cleanup and evidence hashes. It checked **104 canonical maximum-HP values** using `get_max_hp`. All observations use one version group: `128773e3f46c6de792667f87abe01579f13bb7b47c7028d0aaa83406ca965376`. Loaded code audits before and after checked **2,238 functions across 45 game modules**, with zero mismatches; game code matches the preceding full-sweep build. **114 Python source files and 46 runtime source files** were pinned throughout validation.

## Preservation and cleanup

A verified custom-format PostgreSQL backup was taken before creating accounts. All **6,307 pre-existing Pokémon/gameplay/object rows** remained unchanged, including character-linked attributes. Of 130 pre-existing dirty files, only the two authorized QA runner/observer files changed; the other **128** stayed byte-identical. The only new public source artifacts are the regression test and this report.

Only fresh QA accounts **55, 56, 57**, characters **168, 169, 170**, trainers **72, 73** and private room **167** were used. These accounts are now inactive, passwords unusable, staff/superuser rights removed and temporary credentials deleted. Exact credential-byte scans before and after deletion passed in the same process. Earlier QA accounts stayed disabled. No downloads, dependency installs, migrations, service reloads/restarts, remote operations or commits occurred.

Raw evidence, compressed transcripts, source pins, backup, branch qualifications, test logs and safety reports live under the already ignored `.codex-artifacts/present-cap-runner-20261019/` and sibling `present-cap-runner-20261019-work/`. No ignore-file edit was needed. This validation proves the declared local gameplay contexts; it does not constitute a new full dex sweep or proof of every interaction.

Key indices: `present-qualifications.json`, `results.json`, `pilot-final/results.json`, `final-independent-audit.json`, `current-evidence-sha256.json`, `mandatory-gate-proof.json`, `final-account-safety.json`, `completion.json`.
