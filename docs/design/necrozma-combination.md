# Non-plot Necrozma combine/separate contract (#820)

Status: **local implementation accepted (#825–#830); intentionally released local socket acceptance passed (#831)**.
Reviewed on October 23, 2026 at `ec1203c47564c8e712831d8764394a4300a9b629`.
The [machine-readable plan](necrozma-combination.json) records the exact scope,
dependencies and validation inventory. Closing #820 records this bounded plan;
its original static receipt does not claim implementation. The October 24
[local runtime receipt](../testing/necrozma-items-2026-10-24.md) now qualifies
the two native lifecycles and their existing signatures in the [current Z matrix](z-crystals.md).
The subsequent [released local walkthrough](../testing/necrozma-released-local-2026-10-24.md)
exposed an ordinary zero-PP move-legality gap. Its original candidate failed
acceptance. The [approved replacement walkthrough](../testing/necrozma-released-retry-2026-10-24.md)
passes on repaired candidate `e3557aa`, including ordinary/Z zero-PP rejection
without action, damage or side use. This qualifies the disposable local release;
it does not deploy a shared game.

## Native forms and entry point

| Actual owned base | Actual owned companion | Persistent host form | Temporary source move | Existing Z route after its own gate |
| --- | --- | --- | --- | --- |
| Necrozma | Solgaleo | Necrozma-Dusk-Mane | Sunsteel Strike | Solganium Z → Searing Sunraze Smash |
| Necrozma | Lunala | Necrozma-Dawn-Wings | Moongeist Beam | Lunalium Z → Menacing Moonraze Maelstrom |

The [Pokémon Company's Ultra Sun/Ultra Moon announcement](https://press.pokemon.com/en/MORE-NEW-DETAILS-ANNOUNCED-FOR-POKEMON-ULTRA-SUN-AND-POKEMON-ULT-65344)
establishes these two combinations and signature source moves. Local POKEDEX
defines both forms as changes from Necrozma with Prism Armor; MOVEDEX gives
both ordinary source moves base PP 5. This contract's command, eligibility,
storage, PP and recovery rules are **selected PF2 policy**, not a claim of
complete cartridge or Pokémon GO parity.

Ordinary command in the accepted source at an existing Pokémon Center (`is_pokemon_center`):

```text
+necrozma
+necrozma inspect <host slot or full owned UUID>
+necrozma combine <host slot or full owned UUID>=<companion slot or full owned UUID>/<move slot>
+necrozma combine 3=5/2
+necrozma separate <host slot or full owned UUID>
```

Party selectors retain canonical gaps; boxed sources require a full owned UUID.
Names/nicknames and account-level ownership are not selectors. Discovery and
inspection are read-only. Combine/separate open a review with exact identities,
placements, form, displaced move/PP, held items and return policy; explicit
yes/no confirmation follows. A server-issued request binds this character,
pair/lifecycle, exact terms and version, expires after five minutes and cannot
be reused with changed terms. Re-read ownership, location and all eligibility
inside the committing transaction. Cancel, expiry, stale state and duplicate
input cannot mutate anything or announce success.

The route is free and reusable: no Ring, Solarizer/Lunarizer, quest, story flag,
energy currency, new item or inventory debit. It requires two genuine owned
sources. Existing base-species acquisition remains authoritative; no source
grant, default spawn, live chart or shop is added. Existing Z crystals retain
their own acquisition/equip policy and are unnecessary to combine or separate.
Ultra Necrozma, Ultra Burst and Ultranecrozium are excluded.

## Eligibility and two retained identities

- The caller must be in human form, at a freshly verified Center, outside every
  active/pending battle. Check persisted battle lock/session references as well
  as runtime state; contradictory or stale locks require existing recovery.
- Both distinct UUIDs must resolve to this character's trainer and canonical
  storage. Base Necrozma and the exact companion must be conscious non-eggs in
  ordinary party or box placements. Their canonical native abilities must match
  the reviewed species. Status conditions are allowed and retained.
- Neither member may have another combination, trainer-Fusion reservation,
  current/unlocked trainer-Fusion reference, transfer/listing/Daycare/breeding
  reservation or other conflicting operation. Reject missing, conflicting,
  unplaced, foreign, nickname/Transform or directly granted fused-form sources.
- Necrozma remains the same `OwnedPokemon` UUID and owner. Its species changes;
  its party slot or box/position stays put. Its own genetics, nature, nickname,
  EXP/level, EVs, friendship, flags, Hyper Training and held item remain its own.
  Stats/types come from the checked-in target form using normal stat helpers.
- The companion remains a second, unchanged owned row. No merging of IVs, EXP,
  abilities, held items, moves, PP, rewards or capture identities occurs. Move it
  to a new canonical **combined companion** placement; it is unavailable as a
  battler, item/learning target, trainer-Fusion source or independent possession
  to move, release or transfer until separation. Inspection remains possible.

This is a specific Necrozma native-form lifecycle. Do not call the existing
trainer/Pokémon `+fuse`, change `fusion_id`, `fusion_forms` or fighter EXP, reuse
the `fusion` placement, or create a general species-splicing feature. Other
characters, including same-account alts, have no authority over either row.

## Canonical storage, receipts and lock boundary

Extend `PokemonPlacement` with `combined` and a link to one active
`NecrozmaCombination` record. That record binds storage, host/companion UUIDs,
base/target species, lifecycle UUID, policy version, move binding and the
companion's previous placement hint. The host stays in its ordinary placement;
the companion has no party slot, box or box position, and no active/boxed legacy
mirror. Extend the existing shape constraints, deferred PostgreSQL integrity
checks, placement audit and mirror writer. A side attribute or hidden box is
insufficient. There must be exactly one placement per owned row at commit.

Enforce one active link per member across both roles, distinct members, one
owner/storage, the exact species pair, matching fused host and reciprocal
companion placement. Protect both rows against deletion while linked. No
active link may survive separation. Durable operation receipts retain UUIDs
and the committed outcome without permanent protective foreign keys that would
prevent later legitimate release of separated Pokémon. A receipt must never
recreate a released source or overwrite a newer combination cycle.

Use one service and one transaction for pair/form/move/placement/mirror/receipt
writes. For this one-owner operation, lock character → storage → trainer →
both owned rows in UUID order → placements/link/resources in stable key order.
This follows the character-first battle-mechanic boundary and preserves the
existing storage-before-Pokémon rule. Reservation checks called by an already
storage-locked writer must not acquire the character lock afterward. Audit the
actual battle-start, placement and future #722 lock graph; reconcile any inverse
order before public activation. Never rely on a command-only lock check.

Shared eligibility must cover both linked roles in placement, release,
trainer-Fusion, source creation/capture, battle entry, evolution, field items,
move management and future cross-owner consumers. Permit explicitly listed host
operations below; all companion writes and unreviewed linked operations reject.
Coordinate the hook with #722/#723; completing the entire trading UI #725 is
not a dependency. Do not add a parallel transfer writer or re-enable trading.

Ambiguous legacy/directly granted fused rows are audit findings, not evidence of
a missing companion that may be invented. The migration must audit and stop
before changing invalid data. Provide read-only diagnostics; no automatic
repair, guessed unfusion or deletion. Migration execution/release remains an
explicitly authorized operation in a later issue.

## Separation, health and progression

Separation restores base Necrozma on the same host UUID at its current legal
placement, releases exactly the recorded companion and commits all resources
with the link removal and durable receipt. It is allowed while the host is
fainted or statused, so healing is never required to recover a companion.

Return the companion to its previous party slot if free, otherwise the first
free canonical slot, otherwise an ordinary owner box. A previously boxed
companion prefers its still-valid previous box. Allocate a fresh legal box
position through `PlacementService`; deleted hints are not reservations. Never
evict another Pokémon or compact party gaps. If no legal destination can be
allocated, reject the whole separation and retain the valid pair. Combining
does not reserve the companion's old slot, so a full-party separation is normal.

Use `get_stats`/`get_max_hp` with the host's actual IVs/EVs/nature/level and
Hyper Training. Preserve current absolute HP deficit when changing form, with
fainted HP staying zero and a conscious Pokémon staying at least one HP. Retain
major status/sleep state; never restore a pre-combination HP/status snapshot.
The companion's saved HP/status/PP and other fields remain frozen while reserved.

Host battle/field HP, status, EXP, level, EVs, friendship, Hyper Training and
ordinary held-item changes may persist under their existing validated services.
Only the linked host receives participation rewards. Prevent ability/species
changes and trainer-Fusion/transfer/release while linked. No ability-item bypass
or evolution into another species. New base-Necrozma level-up knowledge can be
recorded without changing active slots; defer prompts/active-set changes until
separation. Never discard EXP or earned knowledge as a consequence of slot locks.

## Two form moves, without PP refills or destructive restoration

`get_valid_moves` currently reads level-up entries. The fused learnsets contain
only `7R/8R/9R` form-source entries, so current ordinary `+teach` does not supply
these moves. The accepted native lifecycle provides the following bounded
policy through its selected slot; learnset metadata alone does not enable Z and
generated learnsets remain unchanged.

1. On combine, the player selects a real slot 1–4, including a genuinely empty
   slot. Bind the exact active moveset and slot; save only that displaced move's
   identity/current PP or empty state. Keep gaps and the other three slots.
2. Install the correct form-only source into canonical active/saved slot and
   learned identity under the combination service. It belongs to the host;
   never copy the companion's move/PP/PP bonuses. Only these two source moves
   receive this native-form exception.
3. Persist a per-host/per-source form-move resource across combination cycles.
   First-ever legitimate introduction gets base PP 5 once. Thereafter restore
   its saved remaining PP, including zero. Existing `MovePPBoost`/`PPCapacity`
   remain the capacity authority; PP bonuses survive separation. Missing or
   contradictory previously used resource data fails closed, never refills.
4. While linked, ordinary attacks, Z actions, field/battle Ether/Elixir/Leppa
   routes, PP Up/Max and healing must commit active PP and its resource history
   together. No second debit or desynchronized mirror. Dormant form PP cannot
   be targeted or healed while unfused. The displaced ordinary move is also
   inactive; it gains no PP from healing the active form slot.
5. Lock active/saved moveset switching, slot edits, forgetting, source replacement
   and mutating learn/teach prompts while linked. Read-only views still work.
   Runtime copied moves must not overwrite the bound native source on sync.
6. On separation, persist the final form-source PP, remove its temporary learned/
   slot exposure and restore only the displaced slot at its stored remaining PP
   (or remove the slot if originally empty). Retain all other moves' current
   PP, knowledge and progression. Never replay a whole old moveset snapshot.

Validate unexpected pre-existing form-only learned/saved-slot state rather than
deleting it or treating it as native proof. Keep the resource history after
separation so changing companions, reconnects or repeated combine/separate
cannot mint PP. Release after a legitimate separation may remove this host's
resource rows; durable receipts still cannot resurrect it.

## Ordinary battles and bounded Z expansion

Build the fused host from its same owned UUID, real target stats/type/Prism Armor
and current canonical slots/PP. The companion never appears in a party/Fusion
roster, chooses an action, receives EXP or changes in battle sync. Validate the
live pair on entry, reconnect and mutation/PP/end-sync boundaries, binding its
lifecycle/version, both UUIDs and owned origin. End/flee/concede restores only
battle state; the persistent combination remains until explicit field separation.

The accepted Z exception is exactly Dawn-Wings + Moongeist Beam + Lunalium Z and
Dusk-Mane + Sunsteel Strike + Solganium Z with valid live pair proof. Direct
fused owned rows, a crystal's `itemUser`, a nickname, copied ability, Transform or
client-supplied species cannot qualify. Do not broadly waive `changesFrom`.

Reuse the existing 200-power signature effects, one source PP and side budget,
protection/immunity/ability boundaries and rollback/checkpoint/end guards.
Keep existing native Lunala/Solgaleo profile identities and fingerprints stable;
add a narrowly proved holder eligibility exception instead of changing their
effect definitions or blindly expanding the native tuple. Existing native
queued/used checkpoints must still rebuild. The combo proof is additional native
provenance, not a spent battle mechanic or a second Z use.

Initial fused-host battle support is ordinary moves/items/flee and these two
reviewed Z signatures in existing human Wild/Trainer/PvP singles and
two-controller doubles only. Mega, Tera, Dynamax and Ultra combinations reject
before queuing in this initial slice; this is a bounded PF2 stacking policy.
Leave all existing unfused/native Tera/Mega/Z policies intact. No new AI
activation or battle format. Do not expand the finite Counter or duplicate a
held crystal: its existing native offers already supply these same items.

## Delivery gates

| Order | Issue | Deliverable | Hard dependencies |
| --- | --- | --- | --- |
| A | [#825](https://github.com/PokemonFusion/Fusion2/issues/825) | Pair schema, canonical companion placement, constraints and audit | #820 design |
| B | [#826](https://github.com/PokemonFusion/Fusion2/issues/826) | Shared reservations, conflicting writers and battle-start locking | A; coordinate #722/#723 |
| C | [#827](https://github.com/PokemonFusion/Fusion2/issues/827) | Atomic combine/separate, receipts, source-slot/resource setup, HP and return placement | A, B |
| D | [#828](https://github.com/PokemonFusion/Fusion2/issues/828) | Ordinary source-slot, PP and progression writer integration | C |
| E | [#829](https://github.com/PokemonFusion/Fusion2/issues/829) | Ordinary command/inspection/confirmation and local acceptance | C, D |
| F | [#830](https://github.com/PokemonFusion/Fusion2/issues/830) | Fused battle/Z provenance and both-form effects | B, D, E |
| G | [#831](https://github.com/PokemonFusion/Fusion2/issues/831) | Integrated acceptance and separately authorized release walkthrough | E, F |

A–F have passed their [local integration and mandatory gates](../testing/necrozma-items-2026-10-24.md)
together; the accepted source registers the ordinary command. G passed its
[separately approved local release walkthrough](../testing/necrozma-released-retry-2026-10-24.md).
The existing running shared game was not changed. Each implementation issue needs focused effects plus real
production-model PostgreSQL tests, then the mandatory fresh combined/repeat/
battle-first gate after Python changes. Static checks in #820 are design evidence.

Acceptance must cover both forms, party/boxed sources, full-party/deleted-box
return, exact identities/mirrors, partner freeze, repeated/cancelled/stale input,
same-account foreign sources, invalid grants and copied forms. Exercise actual
battle/field PP and HP changes before separation, zero/boosted PP across cycles,
switch/faint/revival/reconnect/end, and unchanged native Lunala/Solgaleo Z cases.
Inject failure after each durable write and parent rollback: SQL, caches,
request/receipt state and success notices all agree. Independent PostgreSQL
connections race combine/combine, combine/separate, separate/separate, release,
placement, Fusion, field use, battle entry and supported transfer reservations;
one legal outcome, no missing/duplicated source or deadlock.

## Repository seams and evidence limits

Extend the [placement write contract](../operations/pokemon-placement.md),
`pokemon/models/storage.py`, `pokemon/services/placement.py`, its audit and
deferred trigger pattern. Existing ownership stays in `OwnedPokemon.trainer`.
Reuse `pokemon/services/move_management.py`, `PPCapacity`, field item checks,
`utils/pokemon_utils.py`, `OwnedBattleActor` and `ZMoves`; preserve the existing
trainer-Fusion code and its separate #723 hardening. Runtime native access and
human-readable displays must agree with the canonical link.

The [design validation receipt](../testing/necrozma-design-2026-10-23.md) pins
source facts and issue dependencies at the original design publication.
The later local implementation is recorded separately above; neither receipt
claims live source availability, a shared-game migration or deployment. Plot
items, generated learnset changes, Ultra, trainer-Fusion reinterpretation and
unrelated work remain outside this lifecycle.
