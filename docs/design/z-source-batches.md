# Remaining generic and status Z sources (#864)

Design only, after #863's Flamethrower/Surf slice. The current registry then has
44 explicit mappings on 34 crystals: 20 generic damage, eight status and 16
signatures. The new source inventory enumerates every ordinary MOVEDEX source
against those exact profiles. Metadata alone enables no source.

## Classification and preserved rules

The dated JSON separates accepted generic/status pairs, ordinary damage sources
with native level-up learning, ordinary sources with unresolved native access,
special/variable sources and unreviewed status bonuses. Z/Max descriptors, CAP
and Struggle are excluded. Native learning examples are project metadata;
they do not claim a populated chart, ordinary capture or installed shop.
Every future delivery must prove that acquisition and source preparation.

Special review includes charging/recharge, multi-hit, called/copied moves,
variable/fixed damage, unusual source callbacks, recoil/drain and switching.
Classify and pin their conversion/prevention rules before enabling them. For
status sources, retain the actual ordinary effect and target, with only its
explicit pinned Z bonus. Prevented execution must preserve source PP and side
use; a legitimate executed move facing immunity may spend both under current
policy. No new arbitrary inventory callback or metadata-wide allowlist.

Keep existing actual learned/active source slot and boosted PP capacity, held
crystal custody, native/form proof, ordinary controller/side and format guards,
one-side budget, target class, whole-turn rollback, immutable profile fingerprint
and reconnect/end policy. Leave all 16 signature profiles, including both
live-pair Necrozma consumers, byte-for-byte unchanged. Ultra remains #865.

## Three selected next implementation issues

Each issue contains at most six exact mappings. Type-matched generic Z moves
use normal single-target descriptors, inherent accuracy, no ordinary secondary,
spread, recoil/drain or source self-effect. Powers follow the pinned reference
conversion table; ordinary source moves and dex metadata remain unchanged.

| Batch | Exact crystal/source -> derived power/category | Native level-learning example |
| --- | --- | --- |
| Six special attacks | Electrium Z/Thunderbolt175 Special; Icium Z/Ice Beam175 Special; Grassium Z/Energy Ball175 Special; Psychium Z/Psychic175 Special; Ghostium Z/Shadow Ball 160 Special; Poisonium Z/Sludge Bomb175 Special | Pikachu26; Lapras31; Voltorb-Hisui29; Kadabra35; Gastly29; Grimer26 |
| Six physical attacks | Normalium Z/Body Slam160 Physical; Darkinium Z/Crunch160 Physical; Dragonium Z/Dragon Claw160 Physical; Groundium Z/Earthquake180 Physical; Rockium Z/Rock Slide140 Physical; Steelium Z/Iron Head160 Physical | Snorlax25; Arbok evolution/level-up source; Axew18; Diglett37; Growlithe-Hisui48; Aron22 |
| Six status sources | Normalium Z/Recover clears user's negative stages; Flyinium Z/Roost clears negative stages; Normalium Z/Protect clears negative stages; Poisonium Z/Toxic gives user Defense+1; Electrium Z/Thunder Wave gives user Special Defense+1; Grassium Z/Synthesis clears negative stages | Starmie1; Pidgeot44; Pelipper1; Clodsire40; Mareep4; Bulbasaur27 |

These examples were checked against `get_valid_moves` and the project's level
map; they are not automatic native grants. An evolution-level0 source such as
Arbok requires normal current learning access, not assigning a move to a row.
If the chosen path cannot expose it safely, substitute a verified native
level-learning example within that same named source issue, not a source move.

For status sources pin the reference's ordering relative to ordinary effect
failure, healing caps, Protect's repeat-use check and target immunities. Preserve
positive stages when clearing negative ones. Ordinary Recover/Roost/Synthesis
still follow their normal HP/weather/type restrictions. Do not claim complete
status parity merely by setting a bonus field.

## Per-issue acceptance

Use authored tagged chart/shop prerequisites, then ordinary hunt/capture,
nickname, current legal teaching and moveset menus, buy/inventory/hold/discover,
`+zmove <actual slot>=<legal target>`, actual full turns and unhold. Prove source
PP once, reusable crystal, correct damage or useful status effect, independent
side use and no spread/secondary/self carryover. Include legal ordinary source
controls, single/double targeting, Protect/immunity/prevention, zero/stale PP,
wrong/missing crystal, invalid/foreign/boxed/copied/native/spoofed identities,
suppression under existing physical-crystal policy, pending actions, partial/
outer rollback, reconnect and end. Native prerequisites and deliberately
released socket proof remain separate from offline/SQL evidence.

Rerun #863, the existing42-profile suites and all 16 signature/native-pair
fingerprints, plus required fresh full gates after Python changes. Update the
current source matrix only after each mapping's player/effect proof passes.
Keep every other generic/status source explicitly deferred, with its classified
reason. No plot unlock, new crystal, permanent world stock or blanket coverage.

The qualified #863 source is commit 8341564. The generated inventory covers
862 ordinary source moves: 28 accepted generic/status sources, 269 ordinary
damage sources with native learning metadata, 41 ordinary damage sources with
unresolved native access, 263 special/variable sources requiring review,
227 unreviewed status bonuses and 34 status sources without a reference Z bonus.
These counts sum to the full ordinary inventory. The latter 834 sources remain
unsupported or intentionally excluded; native metadata does not prove public reachability.
The 16 signatures are separately accepted and unchanged. Closing this design certifies
classification and bounded delivery rules, not the remaining runtime support.


## Source inventory and next deliveries

[Complete classified inventory](z-source-coverage-2026-10-25.json). Reference: [Showdown Z power conversion](https://github.com/smogon/pokemon-showdown/blob/7e6cea3605c20b44142b2aab22acf08df75ea52b/sim/dex-moves.ts#L551), [move status bonuses](https://github.com/smogon/pokemon-showdown/blob/7e6cea3605c20b44142b2aab22acf08df75ea52b/data/moves.ts).

| Issue | Exact bounded batch | Dependencies |
| --- | --- | --- |
| [#910](https://github.com/PokemonFusion/Fusion2/issues/910) | Qualify six special attacks through explicit Z mappings | #864, #863 |
| [#911](https://github.com/PokemonFusion/Fusion2/issues/911) | Qualify six physical attacks through explicit Z mappings | #864, #863 |
| [#912](https://github.com/PokemonFusion/Fusion2/issues/912) | Qualify six status sources through explicit Z mappings | #864, #863 |
