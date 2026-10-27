# Manual battle boosters

Use `+item A1 X Attack=1`, substituting the exact item and the acting Pokémon's
own current party slot. Omit `A1` only when one actor can act. In doubles,
select `A1` or `A2` explicitly; the target is still that actor's own party slot.
These eight items work in two-participant wild/trainer/PvP singles and doubles.

| Item | Effect |
| --- | --- |
| X Attack | Attack +2 stages |
| X Defense | Defense +2 stages |
| X Sp. Atk | Special Attack +2 stages |
| X Sp. Def | Special Defense +2 stages |
| X Speed | Speed +2 stages |
| X Accuracy | Accuracy +2 stages |
| Dire Hit | Focus Energy, +2 critical-hit stages |
| Guard Spec. | Side Mist for five turns, including activation |

X items use ordinary boost events. Simple doubles the increase, Contrary
reverses it, and stages stop at ±6. The result message shows the actual stage.
Temporary stages affect ordinary damage, defense, speed order and accuracy;
they do not change owned base stats, EVs, IVs or Nature.

An already capped stage or active Focus Energy/Mist rejects before an action
is declared. Wrong actors/targets, reserves, fainted actors, missing copies,
move selectors, unreviewed formats and Embargo also reject. Magic Room, Klutz
and Heal Block do not suppress these bag effects. Field/held routes are absent.
Normal medicine and capture retain their existing policies.

A useful resolution spends the actor's action and one copy together. An earlier
normal action can make a queued boost redundant: that turn proceeds with no
copy spent. A stale owner, copy or checkpoint aborts the complete turn, restoring
retryable input and resources. Sibling declarations remain intact. A last copy
can fund only one reserved actor. Submit declarations and affected turns as
fresh battle input; a containing transaction is refused before mutation.

Dire Hit uses the real Focus Energy condition. Its +2 critical stages combine
with other bonuses once, with ordinary critical prevention. Switching/fainting
clears it. The supported normal Baton Pass path transfers it to the incoming
recipient; it cannot remain active on the outgoing bench Pokémon. Reconnect
retains the same condition/source without a second item debit.

Mist belongs to the side and retains its remaining duration when its user
switches or faints. It blocks opposing negative stage changes with source/effect
context, while allowing positive changes, self-debuffs, Haze/Clear Smog resets
and the reviewed Infiltrator move path. Ability changes apply before this
filter, so Contrary can turn an opposing drop into a permitted benefit. An
active copy cannot refresh the timer. Reconnect preserves the exact side,
source and remaining duration without replaying activation. A legacy boolean
screen alone cannot grant indefinite protection. Battle end clears these
temporary effects before owned-state synchronization.

The optional `world/battle_booster_counter.json` offers all eight items with
`boosters`/`back`: X items and Dire Hit cost 1,000 each; Guard Spec. costs 1,500;
each starts with five finite copies. These are selected PF2 prices. Explicit
operator installation is required; importing code installs no stock. There is
no automatic refill or resale. Source publication, disposable command/SQL
qualification and deliberately released socket acceptance remain distinct.
