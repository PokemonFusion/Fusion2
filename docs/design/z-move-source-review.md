# Reviewed sources for the bounded Z rollout

This is the pre-implementation mapping for #797–#808. It enables no runtime
route, public stock or native form. The existing [contract](z-moves.md) and
[crystal gates](z-crystals.md) remain authoritative. Each row requires actual
command, PP, battle-effect, checkpoint and cleanup acceptance before release.

The checked-in MOVEDEX, ITEMDEX and LEARNSETS are the PF2 content authority.
The primary simulator's [power constructor](https://github.com/smogon/pokemon-showdown/blob/1636bf6d0848fb3c9330576963a647d4e179d278/sim/dex-moves.ts)
and [Z bonus dispatcher](https://github.com/smogon/pokemon-showdown/blob/1636bf6d0848fb3c9330576963a647d4e179d278/sim/battle-actions.ts)
were reviewed at `1636bf6d0848fb3c9330576963a647d4e179d278`. Its selected
ordinary powers below produce 100 for base power below 60, and 120 for these
60-power sources. These values are frozen explicitly; generic Z definitions'
sentinel power 1 never supplies damage. No blanket source-power inference is
part of the proposed runtime allowlist.

## Generic damage list

Every row has priority 0, one opposing active target, no ordinary source contact,
secondary effect, recoil, charge or recharge. Category and crystal type are
explicit. Holders are checked-in learnset examples; generic eligibility is not
species-exclusive. The owned holder must actually know the selected active move.
All other ordinary source moves remain deferred.

| Crystal | Native example | Actual source | Type / category | Z power | Gate |
| --- | --- | --- | --- | ---: | --- |
| Normalium Z | Eevee | Tackle | Normal / Physical | 100 | #797–#799 |
| Buginium Z | Caterpie | Bug Bite | Bug / Physical | 120 | #800 |
| Darkinium Z | Eevee | Bite | Dark / Physical | 120 | #800 |
| Dragonium Z | Altaria | Dragon Breath | Dragon / Special | 120 | #800 |
| Electrium Z | Pikachu | Thunder Shock | Electric / Special | 100 | #800 |
| Fairium Z | Sylveon | Fairy Wind | Fairy / Special | 100 | #800 |
| Fightinium Z | Machop | Karate Chop | Fighting / Physical | 100 | #800 |
| Firium Z | Charmander | Ember | Fire / Special | 100 | #801 |
| Flyinium Z | Pidgeotto | Wing Attack | Flying / Physical | 120 | #801 |
| Ghostium Z | Gastly | Lick | Ghost / Physical | 100 | #801 |
| Grassium Z | Bulbasaur | Vine Whip | Grass / Physical | 100 | #801 |
| Groundium Z | Diglett | Mud-Slap | Ground / Special | 100 | #801 |
| Icium Z | Swinub | Powder Snow | Ice / Special | 100 | #801 |
| Poisonium Z | Ekans | Poison Sting | Poison / Physical | 100 | #802 |
| Psychium Z | Kadabra | Confusion | Psychic / Special | 100 | #802 |
| Rockium Z | Geodude | Rock Throw | Rock / Physical | 100 | #802 |
| Steelium Z | Aron | Metal Claw | Steel / Physical | 100 | #802 |
| Waterium Z | Squirtle | Water Gun | Water / Special | 100 | #802 |

Each example has a direct or inherited checked-in learnset entry. Historical
sources remain PF2 content; this does not assert a complete single-generation
learnset system. Existing move teaching/ownership remains authoritative.

## Four simple status sources (#803)

Apply the Z bonus after ordinary prevention passes and the source PP/use is
paid, before the ordinary source effect. A blocked or ineffective base effect
does not undo a started bonus. Caps and ordinary HP calculation still apply.

| Crystal | Source / native example | Z bonus | Ordinary base effect |
| --- | --- | --- | --- |
| Normalium Z | Splash / Magikarp | Attack +3 | Normal Splash no-effect result |
| Normalium Z | Growl / Eevee | Defense +1 | Normal opposing Attack reduction |
| Normalium Z | Swords Dance / Scyther | Clear only the user's negative stages | Normal Attack +2 afterward |
| Icium Z | Haze / Koffing | Heal user to calculated maximum HP | Normal field boost clearing afterward |

## Four special status sources (#804)

| Crystal | Source / native example | Exact selected Z bonus |
| --- | --- | --- |
| Darkinium Z | Memento / Koffing | One full-HP replacement heal bound to this side/active slot, retained across rebuild until its incoming holder consumes it; ordinary Memento follows |
| Ghostium Z | Destiny Bond / Gastly | Existing one-turn Follow Me redirection on the user; normal Destiny Bond follows |
| Flyinium Z | Tailwind / Pidgeot | Existing Focus Energy +2 critical stage until switching; normal Tailwind follows |
| Ghostium Z | Curse / Gastly or Onix | Current Ghost type: full user heal before ordinary Ghost Curse HP cost; otherwise Attack +1 before ordinary non-Ghost Curse changes |

The selected PF2 restriction policy is conservative: the source must be an
otherwise legal active move. No Z bypass for Encore, Disable, Taunt, choice,
Assault Vest or Imprison restrictions. Called, locked charging/recharge, variable,
fixed, multi-hit and spread sources remain deferred unless a named status or
signature mapping explicitly accepts its own behavior. Invalid combinations fail before queuing.
This is a bounded PF2 policy, not a claim to implement every cartridge exception.

## Signature and release gates

#805–#808 retain their exact item/native/source lists. Their existing intrinsic
signature power, type, category, target and special effects require separate
per-signature review and actual effects. No `itemUser` metadata row alone grants
access to a native/fused/cap form. Existing native acquisition and battle-form
lifecycles must be verified, or a named prerequisite keeps that subset deferred.
Ultranecrozium Z remains outside these batches pending separate Ultra/native
lifecycle work. No new species fusion, plot form, Ring, key or quest is introduced.

The first optional Counter offer is Normalium Z at 10,000 and finite stock one.
Only accepted crystal batches may add their named offers with that same policy.
Recipes do not install sources, refill stock or establish deployed availability.
Source/player setup, local automated proof, live acceptance and deployment stay
separate. The reviewed public source files were cached as text only; their SHA256
identities are `5c15a78ff4a491c1eecbda909c63535924589aba7e15b73a895d41e6b504f02f`
(power constructor) and `9d477a6296f8916cbbbfc36ae18bb0729dfda0646e4ee1c00ccb4199661c56d4`
(dispatcher).
