# Battle presentation

The default `compact` style uses colored combatant cards, ten-cell HP bars,
full status names, stable A1/A2/B1/B2 field positions, a short move list and
grouped messages from the previous committed turn. It supports singles,
doubles and four-controller Multi Battles. Each trainer sees exact HP only
for their own battlers; allies, opponents and observers see percentages.

Use `+battleui` to redraw the current field. Choose a different presentation
with `+battleui/style compact`, `legacy`, `classic_modern` or `pf1`.
`+battleui/style default` returns to the new default. Saved explicit choices
remain effective.

The displayed move letters are choices for `+attack`, not global commands:
`+attack A B1` selects move A and target B1. `+attack` opens the interactive
selector. In doubles, select the acting cell first, for example
`+attack A2 A B1`. Within the selector, `? A` shows power, accuracy and the
move description without submitting an action; `cancel` leaves the selector.
Outside that selector, `+movedex Thunderbolt` shows the full dex entry.

Move lists show remaining PP. A maximum is shown only when supplied by the
move's data; runtime snapshots that contain remaining PP alone do not imply
a maximum. `NO PP` and `UNAVAILABLE` are distinct. Normal battle validation
still decides legal actions, targets, items and switches.

`+uimode ascii` uses ASCII HP artwork. `+uimode screenreader` removes color,
rules and HP artwork while retaining identity, conditions, HP and commands.
Compact output wraps to the viewer's configured or negotiated terminal width.
Weather, terrain and Trick Room come from the current battle field. Fainted
controllers receive replacement guidance, failed saves point to `+battle/retry`,
and a completed battle no longer offers another attack. Empty move slots retain
their letters without becoming selectable moves.

Previous-turn messages are presentation state for the current session, not
new game records. They are collected only when the normal message buffer
publishes committed results. Classic viewers retain their existing event
stream. The final turn's compact results are delivered before battle cleanup.

## Verification

`tests/battle/test_compact_battle_ui.py` covers presentation, ownership, PP, physical
slots, stale selectors and committed-turn delivery. The standalone helpers
`tests/helpers/compact_battle_render.py` and
`tests/helpers/compact_battle_player_flow.py` exercise real ANSI/HTML parsing
and command/engine routes with database connections refused. The command helper
uses synthetic controllers, captured interactive transport and a supplied
session registry; it does not certify socket login, owned SQL persistence or
deployment. The mandatory gate also retains the existing battle and recovery
regressions. See the [dated verification report](testing/compact-battle-ui-2026-10-27.md).
