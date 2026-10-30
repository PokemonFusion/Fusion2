# Daycare custody (#727)

Breeding production and eggs use the separate [breeding route](breeding.md)
from #728; depositing by itself does not start that activity or grant an egg.

The beta Daycare holds two hatched owned Pokemon per character. Deposit costs
100 existing trainer money once per stay; retrieval is free. There is no passive
EXP, HP/PP restoration, friendship or evolution. Breeding uses its own explicitly
started cycle, cost and cooldown; depositing alone never starts one.
Depositing and retrieving have no cooldown.

At an explicitly configured Daycare, [Mirror Herb teaching](../contextual-and-field-items.md#mirror-herb-teaching)
is a separate free review/confirm route: `+daycare herb <recipient>=<donor>/<move>`.
Keep both eligible owned Pokemon in the ordinary party rather than depositing
them. The recipient needs a held Herb and empty move slot; exact native Gen 9
egg data and the donor's active knowledge authorize the move. The reusable Herb,
donor and existing PP are preserved. This does not change custody or breeding.

```text
+daycare deposit 3
+daycare
+daycare retrieve ENTRY_ID
```

Deposit accepts canonical party slots and unique owned UUID prefixes of at least
eight hex characters, including boxed Pokemon. Status shows the exact entry ID,
Pokemon ID and custody place, and works after reconnect. Retrieval returns the
same Pokemon to its old party slot if free, another free slot otherwise, then a
box if the party is full. It never evicts an existing member. Repeating retrieval
returns the saved receipt without creating, healing or moving another Pokemon.

The deposited Pokemon retains its trainer owner and exactly one canonical
`daycare` placement, outside party/box mirrors, with an exclusive entry-bound
claim. It cannot battle, be released, moved, fused, traded or listed while
deposited. Foreign IDs, eggs, active/unlocked Fusion sources, battle participants,
conflicting claims, full Daycare and insufficient money are rejected before fees.
Deposit, fee, placement and claim save together; withdrawal, destination and
receipt save together. Competing requests use the shared owner/storage lock order.

Each new stay has one entry identity; retry of an active deposit on the same
Pokemon returns its existing entry rather than charging twice. Once a stay is
retrieved, an explicit later deposit begins a new stay with a new fee. Completed
receipts are historical, and later ownership/storage changes do not alter them.

Staff inspect the entry, owned UUID, canonical placement and claim together.
The placement/Daycare audit is read-only. A missing or conflicting record requires
review; automatic recovery never guesses an owner or fabricates/deletes a Pokemon.
An active breeding cycle must be collected/cancelled through its own route before
parent retrieval. No cancellation charge or insufficient-funds gate can strand a
Pokemon already in Daycare.
