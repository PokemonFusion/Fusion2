# Alcremie evolution with the existing Sweets (#756)

## PF2 action and selection contract

The action and form-selection rules in this section were recorded before
implementation. PF2 uses an explicit
`+evolve` request as the non-plot equivalent of spinning; it does not require
cartridge rotation timing, a story unlock, a builder room flag or an arbitrary
completion flag. Only an owned, unreserved, non-egg Milcery holding one of the
seven existing Sweets is eligible. The evolution command is unavailable in battle.

1. Inspect `+party <party-slot>` and copy its full `ID`.
2. Equip the actual item with `+hold <party-slot>=<complete Sweet name>`.
3. Use `+evolve <pokemon-id>` for Vanilla Cream, or
   `+evolve <pokemon-id>=<complete cosmetic target>` for a listed cream.
4. Inspect `+party <party-slot>` to see the saved cream and Sweet decoration.

Allowed Sweets: **Berry Sweet, Clover Sweet, Flower Sweet, Love Sweet, Ribbon
Sweet, Star Sweet and Strawberry Sweet**. The held Sweet determines the decoration
and is consumed once on successful evolution. An extra bag copy is not consumed.
Supplying a Sweet as the command's inventory item is rejected: equip it first.

The cream choice is independent of the Sweet. The only supported targets are
the base form and the eight cosmetic names already listed in Alcremie's PF2 dex:

| Command target | Cream |
| --- | --- |
| `Alcremie` (or no target) | Vanilla Cream |
| `Alcremie-Ruby-Cream` | Ruby Cream |
| `Alcremie-Matcha-Cream` | Matcha Cream |
| `Alcremie-Mint-Cream` | Mint Cream |
| `Alcremie-Lemon-Cream` | Lemon Cream |
| `Alcremie-Salted-Cream` | Salted Cream |
| `Alcremie-Ruby-Swirl` | Ruby Swirl |
| `Alcremie-Caramel-Swirl` | Caramel Swirl |
| `Alcremie-Rainbow-Swirl` | Rainbow Swirl |

Names follow the existing complete-name normalization. Unknown targets and Gmax
are rejected. There are 63 supported Sweet/cream combinations; this adds no new
dex definitions and no Mega/Gmax functionality.

## Persistence and failure contract

Battle species remains canonical `Alcremie`. The selected exact cosmetic target
and consumed Sweet display name are saved as two bounded result-metadata tags
in the owned Pokemon's existing `flags` array: `alcremie:form:<exact target>` and
`alcremie:sweet:<Sweet name>`. Other tags are preserved. Owned Pokemon have no
JSON metadata field; this route requires no schema change. These result tags
never grant evolution eligibility and are not player-supplied completion flags.
They are decorations, not a retained held item or new battle form.
The ordinary detailed party sheet displays them after a database reload.

The existing evolution service performs the transition and receipt under its
storage/trainer/Pokemon transaction and reservation checks. UUID, trainer,
placement, nickname, corresponding ability slot, HP, major status, EXP, EVs,
moves and PP remain preserved. Failed validation or save restores the held item,
appearance and cached model state. A repeated request cannot consume a second
Sweet or change the completed appearance.

Wrong species/items, missing held items, bag-only requests, unknown targets,
eggs, battle context, reservations, stale model references, save failure and
replays must have production-model regression coverage. Existing stone and
level-held evolution/equip routes remain covered separately.

Local automated command/model proof, live ordinary-player acceptance, staging
publication and deployment are recorded separately in the closeout report.
