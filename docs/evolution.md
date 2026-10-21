# Evolution and held items (#714)

## Player commands

- `+evolve <pokemon-id> [complete item name] [=<exact target>]`
- `+hold <party-slot>=<complete item name>` equips or replaces an item.
- `+hold <party-slot>=` removes it and returns it to trainer inventory.

Names use the shared case, punctuation, accent and gender-symbol normalization,
but must match a full dex key or display name. Synthesized evolution requirements
such as Black Augurite are also recognized. Prefixes and ambiguous dex names
are rejected. Historical inventory aliases are counted and debited together,
using the same atomic trainer operations as battle items. Item evolution uses
trainer inventory. Held items use trainer
inventory first, then one exact carried object for compatibility. Removal and
replacement return the old item to the same owner's trainer inventory, including
items originally equipped from carried objects. Unknown legacy held items are
returned using the trainer's existing inventory normalization instead of being
discarded.

`pokemon/items.py` supplies shared metadata for supported noncompetitive items
omitted from ITEMDEX. Everstone can be equipped by `+hold`; Black Augurite keeps
its full display name in inventory and the same identity in evolution commands.

A supplied evolution item must be the required item for the selected transition;
it cannot be consumed for a level evolution. Held evolution items are consumed
from the Pokemon, not a second copy from the bag. Nicknames are preserved and
abilities follow the corresponding target ability slot (falling back to slot 0).

## Supported data and PF2 rules

The authoritative allowlists and condition evaluator are in
`pokemon/data/evolution.py`. Tests resolve every positive-dex evolution link,
including the 52 display-name/generated-key lookup misses in the June audit.
Both the source's `evos` and the target's `prevo` must agree on the exact form.

| Dex rule | Required evidence |
| --- | --- |
| Default/level | Stored level at least `evoLevel`; all extra conditions also apply |
| `useItem` | Exactly the required item, with gender/region restrictions |
| `levelFriendship` | Friendship at least 160 (Gen 9), plus time where required |
| `levelMove` | Required move in the current active move slots, not just the learned archive |
| `levelHold` | Required held item and time; successful evolution consumes the held item |
| `levelExtra`: Remoraid | Remoraid in the canonical active party |
| `levelExtra`: magnetic field | Current room has `db.magnetic_field = True` |
| `levelExtra`: Sylveon | Friendship at least 160 and an active Fairy move; takes precedence over Espeon/Umbreon |
| Day/night/rain | Room `db.time_of_day` (`day`, `night`, `dusk`) and `db.weather` (`rain`/`raindance`) |
| Regional evolutions | Room `db.region` matches `evoRegion`; matching regional branch blocks the base branch even if another condition fails |
| Hisuian evolutions of base forms | Require region `Hisui` where older dex rows omit `evoRegion` |
| Gender | Target's M/F requirement must match the Pokemon |
| Tyrogue | Calculated Attack vs Defense, using actual level, IVs, EVs and nature |
| Pangoro | A Dark type in the canonical active party |
| Lycanroc-Dusk | Own Tempo and dusk; Own Tempo cannot select the normal branches |
| Toxtricity | Amped/Low-Key branch follows the stored nature |
| Kleavor | `Black Augurite`, preserving the checked-in data's spelling and handling its misplaced item field |
| Alcremie | Milcery holds one of the seven Sweets; explicit `+evolve` replaces spinning, with an optional allowed cream target |

Everstone blocks evolution. Eggs and fusion-reserved Pokemon cannot evolve or
hold items. Room attributes are server-managed context, not player-supplied
assertions. Missing context fails validation. PF2 currently has no authoritative
day/night clock: builders must set `time_of_day`, `region`, and `magnetic_field`
where those evolutions should be available. Weather uses the existing room field.

Evolution remains an explicit player action at an eligible stored level; this
slice does not add an automatic level-up hook. When multiple eligible branches
remain, the player must use `=<target>`. This is PF2's explicit selection policy
for data branches (including cosmetic/rare variants); it does not simulate
cartridge random personality rolls or version exclusivity.

