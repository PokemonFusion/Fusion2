# Thirteen explicit flavor snacks (#889–#891, 2026-10-25)

Accepted locally: the thirteen existing names below now heal up to **10 HP**
through **+berry snack <berry>=<target>**, matching the existing Razz PF2
food equivalent. The command spends the selected bag berry. It does not turn
another flavor berry into Razz or spend an available Razz control copy.

| Issue | Exact names |
| --- | --- |
| #889 | Bluk, Nanab, Pinap, Wepear Berry |
| #890 | Cornn, Magost, Nomel, Rabuta Berry |
| #891 | Belue, Durin, Pamtre, Spelon, Watmel Berry |

[Machine receipt](flavor-snacks-2026-10-25.json) records every named positive,
source identities, raw evidence hashes, regression receipts and full qualification.
[Current index](item-availability-flavor-snacks-index-2026-10-25.json) names the
actual snack command for each item. All 452 world availability entries remain
unverified; the earlier indices and dated acceptance reports are preserved.

The service reuses FieldProgressionUse and FieldBerryUse's current target,
usefulness, atomic debit, persistence and rollback checks. Real party slots,
unique names/full IDs and the actual current Fusion are eligible. Full, fainted,
egg, boxed, foreign, ambiguous/inactive Fusion and battle-locked targets spend
nothing. A held copy remains held. HP and one useful bag debit commit together;
status, PP, genetics and progression stay unchanged.

Validation: **28 new ordinary-command/PostgreSQL cases**, **18 focused checks**
and **284 compatibility cases** passed. The baseline had 22 expected failures
and six passes across the same 28 cases. Each of the thirteen positive flows
buys actual finite stock, holds a second copy, rejects +use, heals HP 1→11
using the selected bag copy, preserves its Razz control/held copy and reloads
through a fresh SQL connection. Each batch also exercises invalid/no-effect
targets, capped current Fusion, partial debit/post-save/outer rollback, two
connections contending for the last copy, and actual battle/held exclusions.

All three mandatory fresh-process orders passed **6,154 tests /4,028 skipped
each**, wrapper exit 0. All **1,136 Python source identities** match the frozen
qualified copy; the **25 unrelated shared dirty paths** are unchanged.

The first compatibility runner requested a nonexistent field_medicine_cases.py
and executed no case. Its failure is retained; the correct field_item_cases.py
then passed all 23 cases. No gameplay repair was made for that runner error.

These are production command classes and store menus with controlled SQL/runtime
fixtures, **not a socket login or deployed/public acquisition claim**. Tagged
source Pokemon, placements, finite stock, wallet and HP/status/battle conditions
are prerequisites, separate from player inputs.

No +use alias, manual battle medicine, automatic held healing, status/PP,
friendship, EV, nature-confusion, contest, lure or capture effect is added.
All fourteen Razz/flavor definitions retain their Natural Gift/Fling identities.
Oran growing, Razz and the nursery's two offers are unchanged. No definition,
plot item, public stock, shared game service or existing human data is changed.
