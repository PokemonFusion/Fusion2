# Bounded berry growing and flavor-use contracts (#776)

Status: **bounded implementation accepted in #809–#812**; see the
[player guide](../berry-nursery.md) and [local SQL acceptance](../testing/berry-player-routes-2026-10-22.md).
Applying the migration, deploying the commands, installing public stock and real
timed live growth remain release work. The original contract below was inspected at
`4f0995b1b53e3b5a040d27092e48da05c67aa2d8`. #767's legacy field feeding is
complete and stays independent. The existing `BerryPlant` dataclass has only
in-memory stage/elapsed/watering state and two unit tests; it supplies no durable
ownership, inventory boundary or player commands.

## Slice A: one owned Oran Berry bed

Use one **Oran Berry**, one personal bed per trainer, at an optional authored
**Berry Nursery**. Proposed normal entry is a labeled `nursery` exit from a
public hub, with a return exit; the opt-in content recipe must accept an explicit
hub instead of assuming an existing dbref or duplicating Adventure rooms.
Room text and `+berry help` explain the costs and four-hour ready time.

Proposed commands, usable only in that nursery:

- `+berry` / `+berry status`: inspect your own empty/growing/ready bed and times.
- `+berry plant Oran Berry`: debit one bag berry and create one growth cycle.
- `+berry water`: water the current not-yet-ready stage, at most once per stage.
- `+berry harvest`: claim this ready cycle once and credit Oran Berry bag stock.

No plot key, farming level, daily login, tool item, fertilizer, currency fee,
quest or staff override. Use exactly one bag Oran Berry; a held berry is not a
seed. Water is free at this authored nursery and needs no inventory item.
Oran retains its existing field/held healing effect after harvest.

Selected **PF2 rules**, not canonical farming/yield claims:

| Rule | Value |
| --- | --- |
| Stage length | 3,600 real elapsed seconds |
| Growth | Four stages; ready at planted UTC + 14,400 seconds |
| Water | One per current stage 0, 1, 2 or 3; ready plants reject watering |
| Yield | One seed-return berry + one for each distinct watered stage; range 1–5 |
| Decay | None; a ready crop waits for its owner |
| Offline time | Counts; command/reconnect derives stage from persisted UTC times |
| Replant | Explicit new plant command after harvest; never automatic |
| Ownership | Trainer's personal bed; no shared/public harvest or transfer |
| Battle/trade | Nursery mutations require no battle lock and no conflicting reservation |

Repeated watering in the same stage gives no extra yield and changes nothing.
There is no catch-up watering of missed stages. Check server UTC only; reject
negative/future-corrupt timestamps rather than accepting client elapsed values.
Going offline, moving rooms or server downtime cannot reset or speed the cycle.

## Durable state and atomic boundaries

Plan a persistent bed/cycle model with a unique trainer bed, immutable cycle
UUID, planted/ready timestamps, four-bit watering mask, current berry ID and
last completed harvest receipt. Proposed model/schema changes need a reviewed
migration file; **running migrations requires separate explicit permission**.
Do not serialize a mutable in-memory `BerryPlant` into a parallel inventory
writer or rely on process timers to credit items.

Lock trainer/inventory and bed in one consistent documented order. Plant's
one-berry debit and cycle creation commit together; failed debit, partial SQL,
bed save or parent transaction rolls both back. Water locks/rechecks the cycle
and current stage; retries in that stage are idempotent. Harvest atomically
locks the same cycle, verifies ready/owner/access, credits its exact yield,
records the completed cycle receipt and empties the bed. A replayed callback,
two concurrent harvests or a write failure cannot double-credit, lose a crop
or reset a newer planting. Bound callbacks to trainer, bed and cycle UUID;
never resolve a stale request against whatever crop is present now.

Inventory and bed caches refresh only after committed writes. Success text is
commit-aware; parent rollback emits no false success. Reconnect/fresh process
reads canonical SQL. A repeated harvest of an already-completed empty bed gives
an honest already-claimed/empty result, while a new explicit planting receives
a fresh cycle. Trainer deletion/account cleanup follows existing owner rules;
no unreviewed cross-owner transfer is introduced.

## Slice B: one explicitly selected Razz Berry snack

Accept a separate small **PF2 functional food equivalent**: proposed
`+berry snack Razz Berry=<party slot, unique full name/ID or fusion>` consumes
one **bag Razz Berry** to heal up to **10 HP** on one living eligible owned
Pokemon outside battle. This effect is a PF2 design choice, **not** a claim that
Razz normally heals in the cartridge games. It grants no contest condition,
flavor preference, friendship, lure/capture bonus or move PP. No ingredients,
new cooked-item definition, cooking skill, recipe book or contest engine.

