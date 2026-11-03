# Six additional Z source mappings — October 29, 2026

Issue #932 appends exactly five generic damage profiles and one status profile
to the existing allowlists. No crystal, ordinary learned move, native form,
side budget or source stock is added. The full registry becomes **69 mappings
on 35 crystals: 37 generic / 15 status / 16 signature / 1 Ultra**.

| Crystal | Source | Exact result | Qualified native PF2 learning example |
| --- | --- | --- | --- |
| Firium Z | Fire Blast | Inferno Overdrive,185 Fire Special | Magmar, level54 |
| Firium Z | Flare Blitz | Inferno Overdrive,190 Fire Physical | Growlithe, level45 |
| Waterium Z | Hydro Pump | Hydro Vortex,185 Water Special | Gyarados, level40 |
| Electrium Z | Thunder | Gigavolt Havoc,185 Electric Special | Pikachu, level41 |
| Groundium Z | Earth Power | Tectonic Rage,175 Ground Special | Gastrodon, level39 |
| Psychium Z | Calm Mind | Clear negative user stages, then ordinary +1 Sp. Atk/+1 Sp. Def | Ralts, level21 |

Learning examples follow PF2's existing combined-generation level allowlist;
they do not replace it with a new generation policy. Actual source acquisition
cases use configured native hunting/capture, `+teach`, the moveset menu, a real
crystal purchase and `+hold`, followed by `+zmove` and source PP payment.
Those tagged sources are prerequisites, not permanent public stock or spawn claims.

The pinned primary [source moves](https://github.com/smogon/pokemon-showdown/blob/ccfaa20f32af363569cd21a9d501b2bc1ded26b1/data/moves.ts),
[generic power conversion](https://github.com/smogon/pokemon-showdown/blob/ccfaa20f32af363569cd21a9d501b2bc1ded26b1/sim/dex-moves.ts)
and [Z action rules](https://github.com/smogon/pokemon-showdown/blob/ccfaa20f32af363569cd21a9d501b2bc1ded26b1/sim/battle-actions.ts)
were reviewed before adding profiles. Damaging copies have normal single targets
and cannot inherit ordinary recoil, burn/paralysis/SpD-drop chances, accuracy or
Thunder weather modification. Calm Mind retains its ordinary post-bonus boost
events and normal ability rules. The existing 63 profile entries remain intact.

**18 new engine cases** pin exact profiles, native level boundaries, real useful
damage/Protect, source preservation, Thunder under sun and Calm Mind ordering.
Ability combinations in the paid mechanics adapters are labelled separately
from native learning and SQL ownership proof.

**94 disposable PostgreSQL cases passed**: five sources each replay the 17-facet
ordinary command matrix (85), and Calm Mind adds nine source/bonus/payment routes.
Controls include real protection, native immunity, sleep, wrong/missing crystal,
depleted PP, invalid actor target/source, copied or stale identity, Magic Room,
Embargo, duplicate input, two checkpoint rebuilds, payment/checkpoint faults and
postbattle held conservation. Calm Mind checks exact stage order, PP and one-side
budget through rebuilds. These are captured command transports over production
models/transactions, without a logged-in socket acceptance run.

The [combined additions receipt](item-additions-2026-10-29.md) records the complete
mandatory gate and final source fingerprints. Earlier dated Z receipts stay
historical; source-only availability and deployed/live code are separate facts.
