# Oran growing and Razz snacks

At a configured **Berry Nursery**, follow its `nursery` exit from the selected
public hub and use `back` to return. `+store` → **Buy items** offers Oran Berry
and Razz Berry for 100 each, initially five of each. Stock is finite, with no
automatic refill or resale. This optional recipe does not create public stock
until an operator deliberately installs it at a reviewed hub.

Use `+berry help` anywhere for discovery. At the nursery:

1. Buy one Oran Berry and check `+inventory`.
2. Use `+berry plant Oran Berry`. It spends one bag seed on your private bed.
3. Use `+berry status` for the cycle, server UTC ready time and expected yield.
4. Use `+berry water` once during each of the four one-hour stages. Water is free;
   missed stages cannot be watered later. Each distinct watering adds one berry.
5. After four real elapsed hours, use `+berry harvest` once for 1–5 Oran Berries.
   Ready plants do not decay. Offline time counts. Replant explicitly afterward.
6. Use the harvested berry normally, for example `+use Oran Berry=3`.

Only the owner can tend their bed. A held Oran Berry is not a seed. Battle locks,
the wrong room, changed cycles and invalid saved times reject safely. Repeated
watering or harvest cannot add extra credit, and an old request cannot reset a
newer crop. No tools, currency fee, plot unlock, farming level or process timer.

Independently, `+berry snack Razz Berry=3` feeds one bag Razz Berry to an eligible
living, injured owned party member for up to **10 HP**. `fusion`, a unique name
or a full Pokemon ID uses the shared field target rules. It works outside battle
without a nursery or crop. Fainted/full/egg/box/foreign/ambiguous/inactive Fusion
targets and held-only stock consume nothing. HP and one debit commit together;
status, PP, held items, genetics and progression stay intact.

The Razz effect is a selected **PF2 food equivalent**. It grants no contest,
friendship, lure or capture effect. `+use Razz Berry` remains unsupported. Other
flavor berries, growing species, shared beds and broad agriculture are deferred.

The [acceptance receipt](testing/berry-player-routes-2026-10-22.md) separates
production-command/SQL checks with controlled server time from live timed growth.
The earlier [nine-item release walkthrough](testing/item-live-2026-10-22.md)
did not include this later feature. Deployment, applying the reviewed
`0046_berry_bed` migration, permanent source installation and live four-hour
acceptance require their own release work.

For source authoring only, `BerryNursery.install(reviewed_hub)` in
`pokemon.services.item_counter` installs the checked-in `world/berry_nursery.json`.
It validates the existing item names and links, serializes competing installers,
and rejects drift/conflicts. Reinstalling preserves sold stock. It leaves the
six-item Supply Corner and Adventure content independent.