For Milcery, equip Berry, Clover, Flower, Love, Ribbon, Star or Strawberry Sweet
with `+hold <slot>=<complete Sweet name>`. Find the full ID on `+party <slot>`,
then use `+evolve <pokemon-id>` for
Vanilla Cream or `+evolve <pokemon-id>=Alcremie-Ruby-Cream` (or another listed
cream). The held Sweet is consumed once; bag copies remain untouched. The cream
and Sweet decoration persist and appear on `+party <slot>`. All nine creams and
the non-plot action/persistence rules are listed in
[Alcremie evolution](alcremie-evolution.md). No Gmax target is available here.

## Explicitly unsupported

These fail closed, even at level 100 or with a supplied item. Unknown future
`evoType` or `evoCondition` values also fail closed.

| Condition | Reason |
| --- | --- |
| All `trade`, including held-item and partner-species trade | Trading and trade-equivalent substitutes are outside this slice |
| Malamar: console upside-down | No PF2 equivalent is defined |
| Sirfetch'd: 3 critical hits in a battle | No persisted evolution counter |
| Runerigus: 49 HP lost and Dusty Bowl sculpture | No persisted journey/damage evidence |
| Urshifu: either tower | No tower completion evidence |
| Wyrdeer/Overqwil: Agile/Strong move uses | No style-use history |
| Ursaluna: Peat Block and full moon | No authoritative lunar state |
| Basculegion: 294 recoil without fainting | No persisted recoil streak |
| Pawmot/Rabsca/Brambleghast: Let's Go steps | No persisted Let's Go activity |
| Annihilape: Rage Fist uses | No persisted move-use count |
| Kingambit: defeat leading Bisharp | No persisted qualifying battle history |
| Gholdengo: 999 Coins | No supported coin inventory/counter |
| Shedinja (dex only records a level) | Requires an additional Pokemon, spare party slot, and Poké Ball transaction |
| Palafin (dex only records a level) | No Union Circle equivalent |

All current `other` rules are deliberately unsupported for these reasons. This
slice does not fabricate completion flags or expose command overrides for them.

## Integrity and retries

The service locks storage, trainer, then Pokemon, using the placement service's
ownership and reservation checks. All trainer add/remove writers now share the
trainer row lock, preventing lost quantity updates. Inventory mutation and the
Pokemon save occur in one transaction. Character inventory caches update only
after commit. Fresh `values()` reads bypass Evennia's identity map, and rollback
restores cached model fields without a second save.

One compact `evo:` receipt uses the existing Pokemon `flags` field. A repeated
request with the same item/target at the same level is a no-op, including an
implicit high-level request that could otherwise advance two stages. To evolve
the next stage at that level, explicitly name its target. The receipt is replaced
on the next successful evolution. Failed attempts do not write a receipt.
Held operations set desired state: re-equipping the same item or removing an
already empty slot is a no-op. No schema migration is needed.

## Validation

- `pytest -q` for the repository suite.
- `python tests/integration/evolution_cases.py` for real ORM success, rollback,
  invalid conditions, carried-object compatibility, replacement, removal, retries,
  inventory aliases, synthesized item requirements, and cache behavior.
- `python tests/integration/alcremie_cases.py`, with `PF2_TEST_POSTGRES_DSN` set,
  for all 63 Sweet/cream combinations, actual ID discovery/commands, SQL reloads,
  held-item consumption, cosmetic persistence, failure controls and concurrent retries.
- Set `PF2_TEST_POSTGRES_DSN` to an expendable test database to also run competing
  evolution/equip/remove requests across independent connections. The harness
  creates and drops only a random test schema and does not run migrations.
- The existing PostgreSQL lifecycle CI runs both integration scripts plus the
  focused evolution/command tests.

The merged workflow retains the battle progression, status, capture, medicine,
nickname/Fusion display and Adventure/gym recovery checks introduced in #721.
Evolution adds 27 real-model PostgreSQL cases, including Black Augurite through
the real command, retries, accented/gender-symbol source names, legacy inventory
aliases and preservation of saved HP, PP, EXP, EVs and major status. Together
the ten production-model PostgreSQL suites exercise 144 cases. Disposable-schema
tests do not validate a running game or replace live gameplay acceptance.
