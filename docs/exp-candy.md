# EXP Candy

Use one copy outside battle with `+use Exp. Candy XS=3`, substituting the full
size and a current party slot, exact owned name, full ID or `fusion`.
`+inventory`, `+itemdex` and `+help +use` describe these field items.

| Item | EXP per copy | Optional counter price | Finite stock |
| --- | ---: | ---: | ---: |
| Exp. Candy XS | 100 | 100 | 10 |
| Exp. Candy S | 800 | 800 | 10 |
| Exp. Candy M | 3,000 | 3,000 | 5 |
| Exp. Candy L | 10,000 | 10,000 | 2 |
| Exp. Candy XL | 30,000 | 30,000 | 1 |

A same-level EXP gain is useful. A final partial gain stops at the species'
level100 threshold and consumes one copy; level100 consumes nothing. Invalid
level/EXP or an explicitly unknown growth curve requires review. Current project
species records omit growthRate, so they use the existing medium-fast default.
The service also accepts the growth curves already implemented by the project;
it does not guess an unimplemented erratic curve.

Living Pokémon keep their absolute HP deficit with a minimum of1; fainted
Pokémon remain at0. This does not cure status, refill moves, change genetics or
Hyper Training, or automatically evolve. Use the separate `+evolve <full ID>`
decision when eligible. Rare Candy retains its existing one-level behavior.

Every crossed-level move is saved as actual knowledge in level/name order,
without duplicates. EXP, level, HP, bag debit, knowledge and pending choices
commit together. Active moves remain unchanged until a choice:

1. `+learn pending` lists earned moves and the actual four active slots.
2. `+learn pending <current token>=3` activates that move in slot3.
3. `+learn pending <current token>=store` keeps the knowledge and declines
   activation. It does not refund or repeat the paid EXP.

List again after handling a move or changing a set. Listing rotates old tokens;
a changed target, owner, placement, set or PP state invalidates an old reply.
Filling a hole or replacing one slot preserves every other slot's current PP
and capacity. A busy menu or disconnect keeps the durable choices; resume with
`+learn pending` after returning. Boxed targets must be withdrawn first.

The current owned party/Fusion and field reservation checks still apply. Eggs,
foreign or ambiguous targets, inactive Fusion reservations and battles reject.
Native combined Necrozma hosts earn only base Necrozma knowledge. Their active
choices stay deferred until separation, with bound/displaced slots and both
sources' PP preserved; the combined companion stays frozen.

`world/exp_candy_counter.json` is an optional finite buy-only recipe. An operator
must explicitly install it at a selected hub with `ItemCounter`; importing code
does not create stock. It offers `expcandy`/`back`, no refill and no resale.
Prices are selected PF2 policy. Disposable SQL/captured-command qualification,
permanent stock and deliberately released socket acceptance are distinct.
The source/released acceptance follow-up is #896.
