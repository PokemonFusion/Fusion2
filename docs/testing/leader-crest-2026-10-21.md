# Leader's Crest and Kingambit — issue #761

Native owned Bisharp now qualifies by personally finishing three distinct
authored Crest-bearing leader Bisharp in committed NPC/wild victories, then
gaining the required level and using ordinary `+evolve <full Pokemon ID>`.
The [selected PF2 contract](../kingambit-evolution.md) was written before code;
the existing-item gate and closed #755/#756 dependencies were checked first.
The player's Bisharp needs no Crest in its bag or held slot. Equipped and bag
copies are preserved, including after successful evolution and SQL reload.

Leader identity requires a real native `EncounterPokemon` originally holding
the Crest and still physically holding it at the finishing move. Suppression
does not remove possession. The direct lethal move ledger identifies the actual
owned, living, untransformed active Bisharp in canonical party placement. A moved-in
Crest, nickname, client argument, arbitrary flag, another Pokemon's KO, bench EXP
or missing attribution cannot manufacture qualification. The complete item
definition is supplemental Held Items metadata with a PF2 reference price of
1500 and a qualification role; no new combat-stat effect is advertised.

The bounded rule uses existing authored static NPC held-item templates and the
ordinary placed-NPC challenge route. The tests deliberately create their NPCs
as fixture setup. No live NPC, stock or reward was populated. Server-configured
wild leaders use the same rule. Relative to the [cartridge reference](https://bulbapedia.bulbagarden.net/wiki/Leader%27s_Crest#Effect),
the whole-victory, original-leader and direct-move restrictions are documented PF2
adaptations. The player-held Crest is neither required nor consumed.

## Persistence and failure handling

A candidate is sealed in the existing faint receipt, within the existing full
turn/checkpoint transaction. Terminal victory records a separate existing
`BattleRewards` effect only after faint delivery succeeds. Its claim locks the
character, trainer and owned rows; private owner/UUID evidence and the once-only
claim marker commit together. Failed writes preserve the terminal session or
pending receipt for `+battle/retry`, and count stays bounded at three identities.
No model, schema, migration or general history subsystem was added.

The level floor is the greatest pre-EXP level at the first three qualifying
KOs. Current stored level must exceed it. The third KO's normal EXP can provide
the increase; later EXP or the existing Rare Candy route can also do so. Earlier
level-ups alone are insufficient. Later victories/replays cannot increase a
completed floor, and there is no new level-100 substitute.

The existing evolution service reads private evidence under its existing
storage/trainer/Pokemon transaction and retains ownership, egg, Everstone,
reservation and battle guards. Exact reviewed source/target/condition metadata
limits the Kingambit exception; generic `other` conditions remain unsupported.
Identity, owner, canonical placement/mirrors, held item, EXP, HP/status, IVs/EVs,
friendship, moves/PP and unrelated state are preserved; canonical species,
ability-slot mapping, derived stats/types and the usual evolution receipt change.

Failure injection found that an update to an existing Evennia Attribute could
remain in its identity cache after SQL rollback. Qualification, receipt and
pending-index reads now use the Attribute relation's stored SQL values directly.
A further probe failed after writing a claim marker: its stale cached value
could make recovery skip a rolled-back claim. The permanent test now fails after
actual evidence, claim-marker and pending-index SQL writes. Each requires
unchanged progress, then exactly one increment after reconnect/recovery.
Independent-connection claim/evolution races are also covered.

## Ordinary player proof

Two complete automated walkthroughs use production command parsing/execution:
`+itemdex Leader's Crest`, `+inventory`, optional `+hold 3=Leader's Crest`, three
fresh `+challenge <authored NPC>` / `+attack Brick Break` victories, reconnect on
the second fight, `+party 3`, failed early `+evolve`, `+use Rare Candy=3`,
`+evolve <full ID from the sheet>`, SQL reload, `+party 3` and repeated evolution.
One has no bag Crest and keeps Leftovers; one keeps its equipped Crest and spare
bag copy. Same-ID state, PP, canonical slot and compatibility mirrors are checked.

The 29-case PostgreSQL suite also covers multiple leaders in one battle, threshold
boundaries, early versus third-KO level-ups, fourth-win saturation, actual wild
victory, PvP, capture, flee, loss/abort, scripted/no-progression fights, wrong or
removed items/species, foreign references/owners, another attacker, missing
attribution, suppression, fake flags, stale checkpoints, failed result/claim/
checkpoint/evolution writes, reconnect/retry and concurrent claim/evolution.
Only transport resolution and encounter fixture selection are adapted; production
commands, combat, receipts, models, locks and effects run against real PostgreSQL.
The new suite is wired into lifecycle CI; no hosted CI result is claimed here.

Initial failures included incorrect description assertions, missing disposable
ContentType lookup transport, missing factory imports, injection before choice
storage instead of at the turn checkpoint, and use of field `+use` rather than
battle `+item` for capture. Those were fixture errors. The stale Attribute after
SQL rollback was a product issue and received the direct stored-value repair.
The first gate was superseded after the late-marker probe exposed the additional
receipt-cache bug; only complete final reruns against the repaired source count
below.

## Final validation

| Check | Passing result |
| --- | --- |
| PostgreSQL leader crest | 29 cases |
| PostgreSQL battle recovery | 36 cases |
| PostgreSQL progression | 11 cases |
| PostgreSQL trainer challenge | 10 cases |
| PostgreSQL player doubles | 10 cases |
| PostgreSQL adventure lifecycle | 9 cases |
| PostgreSQL evolution | 28 cases |
| PostgreSQL alcremie | 76 cases |
| PostgreSQL trade held | 33 cases |
| PostgreSQL peat block | 29 cases |
| PostgreSQL ui | 14 cases |
| PostgreSQL smoke ball | 17 cases |
| PostgreSQL remaining item | 8 cases |
| PostgreSQL field food | 70 cases |
| Total PostgreSQL | 380 cases |
| Focused pytest | 222 tests |
| Mandatory combined, repeat and battle-first | 4,535 passed / 4,014 skipped in each process |

All processes exited successfully. All 959 frozen Python files remained unchanged during validation. All test schemas were removed, public tables remain empty, and the private cluster was stopped. Skips remain outside enabled scope; existing warnings are retained.

The [JSON report](leader-crest-2026-10-21.json) retains source/output hashes,
commands, walkthrough identities, process results and private-database cleanup.
Historical #757 matrix and earlier reports remain pinned snapshots; the support
guide links this later addition separately.

This is local automated ordinary-command/model acceptance with captured session
transport and separate disposable setup. It does not establish live login
acceptance, hosted CI completion, main merge or deployment. Existing game data
and services, the migration runner, generated dex files, plot-only content and
unrelated work were excluded.
