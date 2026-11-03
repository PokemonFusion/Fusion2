# Stat-item next-action acceptance — October 29, 2026

All **37 disposable PostgreSQL cases passed** (54.805s): 18 independent normal
fixtures, 18 matching Magic Room controls and one matrix comparison. They record
**364 ordinary command inputs**, 19 paired stat probes and independent owned-row
HP, PP, held-item and bag/history conservation after checkpoint restoration.
The [machine receipt](item-next-action-2026-10-29.json) pins sources and raw logs.

This supplements #922–#924 and #929. Attack and Special Attack increase actual
next-move damage; Defense and Special Defense reduce actual incoming damage;
Salac changes the next ordinary action order. Both Weakness Policy stats have
their own probe. The observation wrapper calls the unmodified production move
method; damage, accuracy and order are never replaced.

Fixtures supply native level 50 Mew holders and level 55 Mew opponents, legal
known slots checked against native learning metadata, injuries and bag stock.
Starf explicitly prepares four stats at +6, leaving Attack as its sole eligible
choice; this establishes next-action behavior, not earned-stage acquisition or
random sampling (covered separately). False Swipe preserves a low-HP target;
the captured damage is read before residual terrain healing.

| Item | Stat | Ordinary probe | Suppressed control → consumed item |
| --- | --- | --- | --- |
| Absorb Bulb | special_attack | Confusion | 16 → 24 HP |
| Apicot Berry | special_defense | Mud-Slap | 12 → 9 HP |
| Cell Battery | attack | Pound | 18 → 26 HP |
| Electric Seed | defense | False Swipe | 23 → 16 HP |
| Ganlon Berry | defense | False Swipe | 20 → 16 HP |
| Grassy Seed | defense | False Swipe | 23 → 16 HP |
| Kee Berry | defense | False Swipe | 23 → 16 HP |
| Liechi Berry | attack | Pound | 18 → 26 HP |
| Luminous Moss | special_defense | Mud-Slap | 12 → 9 HP |
| Maranga Berry | special_defense | Mud-Slap | 12 → 9 HP |
| Misty Seed | special_defense | Mud-Slap | 12 → 9 HP |
| Petaya Berry | special_attack | Confusion | 16 → 24 HP |
| Psychic Seed | special_defense | Mud-Slap | 12 → 9 HP |
| Salac Berry | speed | Rain Dance | foe first → holder first |
| Snowball | attack | Pound | 18 → 26 HP |
| Starf Berry | attack | Pound | 18 → 34 HP |
| Throat Spray | special_attack | Confusion | 16 → 24 HP |
| Weakness Policy | attack | Pound | 18 → 34 HP |
| Weakness Policy | special_attack | Confusion | 16 → 31 HP |

The **363 focused regression cases** passed separately, with one denied-cache
write warning. No runtime code changed for this supplement. Every runtime
fingerprint in the preceding repair/addition receipts still matches. The final
mandatory gate on those sources remains **8,135 passed / 4,032 skipped in each
of three fresh processes**; this new SQL runner is separate evidence and was
added to lifecycle CI. Prior receipts remain dated and unchanged.

The three distinct batches now total **374 passing SQL cases** (211 repairs,
126 additions and these 37), run separately. All schemas were
dropped and the private helper stopped. Captured transport establishes no socket,
public acquisition, shared-world stock or deployed acceptance. No push, migration,
service restart or deployment occurred.
