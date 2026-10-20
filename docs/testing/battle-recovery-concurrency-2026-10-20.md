# Local battle recovery and concurrency acceptance — 2026-10-20

**31/31 live scenarios, nine real server reloads, one natural reward-replay check, and the 20-scenario pilot passed on the repaired build.** Two game defects were diagnosed, reproduced with fresh fixtures, fixed, and retested.

Build: staging `af07850` plus the four source/test files listed below. Changes are local and uncommitted. No downloads, installs, migrations or remote operations were performed.

## Confirmed repairs

- **Native form names after recovery:** Evennia converted the `SpeciesName` string subclass into saved character lists. Restoring a transformed Ogerpon or Terapagos corrupted its display name and could raise a waiting-message exception. Checkpoints now write plain text, including nested native-form backups. All four Ogerpon forms and Terapagos passed repeated real Attribute rebuilds; live Hearthflame passed an actual server reload. Ordinary names and persisted nicknames remain intact.
- **Restored weather and terrain:** Field identifiers and timers survived, but their runtime handlers did not. Rebuild now reconnects handlers without replaying entry callbacks or resetting durations. Sun, rain, Electric Terrain and Grassy Terrain expire normally, including item-extended timers; live sun and Electric Terrain also expired correctly after real reloads.

## Live evidence

Two fresh ordinary Player accounts submitted battle choices over real localhost Telnet connections. A separate temporary setup account prepared only manifest-pinned fresh fixtures and observed state. Staff did not submit battle choices or replace mechanics callbacks. In-process checkpoint rebuilds and actual process-replacing reloads are identified separately in the JSON evidence.

| Coverage | Result |
| --- | --- |
| Pending singles actions through reconnect, rebuild and reload | PP remains unspent while waiting; one later turn executes once |
| Singles simultaneous commands | Ten barrier-synchronized turns; each turn and each PP debit occurs once |
| Doubles interleaving, invalid foreign actors, reconnect/rebuild/reload | Valid sibling choices survive; all four slots execute once |
| Invalid switch/item/actor commands | Existing queued legal action and resources preserved |
| Targeted Revive, Ether and Potion | Correct reserve/move/HP target; one inventory debit; retry does not repeat effects |
| Canonical reserve switch | Correct owned Pokémon becomes active after rebuild |
| Fly, Power Herb and Booster Energy | Charge/PP, consumption and native activation state survive recovery |
| Field effects and native Terastallization | Timers, used Tera budget and native identity remain correct |
| Concession, reconnect and retry | Locks clear; next battle works; completed battle does not resume |
| Natural wild knockout and replay | +36 EXP and +1 Speed EV once; reconnect and concurrent/repeated retry give no second award; encounter removed |

The independent proof audit checked 262 ordinary commands and 184 observations across all 31 live cases: zero errors. All cases ended through normal player cleanup; no staff fallback was required. The separate pilot retained-proof audit passed all 20 cases.

## Database and automated evidence

- **154/154 PostgreSQL tests passed** across 12 fresh disposable-schema suites: battle recovery, player doubles, trainer challenge, capture/Ether, captured PP, remaining items, gym/Adventure recovery, progression, Tera, status items, cloud gameplay and Adventure lifecycle.
- SQL tests include failed checkpoint/reward/cleanup writes, runtime and RNG rollback, stale checkpoint replay, duplicate and distinct concurrent claims, concurrent capture and last-Ether use, foreign claims, restored doubles choices, faint/reserve state and stale cleanup versus a newer battle. Fault injection remained in disposable schemas. Public gameplay fingerprints and both battle-registry metadata values were unchanged across the final quiet SQL run. All generated schemas were removed.
- **7/7 real Twisted AMP wire tests passed** with database access blocked. These are transport tests and are separate from the nine real live reloads.
- **8,213 all-options pytest tests passed**, including installed local dex, callback and Showdown checks. No reference files were fetched. Existing model-reimport/deprecation warnings remain; no final failures.
- Loaded-code audits before and after final acceptance matched **50 modules / 2,738 functions** to the pinned repaired source. Generated/external functions are listed separately.

## Diagnosed test setup issues

Two original SQL-suite errors came from mock player/room wrappers missing the real objects’ `pk` alias; their recovery assertions had succeeded. The fixtures now expose the correct keys. Other retained false flags involved saver-container JSON formatting, lowercase inventory names, the field-timer observation path, an unsaved nickname fixture, public metadata being compared while authorized live QA was advancing it, and an all-options temporary directory placed inside the artifact tree. These were corrected in observations/fixtures/orchestration, and affected checks were rerun. No game rule was changed to force an otherwise expected failure to succeed.

## Protected data and cleanup

- A verified 471,212-byte local PostgreSQL backup preceded fixture creation. Its SHA-256 is `c46f89a8df38ba0280249d4854afff6f1b3d476a26f56bc549f32869c0cd0151`.
- **All 7,157 pre-existing protected rows across 32 tables remain byte-for-byte unchanged**, covering existing characters, Pokémon, placements, ownership, storage and related attributes. A final read-only fingerprint check also followed the automated gates.
- All three fresh QA accounts are disabled, their passwords are unusable, temporary staff access is removed, and the credential file is deleted. They retain 1 fresh QA-owned Pokémon; no existing Pokémon were deleted or edited.
- The original room registry and live cache were restored exactly; the advanced QA battle counter was retained to avoid ID reuse. Pre-existing unrelated lock values were preserved.
- All 1,113 pinned original project files match the accepted build; only the four authorized recovery/test files differ from the original snapshot. The two pre-existing untracked item reports were preserved.
- Credential scan: 2519 files, zero exact-password matches or scan errors. Raw evidence, backups, transcript rotations and automated logs remain under already ignored `.codex-artifacts/`; game logs and pytest temporary directories are already ignored.

## Files changed

- `pokemon/battle/_shared.py`
- `pokemon/battle/battledata.py`
- `pokemon/battle/logic.py`
- `tests/integration/battle_recovery_cases.py`

## Remaining acceptance boundaries

- Abrupt process termination/power-loss and cold-boot acceptance were not run on the live game.
- These bounded action/claim races are not sustained load or many-room concurrency testing.
- The full species/move/ability/item catalog was not rerun after these recovery changes.
- Remote deployment, migration rehearsal and browser-client acceptance remain separate.

[Machine-readable case matrix and diagnosis record](battle-recovery-concurrency-2026-10-20.json).

Raw retained evidence: `H:\PokemonFusionProject\fusion2\.codex-artifacts\battle-recovery-live-20261020`.
