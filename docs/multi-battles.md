# Four-trainer Multi Battles

Multi is four players in two teams, A1/A2 versus B1/B2. Each trainer controls
one active Pokémon and only their own party, current participating Fusion and
inventory. Four distinct player accounts are required. This differs from
ordinary doubles, where two trainers each control two active Pokémon.

## Meet, choose teams and consent

1. Meet in one room. The host types `+pvp/multi create` and takes A1.
2. Three other players type `+pvp/multi join A2`, `+pvp/multi join B1` and
   `+pvp/multi join B2`, choosing their own teams.
3. Read `+pvp/multi status`. All four independently type `+pvp/multi ready`.
4. The host types `+pvp/multi start`.

`unready` revokes your consent. `join <free slot>` changes your own team slot;
the host keeps A1. Joining/changing/leaving clears remaining readiness. `leave`
leaves the lobby; when the host leaves, it cancels. Lobbies expire in ten minutes
and hold no movement or asset locks. The room timer removes absent members and
cancels an absent host's request, so returning requires fresh consent.

At launch all four must still be present and connected, with eligible current
parties/Fusion and at least one conscious battler each, and no conflicting
battle or Pokémon reservation. An unready or unavailable player prevents launch.
A failed launch retains the lobby and rolls back partial battle locks. A stale
or duplicate start cannot create another match.

## Independent actions and shared team effects

The field shows four stable physical labels, controller names, Pokémon,
public HP/status and missing choices. For the trainer currently in A2:

```text
+attack A2 Water Gun B1
+attack A2 Helping Hand A1
+attack A2 Surf
+switch A2 6
+switch A2 fusion
+item A2 Potion=3
```

Use your actual learned moves and saved party numbers. Party gaps remain; a
full party can also have the supported `fusion` reserve. You cannot choose a
teammate's action, use their items or borrow their reserves. Your item targets
also belong to you. A valid queued choice cannot be overwritten by another
input. All living controllers must choose before one turn resolves.

Ally support, screens, side guards and hazards use the whole team. Spread moves
use their real recipients: Surf can hurt your teammate. Follow Me draws eligible
opposing attacks to its user for that turn; it does not redirect a teammate's
attack or collapse a spread move. Ally Switch exchanges physical cells;
control follows each trainer's own Pokémon. Check `+status` before the next
input. Normal and forced switches retain the acting trainer's current cell.

The existing allowance is **one Tera, one Mega and one Z use per team**; these
budgets are separate, with the existing incompatibility rules for one actor.

- `+tera A2` reserves an eligible active actor. `+tera A2 cancel` cancels that
  actor's pending Tera; a partner cannot cancel it.
- `+mega A2` reserves an eligible native held-stone form under the existing
  species/ability/current-owner rules.
- `+zmove A2 Tackle=B1` queues an explicitly supported source with its reusable
  held crystal. It is one move action; no second `+attack` is needed.

A pending team reservation blocks a competing one. A switch cancels only that
actor's uncommitted mechanic. Consumed uses survive switches and reconnect.
No new plot gate or mechanic catalogue is introduced by Multi.

## Exhaustion, reconnect and results

When one trainer exhausts their own roster, their cell stays empty while the
partner continues. It owes no action. There is no borrowing or partner takeover.
A team loses after both rosters are exhausted; simultaneous exhaustion draws.
The existing PvP policy gives no EXP, trainer XP or prize money. Each of the four
trainers receives one durable outcome; replay cannot create extra rewards.

Every turn has a five-minute action deadline. Reconnect restores your exact
controller, roster, legal queued choices and shared effects without resetting
that clock. The room timer checks at most thirty seconds later. A team missing
an overdue living controller's input forfeits; if both teams owe choices, it is
a draw. An eliminated controller cannot forfeit for a living partner.

`+concede yes` confirms a forfeiture for your **whole team**. A bare `+concede`
asks for confirmation. A disconnect never transfers your control to a partner.

If a turn or result cannot save, use `+battle/retry`. Valid teammate inputs are
retained; pending delivery/cleanup holds the session until it can save. The room
timer also retries terminal cleanup. A completed/aborted match clears all four
controllers' battle locks while retaining their outcome receipts. Unused room
timers remove themselves after their lobby and matches are gone.

Implementation tests, a live four-account walkthrough and deployment are
separate records. Adding code or passing captured commands does not show that a
shared server has been updated. Existing singles, ordinary doubles and NPC
formats remain available through their existing routes.
