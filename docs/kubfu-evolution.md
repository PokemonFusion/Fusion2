# Kubfu evolution through functional Scrolls (#762)

## Selected PF2 rule, recorded before implementation

Native owned **Kubfu** evolves through the existing explicit bag-item command:

| Functional item | Canonical target | Style | PF2 reference price |
| --- | --- | --- | --- |
| Scroll of Darkness | `Urshifu` | Single Strike | 10000 |
| Scroll of Waters | `Urshifu-Rapid-Strike` | Rapid Strike | 10000 |

`+evolve <full Pokemon ID> <complete Scroll name>` selects exactly the matching
branch. An optional `=<canonical target>` must agree with that item. Bare
`+evolve`, a target alone, incomplete names, a mismatched target/item or arbitrary
tower-completion text/flags cannot evolve Kubfu. The chosen item is required in
the actual trainer bag, and exactly **one copy is consumed on success**. A held
copy does not supply that debit; any separate equipped copy remains held.
Failed, unavailable or replayed requests consume nothing.

This is a non-plot PF2 item equivalent for the two checked-in tower predicates.
No tower, quest, location, time, region, friendship, new level threshold or
completion flag is required. Existing owner, native source/form, egg,
Everstone, battle-lock and Fusion-reservation guards remain in force. The shared
evaluator still checks exact source `evos`, target `prevo`, any explicit dex
level/gender/region constraints and reviewed target metadata. It never treats
generic `other` or tower-completion conditions as true.

The bounded mappings require the exact native Kubfu source and the reviewed
Urshifu/Urshifu-Rapid-Strike names, type `other`, original tower strings and
expected form metadata. The Rapid Strike branch deliberately admits only its
existing `baseSpecies="Urshifu"` / `forme="Rapid-Strike"` row. Evolved Urshifu
cannot switch style using a Scroll; other sources, foreign forms and Gigantamax
targets are excluded. No generated species/dex data is edited.

The modern games' bag items select the same branches, as described in the
[Darkness](https://bulbapedia.bulbagarden.net/wiki/Scroll_of_Darkness#Effect) and
[Waters](https://bulbapedia.bulbagarden.net/wiki/Scroll_of_Waters#Effect) references
(reviewed October 21, 2026). Their Key Item classification and tower appearances
are not PF2's item role. PF2 deliberately uses consumable **Evolution Items**, a
10000 reference price per Scroll, and opt-in normal shop/reward acquisition.
Those consumption/cost choices are PF2 policy, not a claim of cartridge parity.
The existing item-price CSV has no Scroll rows and remains unchanged; an authored
shop charges its configured stock price. There are no automatic grants or live
NPC/shop/reward changes.

## Ordinary player route and persistence

Builders may stock either complete item name through the existing shop editor
or existing reward configuration. Ordinary players purchase from configured
stock, inspect `+inventory` / `+itemdex <Scroll name>`, copy the full owned ID
from `+party <slot>`, and choose their item:

```text
+evolve <full ID> Scroll of Darkness
+evolve <full ID> Scroll of Waters
```

The optional explicit forms are `=Urshifu` and `=Urshifu-Rapid-Strike`, respectively.
These are two alternatives for a Kubfu; one Pokemon completes one evolution.
`+use` and holding a Scroll do not invent a second evolution route.

The existing evolution service locks storage, trainer and the fresh owned row,
checks ownership/placement/reservation/context, debits the chosen bag item,
saves the same Pokemon and records its normal evolution receipt in one
transaction. Failed writes roll back inventory, species and receipt, then
restore cached model state. Reconnect/reload/retry and competing requests must
never spend twice or switch an evolved form.

Evolution preserves UUID, owner, nickname, canonical party/box placement and
mirrors, held item, current HP/status/sleep, EXP, IVs/EVs, friendship, moves/PP
and unrelated flags. Canonical species, mapped ability (`Inner Focus` to
`Unseen Fist`), derived types/stats and the normal evolution receipt change.
No healing, stat rescaling, new move grant, legendary acquisition, story unlock
or Gigantamax capability is added.

Validation must exercise ordinary purchase/display/evolve/reload/retry commands
for both branches, item/target/source/condition negatives, failed debit/save,
foreign ownership, reservations, held-only copies, boxed placement and real
concurrent requests. Automated disposable command/model proof, live login,
hosted CI, main merge and deployment are separate evidence categories.
