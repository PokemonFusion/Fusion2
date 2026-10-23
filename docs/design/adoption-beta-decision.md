# Adoption beta decision

Decision recorded October 23, 2026 for [#724](https://github.com/PokemonFusion/Fusion2/issues/724).
The project owner explicitly selected **defer Adoption from beta**. Adoption is
a demonstrated PF1 capability, but it is not a PF2 closed-beta requirement.
There is no Adoption implementation task on the active critical path.

Consent trading and the player marketplace provide the beta's ownership-exchange
routes. Building a third route would add donation payments, a system-owned pool,
egg custody, pricing, expiry and recovery policy before those foundations have
been accepted. Deferral avoids adding that economy to the beta. It does not
claim those other October systems are already implemented or accepted.

## Surviving PF1 evidence

The reviewed files are in the separate local `legacy_pf1/game/muf` archive;
they are not PF2 runtime code. `PF1_MUF_inventory.md` identifies their programs.
The archive proves coded capabilities, not deployment, frequency of historical
use, reliability under concurrency, or the desirability of copying the policy.

| Source | Observed behavior |
| --- | --- |
| `316.m:7–23` (`FindCost`) | Price is level times the sum of base stats times rarity. An egg price multiplier is commented out. |
| `316.m:26–96` (`Donate`) | Select a populated party slot 1–6, including an egg, and confirm. Store the same Pokémon ID in the adoption pool, remove current-trainer and RP-status properties and the party link, reset happiness/bond and restore HP. Pay price divided by `(daily donation count + 1)` and then by 10; increment the donation achievement. |
| `316.m:100–170` (`DisplayRecord`, `PickOne`) | Inspect the record and price, confirm, require a free party slot and sufficient credits, set the current trainer, insert the same ID into that slot, remove the pool record and debit credits. There is no box overflow in this path. |
| `316.m:173–342` | Random display and filters for species, gender, nature, level and eggs lead to record selection. |
| `316.m:346–366` (`main`) | Require an RP identity, email validation and a room marked as an Adoption Center. Offer donation or browsing. |
| `299.m:488–529` | Breeding creates a Pokémon ID with original/current trainer, mother, creation time and egg timer. |
| `299.m:637–670` (`DaycareMenu`) | Offer a pending Daycare egg; retain it when the party is full or the player asks to collect later. The refusal message promises a good home, but this branch only clears `daycare/egg`: it does **not** insert a pool record. This is not evidence of a working Daycare-to-Adoption transfer. |
| `220.m:22,132`, `1013.m:6–47` | Daily maintenance resets the donation achievement and calls `AdoptDaily`. That routine compacts pool records and randomly deletes roughly one fifth of pooled Pokémon, including their stored data. |

Donation/acquisition reuse the existing ID; those paths do not explicitly rewrite
the original-trainer property. They also do not establish an atomic PF2 ownership
or provenance contract. These observations must not be treated as permission to
repair, import or delete legacy records.

Archive SHA-256 fingerprints (case insensitive):

| File | SHA-256 |
| --- | --- |
| `316.m` | `bfe9a55ae6b4282a500a1fb99cfba7d573d9bafb16d3181fbb456d25660d5967` |
| `299.m` | `4bff4a91066d4bf4802d1562a547f44d327619bab8d40d397cd228fc4195920a` |
| `220.m` | `793848cd41419f194ad911ca11caa263aa5b4bd88e146c23b16e69986ad1df22` |
| `1013.m` | `730e7bd8af18cd0bfa1110ad652b8d957a2d551514ec1903acbaa160fa33b4ad` |

## Consequences and future boundary

Beta adds no donation reward, adoption purchase, pool refresh, random destruction
or adoption achievement. No donation/buyback or repeat-adoption credit/progression
loop is introduced. Daycare and breeding must retain or explicitly return owned
assets through their own recoverable routes; rejection must not silently donate
or delete an egg.

A future proposal requires a fresh product decision and a separate implementation
issue. It must settle supported assets (including eggs), custody/provenance,
confirmation and discovery, capacity, pricing and anti-farming policy,
expiry/reclaim without silent loss, shared transfer/reservation reuse, concurrent
payment/ownership writes, retries and ordinary-player acceptance. The PF1 formulas
and destructive maintenance are not approved defaults.

Verification for this decision is source review plus the owner's explicit answer.
No Adoption runtime, migration, live deployment or player walkthrough is claimed.
