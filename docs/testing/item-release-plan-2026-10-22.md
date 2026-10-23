# Released-build item walkthrough plan (#782)

Status: **approved and executed for #782** at pinned candidate
`af0eca6e63924c9108c3adbce389cc875be4c702`. The separate
[released-player report](item-live-2026-10-22.md) records the actual commands,
nine named item outcomes, reload retry, remaining feedback defects and verified
fixture cleanup. Sections below preserve the pre-approval observations and plan.
This one-time approval does not authorize later deployments or permanent sources.

## Fresh read-only observations

On October 22, 2026, PF2-Dev has clean checkout
`b7637cb8d810c5d1706b4ebade8ec4099c553c08` at
`/home/evennia/testing/fusion2`. The observed Evennia process uses
`/home/evennia/testing/evenv/bin/python3`, the same working directory, and
started October 16 at 11:53:09 server time. This identifies the checkout/process;
it does not certify the exact loaded bytecode.

A **read-only** database transaction reports latest recorded Pokemon migration
`0044_owned_pokemon_status`. The pre-existing staging migration
`0045_production_strategy_gym` is absent, as are its inspected gym columns.
No new item feature in this batch needs a migration, but advancing that older
checkout to the complete current staging build would also bring this existing
gym schema change. It must not be silently applied as an item fix.

At that pre-approval inspection, no release, migration, service reload/restart,
live shop setup, account grant, character change or live walkthrough had occurred. The
earlier no-shop source snapshot remains dated evidence, not a refreshed claim
about all current sources. Zero live batches are newly accepted here.

## Release decision required

Choose an intentionally reviewed QA target/build before executing the live
batch. A separate QA environment can keep the existing PF2-Dev world unchanged.
Using the current PF2-Dev checkout instead requires explicit approval to advance
source, apply the existing missing gym migration and reload Evennia. The
repository [operational guardrails](../../AGENTS.md) require asking before
migrations/restarts, prohibit unapproved PF2-Dev source changes, and require
exact setup/configuration commands to be proposed first.

For operator review only, the PF2-Dev option has this command shape; replace
`PINNED_CANDIDATE_SHA` with #782's published immutable SHA and approve the exact
expanded commands before execution:

```text
cd /home/evennia/testing/fusion2
git status --porcelain
git fetch origin staging
git merge --ff-only PINNED_CANDIDATE_SHA
/home/evennia/testing/evenv/bin/evennia migrate pokemon 0045_production_strategy_gym
/home/evennia/testing/evenv/bin/evennia reload
```

The [Evennia reload documentation](https://www.evennia.com/docs/5.x/Setup/Running-Evennia.html#reloading)
describes a server reboot while the Portal retains connections. It remains a
service operation requiring the repository's explicit approval.

Do not run this block while uncommitted remote work, active human battles or
unreviewed release content remain. Any needed backup/maintenance/release
procedure belongs to that separate approval. Verify the launcher and pending
migration plan on the chosen environment first; a passing local suite does not
approve operations on an older server.

## Bounded live batch after the release

Use disposable tagged ordinary players and native targets. Keep a separate
staff setup transcript; no admin elevation of test players, editing human
characters or copying existing Pokemon. Inspect public access/stock before
claiming obtainability. Stocked fixtures are explicit test source configuration,
never a claim that every existing world location supplies these items.

The six-offer [Supply Corner](../item-supply-route.md) provides Potion, Oran
Berry, Fresh Water, Fire Stone, Leftovers and Smoke Ball only. Its setup must
name the reviewed hub and invoke the duplicate-safe installer explicitly; do
not replay the whole Alpha/Adventure recipe. Verify ordinary movement/discovery,
Buy, inventory, useful effect and reconnect for each selected route.

Rare Candy and PP Up/Max need an additional deliberately authored source;
they are **not** supplied by that six-item recipe. Review a separate tagged QA
counter or verify another real source before the batch. Selected disposable
reference offers may be Rare Candy 4,800/stock3, PP Up 9,800/stock3 and PP Max
15,000/stock2, finite/no refill and no direct bag grants. These are proposed PF2
QA authoring values awaiting setup approval, not installed content or current
availability. Missing funds may be staff fixture setup and must be recorded
as such. A grant is never substituted for ordinary acquisition proof.

Record command-level expected and actual source, target, cost/debit, durable
effect and reconnect state for Rare Candy, PP capacity, medicine, berry, food,
evolution and held escape/healing. Include no-effect/invalid-target use without
spending stock. Existing Hopo/Rage/coin routes may be additional named cases if
their separate deliberate sources are configured; do not silently enlarge the
required batch or all-item obtainability claims.

Check loaded revision/runtime after release, not just Git HEAD. Retain source
and fixture identities and exact commands/output. Keep the 18 historical held
item batch boundaries; this representative live batch cannot stand in for
freshly replaying all of them. Mega, Z and growing remain implementation plans.

Cleanup covers only the tagged fixtures created for this run, after confirming
their identities and preserving all human data/sessions. Source installation,
fixture removal and any decision to retain public stock require their own
explicit approved scope. Record fixture cleanup before closing #782; publish
live results separately from local automation, hosted CI, main merge and deployment.
