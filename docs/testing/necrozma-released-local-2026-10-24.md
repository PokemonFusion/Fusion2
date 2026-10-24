# Native Necrozma released local walkthrough — October 24, 2026

**Candidate `02c81c0d62364d48d3cdae6d8b57023d8ed99249` failed acceptance.**
The separately approved local instance ran real ordinary-player socket flows,
but an additional ordinary zero-PP attack check exposed a move-legality defect.
#831 remains open. This receipt is not shared-server deployment or acceptance
of a replacement build. The [lossless JSON](necrozma-released-local-2026-10-24.json)
retains all 203 socket observations, 15 independent SQL snapshots, exact staff
setup/state prerequisites, source identities and teardown evidence.

## Released environment and authorization

The user explicitly replied **“Approve local release + QA”** to the
[published exact plan](necrozma-release-plan-2026-10-24.md). The environment was
`necrozma-release-777571d2a1114aac812d180fff18a87f`, using the archived candidate's
1,116 verified Python files, a new disposable PostgreSQL schema and new loopback
ports 53231–53235. Its source remained unchanged throughout the walkthrough.
No PF2-Dev source, game database, existing service, human character, permanent
source or unrelated battle UI work was changed.

Input was automated over two independent ordinary telnet sockets. The players
created accounts, logged in, selected `goic 1` and completed human Squirtle
onboarding through `chargen`. SQL confirms both account and character permissions
remained Player, with neither account a superuser. Staff commands used a separate
operator connection. Authentication inputs and generated credentials are redacted.

The approved staff setup authored tagged Center/arena/exits, four base hunt
charts, finite stock and labelled wallets. **No source Pokémon, fused row or bag
item was granted.** Subsequent labelled PP0/HP0 prerequisites are separately
recorded and are not represented as ordinarily earned damage or PP spending.

## Ordinary player outcomes

| Flow | Exact route and observed result |
| --- | --- |
| Acquisition | `qa route`, `+store` → Buy, finite Master Ball/crystal/recovery/PP purchases; walk source trails, `+hunt`, `+item Master Ball`, reply `no` to nickname. Both base Necrozma plus native Solgaleo/Lunala were genuinely captured. |
| Center/review | Outside-Center combine refused. At Center, `+necrozma combine 2=3/1` reviewed UUIDs, displaced move, source PP, reservation and return rules. `no` cancelled unchanged; `yes` produced the correct form. A Dawn review opened before `+hold 2=Lunalium Z` was rejected as stale on confirmation. |
| Placement/inspection | `+party` preserved host slot 2, excluded the reserved companion and reported total ownership separately. `+necrozma inspect <companion UUID>` displayed the same owned source in `combined`. Ordinary storage deposit could not move it. |
| Battle | Both walked `east`; `+pvp/create single`, `+pvp/join NativeDusk18a87f`, `+pvp/start` gave consenting PvP. Both used `+switch 2`, ordinary Sunsteel Strike/Moongeist Beam, then their existing signature through `+zmove 1=<target>`. Actual attacks caused damage/KOs. |
| PP/Z budget | First battle SQL source PP changed Dusk 5→2 after two ordinary attacks plus one Z; Dawn 5→3 after one ordinary attack plus one Z. HUD showed each side's use spent; repeat Z input was rejected. Crystals remained held. |
| Reconnect/end | Dusk closed its socket, reconnected, logged in and used `goic 1`/`+showbattle`; the same battle and both spent budgets returned. Dawn's `+concede yes` ended it and SQL confirmed cleared battle locks. |
| Field items | `+use Revive=2` revived the truly battle-fainted Dusk host. `+use Ether=2` restored its source; purchased PP Up/PP Max used the displayed `+use 1` selection and produced 6/6 and 6/8 displays. Separate labelled PP0 sources were restored by ordinary Ether to 6 and 8. Dawn's separately labelled HP0 host was revived normally. |
| Full party | Further ordinary Eevee captures filled all six Dusk party slots. `+necrozma separate 2` → `yes` restored base Necrozma and returned Solgaleo to Box 1 without evicting an occupant. |
| Box/fainted return | Dawn deposited Lunala into Box 2 before combination and selected its full UUID. Separation while the labelled host was fainted succeeded, kept HP0 and returned Lunala to Box 2 position 1. A later combine correctly refused that fainted source until another purchased Revive was used. |
| Zero/boost cycle | After labelled PP0 and separation, recombination reviews and confirmations both retained source 0. `+party/moves 2` showed Sunsteel 0/6 and Moongeist 0/8, with boosted capacities preserved. |

## Failed check and bounded repair

In a second real PvP battle, the expected zero-PP ordinary attack rejection
failed. Both `+attack Sunsteel Strike` and `+attack Moongeist Beam` queued;
Sunsteel Strike actually damaged/fainted the opposing host. Its active slot and
resource bank remained **0** before and after. The opposing saved action became
illegal after that host fainted. Later Z inputs occurred after this battle had
ended, so they provide no zero-PP Z acceptance evidence.

`LegalActions._move` constructed a move from a name-only runtime object and used
the dex's capacity as remaining PP, ignoring the attached owned active slot.
The repair reads the matching owned slot's remaining PP, including explicit
zero. Temporary Mimic/Transform slots retain their independent runtime PP.
Regression checks exercise ordinary command rejection without a declaration or
state change for both genuinely acquired native forms, positive owned PP,
Struggle fallback and independent copied PP. No migration or frozen-instance
source edit is part of the repair.

The repair passed **181 focused checks**, **182 production-model PostgreSQL
cases across nine suites** (including 15 native player-flow cases), and three
fresh full orders of **4,933 passed / 4,014 skipped each**. All 1,116 tested
Python identities match commit `e3557aadced7fc5897b7024d1377047117735a64`.
The [repair receipt](necrozma-pp-repair-2026-10-24.json) retains the complete
new two-form ordinary-command/SQL regression observations, exact commands,
log hashes and committed source identities.
Replacement released acceptance still requires an exact published candidate,
separate operator authorization and a successful rerun.

## Protected data, diagnostics and cleanup

All 15 SQL snapshots matched both companions' entire owned rows, active/saved
moves, learned moves and PP boosts to their capture baselines. The protected
sentinel was unchanged. Final state had 11 legitimately owned Pokémon, zero
active pairs, reserved placements, battle locks or orphan resources. Two zero-PP
dormant banks were legitimate owned history until the disposable schema's removal.

Capture nickname menus and the ordinary hunt cooldown rejected premature inputs;
the driver retried through their displayed routes without bypassing either.
Bare `1` was rejected by the command parser; the documented `+use 1` completed
the pending PP choices. Buy entry displayed a redundant Usage line before stock;
finite purchases still succeeded. Failed read-only observer attempts referenced
unavailable manager/Move attributes, changed no game state and are excluded from
accepted runtime-budget proof. These diagnostics remain in the lossless receipt.

Both players separated their sources and quit. The supervisor stopped only the
new archived instance through its own AMP port, verified all five listeners
closed and dropped only its generated schema. The task PostgreSQL fixture
remained available for the repair's disposable automated checks, including
the full gate's SQL wrappers. After all checks ended, it was verified clean
(no disposable schemas or public tables) and stopped. Existing game services
and databases stayed untouched.
