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
| Existing trade-held items | Exact allowlisted source/target/item triples; `+hold` then `+evolve` consumes the held item without transferring ownership |
| Link Cord | One bag copy through `+evolve` for 14 exact trade-only mappings; preserve Alolan form and all four Pumpkaboo sizes; Karrablast and Shelmet need no partner species |
| Ordinary Ursaluna | Exact Ursaring source and a bag Peat Block; explicit item-use equivalent replaces the lunar condition |
| Kingambit | Native owned Bisharp's private evidence of three leader victories, then a stored level above the third-KO floor; no bag item |
| Urshifu styles | Native Kubfu uses a bag Scroll of Darkness for Single Strike (`Urshifu`), or Scroll of Waters for `Urshifu-Rapid-Strike`; consumes one copy |

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

The 14 existing trade-held items support 17 exact transitions through the
[non-transfer evolution equivalent](trade-held-evolution.md). Equip the required
item, then `+evolve <pokemon-id>` without supplying a bag item. Ownership,
canonical placement and bag copies stay unchanged. Ordinary consent trading
does not trigger automatic evolution; this route adds no transfer or trade callback.

For the 14 supported trade-only mappings, use `+evolve <pokemon-id> Link Cord`.
One real bag cord evolves only that Pokemon, preserving its Alolan form or
Pumpkaboo size. Karrablast and Shelmet evolve independently without the other
species. Existing trade-held items require no additional cord. Full mappings,
item availability and preservation rules are in [Link Cord evolution](link-cord-evolution.md).

For ordinary Ursaluna, copy Ursaring's full ID from `+party <slot>` and use
`+evolve <pokemon-id> Peat Block`. PF2 deliberately selects an explicit item-use
equivalent instead of a lunar simulation: it requires no moon/time/region state,
and consumes one real bag item. Held-only copies and arbitrary flags do not
activate it, and Bloodmoon cannot be selected. The bounded rule, opt-in shop
acquisition and preservation limits are in [Peat Block evolution](peat-block-evolution.md).

For Kingambit, the actual native Bisharp must personally finish three qualifying
leader Bisharp in committed NPC/wild victories, then gain a level. Opponent
identity comes from an originally Crest-bearing server encounter that still
holds its Crest at KO. Private durable faint/victory receipts track the actual
owned Pokemon; completion flags, a bag Crest and EXP Share do not grant credit.
`+party <slot>` shows progress; use `+evolve <full-id>` when ready. Your held item
and bag stock are not consumed. See [Kingambit qualification](kingambit-evolution.md)
for PF2's direct-move, native identity, victory and level-trigger limits.

For Kubfu, use `+evolve <full-id> Scroll of Darkness` for Single Strike, or
`+evolve <full-id> Scroll of Waters` for Rapid Strike. The actual bag item selects
the branch; an optional exact target must agree. PF2's functional consumable
Scrolls replace tower completion without requiring plot flags, extra levels or
friendship. Held-only copies and already evolved Urshifu cannot activate the
route. See the [Kubfu item contract](kubfu-evolution.md) for acquisition,
consumption, preservation and form limits.

## Explicitly unsupported

These fail closed, even at level 100 or with a supplied item. Unknown future
`evoType` or `evoCondition` values also fail closed.

| Condition | Reason |
| --- | --- |
| Unlisted `trade` transitions | Only the existing held-item allowlist and the 14 exact Link Cord mappings have direct equivalents; ordinary trades do not trigger evolution |
| Malamar: console upside-down | No PF2 equivalent is defined |
| Sirfetch'd: 3 critical hits in a battle | No persisted evolution counter |
| Runerigus: 49 HP lost and Dusty Bowl sculpture | No persisted journey/damage evidence |
| Wyrdeer/Overqwil: Agile/Strong move uses | No style-use history |
| Basculegion: 294 recoil without fainting | No persisted recoil streak |
| Pawmot/Rabsca/Brambleghast: Let's Go steps | No persisted Let's Go activity |
| Annihilape: Rage Fist uses | No persisted move-use count |
| Shedinja (dex only records a level) | Requires an additional Pokemon, spare party slot, and Poké Ball transaction |
| Palafin (dex only records a level) | No Union Circle equivalent |

Other `other` rules remain unsupported; Milcery's listed Sweet route and the
exact Peat Block, qualified Kingambit, two Kubfu Scroll transitions and the
[999-coin Chest Gimmighoul equivalent](gimmighoul-evolution.md) are
explicit exceptions. No completion flags or command overrides grant eligibility.

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
- `python tests/integration/trade_held_cases.py`, with an explicit test DSN,
  for all 17 existing trade-held mappings, ID discovery/equip/evolve/reload,
  ownership and placement preservation, rollback, retries and competing requests.
- `python tests/integration/link_cord_cases.py`, with an explicit test DSN,
  for all 14 bag-cord mappings, form/size preservation, independent Karrablast
  and Shelmet, guarded failures, rollback and competing final-copy requests.
- `python tests/integration/peat_block_cases.py`, with an explicit test DSN,
  for shop/evolution flow, SQL reload, exact species/form/item restrictions,
  missing/spoofed context, rollback and competing completion/reservation requests.
- Set `PF2_TEST_POSTGRES_DSN` to an expendable test database to also run competing
  evolution/equip/remove requests across independent connections. The harness
  creates and drops only a random test schema and does not run migrations.
- The existing PostgreSQL lifecycle CI runs these integration scripts plus the
  focused evolution/command tests.

The merged workflow retains the battle progression, status, capture, medicine,
nickname/Fusion display and Adventure/gym recovery checks introduced in #721.
The existing evolution/equip suite has 28 real-model PostgreSQL cases, including Black Augurite through
the real command, retries, accented/gender-symbol source names, legacy inventory
aliases and preservation of saved HP, PP, EXP, EVs and major status. The separate
Sweet and trade-held suites extend that coverage as described above.
Disposable-schema tests do not validate a running game or replace live gameplay
acceptance.
