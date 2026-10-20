# Local battle-item repair acceptance — 2026-10-20

All 51 failed or unobserved checks retained from the [earlier item audit](battle-items-2026-10-20.md) now have passing effect evidence. The final local build passed **130 checks across 79 affected items, using 176 PvP battle cases**, plus the **20-scenario pilot**. These are checks, not 51 distinct defects. All 62 items previously marked `needs_work` are represented in this affected rerun.

This report supersedes the earlier report's outstanding diagnosis list. Its remaining historical results are preserved as evidence from that earlier build. This was an affected-item rerun, not a new sweep of all 283 retained items or all 576 definitions.

## Repairs by existing issue

| Existing issue | Repair and observed acceptance |
| --- | --- |
| [#747](https://github.com/PokemonFusion/Fusion2/issues/747) | Followed the existing item tracker and bounded groups below. No issue was closed or changed. |
| [#748](https://github.com/PokemonFusion/Fusion2/issues/748) | Battle medicine selects an exact owned party/Fusion target, including fainted reserves. Validated placement/ownership, one inventory debit, replay protection, checkpoint identity, and no-effect preservation. |
| [#749](https://github.com/PokemonFusion/Fusion2/issues/749) | Energy Powder, Energy Root, Heal Powder, Revival Herb, Max Ether, Elixir, and Max Elixir now use the battle medicine/PP service. Ether/Max Ether support selected move slots/names; boosted PP caps and bitterness persist. Runtime HP/status/PP updates occur before subsequent actions and the turn checkpoint, including inside the outer battle transaction. |
| [#751](https://github.com/PokemonFusion/Fusion2/issues/751) | Shell Bell uses actual aggregate spread damage once per move. The retained Surf fixture dealt 60 total HP and healed 7 HP. Single-target, Substitute, and non-damaging guards also passed. |
| [#752](https://github.com/PokemonFusion/Fusion2/issues/752) | Utility Umbrella applies holder-local weather rules to damage, Thunder/Hurricane accuracy, Weather Ball, and solar charging paths. Nearby Boots/Pads and suppression checks passed. |
| [#753](https://github.com/PokemonFusion/Fusion2/issues/753) | Blunder Policy reacts to an actual accuracy miss; Metronome tracks repeated moves and resets; Gems consume only after qualifying damage and remain held on immunity, Protect, or a miss. Successful power, second-use, and Substitute cases passed. |
| [#757](https://github.com/PokemonFusion/Fusion2/issues/757) | Joined held-item move/hit hooks and effective-item consumers; repaired the native effects listed below. |

The #757 repairs cover:

- Punching Glove contact removal, Loaded Dice hit counts, and actual King's Rock/Razor Fang flinches.
- Enigma Berry healing, Room Service/Mirror Herb event ownership, and Adrenaline Orb activation from native Intimidate.
- Air Balloon immunity/pop, Ring Target immunity negation, Safety Goggles protection, and Float Stone weight.
- Eject Button, Eject Pack, and Red Card switching, including no-reserve negatives; Binding Band residual damage, Grip Claw duration, and Destiny Knot reflection.
- Choice Band/Specs/Scarf legal locked moves and reset after switching; Assault Vest status restriction; Life Orb successful-damage, Magic Guard, and Sheer Force guards.
- Power Herb charge release and sun retention; Booster Energy's native Protosynthesis/Quark Drive activation, damage or turn-order effect, and consumption.
- Existing Blue Orb/Red Orb forms and Rusted Sword/Shield crowned forms. Behemoth Blade/Bash spends PP from the original Iron Head slot; ineligible species retain their form and item. This does not implement a full Mega/Z system.
- Weather/terrain expiry through canonical clearing, ending field-dependent Protosynthesis/Quark Drive boosts. Terrain Extender and Heat Rock were observed through the full eight-turn lifetime and a subsequent unboosted turn.

The qualifying-hit path also stops raw status/secondary effects after a miss or immunity. This repairs the diagnosed Inferno burn and Dynamic Punch confusion after misses. Bitter Malice's positive regression now uses a susceptible target; immunity remains ineffective.

## Diagnosis before repair

Fresh tagged fixtures and retained commands/states distinguish mechanics failures from expected outcomes. Positive and relevant negative regressions accompany the production changes.

The priority live revival rerun exposed an additional persistence defect: an `on_commit` runtime update waited until after the outer turn transaction. Faint processing/checkpoint saving therefore saw stale zero HP. Real PostgreSQL regressions reproduced both revival and PP ordering inside an outer transaction before the service was corrected.

The final live rerun exposed eight assertion/fixture flags, not additional item-effect defects:

| Flag | Diagnosis and corrected proof |
| --- | --- |
| Enigma Berry | A 16-HP super-effective hit was fully offset by capped healing. Replaced the incorrect net-damage requirement; both full-HP cap and wounded-holder quarter-HP healing now pass. |
| Three Choice items | The assertion read final PP after a later legal move instead of PP immediately after the rejected move. The corrected point-in-time assertion proves Water Gun remains at 25 PP while locked, then reaches 24 after switching resets the lock. |
| Two field-expiry probes | Added explicit active/expired field assertions and observed the move that actually spent PP in the control. Native ability activation ends; Quark Drive's turn-order advantage ends and post-sun damage matches its control. |
| Two flinch items | The game says the target is “unable to move,” rather than spelling out “flinch.” Matched no-item controls spend one PP; item holders prevent the target's move without spending target PP. Fresh healthy fixtures exclude other prevention causes. The native secondary is installed; neither probability nor success was forced. |

The revival fixture also now observes the opponent's Splash PP, because using medicine correctly replaces the user's move action. Earlier failed attempts remain separate from the final case declarations.

## Final verification

| Verification | Final result |
| --- | --- |
| Mandatory combined, repeat, and battle-first processes | 4,199 passed each; 4,014 optional skips each |
| All options: local dex, Showdown, callbacks | 8,213 passed |
| Standalone isolated PostgreSQL item suites | 8 + 16 + 21 passed; disposable schemas removed |
| Affected live item assertions | 130/130 passed; 79 items; 176 distinct battle cases |
| Independent item evidence audit | 130 re-evaluated; zero errors |
| Loaded game source, before and after acceptance | 50 modules / 2,738 functions matched; zero mismatches; 67 generated/external functions listed separately |
| Real-login pilot and independent pilot audit | 20/20 passed; zero evidence errors |
| Complete native team matches | Five finished by team knockout; no concession or staff cleanup |
| Reward/control wild battles | Nine finished by knockout; control and eight reward effects passed |
| Oran Berry wild lifecycle | Consumption persisted through natural victory and encounter cleanup |

The complete matches used native abilities and actual local learnsets, ordinary Player commands, and natural battle randomness. Staff prepared only new fixtures and disposable encounters. PvP included voluntary switching and one persisted Potion debit in each match. Items and HP were checked against durable owned state. The independent complete-battle audit checked code versions, evidence hashes, outcomes, ordinary-player status, and cleanup.

| Complete match | Turns |
| --- | ---: |
| Six-on-six singles | 18 |
| Six-on-six singles, reversed teams | 19 |
| Six-on-six doubles | 7 |
| Three-on-three NPC singles | 12 |
| Three-on-three NPC doubles | 4 |

## Data safety and cleanup

- **All 6,917 pre-existing protected rows across 32 tables remained unchanged.** Existing characters, Pokémon, ownership, storage, placements, and related protected data were not edited or deleted.
- A verified PostgreSQL backup and the initial source snapshot were retained before QA. Only fresh manifest-pinned QA accounts/characters and their fixture Pokémon were used. All three QA accounts are now inactive, passwords unusable, setup staff privileges removed, and the credential file deleted. One newly created QA-owned Pokémon remains attached to the disabled QA identity.
- The original room registry was restored exactly and its live cache refreshed. The QA-advanced battle counter was retained to prevent ID reuse. Original unrelated character battle-lock values were preserved.
- Offline collection initially reached `ServerConfig` despite the no-Evennia flag. Only the test-written battle registry/counter metadata was restored from the verified backup; runtime clock metadata was preserved. Protected character/Pokémon records never changed. The offline suite now refuses ORM connections before collection, and its incomplete unit mocks were corrected. All three fresh mandatory processes and the all-options process passed with that guard enabled.
- Of 1,106 original nonignored files, 1,080 remain byte-for-byte unchanged. Twenty-six existing files contain scoped repair/observer/test changes and three new Python files contain regressions. The frozen 1,109-file candidate had no drift at final acceptance; these two report artifacts were added afterward.
- Logs, compressed evidence, source archives and backups remain in already ignored `.codex-artifacts/`; game logs are ignored too. The final credential scan covered 631 files and found no secret matches or scan errors.
- No downloads, dependency installs, migrations, commits, GitHub writes, remote reloads, or production deployments were performed. Authorized reloads affected only the local server.

## Scope still requiring separate acceptance

No item-effect failures remain in this repair set. The broader issues remain open: field `+use` medicine and manual berry routes, field evolution/training and acquisition paths, excluded definitions/new item groups, and any full Mega/Z functionality still need their own implementation/acceptance where missing.

A fresh full 283-item rerun should follow these shared battle-engine changes before combining this result with historical item coverage. Pairwise ability/item/move interactions, probability distributions, disconnect/reconnect and concurrent-player lifecycle cases, browser UI, and remote deployment acceptance are not established by these bounded tests.

Global weather/terrain moves can still print a redundant “no effect” line for an additional target after successfully applying their field effect. Explicit state, lifetime, and actual-effect assertions prove the effect here; the misleading narration remains a separate presentation follow-up.

## Retained evidence

The [machine-readable repair matrix](battle-item-repairs-2026-10-20.json) records each current check, issue attribution, case hashes, observed effects, and build identity. Private raw evidence is under `.codex-artifacts/item-repairs-20261020/`:

- `final-item-plan.json`, `item-effect-results.json`, `item-evidence-audit.json`, `complete-battle-evidence-audit.json`, and `pilot-final/evidence-audit.json`.
- `candidate07-source.zip`, `candidate07-loaded-code-audit-before.json`, `candidate07-loaded-code-audit.json`, and archived runner sources addressed by their recorded SHA-256 values.
- `final-protection.json`, `final-source-protection.json`, `final-registry-protection.json`, `final-account-safety.json`, and `secret-scan-after-disable.json`.

Executable runners and failed attempts are retained there. A future run must prepare fresh QA accounts; these credentials have been retired.
