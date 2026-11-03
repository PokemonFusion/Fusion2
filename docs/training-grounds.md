# Training Grounds

The Training Grounds provide free focused EV practice and free confirmed
retraining. Existing battle EV and EXP awards continue normally. Vitamins,
feathers and EV berries remain useful shortcuts. Nothing installs these locations
automatically; an operator must select an actual hub for the explicit authoring
recipes in `pokemon/services/item_activity_routes.py`.

At the Grounds, use `+train 3=Attack` (party slot, full ID or `fusion`) to preview
up to 64 EVs in HP, Attack, Defense, SpA, SpD or Speed. Confirm within five minutes
with `+train confirm`. Then complete three exercises using
`+train continue technique`, `+train continue pace` or `+train continue recovery`.
The first opens after 30 seconds, and each later input must be at least 30 seconds
after the previous completed step. Every choice has the same numerical effect.
Time alone gives nothing. `+train` shows persistent progress after reconnect;
`+train cancel` is free and works anywhere. Only one activity can be active.

Training clips at 252 EVs per stat and 510 total, grants no EXP or PP, and does
not change genetic IVs or nature. Maximum-HP changes preserve the existing HP
deficit. Exercise requires a living owned non-egg party member or current Fusion,
outside battle and other reservations. Custody, level, placement and EV changes
invalidate an old selection. Training does not lock a Pokemon out of normal play.

For free retraining, preview `+train reset 3=Attack/32`, `+train reset 3=Attack`
or `+train reset 3=all`, then `+train confirm` within five minutes. The preview
shows EVs, calculated stats and HP before and after. Partial resets require an
exact amount available in that stat. Reset grants no rewards, levels or healing;
a fainted target stays fainted. Cancel an active exercise before resetting.

Each sixth useful completed session earns one Rare Candy, each twelfth also earns
one Bottle Cap, and session 60 also earns one Gold Bottle Cap once per character.
Clipped but useful sessions count; cancelled and no-effect activities do not.
The EV change, counter and bag rewards commit together. Existing item eligibility,
including level 50 for Hyper Training, applies when using earned items.

For a Hardy level-50 Mew with zero genetic IVs and zero EVs, actual stats are
160 HP and 105 in each other stat. Four sessions raise one stat's EVs to 252.
Attack and Speed then calculate to 136 each: eight sessions, requiring at least
12 minutes of active spaced inputs. A ninth HP session uses the remaining six
EVs; a free two-point HP reset produces the usual 252/252/4 allocation. This is
an initial measured tuning contract, not a promise that every build should use it.

## Optional Training Trail

The explicitly authored Trail enables `+hunt` with no wild or NPC battles.
Each search has a 5% chance of one training item and the existing three-second
character cooldown. Conditional on success, each of six feathers has weight 8,
each of six EV berries has weight 6, Rare Candy 12, Bottle Cap 3 and Gold Bottle
Cap 1, totalling 100. The exact profile is `training-v1`, with rate 5 and no
`itemfinder_item`. Unknown or mixed configuration grants nothing. The original
named Potion source keeps its existing behavior and random draw count.

Finder supplies are optional. Focused practice and free resets provide the
baseline route; useful-session milestones provide an earned route to Candy and
Caps. There is no new currency, automatic shop refill or blanket catalog drop.
World placement and existing-character acquisition remain separate acceptance
work until an actual installation is reviewed and authorized.
