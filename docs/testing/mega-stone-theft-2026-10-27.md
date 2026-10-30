# Native Mega Stone theft protection — October 27, 2026

Issue [#920](https://github.com/PokemonFusion/Fusion2/issues/920) is accepted on
the frozen local source candidate based on `3e47260e9da188ceca3203778644c15d85bb16ab` plus the exact
seven Python fingerprints in the [machine report](mega-stone-theft-2026-10-27.json).
Publication and deployment remain separate from these checks.

## Behavior and exact scope

All **47 standard Mega Stones** now reuse `HeldItemIdentity.matches` through one
shared holder-only rule. A renamed compatible native keeps its stone; a foreign
nickname or genuine copied appearance grants no protection. A compatible thief
does not protect a foreign holder's stone. Actual Mega forms retain the original
native family. Physical protection survives Magic Room, Embargo and Klutz without
re-enabling suppressed effects. Sticky Hold, occupied Thief, swaps and legitimate
damage still use their ordinary rules.

The pinned [reference item hook](https://github.com/smogon/pokemon-showdown/blob/7e6cea3605c20b44142b2aab22acf08df75ea52b/data/items.ts#L540)
and [TakeItem dispatch](https://github.com/smogon/pokemon-showdown/blob/7e6cea3605c20b44142b2aab22acf08df75ea52b/sim/pokemon.ts#L1819)
establish that its hook's second argument is the holder, despite its source name.
An AST comparison proves that exactly the 47 accepted `onTakeItem` methods changed
in the item callback module; every other method, including Crucibellite, is intact.
No engine, catalog, plot, stock or unrelated item effect changed.

## Fresh verification

- **551 new engine cases** cover all 47 stones with actual Thief, Knock Off,
  Trick and Switcheroo, native/foreign names, both source roles and real Mega
  form changes. Bounded suppression, Transform, malformed identity, Sticky Hold
  and occupied-source controls complement the full stone matrix.
- **1,689 focused tests passed**, retaining prior Plate/Memory/Drive/
  Origin/Primal/Rusted protections, Mega consumers and native item-form checks.
- **21 new PostgreSQL cases passed:** 20 completed ordinary battle/conservation
  routes and one isolated failed-equip rollback. They drive actual +inventory,
  +party, +hold, +pvp/create/join/start, +attack and +mega parsers over real owned
  rows. One pending-action and two completed-checkpoint rebuilds preserve paid
  PP, HP, held copies and bags; postbattle +hold returns reusable items once.
- Actual Skill Swap from native Klutz Swoobat tests suppression without assigning
  an illegal native ability. Genuine Transform cannot protect foreign Mew;
  actual +mega still activates Blastoise-Mega, retains its stone and reverts at end.
- The preserved Mega suites passed **60 core and 50 per-stone/effect cases**,
  for **131 final SQL cases total**. Their separate fixtures test existing
  acquisition, activation, native guards, budgets, useful effects and rollback.

| Mandatory fresh process | Passed | Skipped | Duration |
| --- | --- | --- | --- |
| combined | 7,200 | 4,031 | 723.00s |
| repeat | 7,200 | 4,031 | 704.72s |
| battle-first | 7,200 | 4,031 | 634.77s |

All three mandatory orders returned zero. Existing model-registration warnings
remain visible in the machine receipt; skipped cases are not acceptance proof.
Commands, source/log hashes and explicit fixture observations are retained there.

## Diagnosis and preservation

The fresh pre-fix reproduction had 499 failures and 52 passing controls. After
the production repair, two low-defense fixtures legitimately fainted to Knock
Off. Calculated legal defensive IV/EV/nature setup corrected those fixtures;
attack power and fainting rules stayed intact. One occupied-source expectation
was also corrected without changing mechanics.

An older Mega fault case deliberately changes a roster member into an egg after
start. Its teardown now asserts #918's protected end refusal and unchanged
checkpoint instead of bypassing quarantine. Schema-owned cleanup removes only
its disposable fixture. The preliminary core failure and superseded incomplete
gate are retained; the final core rerun and complete final gate qualify this build.

The first complete combined order also exposed one legacy callback wiring test
that supplied only an Abomasnow nickname. It now uses a real native Abomasnow
and an explicit foreign-name control. That failed run (7,199 passed / one failed)
is retained separately; no production code changed after the successful SQL runs.

All **1,198 repository Python source identities** were pinned for the complete
final three-order gate. The production and SQL-flow sources remained unchanged
between SQL qualification and that gate. The **25 unrelated dirty paths** retain
their baseline bytes/status. Only the two production item files, new/affected
tests and this issue's guide/evidence are included for publication.

## Acceptance limits and cleanup

This is local automated engine and production-command/model acceptance with
captured transport, not a Telnet/WebSocket login or shared game release. Native
rows, known move slots, nicknames and bag copies were labelled separate setup;
public species, move-learning and stone stock are not certified. Model tables
were created directly in random disposable schemas, without migrations or their
integrity triggers. No existing game database, character, world stock or Evennia
service was changed. Schemas were removed and the task-owned loopback cluster
stopped with zero disposable schemas and zero public tables.

Generic Knock Off damage still follows its existing item-presence power policy.
This bounded theft repair does not qualify every damage interaction or change
other backlog items. Plot-only and CAP items remain excluded.
