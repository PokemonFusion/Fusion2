# Local battle-item effect audit - 2026-10-20

**The battle system is not ready for release.** The ordinary battle workflow works in the completed matches, but live effect checks still expose concrete mechanics gaps and known missing item routes.

The final audited build tested **283 retained battle/reward items**, using **407 effect/interaction checks** (543 retained PvP cases) plus eight item reward checks against a natural wild-battle control. There are **364 verified checks, 49 failed checks, and two unobserved chance branches**. Failures are checks, not a count of distinct defects.

The complete 576-definition classification is in [the per-item matrix](battle-item-matrix-2026-10-20.json). Items marked `tested_effects_verified` have passed their declared checks; that does not qualify every species, interaction, item removal/replacement, rebuild, or acquisition path. All eighteen Gems remain marked for work because they share the demonstrated consumption-gating defect.

## Existing issue scope

Read the current open item tracker [#747](https://github.com/PokemonFusion/Fusion2/issues/747) and groups #748-#762. This run concentrates on existing battle effects and verification [#757](https://github.com/PokemonFusion/Fusion2/issues/757). Field evolution, field growth/training, capture/TR/TM expansion, full Mega/Z mechanics, redundant incense, and collector/clutter definitions account for the 293 exclusions. No new item definitions, migrations, downloads, GitHub issue changes, commits, or remote/production deployments were performed.

Staff prepared only new, manifest-pinned QA fixtures. Two ordinary Player accounts submitted real localhost PvP/item/attack/switch commands. Individual effect probes sometimes use staff-supplied moves/abilities for isolation. The complete-match teams use native abilities and moves from their actual local learnsets. NPC opponents are newly created disposable encounters; no public trainer or player party was reused.

## Repairs loaded and verified

- Chilan neutral-Normal reduction; Lum confusion/status cure timing; Leppa authoritative owned PP and boosted caps; Micle activation and a directly observed accuracy outcome; five flavor berries with nature and Own Tempo handling.
- Berry/Gold Berry held activation and amounts; Ice Berry burn cure; Bitter/Miracle volatile confusion cure; Mystery Berry authoritative depleted PP without uncached-move exceptions.
- Native Eviolite eligibility; Heavy-Duty Boots across all four hazards with Klutz negative proof; Protective Pads against Rocky Helmet with suppression proof.
- Shell Bell actual single-target/Substitute damage and no stale status-move healing. **Spread aggregation remains broken.**
- All eighteen Gems now boost one matching attack by 1.3 without offensive stat stages; second unboosted attacks and Substitute power were checked. **Miss/protection/immunity consumption remains broken.**
- Native effective weather rocks, Light Clay screen duration callbacks, and their full expiration lifetimes. Safeguard remains five turns. Terrain Extender now sets the right counter, but the general terrain expiration defect keeps it incomplete.
- Zoom Lens now uses the target remaining-action queue. Positive late movement and an expected-negative early-movement miss were observed.
- Held consumption persists to owned Pokemon through normal battle end; item update registration is deduplicated and replacement-safe.
- Power-item EV aliases retain the species yield, and native reward callbacks are not applied twice. Live Power Anklet now gives nine Speed EVs against the one-EV Rattata control; all eight reward items pass.

## Complete ordinary-player battles

| Match | Turns | Completion |
|---|---:|---|
| ordinary-full-single | 18 | Natural team knockout; HP/items saved |
| ordinary-full-single-reverse | 21 | Natural team knockout; HP/items saved |
| ordinary-full-double | 7 | Natural team knockout; HP/items saved |
| ordinary-npc-single | 12 | Natural team knockout; HP/items saved |
| ordinary-npc-double | 5 | Natural team knockout; HP/items saved |

The three PvP matches were six-on-six (two singles and one doubles). Both NPC matches were three-on-three. PvP also used a voluntary switch, ordinary Potion choice, and exactly one saved inventory debit. There were no staff battle choices, concessions, or forced cleanup in these five completed matches. All nine reward/control wild encounters ended by knockout and were deleted normally.

The separate 20-scenario real-login pilot passed and its evidence audit passed. The additional Oran wild lifecycle check confirms consumed held items remain absent after normal victory and encounter cleanup.

## Remaining work by existing issue

| Issue | Diagnosed work |
|---|---|
| [#748](https://github.com/PokemonFusion/Fusion2/issues/748) | Canonical reserve revival/item targeting. |
| [#749](https://github.com/PokemonFusion/Fusion2/issues/749) | Seven unwired medicine/PP/revival items; selected-move PP targeting remains outside the verified Ether first-slot path. |
| [#751](https://github.com/PokemonFusion/Fusion2/issues/751) | Shell Bell spread damage rollup: 60 total damage healed 1 HP instead of 7. |
| [#752](https://github.com/PokemonFusion/Fusion2/issues/752) | Utility Umbrella holder-local weather effects. Boots/Pads checks passed. |
| [#753](https://github.com/PokemonFusion/Fusion2/issues/753) | Blunder Policy activation, Metronome repeat lifecycle, and Gem successful-hit consumption gating. Zoom Lens checks passed. |
| [#757](https://github.com/PokemonFusion/Fusion2/issues/757) | Choice locks reject their allowed move; Assault Vest allows Growl; Life Orb ignores immunity/recoil exceptions; missing held-item move modifiers; Enigma/Room Service/Adrenaline/Booster Energy activation; Air Balloon/Ring Target/Goggles; switching/trapping/reflection/weight effects; form activation and terrain expiry. |

King's Rock and Razor Fang did not flinch in forty retained natural windows each. Source inspection finds the missing held-item `onModifyMove` dispatch shared with Glove/Dice; these are not marked as successful flinch proof.

Miss qualification also exposed **Inferno applying burn and Dynamic Punch applying confusion after a narrated accuracy miss**. These are separate move-hit-gating defects, not expected status immunity or random failure. The runner now distinguishes direct attack damage from burn/confusion damage. Vile Vial equal HP loss was an expected rounding artifact; a stronger qualifying attack verified its damage boost without a game fix.

### Per-check diagnosis

| Check | Item | Diagnosis |
|---|---|
| medicine-heal-Energy Powder | Energy Powder | Existing definition is not wired into the battle medicine dispatcher; the requested HP, status or PP change did not occur. |
| medicine-heal-Energy Root | Energy Root | Existing definition is not wired into the battle medicine dispatcher; the requested HP, status or PP change did not occur. |
| medicine-status-Heal Powder | Heal Powder | Existing definition is not wired into the battle medicine dispatcher; the requested HP, status or PP change did not occur. |
| medicine-pp-Max Ether | Max Ether | Existing definition is not wired into the battle medicine dispatcher; the requested HP, status or PP change did not occur. |
| medicine-pp-Elixir | Elixir | Existing definition is not wired into the battle medicine dispatcher; the requested HP, status or PP change did not occur. |
| medicine-pp-Max Elixir | Max Elixir | Existing definition is not wired into the battle medicine dispatcher; the requested HP, status or PP change did not occur. |
| reserve-revival-route-Revive | Revive | The ordinary item command cannot address the fainted reserve. PlayerChoices.item always selects the acting active Pokemon; reserve revival needs the canonical target route. |
| reserve-revival-route-Max Revive | Max Revive | The ordinary item command cannot address the fainted reserve. PlayerChoices.item always selects the acting active Pokemon; reserve revival needs the canonical target route. |
| reserve-revival-route-Revival Herb | Revival Herb | The ordinary item command cannot address the fainted reserve. PlayerChoices.item always selects the acting active Pokemon; reserve revival needs the canonical target route. |
| enigma-heal | Enigma Berry | A qualifying super-effective hit dealt 16 HP, but the berry did not heal or consume. The damage path dispatches DamagingHit and ability onHit, while Enigma is registered as item onHit. |
| field-trigger-Room Service | Room Service | Trick Room lowered the setter Slowpoke instead of the item holder. The global field callback receives the event Pokemon rather than resolving its item holder. |
| adrenaline-trigger | Adrenaline Orb | Intimidate lowered Attack, but Speed did not rise and the Orb remained. The callback tests effect.name against Intimidate and does not recognize the native boost effect representation. |
| balloon-immunity-pop | Air Balloon | Earthquake damaged a holder with an intact Air Balloon in a clear field. Entry installs a volatile flag, but the ordinary Ground-immunity path does not honor it. |
| immunity-Ring Target | Ring Target | A Normal attack remained ineffective against the Ghost holder. Ring Target uses the Showdown onNegateImmunity=False encoding; the damage path only removes immunity for True. |
| goggles-powder-weather | Safety Goggles | Spore put the Safety Goggles holder to sleep. The item onTryHit powder veto is not applied in this normal status-move path. |
| glove-contact | Punching Glove | Held-item onModifyMove is not dispatched in the ordinary move preparation path. Glove contact remains active, Dice can hit three times, and flinch secondaries are never installed. The multihit calculator also samples the default distribution instead of honoring the requested 4-5 range. |
| herb-charge | Power Herb | Solar Beam still charged and Power Herb remained held in clear weather. The charging path does not dispatch the item onChargeMove hook. |
| dice-hit-count | Loaded Dice | Held-item onModifyMove is not dispatched in the ordinary move preparation path. Glove contact remains active, Dice can hit three times, and flinch secondaries are never installed. The multihit calculator also samples the default distribution instead of honoring the requested 4-5 range. |
| metronome-repeat | Metronome | Three consecutive attacks dealt 18 HP each. The definition only registers onStart; its repeat counter and damage callbacks are not connected to ordinary uses. |
| priority-Custap Berry | Custap Berry | The berry consumed at low HP, but faster Squirtle still acted before Snorlax. The priority callback belongs to the removed item and the custap volatile does not carry that callback. |
| native-form-Blue Orb | Blue Orb | Preparing the eligible native species with the item did not activate its expected Primal/Crowned form. This activation route remains unsupported or feature-gated; prepared form entries are not activation proof. |
| native-form-Red Orb | Red Orb | Preparing the eligible native species with the item did not activate its expected Primal/Crowned form. This activation route remains unsupported or feature-gated; prepared form entries are not activation proof. |
| native-form-Rusted Sword | Rusted Sword | Preparing the eligible native species with the item did not activate its expected Primal/Crowned form. This activation route remains unsupported or feature-gated; prepared form entries are not activation proof. |
| native-form-Rusted Shield | Rusted Shield | Preparing the eligible native species with the item did not activate its expected Primal/Crowned form. This activation route remains unsupported or feature-gated; prepared form entries are not activation proof. |
| booster-Flutter Mane | Booster Energy | Native Protosynthesis/Quark Drive did not activate from Booster Energy. Its callback checks a non-native abilities list and Paradox tags instead of the actual ability representation. |
| booster-Iron Bundle | Booster Energy | Native Protosynthesis/Quark Drive did not activate from Booster Energy. Its callback checks a non-native abilities list and Paradox tags instead of the actual ability representation. |
| switch-Eject Button | Eject Button | The qualifying hit or stat drop did not switch the expected Pokemon. Callbacks call optional switch_out methods instead of queuing the native battle replacement protocol. |
| switch-Eject Pack | Eject Pack | The qualifying hit or stat drop did not switch the expected Pokemon. Callbacks call optional switch_out methods instead of queuing the native battle replacement protocol. |
| switch-Red Card | Red Card | The qualifying hit or stat drop did not switch the expected Pokemon. Callbacks call optional switch_out methods instead of queuing the native battle replacement protocol. |
| trap-Binding Band | Binding Band | The held item did not change the native trap effect: Binding Band retained default residual damage, and Grip Claw retained four remaining turns. The Bind/partial-trap path does not apply these item modifiers. |
| trap-Grip Claw | Grip Claw | The held item did not change the native trap effect: Binding Band retained default residual damage, and Grip Claw retained four remaining turns. The Bind/partial-trap path does not apply these item modifiers. |
| mirror-copy | Mirror Herb | The foe gained Swords Dance boosts, while the holder gained none. The callback operates on the boost event target/source rather than resolving the Mirror Herb holder. |
| destiny-attract | Destiny Knot | Attract affected an opposite-gender Eevee, but was not reflected to Slowpoke. The move applies the volatile without dispatching the item Attract reaction. |
| umbrella-Rain Dance | Utility Umbrella | Incoming rain-boosted Water and sun-boosted Fire damage was unchanged by Utility Umbrella. The installed item flag is not consumed by the holder-local weather damage calculation. |
| umbrella-Sunny Day | Utility Umbrella | Incoming rain-boosted Water and sun-boosted Fire damage was unchanged by Utility Umbrella. The installed item flag is not consumed by the holder-local weather damage calculation. |
| float-weight-damage | Float Stone | Low Kick dealt 41 HP with and without Float Stone against Wailmer, whose halved weight should cross a power threshold. Native species weight and the onModifyWeight item hook are not joined in this path. |
| flinch-King's Rock | King's Rock | Held-item onModifyMove is not dispatched in the ordinary move preparation path. Glove contact remains active, Dice can hit three times, and flinch secondaries are never installed. The multihit calculator also samples the default distribution instead of honoring the requested 4-5 range. |
| flinch-Razor Fang | Razor Fang | Held-item onModifyMove is not dispatched in the ordinary move preparation path. Glove contact remains active, Dice can hit three times, and flinch secondaries are never installed. The multihit calculator also samples the default distribution instead of honoring the requested 4-5 range. |
| blunder-miss | Blunder Policy | A narrated accuracy miss left Speed unchanged and Blunder Policy held. The definition and miss resolution lack the qualifying miss activation/consumption route. |
| lifetime-Terrain Extender | Terrain Extender | Electric Terrain remained active after both the normal five-turn and extended eight-turn limits. Terrain residual processing does not decrement the generic duration when its handler has no onFieldResidual method. The Extender counter fix alone is therefore partial. |
| restriction-Choice Band | Choice Band | The correct locked Tackle is rejected on the next turn for all three Choice items. Choicelock callbacks compare a move object with the stored move name, so legal move enumeration rejects even the allowed move. |
| restriction-Choice Specs | Choice Specs | The correct locked Tackle is rejected on the next turn for all three Choice items. Choicelock callbacks compare a move object with the stored move name, so legal move enumeration rejects even the allowed move. |
| restriction-Choice Scarf | Choice Scarf | The correct locked Tackle is rejected on the next turn for all three Choice items. Choicelock callbacks compare a move object with the stored move name, so legal move enumeration rejects even the allowed move. |
| restriction-Assault Vest | Assault Vest | Growl was accepted and executed with Assault Vest, spending PP. Its disable callback does not exclude the native rebuilt status candidate; the fallback Tackle was consequently already-queued input. |
| life-orb-immunity-negative | Life Orb | Life Orb removed 16 HP despite immunity, Magic Guard, or a Sheer Force qualifying move. Its direct HP subtraction bypasses successful-damage and recoil-suppression checks. |
| life-orb-recoil-Magic Guard | Life Orb | Life Orb removed 16 HP despite immunity, Magic Guard, or a Sheer Force qualifying move. Its direct HP subtraction bypasses successful-damage and recoil-suppression checks. |
| life-orb-recoil-Sheer Force | Life Orb | Life Orb removed 16 HP despite immunity, Magic Guard, or a Sheer Force qualifying move. Its direct HP subtraction bypasses successful-damage and recoil-suppression checks. |
| gem-immunity-negative | Normal Gem | A matching Gem consumed against immunity, Protect, or an actual narrated accuracy miss. Consumption happens before successful-hit qualification. This shared path affects all eighteen Gems, despite correct power/one-use behavior on successful hits. |
| gem-protect-negative | Normal Gem | A matching Gem consumed against immunity, Protect, or an actual narrated accuracy miss. Consumption happens before successful-hit qualification. This shared path affects all eighteen Gems, despite correct power/one-use behavior on successful hits. |
| gem-miss-negative | Fire Gem | A matching Gem consumed against immunity, Protect, or an actual narrated accuracy miss. Consumption happens before successful-hit qualification. This shared path affects all eighteen Gems, despite correct power/one-use behavior on successful hits. |
| shell-spread-heal | Shell Bell | Surf dealt 32, 15 and 13 actual HP across three targets (60 total), but Shell Bell healed only 1 instead of 7. Additional spread damage is not accumulated into the source move total used for healing. |

## Verification and data safety

- Mandatory clean-process combined, repeat, and battle-first suites: **4,121 passed each** (4,014 optional skips). All-options local dex/Showdown/callback run: **8,135 passed**. No dependencies were downloaded.
- Live source audit before and after acceptance: **47 modules / 2,716 functions matched**, no mismatches. Generated/external dataclass functions are listed separately in the audit.
- Independent item audit checked the exact case declarations, ordinary command transcript, evidence SHA-256 values, loaded-code versions, cleanup, durable item state, and declared effects: **407 checks / 543 cases, zero evidence errors**.
- **6770 pre-existing protected rows remained unchanged.** All three fresh QA accounts were disabled, the setup account staff privileges removed, passwords invalidated, and the temporary credential file deleted. The battling accounts remained ordinary players. Existing characters and Pokemon were not edited or deleted.
- The initial 1,101-file source snapshot is retained; 1,091 unrelated existing files remain byte-for-byte unchanged. Ten existing files contain scoped repairs/observer/contract changes; three new Python files contain item helpers and regressions.
- Raw logs, backups, transcripts and compressed evidence are under the already ignored `.codex-artifacts/` directory; game logs are also ignored.

## Local evidence

- `.codex-artifacts/battle-items-20261020/final-item-plan.json` - finite current plan; older attempts remain separate.
- `item-evidence-audit.json`, `diagnosed-final-failures.json`, `complete-battle-audit.json`, `reward-item-results.json` - audited outcomes and exact evidence hashes.
- `candidate04-loaded-code-audit-before.json`, `candidate04-loaded-code-audit.json`, `final-protection.json`, `final-account-safety.json`, `secret-scan-after-disable.json` - loaded build and safety proof.
- `candidate04-source.zip`, `initial-source.zip` (in the sibling work folder), and the verified pre-QA PostgreSQL dump retain recovery material.
- `item_probe_core.py`, `item_plan*.py`, `ordinary_battles.py`, `npc_battles.py`, and archived runner source hashes retain the executable local checks. Reuse the fresh-account preparation workflow for a future run; these credentials are retired.