The command delegates to the shared field-item target/lock/transaction checks
and existing medicine HP calculation; it does not bypass them through the bed
service. Require fresh canonical owned party/current Fusion, non-egg and no
battle/reservation, reject ambiguous/stale/foreign/boxed targets and dead/full-HP
targets without debit. Clamp to max HP from `get_max_hp` with current genetics,
EVs/nature/Hyper Training, preserving status, PP, held items and progression.
Exactly one useful heal and one bag debit commit atomically; insufficient stock,
failed/partial debit, post-save/parent rollback or competing final-copy requests
leave no partial result. A held Razz Berry cannot fund the snack.

Ordinary `+use Razz Berry` remains explicitly unsupported until this named
feature deliberately chooses/registers that alias and tests it. Other flavor,
EV and combat-only berries are not implicitly enabled by a shared suffix. Existing
Oran/legacy/EV field feeding and held effects retain their own semantics.

## Intentional acquisition and release

Author an optional two-offer nursery counter using existing `+store`: **Oran
Berry 100 / stock 5**, **Razz Berry 100 / stock 5**, finite stock and no automatic
refill. These are selected PF2 values. The shop and one-bed-per-owner contract
require explicit nursery setup; they are not a live seeding operation, an
automatic stock default or an extension of #781's separate six-item location.
The content recipe must validate all offers/links and prevent duplicate setup.
No source is inferred from item metadata or from the helper tests.

The normal walkthrough starts at a real authored hub exit, discovers the nursery
and shop, buys berries, checks inventory and plants/waters/harvests/reloads. Staff
setup and test clock manipulation are separate evidence. A local controllable
clock proves boundaries; a live timed acceptance must record real timestamps
and cannot claim four-hour growth from an administrative state jump.

Slice B's walkthrough purchases Razz, discovers snack help, damages an eligible
fixture through normal play, snacks, checks one debit/+10-or-clamped HP and
reconnects. It may use the same optional nursery counter but does not depend on
building agriculture. Each feature needs independent acceptance and release.

## Implementation and acceptance gates

Separate follow-ups cover durable bed/atomic operations, growing commands and
optional content, the one Razz snack, and integrated growth/recovery acceptance.
Every implementation issue links this contract and retains its own prerequisites.
Growing cannot ship from dataclass tests alone; snacks cannot ship from metadata
or an invented contest-stat row.

Required SQL/reload/failure cases include 0/3,599/3,600/14,399/14,400 seconds,
offline progress, repeated clock reads, every watering bit, min/max yield, wrong
owner/room/battle, repeated harvest and replant with stale callbacks, final seed
contention, simultaneous water/harvest, failed post-credit bed save and outer
rollback. Test ordinary command routes plus real transaction contention without
weakening unique/stock/receipt assertions. Snapshot/reconnect must preserve the
same cycle and committed inventory. Snack coverage includes useful/clamped/no-effect
HP, fainted/egg/boxed/Fusion/ambiguity, bag/held separation, last copy, save/debit
failure and unchanged current medicine/berry behavior.

New schema implementation tests use disposable schemas; migrations are reviewed
without applying them to a running world. Executable changes require affected
field/progression/commerce checks and the mandatory three-order gate. Local
automated, manually timed live, configured-source, CI and deployment evidence
remain separate (#781/#782). Plot ingredients, broad agriculture/economy,
all-berry growing, shared beds, contests and unrelated acquisitions are excluded.

## Local references

- [In-memory helper](../../pokemon/helpers/berry_system.py) and its
  [two tests](../../tests/items/test_berry_system.py).
- [Field target/transaction checks](../../pokemon/services/field_items.py),
  [field berries](../../pokemon/services/field_berries.py) and
  [field food](../../pokemon/services/field_food.py).
- [Current acquisition limits](../item-availability.md) and
  [field berry evidence](../testing/field-berries-2026-10-20.md).

This contract specifies PF2 gameplay rather than importing a generation-wide
farming or contest ruleset. It changes no current field/held effects, runtime
models, database, stock or characters.

## Created implementation issues

| Issue | Deliverable | Depends on |
| --- | --- | --- |
| [#809](https://github.com/PokemonFusion/Fusion2/issues/809) | Persist one Oran Berry bed and atomic growth operations | #776 design |
| [#810](https://github.com/PokemonFusion/Fusion2/issues/810) | Add ordinary Oran growing commands and opt-in nursery content | #809 |
| [#811](https://github.com/PokemonFusion/Fusion2/issues/811) | Add the bounded Razz Berry field snack equivalent | #776 design |
| [#812](https://github.com/PokemonFusion/Fusion2/issues/812) | Accept durable Oran growth and independent Razz snack player slices | #810, #811 |

The bounded implementation supplies #809/#810's durable Oran growing and #811's
independent Razz snack. #812's receipt accepts local production-command/SQL,
reconnect, replay and contention evidence without claiming live timed growth,
full agriculture or contests. The [original design validation receipt](../testing/item-designs-2026-10-22.md)
remains historical design evidence. Lock order is room → character → storage →
trainer → bed; inventory is written under the trainer lock. Cycle callbacks bind
the UUID observed before waiting for locks. Bed state is read directly from SQL,
inventory caches retain their existing commit-aware updates, and successful
mutation notices use `transaction.on_commit`.
