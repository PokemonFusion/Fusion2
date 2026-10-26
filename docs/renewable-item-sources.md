# Reviewed renewable item sources

Two opt-in sources are supported: a named Potion finder and native level-5
Rattata holding Oran Berry. A species/item dex entry or unnamed finder rate
does not install either source. Any world configuration needs its own reviewed
room/route, installation authority and released player acceptance.

| Route | Exact room/chart authoring | Normal player flow |
| --- | --- | --- |
| Potion finder | `allow_hunting=True`, `noitem=False`, `itemfinder_item="Potion"`, integer `itemfinder_rate=5` | `+hunt` → `+inventory` → `+use Potion=<current target>` |
| Wild held Oran | Hunting enabled, `noitem=False`; chart entry `name="Rattata"`, `min_level=5`, `max_level=5`, positive weight, `held_item="Oran Berry"`, integer `held_item_chance=5` | `+hunt` → ordinary capture → inspect actual current held item → `+hold <caught slot>=` → `+inventory` → `+use Oran Berry=<current target>` |

The durable finder receipt binds the real server attempt and a successful or
failed roll. It credits at most one Potion, rejects replay and serializes
competing claims over the same character. Three elapsed seconds separate
attempts; clearing a transient cooldown or reconnecting does not grant an
extra roll. Current location, hunting flags, battle lock and exact source
configuration are rechecked. Invalid/disabled/noitem/unnamed sources grant
nothing. Post-credit or receipt-write failure rolls back both receipt and bag.
Finder credits require a fresh player command outside a containing transaction:
an outer abort cannot leave a successful find announcement for a lost Potion.

The native wild rule accepts only the exact Rattata/Oran tuple and integer
chance. `noitem` suppresses it. Capture retains only the encounter's current
uneaten/unremoved held item. Consumption or removal remains explicitly empty
through save, reconstruction and capture; old encounter metadata cannot refill
it. Capture replay cannot mint another Pokémon or berry. Capture-ball supply is
outside this item-source delivery.

The named-source qualification uses tagged disposable rows, exact 5% authoring,
controlled legal success/failure rolls and actual elapsed cooldown time. This
is reproducible automated command/SQL evidence, not a natural-frequency sample,
socket login, shared source installation or a claim that current rooms stock
the broader catalog. See [the report](testing/renewable-item-sources-2026-10-25.md).
