# Field items

Use `+use <item>=<target>` outside battle. Medicine and berry feeding share the
same transaction, fresh ownership/placement checks and canonical target rules.
Targets are party slots 1-6 (with gaps preserved), unambiguous names, full
Pokemon UUIDs, or `fusion`/`self`/`me` for the current reserved Fusion. Eggs,
boxed Pokemon, foreign owners and inactive Fusion reservations are ineligible.
An effective use consumes one item; invalid or ineffective uses consume none.

## Existing berry feeding allowlist

| Items | Field effect |
| --- | --- |
| Oran Berry | Restore up to 10 HP |
| Sitrus Berry | Restore up to 1/4 maximum HP, rounded down |
| Figy, Wiki, Mago, Aguav, Iapapa Berry | Restore up to 1/3 maximum HP, rounded down |
| Berry Juice | Restore up to 20 HP |
| Cheri Berry | Cure paralysis |
| Chesto Berry | Cure sleep, including its saved remaining turns |
| Pecha Berry | Cure poison or toxic poison |
| Rawst Berry | Cure burn |
| Aspear Berry | Cure freeze |
| Lum Berry | Cure any of those major persistent conditions |
| Leppa Berry | Restore up to 10 PP to one current active move |
| Pomeg, Kelpsy, Qualot, Hondew, Grepa, Tamato Berry | Reduce the corresponding EV and increase friendship as below |

HP recovery requires a living, injured target and is capped at its calculated
maximum HP. Manual feeding can be used above the automatic held activation
threshold. Status cures require the matching saved condition on a living target.
Leppa requires a living target with a depleted active move. Use
`+use Leppa Berry=3/Water Gun` or `+use Leppa Berry=3/4`: move numbers retain
canonical active-slot gaps. Without `/move`, restore the first depleted active
move. Stored PP boosts and current dex data determine its cap; other moves are
untouched. Examples: `+use Oran Berry=3`, `+use Lum Berry=fusion`.

The five flavor recovery berries have a concrete HP effect in this allowlist.
Their nature-based confusion is a combat-only volatile and is not introduced or
persisted by field feeding. Lum's field use cures persistent status, not a
nonexistent out-of-battle confusion state. The existing held effects retain
their normal thresholds, nature/confusion rules, triggers and consumption.

## EV berries

| Berry | Stored EV index | Stat |
| --- | --- | --- |
| Pomeg | 0 | HP |
| Kelpsy | 1 | Attack |
| Qualot | 2 | Defense |
| Hondew | 3 | Special Attack |
| Grepa | 4 | Special Defense |
| Tamato | 5 | Speed |

The PF2 field policy removes `min(10, current EV)` from the selected stat and
adds friendship based on its value before feeding: +10 below 100, +5 from
100-199, or +2 from 200-254. Friendship is capped at 255. Either useful effect
permits feeding: zero EVs can still gain friendship, and maximum friendship can
still permit an EV reduction. At zero selected EVs and 255 friendship, the use
has no effect or cost. No additional location, held-item or luxury-ball bonus is
applied by this policy.

EV arrays retain project limits (six values, 0-252 each, total at most 510).
Invalid saved EV or friendship rows are rejected for staff review without
spending an item. Project stat helpers recalculate the affected stats. When HP
EVs fall, current HP changes by the maximum-HP difference to preserve missing
HP; a living target stays at least at 1 HP, and a fainted target stays at 0.
EV berries can be fed to fainted eligible members and never revive or cure them.
HP/status/PP, EVs, friendship and inventory remain durable and atomic; a failed
write rolls back the debit, and waiting uses recheck fresh saved values.

## Limits

This is an explicit 21-item field allowlist (20 berries and Berry Juice), not
generic support for every `isBerry` entry. Persim/Bitter (confusion-only), Enigma
(damage-triggered), resist, stat-boost, accuracy, retaliation and other combat
berries remain held-only. Contest/flavor-only berries such as Razz and Bluk have
no manual field effect. No plants, harvest persistence, contests, cooking, new
berry names, plot items or additional training items are introduced.

`+use` is blocked during battle. This work adds no battle inventory-feeding
action, and EV reduction is field-only. Existing held berries still work through
their repaired battle paths. Field medicine, Rare Candy and PP Up/PP Max retain
their existing command routes; see `help use` and the in-game maintenance help.
