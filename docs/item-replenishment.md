# Explicit operator replenishment

`ItemReplenishment` implements #876 for a separately reviewed, explicitly
opted-in consumable counter. It is an operator Python API, with no player
command, scheduler, startup hook or implicit installer integration. It does
not install a shop or opt in any current world object.

The original six-item Supply Corner remains finite, buy-only and excluded.
Its source key and room tag are refused. The seven proposed counters in
[the acquisition policy](design/item-acquisition-policy.md) remain finite
and do not opt in merely because this service exists.

## Authoring and operation

Prepare a concrete world-change plan with the target build, exact room, source
key/version, initial prices/quantities, operator account, baselines and rollback.
Obtain the applicable operational approval before executing it. The source
must already be an enabled buy-only shop with its exact untouched initial stock.
Caps are supplied by a reviewed `ReplenishmentPolicy`, never inferred from
depleted stock. Canonical selected consumables are explicitly allowlisted;
plot/capture/clutter items and reusable held items are excluded. Additional
families require their own policy review.

The API shape below is an example for a **new reviewed counter**, not an
instruction or authorization to change an existing room:

```python
from uuid import uuid4
from pokemon.services.item_replenishment import (
    ItemReplenishment, ReplenishmentPolicy,
)

policy = ReplenishmentPolicy(
    "reviewed-status-counter", 1,
    (("Antidote", 100, 20), ("Paralyze Heal", 200, 20),
     ("Awakening", 250, 10), ("Burn Heal", 250, 10),
     ("Ice Heal", 250, 10), ("Full Heal", 600, 10)),
)
# room and operator are actual approved ObjectDB/AccountDB instances.
marker = ItemReplenishment.configure(room, policy, operator)
# Persist the request UUID in the private operation record before calling.
request_id = str(uuid4())
receipt = ItemReplenishment.refill(room, policy, operator, request_id)
```

The operator must currently be an active, non-bot Builder-or-higher account
(or active human superuser). Every call reads account permissions from SQL.
Character permissions, account-like objects and cached elevation do not grant
access. `configure` is explicit and idempotent: retries preserve the original
instance, caps, timestamps, stock and receipts. It refuses rebinding or policy
changes. An already depleted source cannot bootstrap its own lower or larger caps.

The first refill is eligible exactly 24 real UTC hours after opt-in. Each later
refill is eligible exactly 24 hours after the last committed refill. Midnight
alone grants nothing. Late calls accumulate no debt or extra windows. Only the
missing quantity up to each initial cap is added; prices never change. A full
counter returns `None`, writes no receipt, and consumes neither a window nor
the proposed request UUID. Clock rollback, policy/stock/flag drift and ambiguous
or damaged ledger records require review and leave stock untouched.

The receipt records source/version/instance, room, operator, request UUID,
sequence, prior timestamp, eligibility timestamp, actual UTC timestamp, exact
before/after offers and per-item stock delta. It includes an integrity digest.
Use the same UUID after an uncertain result. A committed replay returns its
original historical receipt, including after later purchases or refills, and
never adds stock again. A different operator cannot reuse that request identity.
Retain all historical receipts; do not delete or edit them to reset eligibility.

## Transactions and player behavior

Refills lock the same room row used by `ShopPurchase`. Stock, receipt and latest
marker commit together. Concurrent purchases see a legal serialized order;
concurrent refill UUIDs share one rolling interval. Per-request history prevents
old replay IDs from becoming usable again after a newer refill.

Shared Attribute values are refreshed only after an outer commit. Exceptions
after stock or receipt SQL and containing-transaction rollback undo the whole
action. A returned result inside a caller-owned transaction is tentative until
that transaction commits; do not announce success or publish it beforehand.
There is no automatic player message or wallet/bag/Pokémon change from refill.

Players continue to use ordinary `+store`, buy-menu input, `+inventory`, `+use`
and the existing item routes. Funds, finite stock, whole quantities, current
owned targets and useful-effect checks remain in their original services.
Refilling is never player resale, free item credit or a new effect implementation.

The [dated checks](testing/item-replenishment-2026-10-25.md) separate disposable
operator setup, ordinary production commands, SQL evidence and full offline
tests. No source has been opted in on PF2-Dev by this delivery.
