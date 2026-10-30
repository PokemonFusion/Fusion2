# Reusable item cleanup after final KO

Actual last-opponent KO left an existing Venusaurite or Normalium Z battle
unable to end: the owned-mechanic guard rejected a completed battle even for
its cleanup validation. Both existing-item player routes reproduced the error.

The guard now permits only its `active=False` ownership/source validation on
a completed battle. New activation still refuses; current owner, placement,
native provenance and held-item checks are retained. This repair is committed
separately from the new Ultra route.

Two ordinary purchase/equip/declaration/attack/final-KO/end/return command and
PostgreSQL cases pass, including explicit post-completion activation rejection.
The independently staged prerequisite also passed both cases before commit. The enclosing
frozen Ultra cohort also passed all three mandatory fresh orders:6,613 passed
/4,028 skipped each, exit0. [Machine receipts](reusable-item-completion-2026-10-26.json)
retain the original failures and distinguish the cohort from the standalone run.

No shared schema, service, stock or human fixture was changed. New Ultra work
and all25 unrelated shared dirty paths remain outside this prerequisite commit.
