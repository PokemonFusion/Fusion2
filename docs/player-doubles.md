# Player doubles

September #708 adds normal-player 2v2 battles using the shared legal-action
foundation from #710. Singles retains its existing command syntax.

## Launching a battle

Create a room-local request with `+pvp/create double [password]`. The opponent
uses `+pvp/join <host> [password]`, then the host uses `+pvp/start`.
`+pvp/create`, the old password-only syntax, and `+pvp/create single` launch
singles. Requests list their format. Both players need two conscious party
members for doubles; this is checked when creating, joining and starting.
Failed readiness checks preserve the request instead of consuming it.

An enabled placed NPC with `trainer_challenge.battle_format = "double"` can
also be challenged through `+challenge <NPC>`. Both teams need two usable
members, and the entire NPC roster remains available for replacement.

## Giving commands

The prompt labels the four field positions with names and HP percentages.
Choose one independent action for every living Pokémon you control:

```text
+attack A1 Water Gun B2
+attack A2 Tackle B1
+switch A2 3
+item A2 Potion
```

The actor prefix is required when two of your Pokémon are active. A1/A2 belong
to the host; B1/B2 belong to the opponent. The switch number is a party slot,
not a field position. A queued action cannot be overwritten by a second input,
and two actors cannot reserve the same incoming Pokémon.

`+attack A2` or `+switch A2` opens an interactive prompt for that actor. Move
letters refer to its learned move slots. The move prompt accepts a letter/name
and target, such as `A B2`. Expired turn or replaced-actor callbacks are refused.

Single-target moves require an explicit legal target when more than one is
available. Move metadata determines whether foes, allies or self are allowed.
Self and spread moves need no target token; their confirmation names the
affected positions. Surf includes the user's ally, while opposing-side spread
moves such as Growl affect both foes. Each move spends PP once.

Medicine targets the named actor; balls retain their wild-battle restriction.
Party items and run/concede rules otherwise use the existing engine behavior.

## Slots, switching and saved choices

A2 stays A2 if A1 faints. Empty positions do not block turn readiness. Existing
automatic forced replacement chooses the first legal reserve and announces
the affected field slot. Attacks target a field position through a voluntary
switch, so its incoming Pokémon receives the attack.

Checkpoints retain independent declarations and actor/target references.
Reload discards an invalid human choice individually and asks for a new one,
preserving the sibling's valid choice. Selection and execution revalidate
legality without substituting a different move for a human input.
The additive checkpoint fields require no database migration.

## Validation and staging acceptance

`tests/battle/test_player_doubles.py` covers independent declarations, ambiguity,
ally/self/spread targets, PP, exact-slot switches, reserve reservations,
stable fainted slots, stale menu views and failed-save rollback.
`tests/integration/player_doubles_cases.py` uses real production models and
normal-player command classes in disposable PostgreSQL schemas. It checks
room request persistence, independent actions/rebuilds, authoritative HP/PP,
illegal/stale targets, switched-in targets, one remaining slot, and a complete
doubles battle through terminal cleanup. The trainer-challenge integration
suite also checks an ordinary player's configured NPC doubles launch.

The [September closeout](testing/september-closeout-2026-10-23.md) records fresh
command/PostgreSQL regressions and retained October 16 ordinary-player Telnet
acceptance, including a completed doubles battle and both cleared locks. The
dated protocol evidence is local; it does not claim a new remote deployment.
For a later intentionally released build, the repeat walkthrough is:

1. With two ordinary accounts, create/join/start a doubles PvP request and
   confirm four named positions. Check an insufficient-party rejection.
2. Submit distinct commands for both actors, including an ally-only move,
   a self move, a foe target and a spread move without a target argument.
3. Try a foreign actor, unavailable target and repeated action. Confirm the
   valid sibling action remains queued. Open a move prompt, advance the turn
   elsewhere, and verify its old input is refused.
4. Switch A2, attack that position, then faint A1. Confirm replacements and
   the surviving A2 keep their labels; play through the last remaining slot.
5. Complete the battle and confirm both characters' locks clear. Repeat a
   configured NPC doubles challenge, then a singles battle with the old syntax.

Record ordinary-player results separately from any staff/admin checks. This
PR does not implement later AI strategy, prediction, new move mechanics or
formats with more than two active Pokémon per side.
