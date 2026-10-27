# Leader's Crest and Kingambit (#761)

## Selected PF2 qualification, recorded before implementation

A native owned **Bisharp** must personally finish **three distinct leader
Bisharp encounters** with direct damaging moves, and its stored level must
increase after the third qualifying KO. Evolution remains an explicit normal
`+evolve <full Pokemon ID>` action. No bag item is supplied or consumed, and
neither a Crest nor any other ordinary held item on the player's Bisharp is
consumed. Everstone and existing ownership/egg/reservation/battle guards apply.

PF2 identifies a leader by the server-created `EncounterPokemon` row: native
Bisharp, NPC or wild source, and a Leader's Crest in its original held slot.
The same native runtime opponent must still physically hold that Crest when
defeated. Item suppression does not remove physical possession. Removing or
stealing the Crest prevents credit; giving one to an originally unqualified
opponent does not manufacture leader identity. Pawniard followers are optional
presentation, not player-provided qualification flags. This is PF2's bounded
leader identity rule, with normal static NPC held-item templates as the selected
authoring/acquisition route. No live NPC, shop or reward stock is populated.

The defeating Bisharp must be an untransformed, living active member of the
controller's canonical owned party, with matching persistent species/owner.
Fusion reservations, nicknames and transformed species cannot supply identity.
The actual finishing move's source and lethal damage ledger establish credit;
EXP Share, bench participation, another Pokemon's KO, ally damage, residual
damage, recoil-only attribution and missing/stale attribution do not qualify.
Only ordinary wild/NPC trainer battles with normal progression enabled qualify.
PvP, scripted encounters, capture, flee, losses/draws and aborted sessions do not.

This intentionally narrower PF2 rule requires the whole encounter to end in a
committed victory. It records no progress from provisional KOs in a lost fight.
The cartridge baseline associates the defeated Bisharp's Crest and finishing
blow with Kingambit eligibility
([Leader's Crest reference](https://bulbapedia.bulbagarden.net/wiki/Leader%27s_Crest#Effect),
reviewed October 21, 2026). PF2's victory, original-leader identity and direct-move
limits are explicit adaptations rather than claims of cartridge equivalence.

## Persistence, count and level trigger

The normal faint effect plan seals a primitive qualifying candidate alongside
its existing durable EXP/EV receipt. The full turn and checkpoint transaction
must commit, and the faint receipt must be claimed, before terminal victory can
record its existing `BattleRewards` effect. The victory claim updates private
server evidence keyed by owner and actual owned Pokemon UUID, in the same
transaction as the receipt's once-only marker. Room cleanup cannot erase it.

Evidence retains at most three distinct encounter UUIDs and a level floor. The
floor is the greatest pre-EXP level observed among those qualifying KOs; in
ordinary sequential play it is the level at the third KO. Eligibility requires
the current stored level to exceed that floor. EXP from the third KO may supply
that increase; otherwise later normal battle EXP or Rare Candy can. No special
level-100 substitute is introduced. Counts saturate at three, and later/replayed
results cannot raise the floor or spend an item. Repeating a freshly generated
NPC challenge is allowed; replaying the same encounter/result is not new credit.

The service reuses the existing character/trainer receipt locks. Evolution reads
fresh private evidence while holding its existing storage/trainer/Pokemon locks;
client text and arbitrary Pokemon completion flags do not grant eligibility.
Failed result/claim writes roll back and retain the terminal session or pending
receipt for `+battle/retry`. Failed evolution writes use the existing rollback
and cached-instance restoration. No schema or migration is added.

Private evidence, battle receipt and pending-index reads use the Attribute
relation's SQL values, bypassing Evennia's model identity cache. Rolled-back
qualification, claim-marker and pending-index writes must not remain visible
through cached Attribute values or cause a retry to skip undelivered progress.

## Normal player route and item role

Builders may deliberately configure an ordinary static NPC template with
`species="Bisharp"` and `held_item="Leader's Crest"`, then expose it through the
existing placed-NPC `+challenge` mechanism. This uses existing authored encounters,
not a new storyline or staff evolution bypass. The same identity rule supports
server-created wild encounters if deliberately configured with that held item.
Leader's Crest is supplemental metadata in Held Items, with a PF2 reference
price of 1500; existing shop/reward configuration may offer it without automatic
grants. It has no new combat-stat effect or disposable evolution-stone behavior.

```text
+challenge <configured NPC>
+attack Brick Break
[win; repeat until three qualifying leader defeats]
+party 3
[gain a level if the third KO did not already provide it]
+evolve <full ID from +party 3>
+party 3
```

The detailed Bisharp party sheet shows the private count and required next level.
Normal equip/removal and itemdex/inventory displays remain available. Equipping,
buying, typing or using a Crest alone never grants qualification. The evolving
Pokemon keeps identity, ownership, placement, held item and saved gameplay state
under the existing evolution transaction, except canonical species, mapped
ability, derived types/stats and its normal evolution receipt.

Plot-only content, broad battle-history analytics, general encounter editing,
unrelated evolutions, general equip changes and live deployment remain outside
this issue. Automated command/model proof and live login acceptance are separate.
